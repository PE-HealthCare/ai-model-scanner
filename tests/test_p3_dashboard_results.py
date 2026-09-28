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

    def test_why_flagged_rows_are_ranked_and_match_frozen_explainer(self):
        from src.p3_ml_dashboard.report import build_why_flagged_rows
        from src.p3_ml_dashboard.tree_shap_explainer import explain_shap_attributions

        shap = {name: 0.01 for name in FEATURE_NAMES}
        shap["entropy"] = 0.9
        shap["std"] = -0.4
        ml = _valid_p3_ml(shap_attributions=shap)
        rows = build_why_flagged_rows(ml)

        self.assertEqual([r["rank"] for r in rows], list(range(1, len(rows) + 1)))
        self.assertEqual(rows[0]["feature_name"], "entropy")
        self.assertEqual(rows[0]["direction"], "POSITIVE")
        self.assertEqual(rows[1]["feature_name"], "std")
        self.assertEqual(rows[1]["direction"], "NEGATIVE")

        # Presentation only: rows must equal the frozen explainer output verbatim.
        expected = explain_shap_attributions(ml["shap_attributions"], is_quantized=False)
        self.assertEqual(
            [r["explanation"] for r in rows],
            [a.explanation for a in expected.attributions],
        )

        # Honest empty state when every attribution is zero.
        zero_ml = _valid_p3_ml(shap_attributions={name: 0.0 for name in FEATURE_NAMES})
        self.assertEqual(build_why_flagged_rows(zero_ml), [])

    def test_why_flagged_rows_top_n_bounds_ranking(self):
        from src.p3_ml_dashboard.report import build_why_flagged_rows

        shap = {name: 0.01 for name in FEATURE_NAMES}
        shap["entropy"] = 0.9
        rows = build_why_flagged_rows(_valid_p3_ml(shap_attributions=shap), top_n=3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["feature_name"], "entropy")
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3])

    def test_categories_partition_all_canonical_features(self):
        from src.p3_ml_dashboard.report import CATEGORY_FEATURES

        all_mapped = [f for features in CATEGORY_FEATURES.values() for f in features]
        self.assertEqual(sorted(all_mapped), sorted(FEATURE_NAMES))
        self.assertEqual(len(all_mapped), len(set(all_mapped)))

    def test_categories_are_deterministic_and_match_frozen_explainer(self):
        from src.p3_ml_dashboard.report import CATEGORY_FEATURES, build_finding_categories
        from src.p3_ml_dashboard.tree_shap_explainer import explain_shap_attributions

        shap = {name: 0.01 for name in FEATURE_NAMES}
        shap["lsb_kl"] = 0.9
        shap["entropy"] = 0.4
        shap["ks_stat"] = -0.2
        shap["std"] = 0.3
        prepared = prepare_dashboard_results(
            _valid_p2_risk(), _valid_p3_ml(shap_attributions=shap)
        )
        rows = build_finding_categories(prepared)

        # Deterministic for identical input.
        self.assertEqual(rows, build_finding_categories(prepared))
        self.assertEqual([r["category_id"] for r in rows], list(CATEGORY_FEATURES))

        # Presentation only: every echoed value must match the frozen explainer.
        expected = explain_shap_attributions(shap, is_quantized=False)
        by_feature = {a.feature_name: a for a in expected.attributions}
        for row in rows:
            members = [
                by_feature[name]
                for name in CATEGORY_FEATURES[row["category_id"]]
                if name in by_feature
            ]
            top = max(members, key=lambda a: a.abs_shap_value)
            self.assertEqual(row["status"], "EVIDENCE_PRESENT")
            self.assertEqual(row["top_feature"], top.ui_label)
            self.assertAlmostEqual(row["max_abs_shap"], top.abs_shap_value)
            self.assertEqual(row["direction"], top.direction)

    def test_categories_make_no_unsupported_claims(self):
        from src.p3_ml_dashboard.report import build_finding_categories

        prepared = prepare_dashboard_results(
            _valid_p2_risk(), _valid_p3_ml(shap_attributions={name: 0.05 for name in FEATURE_NAMES})
        )
        rows = build_finding_categories(prepared)
        blob = " ".join(str(v) for row in rows for v in row.values()).lower()
        for forbidden in (
            "malicious",
            "malware",
            "backdoor",
            "tamper",
            "compromis",
            "attacker",
            "payload",
            "steganograph",
            "poison",
            "exploit",
            "attack",
            "detect",
        ):
            self.assertNotIn(forbidden, blob)

    def test_all_zero_shap_yields_no_categories(self):
        from src.p3_ml_dashboard.report import build_finding_categories

        prepared = prepare_dashboard_results(
            _valid_p2_risk(),
            _valid_p3_ml(shap_attributions={name: 0.0 for name in FEATURE_NAMES}),
        )
        self.assertEqual(build_finding_categories(prepared), [])

    def test_quantized_yields_only_divergence_category(self):
        from src.p3_ml_dashboard.report import CATEGORY_FEATURES, build_finding_categories

        prepared = prepare_dashboard_results(
            _valid_p2_risk(), _valid_p3_ml(shap_attributions={"ks_stat": 0.75})
        )
        rows = build_finding_categories(prepared)
        by_id = {r["category_id"]: r for r in rows}
        self.assertEqual(set(by_id), set(CATEGORY_FEATURES))

        divergence = by_id["layer_divergence"]
        self.assertEqual(divergence["status"], "EVIDENCE_PRESENT")
        self.assertEqual(divergence["top_feature"], "Layer KS-Distance")
        self.assertAlmostEqual(divergence["max_abs_shap"], 0.75)

        for category_id, row in by_id.items():
            if category_id == "layer_divergence":
                continue
            self.assertEqual(row["status"], "NOT_EVALUATED_QUANTIZED")
            self.assertEqual(row["status_label"], "Not evaluated (quantized)")
            self.assertIsNone(row["max_abs_shap"])
            self.assertIsNone(row["top_feature"])

    def test_categories_contain_no_layer_identity(self):
        from src.p3_ml_dashboard.report import build_finding_categories

        def _layer(name: str, ks: float) -> dict[str, Any]:
            return {
                "layer_name": name,
                "entropy": 1.0,
                "pov_chi2": 1.0,
                "lsb_kl": 1.0,
                "ks_stat": ks,
                "mean": 1.0,
                "std": 1.0,
                "skewness": 1.0,
                "kurtosis": 1.0,
                "sparsity": 0.1,
                "outlier_pct": 1.0,
            }

        prepared = prepare_dashboard_results(
            _valid_p2_risk(),
            _valid_p3_ml(),
            [
                _layer("SECRET-LAYER-ALPHA", 0.10),
                _layer("SECRET-LAYER-BETA", 0.20),
                _layer("SECRET-LAYER-GAMMA", 0.95),
            ],
        )
        # D6 still selects a layer; categories must not reference it.
        self.assertEqual(prepared["highest_risk_layer"], "SECRET-LAYER-GAMMA")

        rows = build_finding_categories(prepared)
        blob = " ".join(str(v) for row in rows for v in row.values())
        for forbidden in (
            "SECRET-LAYER-ALPHA",
            "SECRET-LAYER-BETA",
            "SECRET-LAYER-GAMMA",
            "highest_risk_layer",
            "layer_name",
            "highest-risk",
        ):
            self.assertNotIn(forbidden, blob)


if __name__ == "__main__":
    unittest.main()
