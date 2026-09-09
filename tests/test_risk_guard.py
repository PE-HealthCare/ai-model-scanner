"""Focused tests: P2 behavioral-evidence MRS routing and BLOCKED guard.

Covers exactly the approved semantics (frozen formulas, no new MRS semantics):

  - quantized + s_behavior=None      -> documented bypass, min(100, 55*s + 45*p)
  - quantized + s_behavior present   -> ValueError (probing skipped by design)
  - non-quantized + s_behavior=None  -> BLOCKED: pipeline stops; no MRS, no
                                        verdict, no risk_results artifact; no
                                        renormalization, no weight redistribution
  - non-quantized + valid evidence   -> min(100, 40*s + 35*p + 25*b)
  - invalid/non-finite evidence      -> rejected, no imputation
  - mock path unchanged (frozen Phase 1 formula, contract-valid payload)
  - blocked real pipeline step emits no risk_results artifact via the existing
    scan_model._validated_step stop mechanism

The full build_risk_results path with a real S_behavior value becomes reachable
only when the Phase 5 prober supplies one; until then the non-quantized
40/35/25 formula is verified through the compute_mrs unit contract.
"""

from __future__ import annotations

import copy
import json
import unittest

from jsonschema import Draft202012Validator

import scan_model
from src.common.utils import ROOT
from src.p1_static_engine.analyzer import build_mock_features
from src.p2_behavioral_risk.prober import (
    build_mock_risk_results,
    build_risk_results,
    compute_mrs,
    compute_s_static,
)
from src.p3_ml_dashboard.classifier import build_mock_ml_results

CONTRACT_DIR = ROOT / "contracts"
OUTPUT_DIR = scan_model.OUTPUT_DIR

FEATURE_NAMES = (
    "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean",
    "std", "skewness", "kurtosis", "sparsity", "outlier_pct",
)


def _load_schema(name: str) -> dict:
    with (CONTRACT_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def _synthetic_features(is_quantized: bool) -> dict:
    """Contract-valid P1 VERIFIED-REAL features payload for P2 tests."""
    static_features = [
        {
            "layer_name": "synthetic.layer1",
            "entropy": 0.98, "pov_chi2": 1.05, "lsb_kl": 0.02, "ks_stat": 0.12,
            "mean": 0.01, "std": 0.24, "skewness": -0.08, "kurtosis": 2.91,
            "sparsity": 0.08, "outlier_pct": 0.30,
        },
        {
            "layer_name": "synthetic.layer2",
            "entropy": 0.97, "pov_chi2": 1.10, "lsb_kl": 0.03, "ks_stat": 0.10,
            "mean": -0.01, "std": 0.22, "skewness": 0.05, "kurtosis": 3.05,
            "sparsity": 0.10, "outlier_pct": 0.40,
        },
    ]
    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "TEST-GEN",
        "input_domain": "VISION",
        "is_quantized": is_quantized,
        "layer_count": len(static_features),
        "static_features": static_features,
    }


def _synthetic_ml_results() -> dict:
    """Contract-valid P3 VERIFIED-REAL ml_results payload for P2 tests."""
    return {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "TEST-GEN",
        "p_tamper": 0.08,
        "shap_attributions": {name: 0.0 for name in FEATURE_NAMES},
        "model_version": "synthetic-test",
    }


class TestBehavioralEvidenceMRSRouting(unittest.TestCase):
    """Frozen-formula routing and the incomplete-evidence BLOCKED guard."""

    def setUp(self):
        # The synthetic upstream payloads must be contract-valid so the
        # pipeline-level test below exercises the real provenance checks.
        Draft202012Validator(_load_schema("features.schema.json")).validate(
            _synthetic_features(is_quantized=False)
        )
        Draft202012Validator(_load_schema("features.schema.json")).validate(
            _synthetic_features(is_quantized=True)
        )
        Draft202012Validator(_load_schema("ml_results.schema.json")).validate(
            _synthetic_ml_results()
        )

    # --- frozen formula: quantized bypass (55/45) -------------------------

    def test_compute_mrs_quantized_bypass_exact_scores(self):
        # 55*0.25 + 45*0.5 = 13.75 + 22.5
        self.assertEqual(compute_mrs(0.25, 0.5, None, True), 36.25)
        self.assertEqual(compute_mrs(0.0, 0.0, None, True), 0.0)
        # min(100, ...) clamp is part of the frozen formula.
        self.assertEqual(compute_mrs(1.0, 1.0, None, True), 100.0)

    def test_build_risk_results_quantized_bypass_uses_frozen_55_45(self):
        features = _synthetic_features(is_quantized=True)
        ml_results = _synthetic_ml_results()
        risk = build_risk_results(features, ml_results, "TEST-GEN")

        expected_s_static = compute_s_static(features["static_features"])
        expected_mrs = min(100.0, 55.0 * expected_s_static + 45.0 * 0.08)
        self.assertAlmostEqual(risk["mrs_score"], expected_mrs, places=12)
        self.assertIsNone(risk["s_behavior"])  # contract: null iff quantized bypass
        self.assertAlmostEqual(risk["s_static"], expected_s_static, places=12)
        self.assertEqual(
            risk["verdict"],
            "PASS" if risk["mrs_score"] < 35 else "REVIEW" if risk["mrs_score"] < 70 else "FAIL",
        )
        # Contract compatibility: null s_behavior validates against the schema.
        Draft202012Validator(_load_schema("risk_results.schema.json")).validate(risk)

    # --- frozen formula: non-quantized with real evidence (40/35/25) ------

    def test_compute_mrs_non_quantized_with_evidence_exact_scores(self):
        # 40*0.25 + 35*0.5 + 25*0.75 = 10 + 17.5 + 18.75
        self.assertEqual(compute_mrs(0.25, 0.5, 0.75, False), 46.25)
        self.assertEqual(compute_mrs(0.0, 0.0, 0.0, False), 0.0)
        self.assertEqual(compute_mrs(1.0, 1.0, 1.0, False), 100.0)

    # --- rejection: behavioral evidence under quantized bypass ------------

    def test_compute_mrs_rejects_evidence_for_quantized_bypass(self):
        with self.assertRaisesRegex(ValueError, "not permitted for a quantized"):
            compute_mrs(0.25, 0.5, 0.75, True)
        # Even an explicit zero is evidence, not the documented absence state.
        with self.assertRaisesRegex(ValueError, "not permitted for a quantized"):
            compute_mrs(0.25, 0.5, 0.0, True)

    # --- BLOCKED guard: non-quantized without behavioral evidence ----------

    def test_compute_mrs_blocked_on_missing_non_quantized_evidence(self):
        with self.assertRaises(ValueError) as caught:
            compute_mrs(0.25, 0.5, None, False)
        message = str(caught.exception)
        self.assertIn("BLOCKED", message)
        self.assertIn("S_behavior", message)
        self.assertIn("NO MRS", message)
        self.assertIn("no renormalization", message)
        self.assertIn("no weight redistribution", message)

    def test_build_risk_results_blocked_without_non_quantized_evidence(self):
        features = _synthetic_features(is_quantized=False)
        ml_results = _synthetic_ml_results()
        with self.assertRaises(ValueError) as caught:
            build_risk_results(features, ml_results, "TEST-GEN")
        message = str(caught.exception)
        self.assertIn("BLOCKED", message)
        self.assertIn("S_behavior", message)
        self.assertIn("no renormalization", message)

    def test_build_risk_results_rejects_missing_is_quantized_tag(self):
        features = _synthetic_features(is_quantized=False)
        del features["is_quantized"]
        with self.assertRaisesRegex(ValueError, "is_quantized"):
            build_risk_results(features, _synthetic_ml_results(), "TEST-GEN")

    # --- rejection: invalid / non-finite / out-of-range evidence ----------

    def test_compute_mrs_rejects_invalid_behavioral_evidence(self):
        for bad in (float("nan"), float("inf"), float("-inf"), -0.5, 1.5):
            with self.assertRaisesRegex(ValueError, r"finite number in \[0, 1\]"):
                compute_mrs(0.25, 0.5, bad, False)

    # --- mock path regression (frozen Phase 1 behavior) -------------------

    def test_mock_path_unchanged(self):
        generation_commit = "TEST"
        features = build_mock_features(generation_commit)
        ml_results = build_mock_ml_results(features, generation_commit)
        risk = build_mock_risk_results(ml_results, generation_commit)

        # Frozen Phase 1 mock formula with mock evidence (s_static=0.10, s_behavior=0.05).
        expected = min(100.0, 40.0 * 0.10 + 35.0 * float(ml_results["p_tamper"]) + 25.0 * 0.05)
        self.assertAlmostEqual(risk["mrs_score"], expected, places=12)
        self.assertEqual(risk["s_static"], 0.10)
        self.assertEqual(risk["s_behavior"], 0.05)
        self.assertEqual(
            risk["verdict"],
            "PASS" if risk["mrs_score"] < 35 else "REVIEW" if risk["mrs_score"] < 70 else "FAIL",
        )
        Draft202012Validator(_load_schema("risk_results.schema.json")).validate(risk)


class TestBlockedPipelineArtifactGuard(unittest.TestCase):
    """The blocked state stops the pipeline and emits no risk_results artifact."""

    def test_blocked_real_pipeline_emits_no_risk_artifact(self):
        features = _synthetic_features(is_quantized=False)
        ml_results = _synthetic_ml_results()

        # Preserve any pre-existing pipeline artifacts so the working tree and
        # committed mock artifacts are left exactly as found.
        saved: dict[str, bytes | None] = {}
        for name in ("features.json", "ml_results.json", "risk_results.json"):
            path = OUTPUT_DIR / name
            saved[name] = path.read_bytes() if path.exists() else None

        original_build_features = scan_model.build_features
        original_build_ml_results = scan_model.build_ml_results

        def fake_build_features(model_path, generation_commit):
            payload = copy.deepcopy(features)
            payload["generation_commit"] = generation_commit  # pass provenance
            return payload

        def fake_build_ml_results(f, generation_commit):
            payload = copy.deepcopy(ml_results)
            payload["generation_commit"] = generation_commit  # pass provenance
            return payload

        scan_model.build_features = fake_build_features  # type: ignore[assignment]
        scan_model.build_ml_results = fake_build_ml_results  # type: ignore[assignment]
        try:
            with self.assertRaisesRegex(ValueError, "BLOCKED"):
                scan_model.run_pipeline("unused.safetensors")

            # The block happened at the P2 step: upstream artifacts exist for
            # this run, but the existing stop mechanism guarantees NO
            # risk_results artifact (the producer raised before persistence,
            # and _validated_step deletes any partial artifact on failure).
            self.assertTrue((OUTPUT_DIR / "features.json").exists())
            self.assertTrue((OUTPUT_DIR / "ml_results.json").exists())
            self.assertFalse((OUTPUT_DIR / "risk_results.json").exists())
        finally:
            scan_model.build_features = original_build_features
            scan_model.build_ml_results = original_build_ml_results
            for name, prior in saved.items():
                path = OUTPUT_DIR / name
                if prior is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(prior)


if __name__ == "__main__":
    unittest.main()
