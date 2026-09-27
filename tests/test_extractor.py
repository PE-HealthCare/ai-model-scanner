import unittest
import math
import numpy as np
import torch
from scipy import stats

from src.p1_static_engine.analyzer import extract_features, TrustedModelContext


class MockModel:
    def __init__(self, tensors):
        self.tensors = tensors

    def state_dict(self):
        return self.tensors


class TestExtractor(unittest.TestCase):
    def test_fp32_features(self):
        t1 = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0], dtype=torch.float32)
        t2 = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0], dtype=torch.float32)
        t3 = torch.tensor([10.0, 100.0, -50.0, 0.0, 0.0], dtype=torch.float32)
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        res = extract_features(ctx, "commit123")

        self.assertEqual(res["layer_count"], 3)
        self.assertEqual(res["mock_status"], "VERIFIED-REAL")
        l3_feats = res["static_features"][2]
        self.assertEqual(l3_feats["layer_name"], "l3")
        self.assertEqual(
            list(l3_feats.keys()),
            ["layer_name", "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean", "std", "skewness", "kurtosis", "sparsity", "outlier_pct"],
        )
        self.assertAlmostEqual(l3_feats["sparsity"], 2.0 / 5.0)
        self.assertAlmostEqual(l3_feats["mean"], 12.0)
        self.assertTrue(0 <= l3_feats["outlier_pct"] <= 100)
        self.assertTrue(l3_feats["entropy"] > 0)
        self.assertTrue(l3_feats["ks_stat"] > 0)

    def test_fp16_features(self):
        t1 = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float16)
        t2 = torch.tensor([2.0, 3.0, 4.0], dtype=torch.float16)
        t3 = torch.tensor([10.0, 4.0, -2.0], dtype=torch.float16)
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        res = extract_features(ctx, "commit123")
        self.assertIsNotNone(res["static_features"][0]["entropy"])

    def test_integer_control_tensors_are_excluded(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32),
            "l2": torch.tensor([2.0, 3.0, 4.0], dtype=torch.float32),
            "l3": torch.tensor([10.0, 100.0, -50.0], dtype=torch.float32),
            "batch_norm.num_batches_tracked": torch.tensor(1, dtype=torch.int64),
        }
        res = extract_features(TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False), "commit123")
        self.assertEqual(res["layer_count"], 3)
        self.assertEqual([f["layer_name"] for f in res["static_features"]], ["l1", "l2", "l3"])

    def test_quantized_features_are_ks_only_and_null_not_nan(self):
        t1 = torch.tensor([-4, -2, 0, 2, 4], dtype=torch.int8)
        t2 = torch.tensor([-3, -1, 1, 3, 5], dtype=torch.int8)
        t3 = torch.tensor([10, 20, 30, 40, 50], dtype=torch.int8)
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", True)
        res = extract_features(ctx, "commit123")

        self.assertTrue(res["is_quantized"])
        self.assertEqual(res["layer_count"], 3)
        for feature in res["static_features"]:
            for name in ("entropy", "pov_chi2", "lsb_kl", "mean", "std", "skewness", "kurtosis", "sparsity", "outlier_pct"):
                self.assertIsNone(feature[name])
            self.assertIsInstance(feature["ks_stat"], float)
            self.assertTrue(math.isfinite(feature["ks_stat"]))
            self.assertFalse(any(isinstance(v, float) and math.isnan(v) for v in feature.values()))

    def test_quantized_fp8_values_are_supported_for_ks(self):
        if not hasattr(torch, "float8_e4m3fn"):
            self.skipTest("PyTorch float8 dtype unavailable")
        t1 = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32).to(torch.float8_e4m3fn)
        t2 = torch.tensor([2.0, 3.0, 4.0], dtype=torch.float32).to(torch.float8_e4m3fn)
        t3 = torch.tensor([10.0, 20.0, 30.0], dtype=torch.float32).to(torch.float8_e4m3fn)
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", True)
        res = extract_features(ctx, "commit123")
        self.assertTrue(all(feature["ks_stat"] >= 0 for feature in res["static_features"]))
        self.assertTrue(all(feature["entropy"] is None for feature in res["static_features"]))

    def test_nan_rejection(self):
        t1 = torch.tensor([1.0, float("nan"), 3.0])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        t3 = torch.tensor([10.0, 100.0, -50.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "NaN or Inf"):
            extract_features(ctx, "commit123")

    def test_inf_rejection(self):
        t1 = torch.tensor([1.0, float("inf"), 3.0])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        t3 = torch.tensor([10.0, 100.0, -50.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "NaN or Inf"):
            extract_features(ctx, "commit123")

    def test_empty_tensor(self):
        t1 = torch.tensor([])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        t3 = torch.tensor([10.0, 100.0, -50.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "empty tensor"):
            extract_features(ctx, "commit123")

    def test_insufficient_layers(self):
        t1 = torch.tensor([1.0, 2.0, 3.0])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "insufficient-baseline condition"):
            extract_features(ctx, "commit123")

    def test_constant_tensor(self):
        t1 = torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0])
        t2 = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0])
        t3 = torch.tensor([10.0, 100.0, -50.0, 0.0, 0.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        # Approved decision: derived non-finite statistics fail closed for the
        # whole extraction (l1 is constant -> NaN skew/kurtosis; l2/l3 are
        # valid). One invalid layer must reject the entire extraction rather
        # than silently excluding that layer.
        with self.assertRaisesRegex(ValueError, "Integrity violated: non-finite derived feature"):
            extract_features(ctx, "commit123")

    def test_all_emitted_fp_features_are_finite(self):
        """Approved decision: every emitted FP feature is a finite numeric value."""
        t1 = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0], dtype=torch.float32)
        t2 = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0], dtype=torch.float32)
        t3 = torch.tensor([10.0, 100.0, -50.0, 0.0, 0.0], dtype=torch.float32)
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        for feat in extract_features(ctx, "commit123")["static_features"]:
            for name, value in feat.items():
                if name == "layer_name":
                    continue
                self.assertTrue(math.isfinite(value), f"{name} not finite")


    def test_layer_names_filter_emits_exactly_selected_layers(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32),
            "l2": torch.tensor([2.0, 3.0, 4.0], dtype=torch.float32),
            "l3": torch.tensor([10.0, 100.0, -50.0], dtype=torch.float32),
            "l4": torch.tensor([-8.0, 6.0, 7.0], dtype=torch.float32),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        res = extract_features(ctx, "commit123", layer_names=["l3", "l1", "l4"])

        self.assertEqual(
            [feature["layer_name"] for feature in res["static_features"]],
            ["l3", "l1", "l4"],
        )
        self.assertEqual(res["layer_count"], 3)

    def test_layer_names_filter_layer_count_matches_selection(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0]),
            "l2": torch.tensor([2.0, 3.0, 4.0]),
            "l3": torch.tensor([10.0, 100.0, -50.0]),
            "l4": torch.tensor([-8.0, 6.0, 7.0]),
            "l5": torch.tensor([11.0, 12.0, 13.0]),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        res = extract_features(
            ctx,
            "commit123",
            layer_names=["l1", "l3", "l5", "l2"],
        )

        self.assertEqual(res["layer_count"], 4)
        self.assertEqual(len(res["static_features"]), 4)

    def test_layer_names_filter_unknown_layer_fails_closed(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0]),
            "l2": torch.tensor([2.0, 3.0, 4.0]),
            "l3": torch.tensor([10.0, 100.0, -50.0]),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        with self.assertRaisesRegex(ValueError, "unknown layer requested"):
            extract_features(
                ctx,
                "commit123",
                layer_names=["l1", "l2", "missing"],
            )

    def test_layer_names_filter_fewer_than_three_fails_closed(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0]),
            "l2": torch.tensor([2.0, 3.0, 4.0]),
            "l3": torch.tensor([10.0, 100.0, -50.0]),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        with self.assertRaisesRegex(ValueError, "at least 3 layers"):
            extract_features(
                ctx,
                "commit123",
                layer_names=["l1", "l2"],
            )

    def test_layer_names_filter_empty_selection_fails_closed(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0]),
            "l2": torch.tensor([2.0, 3.0, 4.0]),
            "l3": torch.tensor([10.0, 100.0, -50.0]),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        with self.assertRaisesRegex(ValueError, "layer_names filter must be non-empty"):
            extract_features(ctx, "commit123", layer_names=[])

    def test_layer_names_filter_ks_reference_remains_full_model(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32),
            "l2": torch.tensor([2.0, 3.0, 4.0], dtype=torch.float32),
            "l3": torch.tensor([10.0, 100.0, -50.0], dtype=torch.float32),
            "l4": torch.tensor([1000.0, 1001.0, 1002.0], dtype=torch.float32),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        filtered = extract_features(
            ctx,
            "commit123",
            layer_names=["l1", "l2", "l3"],
        )
        l1_filtered = next(
            row for row in filtered["static_features"]
            if row["layer_name"] == "l1"
        )

        selected = tensors["l1"].numpy()
        full_reference = np.concatenate([
            tensors["l2"].numpy(),
            tensors["l3"].numpy(),
            tensors["l4"].numpy(),
        ])
        expected_full_model_ks = float(
            stats.ks_2samp(selected, full_reference).statistic
        )

        self.assertAlmostEqual(
            l1_filtered["ks_stat"],
            expected_full_model_ks,
        )

    def test_omitting_layer_names_preserves_full_model_behavior(self):
        tensors = {
            "l1": torch.tensor([1.0, 2.0, 3.0], dtype=torch.float32),
            "l2": torch.tensor([2.0, 3.0, 4.0], dtype=torch.float32),
            "l3": torch.tensor([10.0, 100.0, -50.0], dtype=torch.float32),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)

        implicit = extract_features(ctx, "commit123")
        explicit = extract_features(
            ctx,
            "commit123",
            layer_names=["l1", "l2", "l3"],
        )

        self.assertEqual(implicit, explicit)
if __name__ == "__main__":
    unittest.main()
