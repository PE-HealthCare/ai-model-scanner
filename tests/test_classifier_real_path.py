"""Focused tests for the REAL P3 classification path (trainer <-> scorer contract).

Covers the committed logistic-regression artifact (models/classifier.json,
training_data_status="SYNTHETIC", authoritative=false) and its inference path:

  - the committed artifact is reproduced exactly by the committed trainer code
    (no retraining, no writes);
  - canonical feature ordering is identical between training and inference and
    matches both contracts;
  - score() works on real P1 feature payloads built by the production extractor;
  - tampered synthetic input yields a higher tamper signal than its clean
    counterpart for the methods the training methodology actually separates
    (controlled perturbation, mantissa-bit modification). The committed model
    does NOT reliably separate lsb_manipulation — that is a recorded
    limitation of the synthetic-only model and is deliberately NOT asserted
    as a detection capability;
  - MOCK upstream artifacts can never produce VERIFIED-REAL P3 output;
  - incompatible model dimensions fail closed;
  - scoring is deterministic.

These tests verify an engineering contract, NOT real-world detection
capability: all data is synthetic and holdout metrics describe synthetic-data
separation only.
"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

from src.common.utils import ROOT
from src.common.feature_names import (
    CANONICAL_FEATURE_COUNT,
    FEATURE_NAMES,
    feature_vector,
)
from src.p1_static_engine.analyzer import build_mock_features, extract_layer_features
from src.p3_ml_dashboard import classifier
from src.p3_ml_dashboard.classifier import (
    _load_model,
    _validate_model_artifact,
    build_ml_results,
    score,
)
from src.p3_ml_dashboard.synthetic_tamper import (
    controlled_perturbation,
    mantissa_bit_modification,
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

    # --- D1: committed artifact <-> committed trainer compatibility --------

    def test_committed_model_is_reproduced_by_committed_trainer(self):
        model = _load_model()
        self.assertEqual(model["feature_names"], list(FEATURE_NAMES))
        for field in ("means", "stds", "weights"):
            self.assertEqual(len(model[field]), CANONICAL_FEATURE_COUNT)
        self.assertEqual(model["training_data_status"], "SYNTHETIC")
        self.assertIs(model["authoritative"], False)

        # Recompute the deterministic training pipeline in memory (no writes,
        # no retraining of the artifact on disk).
        import train_classifier as tc

        x, y, _ = tc._dataset()
        idx = np.random.default_rng(tc.SEED).permutation(len(y))
        x, y = x[idx], y[idx]
        n_holdout = max(int(len(y) * tc.HOLDOUT_FRACTION), 4)
        x_tr, y_tr = x[:-n_holdout], y[:-n_holdout]
        x_tr_s, mean, std = tc._standardize(x_tr)
        w, b = tc._fit_logistic(x_tr_s, y_tr)

        self.assertEqual(np.asarray(model["means"]).tolist(), mean.tolist())
        self.assertEqual(np.asarray(model["stds"]).tolist(), std.tolist())
        self.assertEqual(np.asarray(model["weights"]).tolist(), w.tolist())
        self.assertEqual(model["bias"], float(b))

    # --- D2: canonical ordering identical between train and inference ------

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
        self.assertEqual(_load_model()["feature_names"], list(FEATURE_NAMES))

        feats = extract_layer_features(_tensor(3))
        self.assertEqual(list(feats.keys()), list(FEATURE_NAMES))
        self.assertEqual(feature_vector(feats), [float(feats[name]) for name in FEATURE_NAMES])

    # --- D3: score() works on real P1 feature payloads ---------------------

    def test_score_works_on_real_feature_payload(self):
        features = _real_features_payload([_tensor(1), _tensor(2)])
        p_tamper, attributions, model_version = score(features)

        self.assertTrue(0.0 <= p_tamper <= 1.0)
        self.assertEqual(list(attributions.keys()), list(FEATURE_NAMES))
        self.assertEqual(model_version, _load_model()["model_version"])

        # Attributions are the exact linear contributions to the logit:
        # they sum to (logit - bias) and reproduce p_tamper.
        model = _load_model()
        x = classifier._aggregate_layers(features["static_features"])
        z = (x - np.asarray(model["means"])) / np.maximum(np.asarray(model["stds"]), 1e-12)
        expected_logit = float(np.asarray(model["weights"]) @ z + model["bias"])
        self.assertAlmostEqual(sum(attributions.values()), expected_logit - model["bias"], places=12)
        self.assertAlmostEqual(1.0 / (1.0 + np.exp(-expected_logit)), p_tamper, places=12)

    # --- D4: tamper signal where the training methodology supports it ------

    def test_tampered_signal_exceeds_clean_where_methodology_supports_it(self):
        # Deterministic synthetic separation verified for the committed model:
        # controlled perturbation and mantissa-bit modification raise the
        # tamper signal; lsb_manipulation is NOT separated (recorded
        # limitation of the synthetic-only model — deliberately unasserted).
        base = _tensor(7)
        p_clean = score(_real_features_payload([base]))[0]

        perturbed, _ = controlled_perturbation(base, epsilon=0.05, seed=7)
        p_perturbed = score(_real_features_payload([perturbed]))[0]
        self.assertGreater(p_perturbed, p_clean)

        mantissa, _ = mantissa_bit_modification(base, bits=8, seed=7)
        p_mantissa = score(_real_features_payload([mantissa]))[0]
        self.assertGreater(p_mantissa, p_clean)

    # --- D5: MOCK upstream can never produce VERIFIED-REAL P3 output -------

    def test_mock_upstream_cannot_produce_verified_real_output(self):
        mock_features = build_mock_features("TEST")  # producer=P1, mock_status=MOCK
        with self.assertRaisesRegex(ValueError, "VERIFIED-REAL"):
            score(mock_features)
        with self.assertRaisesRegex(ValueError, "VERIFIED-REAL"):
            build_ml_results(mock_features, "TEST")

    def test_rejects_non_p1_producer_and_stale_generation(self):
        features = _real_features_payload([_tensor(4)])
        foreign = copy.deepcopy(features)
        foreign["producer"] = "PX"
        with self.assertRaisesRegex(ValueError, "P1"):
            score(foreign)
        with self.assertRaisesRegex(ValueError, "stale P1 artifact generation"):
            build_ml_results(features, "OTHER-COMMIT")

    # --- D6: incompatible model dimensions fail closed ---------------------

    def test_incompatible_model_artifact_fails_closed(self):
        features = _real_features_payload([_tensor(11)])
        original_loader = classifier._load_model
        broken = copy.deepcopy(_load_model())
        broken["weights"] = broken["weights"][:-1]  # 9 entries != canonical 10
        classifier._load_model = lambda: broken
        try:
            with self.assertRaisesRegex(ValueError, "incompatible"):
                score(features)
            with self.assertRaisesRegex(ValueError, "incompatible"):
                build_ml_results(features, "TEST-GEN")
        finally:
            classifier._load_model = original_loader

        bad_order = copy.deepcopy(_load_model())
        bad_order["feature_names"] = list(reversed(bad_order["feature_names"]))
        with self.assertRaisesRegex(ValueError, "incompatible"):
            _validate_model_artifact(bad_order)

        non_finite = copy.deepcopy(_load_model())
        non_finite["means"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "incompatible"):
            _validate_model_artifact(non_finite)

    # --- D7: deterministic scoring -----------------------------------------

    def test_scoring_is_deterministic(self):
        features = _real_features_payload([_tensor(5), _tensor(6)])
        self.assertEqual(score(features), score(features))
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
        self.assertEqual(ml_results["model_version"], "sigtensor-logreg-synthetic-v1")


if __name__ == "__main__":
    unittest.main()