"""Unit tests for deterministic Natural-Language TreeSHAP explanation layer (Sub-step 4)."""

import re
import unittest

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.tree_shap_explainer import (
    FeatureAttributionExplanation,
    TreeSHAPSummary,
    explain_shap_attributions,
)


class TestTreeSHAPExplainer(unittest.TestCase):
    """Test suite verifying fail-closed validation, canonical ranking, and approved wording."""

    def setUp(self):
        self.sample_fp_attributions = {
            "entropy": 0.0940,
            "pov_chi2": 0.1803,
            "lsb_kl": 1.5662,
            "ks_stat": 0.4708,
            "mean": 0.0683,
            "std": -0.6195,
            "skewness": 0.0613,
            "kurtosis": 0.6826,
            "sparsity": 0.5427,
            "outlier_pct": -0.2133,
        }

    # -------------------------------------------------------------------------
    # 1. Input Validation & Fail-Closed
    # -------------------------------------------------------------------------

    def test_missing_canonical_feature_raises(self):
        bad = dict(self.sample_fp_attributions)
        del bad["entropy"]
        with self.assertRaisesRegex(ValueError, "Missing: .*entropy"):
            explain_shap_attributions(bad)

    def test_unexpected_feature_raises(self):
        bad = dict(self.sample_fp_attributions)
        bad["unexpected_field"] = 0.5
        with self.assertRaisesRegex(ValueError, "Unexpected: .*unexpected_field"):
            explain_shap_attributions(bad)

    def test_non_finite_values_raise(self):
        for bad_val in [float("nan"), float("inf"), float("-inf")]:
            bad = dict(self.sample_fp_attributions)
            bad["entropy"] = bad_val
            with self.assertRaisesRegex(ValueError, "finite"):
                explain_shap_attributions(bad)

    def test_non_numeric_and_bool_values_raise(self):
        bad = dict(self.sample_fp_attributions)
        bad["entropy"] = "0.5"
        with self.assertRaisesRegex(ValueError, "numeric"):
            explain_shap_attributions(bad)

        bad2 = dict(self.sample_fp_attributions)
        bad2["entropy"] = True
        with self.assertRaisesRegex(ValueError, "numeric"):
            explain_shap_attributions(bad2)

    def test_empty_mapping_raises(self):
        with self.assertRaisesRegex(ValueError, "non-empty mapping"):
            explain_shap_attributions({})

    def test_top_n_validation(self):
        for invalid_top_n in [0, -1, -5, "3", True, 2.5]:
            with self.assertRaises(ValueError):
                explain_shap_attributions(self.sample_fp_attributions, top_n=invalid_top_n)

    # -------------------------------------------------------------------------
    # 2. Quantized Path
    # -------------------------------------------------------------------------

    def test_quantized_path_success(self):
        q_attrs = {"ks_stat": 0.85}
        res = explain_shap_attributions(q_attrs, is_quantized=True)
        self.assertTrue(res.is_quantized)
        self.assertFalse(res.all_zero)
        self.assertEqual(len(res.attributions), 1)
        self.assertEqual(res.attributions[0].feature_name, "ks_stat")
        self.assertEqual(res.attributions[0].direction, "POSITIVE")
        self.assertIn("ks_stat", res.summary_text)
        self.assertIn("Layer KS-Distance", res.summary_text)
        self.assertIn("classifierâ€™s positive class relative to the model baseline", res.summary_text)

    def test_quantized_path_negative_shap(self):
        q_attrs = {"ks_stat": -0.42}
        res = explain_shap_attributions(q_attrs, is_quantized=True)
        self.assertEqual(res.attributions[0].direction, "NEGATIVE")
        self.assertIn("classifierâ€™s negative/clean class relative to the model baseline", res.summary_text)

    def test_quantized_path_rejects_extra_fp_keys(self):
        bad = {"ks_stat": 0.5, "entropy": 0.1}
        with self.assertRaisesRegex(ValueError, "Quantized shap_attributions keys must be exactly"):
            explain_shap_attributions(bad, is_quantized=True)

    def test_fp_path_rejects_quantized_payload(self):
        q_attrs = {"ks_stat": 0.5}
        with self.assertRaisesRegex(ValueError, "Missing:"):
            explain_shap_attributions(q_attrs, is_quantized=False)

    # -------------------------------------------------------------------------
    # 3. Deterministic Ranking & Tie-Breaking
    # -------------------------------------------------------------------------

    def test_ranking_by_descending_abs_magnitude(self):
        # lsb_kl (|1.5662|) > kurtosis (|0.6826|) > std (|-0.6195|) > sparsity (|0.5427|)
        res = explain_shap_attributions(self.sample_fp_attributions)
        names = [a.feature_name for a in res.attributions]
        self.assertEqual(names[0], "lsb_kl")
        self.assertEqual(names[1], "kurtosis")
        self.assertEqual(names[2], "std")
        self.assertEqual(names[3], "sparsity")

    def test_deterministic_tie_breaking_by_canonical_order(self):
        tied = {name: 0.1 for name in FEATURE_NAMES}
        tied["entropy"] = -0.5
        tied["pov_chi2"] = 0.5
        tied["std"] = 0.5

        res = explain_shap_attributions(tied)
        top3_names = [a.feature_name for a in res.attributions[:3]]
        self.assertEqual(top3_names, ["entropy", "pov_chi2", "std"])

    # -------------------------------------------------------------------------
    # 4. Zero & Baseline Handling
    # -------------------------------------------------------------------------

    def test_all_zero_attributions(self):
        all_zeros = {name: 0.0 for name in FEATURE_NAMES}
        res = explain_shap_attributions(all_zeros)
        self.assertTrue(res.all_zero)
        self.assertEqual(len(res.attributions), 0)
        self.assertIn("All feature attributions are zero", res.summary_text)
        self.assertIn("baseline expected value", res.summary_text)

    def test_zero_attribution_features_excluded_from_drivers(self):
        sparse = {name: 0.0 for name in FEATURE_NAMES}
        sparse["entropy"] = 0.3
        sparse["std"] = -0.4
        res = explain_shap_attributions(sparse)
        self.assertEqual(len(res.attributions), 2)
        self.assertEqual([a.feature_name for a in res.attributions], ["std", "entropy"])

    # -------------------------------------------------------------------------
    # 5. Language & Forbidden Claim Prohibitions
    # -------------------------------------------------------------------------

    def test_prohibited_terminology_never_appears(self):
        res_fp = explain_shap_attributions(self.sample_fp_attributions)
        res_q = explain_shap_attributions({"ks_stat": 0.7}, is_quantized=True)
        res_zero = explain_shap_attributions({name: 0.0 for name in FEATURE_NAMES})

        all_texts = [
            res_fp.summary_text,
            *[a.explanation for a in res_fp.attributions],
            res_q.summary_text,
            *[a.explanation for a in res_q.attributions],
            res_zero.summary_text,
        ]

        prohibited_patterns = [
            r"\btampered\b",
            r"\btampered class\b",
            r"\bmalicious\b",
            r"\bmalware\b",
            r"\bbackdoor\b",
            r"\battacker\b",
            r"\bhighest-risk layer\b",
            r"\bprobability\b",
            r"\banomaly score\b",
        ]

        for text in all_texts:
            for pat in prohibited_patterns:
                self.assertIsNone(
                    re.search(pat, text, re.IGNORECASE),
                    f"Prohibited pattern {pat!r} found in text: {text!r}",
                )

    def test_exact_approved_phrasing_present(self):
        res = explain_shap_attributions(self.sample_fp_attributions)
        positive_expl = [a.explanation for a in res.attributions if a.direction == "POSITIVE"]
        negative_expl = [a.explanation for a in res.attributions if a.direction == "NEGATIVE"]

        self.assertTrue(len(positive_expl) > 0)
        self.assertTrue(len(negative_expl) > 0)

        for text in positive_expl:
            self.assertIn("toward the classifierâ€™s positive class relative to the model baseline", text)

        for text in negative_expl:
            self.assertIn("toward the classifierâ€™s negative/clean class relative to the model baseline", text)


    def test_summary_highlights_strongest_positive_and_negative_drivers(self):
        # sample_fp_attributions has 8 positive features (max is lsb_kl: 1.5662)
        # and 2 negative features (std: -0.6195, outlier_pct: -0.2133; max neg magnitude is std: |-0.6195|)
        res = explain_shap_attributions(self.sample_fp_attributions)
        # Strongest positive driver is LSB KL-Divergence; strongest negative is Weight Std-Dev
        self.assertIn("Top positive attribution factor(s) shifting the score toward the classifierâ€™s positive class relative to the model baseline: LSB KL-Divergence", res.summary_text)
        self.assertIn("Top negative attribution factor(s) shifting the score toward the classifierâ€™s negative/clean class relative to the model baseline: Weight Std-Dev", res.summary_text)
        # Lower magnitude drivers must not appear in the top drivers summary
        self.assertNotIn("Byte Entropy", res.summary_text)
        self.assertNotIn("Tukey Outlier Pct", res.summary_text)

    def test_summary_handles_ties_for_strongest_driver_in_canonical_order(self):
        # Tie at max positive attribution between entropy (canonical 0) and pov_chi2 (canonical 1)
        tied = {name: 0.1 for name in FEATURE_NAMES}
        tied["entropy"] = 0.8
        tied["pov_chi2"] = 0.8
        tied["std"] = -0.5
        tied["skewness"] = -0.5  # tie at max negative magnitude between std (5) and skewness (6)
        res = explain_shap_attributions(tied)
        self.assertIn("Byte Entropy, LSB Chi-Square", res.summary_text)
        self.assertIn("Weight Std-Dev, Weight Skewness", res.summary_text)

    def test_underlying_attributions_retains_complete_ranked_set(self):
        # Even though summary highlights only the strongest positive/negative drivers,
        # res.attributions must retain the full set of non-zero feature explanations
        res = explain_shap_attributions(self.sample_fp_attributions)
        self.assertEqual(len(res.attributions), 10)
        self.assertEqual(res.attributions[0].feature_name, "lsb_kl")
        self.assertEqual(res.attributions[0].ui_label, "LSB KL-Divergence")
        # Verify all 10 features are represented in descending |SHAP| order
        magnitudes = [a.abs_shap_value for a in res.attributions]
        self.assertEqual(magnitudes, sorted(magnitudes, reverse=True))

if __name__ == "__main__":
    unittest.main()
