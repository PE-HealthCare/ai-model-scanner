"""Focused tests for the minimal P3 TreeSHAP presentation layer (Sub-step 6)."""

import unittest

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.report import format_treemap_section


def _fp_payload(**overrides):
    base = {
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
    payload = {
        "producer": "P3",
        "p_tamper": 0.88,
        "shap_attributions": base,
        "model_version": "lightgbm-phase4-final",
    }
    payload.update(overrides)
    return payload


class TestP3Report(unittest.TestCase):
    def test_fp_section_contains_summary_and_ranked_attributions(self):
        text = format_treemap_section(_fp_payload())
        self.assertIn("P3 TreeSHAP attribution (classifier evidence only)", text)
        self.assertIn("p_tamper (model-level classifier score): 0.8800", text)
        self.assertIn("Summary:", text)
        self.assertIn("Ranked attributions:", text)
        # Strongest positive/negative drivers surface in the summary.
        self.assertIn("LSB KL-Divergence", text)
        self.assertIn("Weight Std-Dev", text)
        # Every canonical feature appears exactly once in the ranked list.
        for name in FEATURE_NAMES:
            self.assertIn(f"({name})", text)

    def test_top_n_bounds_ranked_list_but_keeps_summary(self):
        text = format_treemap_section(_fp_payload(), top_n=2)
        self.assertIn("Summary:", text)
        self.assertIn("  1. ", text)
        self.assertIn("  2. ", text)
        self.assertNotIn("  3. ", text)

    def test_quantized_section_is_ks_stat_only(self):
        payload = {
            "p_tamper": 0.42,
            "shap_attributions": {"ks_stat": 0.75},
            "model_version": "lightgbm-phase4-quantized-ks-only",
        }
        text = format_treemap_section(payload)
        self.assertIn("Layer KS-Distance (ks_stat)", text)
        self.assertIn("For this quantized model", text)
        for name in FEATURE_NAMES:
            if name == "ks_stat":
                continue
            self.assertNotIn(f"({name})", text)

    def test_all_zero_reports_baseline(self):
        payload = _fp_payload(
            shap_attributions={name: 0.0 for name in FEATURE_NAMES},
        )
        text = format_treemap_section(payload)
        self.assertIn("baseline expected value", text)
        self.assertIn("none (all values 0.0)", text)

    def test_invalid_payloads_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            format_treemap_section("not a mapping")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "shap_attributions"):
            format_treemap_section({"p_tamper": 0.5})
        with self.assertRaises(ValueError):
            format_treemap_section({"shap_attributions": {"entropy": 0.1}})
        with self.assertRaises(ValueError):
            format_treemap_section(_fp_payload(), top_n=0)
        with self.assertRaises(ValueError):
            format_treemap_section(_fp_payload(p_tamper=True))
        for bad_p_tamper in (float("nan"), float("inf"), float("-inf"), "0.5"):
            with self.assertRaises(ValueError):
                format_treemap_section(_fp_payload(p_tamper=bad_p_tamper))

    def test_no_layer_identity_or_forbidden_claims(self):
        text = format_treemap_section(_fp_payload()).lower()
        for forbidden in (
            "highest-risk",
            "highest risk",
            "evidence layer l_",
            "layer 0",
            "malicious",
            "tampered",
            "compromised",
            "backdoor",
            "attacker",
            "probability",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
