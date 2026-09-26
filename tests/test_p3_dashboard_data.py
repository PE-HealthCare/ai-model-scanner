"""Tests for P3 dashboard results data path (Step 1)."""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.report import prepare_dashboard_results


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


class TestP3DashboardDataPath(unittest.TestCase):
    def test_prepare_dashboard_results_success(self):
        risk = _valid_p2_risk()
        ml = _valid_p3_ml()

        prepared = prepare_dashboard_results(risk, ml)
        self.assertIn("risk_summary", prepared)
        self.assertIn("ml_results", prepared)
        self.assertEqual(prepared["risk_summary"]["generation_commit"], "commit-abc-123")
        self.assertEqual(prepared["ml_results"]["generation_commit"], "commit-abc-123")

        summary = prepared["risk_summary"]
        self.assertEqual(summary["producer"], "P2")
        self.assertEqual(summary["verdict"], "REVIEW")
        self.assertAlmostEqual(summary["mrs_score"], 42.5)
        self.assertAlmostEqual(summary["s_static"], 0.35)
        self.assertAlmostEqual(summary["p_tamper"], 0.45)
        self.assertAlmostEqual(summary["s_behavior"], 0.20)

    def test_prepare_dashboard_results_quantized(self):
        risk = _valid_p2_risk(s_behavior=None)
        ml = _valid_p3_ml()

        prepared = prepare_dashboard_results(risk, ml)
        self.assertIsNone(prepared["risk_summary"]["s_behavior"])

    def test_prepare_dashboard_results_different_commits_preserved(self):
        # Commits are preserved without requiring equality
        risk = _valid_p2_risk(generation_commit="commit-1")
        ml = _valid_p3_ml(generation_commit="commit-2")

        prepared = prepare_dashboard_results(risk, ml)
        self.assertEqual(prepared["risk_summary"]["generation_commit"], "commit-1")
        self.assertEqual(prepared["ml_results"]["generation_commit"], "commit-2")

    def test_prepare_dashboard_results_rejects_non_p2_or_non_p3(self):
        with self.assertRaisesRegex(ValueError, "must be 'P2'"):
            prepare_dashboard_results(_valid_p2_risk(producer="INVALID"), _valid_p3_ml())

        with self.assertRaisesRegex(ValueError, "must be 'P3'"):
            prepare_dashboard_results(_valid_p2_risk(), _valid_p3_ml(producer="P2"))

    def test_prepare_dashboard_results_preserves_p2_values(self):
        risk = _valid_p2_risk(mrs_score=87.65, verdict="FAIL", s_static=0.91, p_tamper=0.88, s_behavior=0.75)
        ml = _valid_p3_ml(p_tamper=0.88)

        prepared = prepare_dashboard_results(risk, ml)
        summary = prepared["risk_summary"]
        self.assertEqual(summary["verdict"], "FAIL")
        self.assertAlmostEqual(summary["mrs_score"], 87.65)
        self.assertAlmostEqual(summary["s_static"], 0.91)
        self.assertAlmostEqual(summary["p_tamper"], 0.88)
        self.assertAlmostEqual(summary["s_behavior"], 0.75)

    def test_no_highest_risk_layer_injected(self):
        risk = _valid_p2_risk()
        ml = _valid_p3_ml()

        prepared = prepare_dashboard_results(risk, ml)
        self.assertNotIn("highest_risk_layer", prepared)
        self.assertNotIn("highest_risk_layer", prepared["risk_summary"])

    def test_set_dashboard_results_in_session_state(self):
        import ast
        from pathlib import Path

        source = (
            Path(__file__).resolve().parent.parent
            / "src"
            / "p3_ml_dashboard"
            / "dashboard.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        node = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "set_dashboard_results"
        )
        namespace: dict[str, Any] = {"prepare_dashboard_results": prepare_dashboard_results}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "<set_dashboard_results>", "exec"), namespace)
        set_dashboard_results = namespace["set_dashboard_results"]

        fake_session: dict[str, Any] = {}
        risk = _valid_p2_risk()
        ml = _valid_p3_ml()
        res = set_dashboard_results(risk, ml, session_state=fake_session)

        self.assertEqual(fake_session.get("scan_status"), "complete")
        self.assertIn("scan_result", fake_session)
        self.assertEqual(fake_session["scan_result"]["risk_summary"]["generation_commit"], "commit-abc-123")
        self.assertEqual(fake_session["scan_result"]["ml_results"]["generation_commit"], "commit-abc-123")
        self.assertEqual(res, fake_session["scan_result"])


if __name__ == "__main__":
    unittest.main()
