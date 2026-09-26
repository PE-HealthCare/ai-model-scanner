"""Tests for P3 dashboard results presentation (Step 2)."""

from __future__ import annotations

import unittest
from typing import Any

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.report import (
    format_results_summary,
    format_treemap_section,
    prepare_dashboard_results,
)


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


class TestP3DashboardResultsPresentation(unittest.TestCase):
    def test_presents_verdict_mrs_and_scores_verbatim(self):
        prepared = prepare_dashboard_results(_valid_p2_risk(), _valid_p3_ml())
        text = format_results_summary(prepared)
        self.assertIn("Verdict: REVIEW", text)
        self.assertIn("MRS: 42.50", text)
        self.assertIn("Static score (S_static): 0.3500", text)
        self.assertIn("Tamper score (P_tamper, risk): 0.4500", text)
        self.assertIn("Behavioral score (S_behavior): 0.2000", text)
        self.assertIn("producer=P2", text)
        self.assertIn("model_version=lightgbm-final", text)

    def test_quantized_behavior_none_renders_na(self):
        prepared = prepare_dashboard_results(_valid_p2_risk(s_behavior=None), _valid_p3_ml())
        text = format_results_summary(prepared)
        self.assertIn("N/A (quantized", text)

    def test_ml_evidence_reuses_treemap_section(self):
        prepared = prepare_dashboard_results(_valid_p2_risk(), _valid_p3_ml())
        text = format_results_summary(prepared)
        self.assertIn("P3 TreeSHAP attribution (classifier evidence only)", text)
        self.assertIn(format_treemap_section(prepared["ml_results"]), text)

    def test_does_not_recompute_or_invent(self):
        risk = _valid_p2_risk(mrs_score=87.65, verdict="FAIL", s_static=0.91, p_tamper=0.88, s_behavior=0.75)
        ml = _valid_p3_ml(p_tamper=0.88)
        text = format_results_summary(prepare_dashboard_results(risk, ml))
        self.assertIn("Verdict: FAIL", text)
        self.assertIn("MRS: 87.65", text)
        lowered = text.lower()
        self.assertNotIn("highest_risk_layer", lowered)
        self.assertIn("highest-risk layer: unavailable (no eligible per-layer evidence)", lowered)

    def test_rejects_missing_or_invalid_results(self):
        with self.assertRaises(ValueError):
            format_results_summary(None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            format_results_summary({})
        with self.assertRaises(ValueError):
            format_results_summary({"risk_summary": {}, "ml_results": {}})


if __name__ == "__main__":
    unittest.main()
