"""Tests for P3 dashboard D6 presentation wiring."""

from __future__ import annotations

import unittest
from typing import Any

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.report import prepare_dashboard_results


def _static_layers() -> list[dict[str, Any]]:
    return [
        {
            "layer_name": "layer.a",
            "entropy": 1.0,
            "pov_chi2": 1.0,
            "lsb_kl": 1.0,
            "ks_stat": 0.10,
            "mean": 1.0,
            "std": 1.0,
            "skewness": 1.0,
            "kurtosis": 1.0,
            "sparsity": 0.1,
            "outlier_pct": 1.0,
        },
        {
            "layer_name": "layer.b",
            "entropy": 2.0,
            "pov_chi2": 2.0,
            "lsb_kl": 2.0,
            "ks_stat": 0.30,
            "mean": 2.0,
            "std": 2.0,
            "skewness": 2.0,
            "kurtosis": 2.0,
            "sparsity": 0.2,
            "outlier_pct": 2.0,
        },
        {
            "layer_name": "layer.c",
            "entropy": 4.0,
            "pov_chi2": 4.0,
            "lsb_kl": 4.0,
            "ks_stat": 0.90,
            "mean": 4.0,
            "std": 4.0,
            "skewness": 4.0,
            "kurtosis": 4.0,
            "sparsity": 0.4,
            "outlier_pct": 4.0,
        },
    ]


def _valid_p2_risk(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "producer": "P2",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0.0",
        "generation_commit": "commit-abc-123",
        "mrs_score": 42.5,
        "verdict": "REVIEW",
        "s_static": 0.35,
        "p_tamper": 0.45,
        "s_behavior": 0.20,
    }
    base.update(overrides)
    return base


def _valid_p3_ml(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0.0",
        "generation_commit": "commit-abc-123",
        "p_tamper": 0.45,
        "shap_attributions": {name: 0.05 for name in FEATURE_NAMES},
        "model_version": "lightgbm-final",
    }
    base.update(overrides)
    return base


class TestP3DashboardD6Presentation(unittest.TestCase):
    def test_selected_layer_reaches_report(self):
        from src.p3_ml_dashboard.report import format_results_summary

        prepared = prepare_dashboard_results(_valid_p2_risk(), _valid_p3_ml(), _static_layers())
        self.assertEqual(prepared["highest_risk_layer"], "layer.c")
        self.assertIsInstance(prepared["highest_risk_evidence"], float)
        text = format_results_summary(prepared)
        self.assertIn("Highest-risk layer: layer.c (D6 evidence E(l)=", text)
        self.assertIn("P3 TreeSHAP attribution (classifier evidence only)", text)

    def test_unavailable_state_displayed_honestly(self):
        from src.p3_ml_dashboard.report import format_results_summary

        prepared = prepare_dashboard_results(_valid_p2_risk(), _valid_p3_ml())
        self.assertEqual(prepared["highest_risk_layer"], "unavailable")
        self.assertIsNone(prepared["highest_risk_evidence"])
        text = format_results_summary(prepared)
        self.assertIn("Highest-risk layer: unavailable (no eligible per-layer evidence)", text)

    def test_treeshap_cannot_determine_layer(self):
        from src.p3_ml_dashboard.report import format_results_summary

        shap_swapped = {name: 0.01 for name in FEATURE_NAMES}
        shap_swapped["entropy"] = 0.99
        prepared = prepare_dashboard_results(
            _valid_p2_risk(), _valid_p3_ml(shap_attributions=shap_swapped), _static_layers()
        )
        self.assertEqual(prepared["highest_risk_layer"], "layer.c")
        self.assertIn("Highest-risk layer: layer.c", format_results_summary(prepared))

    def test_existing_step1_behavior_preserved(self):
        prepared = prepare_dashboard_results(_valid_p2_risk(), _valid_p3_ml(), _static_layers())
        summary = prepared["risk_summary"]
        self.assertEqual(summary["verdict"], "REVIEW")
        self.assertAlmostEqual(summary["mrs_score"], 42.5)
        self.assertNotIn("highest_risk_layer", summary)
        self.assertNotIn("highest_risk_layer", prepared["ml_results"])


if __name__ == "__main__":
    unittest.main()