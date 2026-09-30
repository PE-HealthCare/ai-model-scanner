import unittest
import math
import numpy as np
import torch
from scipy import stats

from src.common.feature_names import B0_FEATURE_NAMES, B1_ADDITIONAL_FEATURE_NAMES, B1_FEATURE_NAMES, feature_vector

from src.p1_static_engine.analyzer import _b1_features, _ks_stat_against_global, extract_features, TrustedModelContext


class MockModel:
    def __init__(self, tensors):
        self.tensors = tensors

    def state_dict(self):
        return self.tensors


class TestExtractor(unittest.TestCase):
    def test_reused_global_ks_matches_scipy(self):
        rng = np.random.default_rng(20260929)
        cases = {
            "ordinary_random": (rng.normal(size=31), rng.normal(size=47)),
            "unequal_sizes": (rng.normal(size=5), rng.normal(size=101)),
            "ties": (np.array([0., 0., 1., 1., 2., 2.]), np.array([0., 1., 1., 2., 2., 2., 3.])),
            "identical": (np.array([0., 1., 1., 2.]), np.array([0., 1., 1., 2.])),
            "separated": (np.array([-4., -3., -2.]), np.array([4., 5., 6., 7.])),
        }
        for name, (layer, other) in cases.items():
            with self.subTest(name=name):
                expected = float(stats.ks_2samp(layer, other).statistic)
                actual = _ks_stat_against_global(layer, np.sort(np.concatenate([layer, other])))
                self.assertAlmostEqual(actual, expected, places=15)

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

    def test_negative_inf_rejection(self):
        t1 = torch.tensor([1.0, float("-inf"), 3.0])
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

    def test_distributional_moments_use_float64_working_precision(self):
        """Finite extreme FP32 values retain the existing biased Pearson moments."""
        extreme = np.array([3.6060023149192806e18, 2.499744005035609e-05], dtype=np.float32)
        ordinary = np.array([1.0, 2.5, -3.0, 4.0, 8.0], dtype=np.float32)
        fp16 = np.array([-2.0, -0.5, 1.0, 3.0, 6.0], dtype=np.float16)
        near_constant = np.array([1.0, 1.0, 1.0, np.nextafter(np.float32(1.0), np.float32(2.0))], dtype=np.float32)
        ctx = TrustedModelContext(
            MockModel({
                "extreme": torch.from_numpy(extreme),
                "ordinary": torch.from_numpy(ordinary),
                "fp16": torch.from_numpy(fp16),
                "near_constant": torch.from_numpy(near_constant),
            }),
            "resnet18", "VISION", False,
        )
        rows = {row["layer_name"]: row for row in extract_features(ctx, "commit123", feature_set="b1")["static_features"]}

        expected_skew = float(stats.skew(extreme.astype(np.float64), bias=True))
        expected_kurtosis = float(stats.kurtosis(extreme.astype(np.float64), fisher=False, bias=True))
        self.assertFalse(np.all(extreme == extreme[0]))
        self.assertTrue(math.isfinite(rows["extreme"]["skewness"]))
        self.assertTrue(math.isfinite(rows["extreme"]["kurtosis"]))
        self.assertAlmostEqual(rows["extreme"]["skewness"], expected_skew, places=14)
        self.assertAlmostEqual(rows["extreme"]["kurtosis"], expected_kurtosis, places=14)

        # Ordinary values retain the existing FP32 calculation within tight
        # numerical tolerance while FP16 and near-constant values remain real
        # (not imputed) finite statistics.
        self.assertAlmostEqual(rows["ordinary"]["skewness"], float(stats.skew(ordinary, bias=True)), places=6)
        self.assertAlmostEqual(rows["ordinary"]["kurtosis"], float(stats.kurtosis(ordinary, fisher=False, bias=True)), places=6)
        for name in ("ordinary", "fp16", "near_constant"):
            self.assertTrue(math.isfinite(rows[name]["skewness"]))
            self.assertTrue(math.isfinite(rows[name]["kurtosis"]))
            self.assertTrue(all(math.isfinite(rows[name][feature]) for feature in B1_FEATURE_NAMES))

    def test_b1_names_interface_determinism_and_finiteness(self):
        tensors = {
            "l1": torch.tensor([-5., -2., 1., 3., 9.], dtype=torch.float32),
            "l2": torch.tensor([-4., -1., 2., 4., 10.], dtype=torch.float32),
            "l3": torch.tensor([-3., 0.5, 3., 5., 11.], dtype=torch.float32),
        }
        ctx = TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False)
        first = extract_features(ctx, "commit123", feature_set="b1")
        second = extract_features(ctx, "commit123", feature_set="b1")
        self.assertEqual(first, second)
        self.assertEqual(first["feature_set"], "B1")
        row = first["static_features"][0]
        self.assertEqual(list(row.keys()), ["layer_name", *B1_FEATURE_NAMES])
        self.assertEqual(feature_vector(row), [row[name] for name in B0_FEATURE_NAMES])
        self.assertEqual(feature_vector(row, feature_set="b1"), [row[name] for name in B1_FEATURE_NAMES])
        self.assertTrue(all(math.isfinite(row[name]) for name in B1_FEATURE_NAMES))

    def test_b1_distribution_and_finite_cv_policy(self):
        tensors = {
            "l1": torch.tensor([1., 2., 3., 4., 5.], dtype=torch.float32),
            "l2": torch.tensor([2., 3., 4., 5., 6.], dtype=torch.float32),
            "l3": torch.tensor([3., 4., 5., 6., 7.], dtype=torch.float32),
        }
        row = extract_features(TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False), "commit123", feature_set="b1")["static_features"][0]
        self.assertAlmostEqual(row["q01"], 1.04)
        self.assertAlmostEqual(row["q50"], 3.0)
        self.assertAlmostEqual(row["iqr"], 2.0)
        expected_std = math.sqrt(2)
        self.assertAlmostEqual(row["coefficient_of_variation"], expected_std / (3 + expected_std))

        # CV is explicitly bounded relative dispersion, not an epsilon-clamped
        # ordinary CV: std / (abs(mean) + std), with constant tensors at 0.
        cases = {
            "zero_mean": np.array([-2., -1., 1., 2.], dtype=np.float32),
            "near_zero_mean": np.array([-1e-15, 1e-15, 2e-15], dtype=np.float32),
            "constant": np.full(8, 7.0, dtype=np.float32),
        }
        results = {name: _b1_features(values)["coefficient_of_variation"] for name, values in cases.items()}
        self.assertAlmostEqual(results["zero_mean"], 1.0)
        self.assertTrue(0.0 < results["near_zero_mean"] <= 1.0)
        self.assertEqual(results["constant"], 0.0)
        self.assertEqual(results, {name: _b1_features(values)["coefficient_of_variation"] for name, values in cases.items()})
        self.assertTrue(all(math.isfinite(value) for value in results.values()))

    def test_b1_fp_bits_and_local_kl_use_tensor_reference(self):
        # The first layer has a negative value and deterministic FP32 bit order.
        tensors = {
            "l1": torch.tensor([-1., 1., 2., 3.], dtype=torch.float32),
            "l2": torch.tensor([2., 3., 4., 5.], dtype=torch.float32),
            "l3": torch.tensor([3., 4., 5., 6.], dtype=torch.float32),
        }
        row = extract_features(TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False), "commit123", feature_set="b1")["static_features"][0]
        self.assertAlmostEqual(row["sign_bit_fraction"], 0.25)
        self.assertGreaterEqual(row["mantissa_lsb_imbalance"], 0.0)
        self.assertLessEqual(row["low_bit_transition_rate"], 1.0)
        # One deterministic window has its own complete tensor-wide reference,
        # so its KL is exactly zero rather than a cross-model comparison.
        self.assertAlmostEqual(row["local_byte_kl_mean"], 0.0)

        # Two byte windows prove the reference is this tensor's full-byte
        # distribution, not another layer or an external model population.
        large_l1 = torch.linspace(1.0, 2.0, 2048, dtype=torch.float32)
        large = {"l1": large_l1, "l2": torch.linspace(2.0, 3.0, 2048), "l3": torch.linspace(3.0, 4.0, 2048)}
        large_row = extract_features(TrustedModelContext(MockModel(large), "resnet18", "VISION", False), "commit123", feature_set="b1")["static_features"][0]
        byte_values = large_l1.numpy().view(np.uint8)
        global_p = np.bincount(byte_values, minlength=256) / byte_values.size
        expected_kl = []
        for chunk in np.array_split(byte_values, 2):
            p = np.bincount(chunk, minlength=256) / chunk.size
            present = p > 0
            expected_kl.append(float(np.sum(p[present] * np.log(p[present] / global_p[present]))))
        self.assertAlmostEqual(large_row["local_byte_kl_mean"], float(np.mean(expected_kl)))

    def test_b1_fp16_and_quantized_gate(self):
        tensors = {
            "l1": torch.tensor([1., 2., 3.], dtype=torch.float16),
            "l2": torch.tensor([2., 3., 4.], dtype=torch.float16),
            "l3": torch.tensor([3., 4., 5.], dtype=torch.float16),
        }
        result = extract_features(TrustedModelContext(MockModel(tensors), "resnet18", "VISION", False), "commit123", feature_set="b1")
        self.assertTrue(all(math.isfinite(row["exponent_mean"]) for row in result["static_features"]))
        ints = {name: tensor.to(torch.int8) for name, tensor in tensors.items()}
        with self.assertRaisesRegex(ValueError, "B1 is supported only"):
            extract_features(TrustedModelContext(MockModel(ints), "resnet18", "VISION", True), "commit123", feature_set="b1")


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
