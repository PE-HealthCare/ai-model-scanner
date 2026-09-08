import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import torch
from safetensors.torch import save_file

from src.p1_static_engine import analyzer

class TestZeroTrustIntake(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def test_valid_safetensors_intake(self):
        path = self.test_dir / "valid.safetensors"
        save_file({"tensor1": torch.zeros(2, 2)}, path, metadata={"author": "test"})
        analyzer.intake_model(path)

    def test_no_metadata(self):
        path = self.test_dir / "no_meta.safetensors"
        save_file({"tensor1": torch.zeros(2, 2)}, path)
        analyzer.intake_model(path)

    def test_malformed_safetensors(self):
        path = self.test_dir / "malformed.safetensors"
        with open(path, "wb") as f:
            f.write(struct.pack("<Q", 10)) # Valid header size
            f.write(b"NOT_A_JSON")
        with self.assertRaisesRegex(ValueError, "Integrity violated: malformed SafeTensors file"):
            analyzer.intake_model(path)
            
    def test_file_too_small(self):
        path = self.test_dir / "small.safetensors"
        with open(path, "wb") as f:
            f.write(b"tiny")
        with self.assertRaisesRegex(ValueError, "Integrity violated: file too small"):
            analyzer.intake_model(path)

    @patch("src.p1_static_engine.analyzer.MAX_FILE_SIZE", 50)
    def test_file_size_limit(self):
        path = self.test_dir / "large_file.safetensors"
        with open(path, "wb") as f:
            f.write(b"0" * 100)
        with self.assertRaisesRegex(ValueError, "Limit violated: file size"):
            analyzer.intake_model(path)

    @patch("src.p1_static_engine.analyzer.safe_open")
    def test_header_size_limit_exact(self, mock_safe_open):
        path = self.test_dir / "exact_header.safetensors"
        with open(path, "wb") as f:
            f.write(struct.pack("<Q", 5 * 1024 * 1024)) # exactly 5 MB
            f.write(b"0" * 10)
        
        # We expect it to reach safe_open. Since we mock safe_open, it won't actually parse the invalid "0"*10 header.
        # But we still need to catch any Exception that might occur after safe_open if our mock returns a mock object.
        # safe_open returns a context manager, so mock it properly:
        mock_st = MagicMock()
        mock_st.metadata.return_value = {}
        mock_st.keys.return_value = ["t1"]
        mock_st.get_slice.return_value.get_shape.return_value = [1]
        mock_safe_open.return_value.__enter__.return_value = mock_st
        
        analyzer.intake_model(path)
        mock_safe_open.assert_called_once()

    @patch("src.p1_static_engine.analyzer.safe_open")
    def test_header_size_limit(self, mock_safe_open):
        path = self.test_dir / "large_header.safetensors"
        with open(path, "wb") as f:
            f.write(struct.pack("<Q", 6 * 1024 * 1024)) # 6 MB (over 5 MB limit)
            f.write(b"0" * 10)
        with self.assertRaisesRegex(ValueError, "Limit violated: header size"):
            analyzer.intake_model(path)
        mock_safe_open.assert_not_called()

    @patch("src.p1_static_engine.analyzer.MAX_METADATA_SIZE", 50)
    def test_metadata_size_limit(self):
        path = self.test_dir / "large_metadata.safetensors"
        save_file({"t": torch.zeros(1)}, path, metadata={"long_key": "x" * 100})
        with self.assertRaisesRegex(ValueError, "Limit violated: metadata size"):
            analyzer.intake_model(path)

    @patch("src.p1_static_engine.analyzer.MAX_TENSORS", 2)
    def test_tensor_count_limit(self):
        path = self.test_dir / "many_tensors.safetensors"
        save_file({"t1": torch.zeros(1), "t2": torch.zeros(1), "t3": torch.zeros(1)}, path)
        with self.assertRaisesRegex(ValueError, "Limit violated: tensor count"):
            analyzer.intake_model(path)

    @patch("src.p1_static_engine.analyzer.MAX_RANK", 2)
    def test_rank_limit(self):
        path = self.test_dir / "high_rank.safetensors"
        save_file({"t": torch.zeros(1, 1, 1)}, path)
        with self.assertRaisesRegex(ValueError, "Limit violated: tensor 't' rank"):
            analyzer.intake_model(path)

    @patch("src.p1_static_engine.analyzer.MAX_DIMENSION", 10)
    def test_dimension_limit(self):
        path = self.test_dir / "large_dim.safetensors"
        save_file({"t": torch.zeros(2, 15)}, path)
        with self.assertRaisesRegex(ValueError, "Limit violated: tensor 't' dimension"):
            analyzer.intake_model(path)

if __name__ == "__main__":
    unittest.main()
