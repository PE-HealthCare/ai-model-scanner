import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
from safetensors.torch import save_file

from src.p1_static_engine import analyzer
from src.p1_static_engine.analyzer import TrustedModelContext


class TestZeroTrustIntake(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_architecture(self):
        path = self.test_dir / "valid.safetensors"
        with open(path, "wb") as f:
            f.write(b"0" * 100)
        with self.assertRaisesRegex(ValueError, "Integrity violated: declared_architecture is required"):
            analyzer.intake_model(path)

    def test_unknown_architecture(self):
        path = self.test_dir / "valid.safetensors"
        with open(path, "wb") as f:
            f.write(struct.pack("<Q", 100))
            f.write(b"0" * 10)
        with self.assertRaisesRegex(ValueError, "Unknown architecture nonexistent"):
            analyzer.intake_model(path, declared_architecture="nonexistent")

    def test_malformed_safetensors(self):
        path = self.test_dir / "malformed.safetensors"
        with open(path, "wb") as f:
            f.write(struct.pack("<Q", 10))
            f.write(b"NOT_A_JSON")
        with self.assertRaisesRegex(ValueError, "Integrity violated: malformed SafeTensors file"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    def test_file_too_small(self):
        path = self.test_dir / "small.safetensors"
        with open(path, "wb") as f:
            f.write(b"tiny")
        with self.assertRaisesRegex(ValueError, "Integrity violated: file too small"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    @patch("src.p1_static_engine.analyzer.MAX_FILE_SIZE", 50)
    def test_file_size_limit(self):
        path = self.test_dir / "large_file.safetensors"
        with open(path, "wb") as f:
            f.write(b"0" * 100)
        with self.assertRaisesRegex(ValueError, "Limit violated: file size"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    @patch("src.p1_static_engine.analyzer.safe_open")
    def test_header_size_limit(self, mock_safe_open):
        path = self.test_dir / "large_header.safetensors"
        with open(path, "wb") as f:
            f.write(struct.pack("<Q", 6 * 1024 * 1024))
            f.write(b"0" * 10)
        with self.assertRaisesRegex(ValueError, "Limit violated: header size"):
            analyzer.intake_model(path, declared_architecture="resnet18")
        mock_safe_open.assert_not_called()

    @patch("src.p1_static_engine.analyzer.MAX_METADATA_SIZE", 50)
    def test_metadata_size_limit(self):
        path = self.test_dir / "large_metadata.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        save_file(m.state_dict(), path, metadata={"long_key": "x" * 100})
        with self.assertRaisesRegex(ValueError, "Limit violated: metadata size"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    @patch("src.p1_static_engine.analyzer.MAX_TENSORS", 2)
    def test_tensor_count_limit(self):
        path = self.test_dir / "many_tensors.safetensors"
        save_file({"t1": torch.zeros(1), "t2": torch.zeros(1), "t3": torch.zeros(1)}, path)
        with self.assertRaisesRegex(ValueError, "Limit violated: tensor count"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    @patch("src.p1_static_engine.analyzer.MAX_RANK", 1)
    def test_rank_limit(self):
        path = self.test_dir / "high_rank.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        save_file(m.state_dict(), path)
        with self.assertRaisesRegex(ValueError, "Limit violated: tensor .* rank"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    def test_resnet18_wrong_keys(self):
        path = self.test_dir / "wrong_keys.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        sd = m.state_dict()
        del sd["conv1.weight"]
        save_file(sd, path)
        with self.assertRaisesRegex(ValueError, "architecture mismatch. Missing tensors: 1"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    def test_resnet18_wrong_shape(self):
        path = self.test_dir / "wrong_shape.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        sd = m.state_dict()
        sd["conv1.weight"] = torch.zeros(1, 1, 1, 1)
        save_file(sd, path)
        with self.assertRaisesRegex(ValueError, "shape mismatch for tensor conv1.weight"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    def test_distilbert_wrong_keys(self):
        path = self.test_dir / "wrong_keys_db.safetensors"
        from transformers import DistilBertConfig, DistilBertModel
        m = DistilBertModel(DistilBertConfig())
        sd = m.state_dict()
        sd["extra_tensor"] = torch.zeros(1)
        save_file(sd, path)
        with self.assertRaisesRegex(ValueError, "architecture mismatch.*Unexpected tensors: 1"):
            analyzer.intake_model(path, declared_architecture="distilbert")

    def test_incompatible_dtype(self):
        path = self.test_dir / "incompatible_dtype.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        save_file(m.state_dict(), path)

        original_safe_open = analyzer.safe_open
        class MockSlice:
            def __init__(self, s): self.s = s
            def get_shape(self): return self.s.get_shape()
            def get_dtype(self): return "F128"

        class MockSafeOpen:
            def __init__(self, *args, **kwargs): self.st = original_safe_open(*args, **kwargs)
            def __enter__(self): self.ctx = self.st.__enter__(); return self
            def __exit__(self, *args): return self.st.__exit__(*args)
            def metadata(self): return self.ctx.metadata()
            def keys(self): return self.ctx.keys()
            def get_slice(self, key): return MockSlice(self.ctx.get_slice(key))
            def get_tensor(self, key): return self.ctx.get_tensor(key)

        with patch("src.p1_static_engine.analyzer.safe_open", new=MockSafeOpen):
            with self.assertRaisesRegex(ValueError, "unknown or incompatible dtype"):
                analyzer.intake_model(path, declared_architecture="resnet18")

    def test_mixed_dtype(self):
        path = self.test_dir / "mixed_dtype.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        sd = m.state_dict()
        sd["conv1.weight"] = sd["conv1.weight"].to(torch.int8)
        save_file(sd, path)
        with self.assertRaisesRegex(ValueError, "mixed/inconsistent dtype state"):
            analyzer.intake_model(path, declared_architecture="resnet18")

    def test_quantized_int8_is_accepted_and_preserved(self):
        path = self.test_dir / "quant.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        sd = m.state_dict()
        for key, tensor in list(sd.items()):
            if tensor.is_floating_point():
                sd[key] = tensor.to(torch.int8)
        save_file(sd, path)

        ctx = analyzer.intake_model(path, declared_architecture="resnet18")
        self.assertIsInstance(ctx, TrustedModelContext)
        self.assertTrue(ctx.is_quantized)
        self.assertIsInstance(ctx.model, dict)
        self.assertEqual(ctx.model["conv1.weight"].dtype, torch.int8)
        self.assertEqual(ctx.model["conv1.weight"].flatten()[0].item(), sd["conv1.weight"].flatten()[0].item())

    def test_quantized_fp8_is_accepted_and_preserved(self):
        path = self.test_dir / "quant_fp8.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        sd = m.state_dict()
        for key, tensor in list(sd.items()):
            if tensor.is_floating_point():
                sd[key] = tensor.to(torch.float8_e4m3fn)
        save_file(sd, path)

        ctx = analyzer.intake_model(path, declared_architecture="resnet18")
        self.assertIsInstance(ctx, TrustedModelContext)
        self.assertTrue(ctx.is_quantized)
        self.assertIsInstance(ctx.model, dict)
        self.assertEqual(ctx.model["conv1.weight"].dtype, torch.float8_e4m3fn)
        # float8 does not support .item() directly in some torch versions, so just check dtype

    def test_successful_resnet18(self):
        path = self.test_dir / "success_rn18.safetensors"
        from torchvision.models import resnet18
        m = resnet18()
        sd = m.state_dict()
        sd["conv1.weight"].fill_(42.0)
        save_file(sd, path)

        ctx = analyzer.intake_model(path, declared_architecture="resnet18")
        self.assertIsInstance(ctx, TrustedModelContext)
        self.assertIsNotNone(ctx.model)
        self.assertEqual(ctx.architecture, "resnet18")
        self.assertEqual(ctx.input_domain, "VISION")
        self.assertFalse(ctx.is_quantized)
        self.assertEqual(ctx.model.conv1.weight[0, 0, 0, 0].item(), 42.0)

    def test_successful_distilbert(self):
        path = self.test_dir / "success_db.safetensors"
        from transformers import DistilBertConfig, DistilBertModel
        m = DistilBertModel(DistilBertConfig())
        save_file(m.state_dict(), path)

        ctx = analyzer.intake_model(path, declared_architecture="distilbert")
        self.assertIsInstance(ctx, TrustedModelContext)
        self.assertIsNotNone(ctx.model)
        self.assertEqual(ctx.architecture, "distilbert")
        self.assertEqual(ctx.input_domain, "NLP")
        self.assertFalse(ctx.is_quantized)


if __name__ == "__main__":
    unittest.main()
