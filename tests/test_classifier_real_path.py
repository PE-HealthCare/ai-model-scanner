"""Focused tests for the authoritative CP4 REAL P3 classification path.

Covers the LightGBM artifact (artifacts/lightgbm_model.txt, trained via the
committed trainer train_lightgbm_classifier.py through the REAL P1
extractor) and its inference path:

  - the committed LightGBM artifact loads and its feature names/order match
    the canonical D1 order exactly (fail-closed on mismatch);
  - canonical feature ordering is identical between training and inference
    and matches both contracts;
  - build_ml_results() consumes a real, contract-valid P1 features payload
    (built by the production extractor) and produces VERIFIED-REAL output;
  - the locked D10 rule P_tamper = max(p_l) is applied exactly;
  - TreeSHAP attributions come from the actual LightGBM model, map to the
    canonical feature names, and satisfy additivity against the model margin
    of the explained (argmax) layer;
  - MOCK upstream artifacts can never produce VERIFIED-REAL P3 output;
  - stale generation, non-finite features, and missing/invalid artifacts
    fail closed;
  - output is deterministic;
  - the produced payload validates against contracts/ml_results.schema.json.

These tests verify an engineering contract, NOT real-world detection
capability: all data is synthetic.
"""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from src.common.utils import ROOT
from src.common.feature_names import (
    FEATURE_NAMES,
    feature_vector,
)
from src.p1_static_engine.analyzer import build_mock_features, extract_layer_features
from src.p3_ml_dashboard.classifier import (
    DEFAULT_MODEL_PATH,
    MODEL_VERSION,
    _feature_matrix,
    _load_final_model,
    aggregate_p_tamper,
    build_ml_results,
    build_mock_ml_results,
)

CONTRACT_DIR = ROOT / "contracts"


def _tensor(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 0.1, (32, 64)).astype(np.float32)


def _real_features_payload(
    tensors: list[np.ndarray], generation_commit: str = "TEST-GEN"
) -> dict:
    """Contract-valid VERIFIED-REAL P1 payload built by the production extractor."""
    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "input_domain": "VISION",
        "is_quantized": False,
        "layer_count": len(tensors),
        "static_features": [
            {"layer_name": f"synthetic.layer{i}", **extract_layer_features(t)}
            for i, t in enumerate(tensors)
        ],
    }


class TestRealClassifierPath(unittest.TestCase):
    def setUp(self):
        with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as fh:
            features_schema = json.load(fh)
        Draft202012Validator(features_schema).validate(_real_features_payload([_tensor(0)]))
        # --- LightGBM artifact loading (fail-closed) ----------------------------

    def test_committed_lightgbm_artifact_loads_with_canonical_features(self):
        model = _load_final_model()
        self.assertEqual(model.feature_name(), list(FEATURE_NAMES))
        self.assertTrue(DEFAULT_MODEL_PATH.is_file())
        self.assertGreater(DEFAULT_MODEL_PATH.stat().st_size, 0)

    def test_missing_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                _load_final_model(Path(td) / "does_not_exist.txt")

    def test_invalid_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad_model.txt"
            bad.write_text("this is not a valid lightgbm model", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid LightGBM classifier artifact"):
                _load_final_model(bad)

    # --- canonical feature ordering -----------------------------------------

    def test_canonical_feature_ordering_identical_train_and_inference(self):
        with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as fh:
            features_schema = json.load(fh)
        with (CONTRACT_DIR / "ml_results.schema.json").open(encoding="utf-8") as fh:
            ml_schema = json.load(fh)
        self.assertEqual(
            features_schema["properties"]["static_features"]["items"]["required"][1:],
            list(FEATURE_NAMES),
        )
        self.assertEqual(
            ml_schema["properties"]["shap_attributions"]["propertyNames"]["enum"],
            list(FEATURE_NAMES),
        )
        self.assertEqual(_load_final_model().feature_name(), list(FEATURE_NAMES))

        feats = extract_layer_features(_tensor(3))
        self.assertEqual(list(feats.keys()), list(FEATURE_NAMES))
        self.assertEqual(feature_vector(feats), [float(feats[name]) for name in FEATURE_NAMES])
        # --- real path: LightGBM inference on real P1 features ------------------

    def test_build_ml_results_consumes_real_features(self):
        features = _real_features_payload([_tensor(1), _tensor(2)])
        result = build_ml_results(features, "TEST-GEN")

        self.assertTrue(0.0 <= result["p_tamper"] <= 1.0)
        self.assertEqual(list(result["shap_attributions"].keys()), list(FEATURE_NAMES))
        self.assertEqual(result["model_version"], MODEL_VERSION)
        self.assertEqual(result["mock_status"], "VERIFIED-REAL")
        self.assertEqual(result["producer"], "P3")

    # --- D10: P_tamper = max(p_l) -------------------------------------------

    def test_d10_aggregation_exact_rule(self):
        self.assertEqual(aggregate_p_tamper([0.1, 0.9, 0.5]), (0.9, 1))
        self.assertEqual(aggregate_p_tamper([0.5]), (0.5, 0))
        self.assertEqual(aggregate_p_tamper([0.2, 0.2]), (0.2, 0))  # argmax -> first
        self.assertEqual(aggregate_p_tamper([0.0, 1.0]), (1.0, 1))

    def test_d10_aggregation_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            aggregate_p_tamper([])
        with self.assertRaises(ValueError):
            aggregate_p_tamper([float("nan"), 0.5])
        with self.assertRaises(ValueError):
            aggregate_p_tamper([-0.1, 0.5])
        with self.assertRaises(ValueError):
            aggregate_p_tamper([1.5, 0.5])
        with self.assertRaises(ValueError):
            aggregate_p_tamper([[0.5, 0.5]])  # not 1-D

    def test_build_ml_results_p_tamper_is_exact_d10_max_of_per_layer(self):
        features = _real_features_payload([_tensor(5), _tensor(6), _tensor(7)])
        model = _load_final_model()
        X = _feature_matrix(features)
        per_layer = [float(p) for p in model.predict(X)]
        result = build_ml_results(features, "TEST-GEN")
        self.assertAlmostEqual(result["p_tamper"], max(per_layer), places=12)
        # --- TreeSHAP: real model attribution, canonical names, additivity -------

    def test_treeshap_maps_to_canonical_features_and_corresponds_to_prediction(self):
        import shap

        features = _real_features_payload([_tensor(10), _tensor(11)])
        model = _load_final_model()
        X = _feature_matrix(features)
        probs = np.asarray(model.predict(X), dtype=np.float64)
        evidence_layer = int(np.argmax(probs))

        explainer = shap.TreeExplainer(model)
        raw = explainer.shap_values(X[evidence_layer : evidence_layer + 1])
        sv = np.asarray(raw[-1] if isinstance(raw, list) else raw)
        if sv.ndim == 3:
            sv = sv[..., -1]
        if sv.ndim == 2:
            sv = sv[0]

        expected_value = np.asarray(explainer.expected_value).reshape(-1)
        base = (
            float(expected_value[-1]) if expected_value.size > 1 else float(expected_value[0])
        )
        raw_margin = float(
            np.asarray(model.predict(X[evidence_layer : evidence_layer + 1], raw_score=True))[0]
        )
        self.assertTrue(np.all(np.isfinite(sv)))
        self.assertEqual(sv.shape, (len(FEATURE_NAMES),))
        # Explanations correspond to the actual model margin of the explained layer.
        self.assertAlmostEqual(base + float(sv.sum()), raw_margin, places=6)

        result = build_ml_results(features, "TEST-GEN")
        self.assertAlmostEqual(
            sum(result["shap_attributions"].values()), float(sv.sum()), places=10
        )

    # --- fail-closed: mock/stale/non-finite/incompatible ---------------------

    def test_mock_upstream_cannot_produce_verified_real_output(self):
        mock_features = build_mock_features("TEST")  # producer=P1, mock_status=MOCK
        with self.assertRaisesRegex(ValueError, "VERIFIED-REAL"):
            build_ml_results(mock_features, "TEST")

    def test_rejects_non_p1_producer_and_stale_generation(self):
        features = _real_features_payload([_tensor(4)])
        foreign = copy.deepcopy(features)
        foreign["producer"] = "PX"
        with self.assertRaisesRegex(ValueError, "P1"):
            build_ml_results(foreign, "TEST-GEN")
        with self.assertRaisesRegex(ValueError, "stale P1 artifact generation"):
            build_ml_results(features, "OTHER-COMMIT")

    def test_non_finite_feature_rejected_without_imputation(self):
        features = _real_features_payload([_tensor(4)])
        features["static_features"][0]["entropy"] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            build_ml_results(features, "TEST-GEN")

    # --- determinism ---------------------------------------------------------

    def test_scoring_is_deterministic(self):
        features = _real_features_payload([_tensor(5), _tensor(6)])
        self.assertEqual(
            build_ml_results(features, "TEST-GEN"),
            build_ml_results(features, "TEST-GEN"),
        )
        # --- contract compatibility of the real P3 payload ----------------------

    def test_real_ml_results_payload_is_contract_valid(self):
        ml_results = build_ml_results(_real_features_payload([_tensor(5)]), "TEST-GEN")
        with (CONTRACT_DIR / "ml_results.schema.json").open(encoding="utf-8") as fh:
            schema = json.load(fh)
        Draft202012Validator(schema).validate(ml_results)
        self.assertEqual(ml_results["producer"], "P3")
        self.assertEqual(ml_results["mock_status"], "VERIFIED-REAL")
        self.assertEqual(list(ml_results["shap_attributions"].keys()), list(FEATURE_NAMES))
        self.assertEqual(ml_results["model_version"], MODEL_VERSION)

    # --- mock path preserved (Phase 1 regression) ---------------------------

    def test_mock_path_preserved(self):
        result = build_mock_ml_results(build_mock_features("TEST"), "TEST")
        self.assertEqual(result["mock_status"], "MOCK")
        with (CONTRACT_DIR / "ml_results.schema.json").open(encoding="utf-8") as fh:
            schema = json.load(fh)
        Draft202012Validator(schema).validate(result)


if __name__ == "__main__":
    unittest.main()