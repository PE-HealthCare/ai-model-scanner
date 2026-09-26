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
from unittest.mock import patch

import numpy as np
from jsonschema import Draft202012Validator

from src.common.utils import ROOT
from src.common.feature_names import (
    FEATURE_NAMES,
    feature_vector,
)
from src.p1_static_engine.analyzer import (
    build_mock_features,
    intake_model,
    extract_features,
)
from torchvision.models import resnet18
from src.p3_ml_dashboard.classifier import (
    DEFAULT_MODEL_PATH,
    DEFAULT_QUANTIZED_MODEL_PATH,
    DEFAULT_QUANTIZED_PROVENANCE_PATH,
    FP_ONLY_FEATURES,
    MODEL_VERSION,
    QUANTIZED_FEATURE_NAMES,
    QUANTIZED_MODEL_VERSION,
    _feature_matrix,
    _load_final_model,
    _load_quantized_model,
    _quantized_feature_matrix,
    aggregate_p_tamper,
    build_ml_results,
    build_mock_ml_results,
    build_quantized_ml_results,
    extract_training_example,
    train_final_classifier,
    train_quantized_classifier,
)

CONTRACT_DIR = ROOT / "contracts"


def _tensor(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 0.1, (32, 64)).astype(np.float32)


def _real_features_payload(
    tensors: list[np.ndarray], generation_commit: str = "TEST-GEN"
) -> dict:
    """Contract-valid VERIFIED-REAL P1 payload built by the current P1 extractor.

    Uses the *current* real P1 ResNet18 intake boundary for the test fixture, then
    overwrites the selected real layer tensors with synthetic tensors so the payload
    exercises the canonical 10-feature contract extraction path. Callers must
    pass at least 3 tensors (P1 requires a >=3-layer selection).
    """
    from safetensors.torch import save_file

    import torch

    with tempfile.TemporaryDirectory() as td:
        model_path = Path(td) / "model.safetensors"
        trusted = resnet18()
        sd = trusted.state_dict()
        # Overwrite real, varying (non-constant) float layers with the synthetic
        # tensors, tiled to each target shape, keeping all other
        # architecture-valid keys intact so P1 intake still validates.
        selected_keys = ["conv1.weight", "layer1.0.conv1.weight", "layer1.0.conv2.weight"][
            : max(1, len(tensors))
        ]
        ordered_tensors = list(sd.values())
        for key, t in zip(selected_keys, tensors):
            idx = list(sd.keys()).index(key)
            flat = np.ascontiguousarray(t).reshape(-1)
            need = int(sd[key].numel())
            tiled = np.tile(flat, (need + flat.size - 1) // flat.size)[:need]
            tiled = tiled.reshape(tuple(sd[key].shape)).astype(np.float32)
            ordered_tensors[idx] = torch.from_numpy(np.ascontiguousarray(tiled))
        save_file(dict(zip(sd.keys(), ordered_tensors)), model_path)
        context = intake_model(model_path, declared_architecture="resnet18")
        if context is None:
            raise ValueError("current P1 intake returned None for test fixture")
        return extract_features(
            context,
            generation_commit,
            layer_names=selected_keys,
        )


class TestRealClassifierPath(unittest.TestCase):
    def setUp(self):
        with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as fh:
            features_schema = json.load(fh)
        Draft202012Validator(features_schema).validate(_real_features_payload([_tensor(0), _tensor(1), _tensor(2)]))
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

        feats = _real_features_payload([_tensor(3), _tensor(30), _tensor(31)])["static_features"][0]
        self.assertEqual(
            [k for k in feats.keys() if k != "layer_name"], list(FEATURE_NAMES)
        )
        self.assertEqual(feature_vector(feats), [float(feats[name]) for name in FEATURE_NAMES])
        # --- real path: LightGBM inference on real P1 features ------------------

    def test_build_ml_results_consumes_real_features(self):
        features = _real_features_payload([_tensor(1), _tensor(2), _tensor(3)])
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

        features = _real_features_payload([_tensor(10), _tensor(11), _tensor(12)])
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
        features = _real_features_payload([_tensor(4), _tensor(40), _tensor(41)])
        foreign = copy.deepcopy(features)
        foreign["producer"] = "PX"
        with self.assertRaisesRegex(ValueError, "P1"):
            build_ml_results(foreign, "TEST-GEN")
        with self.assertRaisesRegex(ValueError, "stale P1 artifact generation"):
            build_ml_results(features, "OTHER-COMMIT")

    def test_non_finite_feature_rejected_without_imputation(self):
        features = _real_features_payload([_tensor(4), _tensor(42), _tensor(43)])
        features["static_features"][0]["entropy"] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            build_ml_results(features, "TEST-GEN")

    # --- determinism ---------------------------------------------------------

    def test_scoring_is_deterministic(self):
        features = _real_features_payload([_tensor(5), _tensor(6), _tensor(7)])
        self.assertEqual(
            build_ml_results(features, "TEST-GEN"),
            build_ml_results(features, "TEST-GEN"),
        )
        # --- contract compatibility of the real P3 payload ----------------------

    def test_real_ml_results_payload_is_contract_valid(self):
        ml_results = build_ml_results(_real_features_payload([_tensor(5), _tensor(50), _tensor(51)]), "TEST-GEN")
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

    # --- CP4 §4: mock leakage MUST NOT reach final training -----------------
    # extract_training_example/train_final_classifier are given a real
    # on-disk model_path but the P1 extractor they call is mocked to return
    # non-VERIFIED-REAL (MOCK) output. This must fail closed with NO model
    # artifact written, proving mock data cannot leak into the training
    # corpus even when the caller supplies a real-looking file path.

    def test_training_extraction_rejects_mock_upstream_features(self):
        mock_payload = build_mock_features("TRAIN-GEN")  # producer=P1, mock_status=MOCK
        with tempfile.TemporaryDirectory() as td:
            fake_model = Path(td) / "clean_looking.safetensors"
            fake_model.write_bytes(b"not a real safetensors payload")
            with patch(
                "src.p1_static_engine.analyzer.intake_model",
                return_value=object(),
            ), patch(
                "src.p1_static_engine.analyzer.extract_features",
                return_value=mock_payload,
            ):
                with self.assertRaisesRegex(ValueError, "VERIFIED-REAL"):
                    extract_training_example(fake_model, "TRAIN-GEN")

    def test_train_final_classifier_rejects_mock_leakage_and_writes_no_artifact(self):
        mock_payload = build_mock_features("TRAIN-GEN")
        with tempfile.TemporaryDirectory() as td:
            clean = Path(td) / "clean.safetensors"
            tampered = Path(td) / "tampered.safetensors"
            clean.write_bytes(b"x")
            tampered.write_bytes(b"x")
            output_path = Path(td) / "would_be_model.txt"
            with patch(
                "src.p1_static_engine.analyzer.intake_model",
                return_value=object(),
            ), patch(
                "src.p1_static_engine.analyzer.extract_features",
                return_value=mock_payload,
            ):
                with self.assertRaisesRegex(ValueError, "VERIFIED-REAL"):
                    train_final_classifier(
                        [clean],
                        [tampered],
                        generation_commit="TRAIN-GEN",
                        dataset_id="mock-leakage-regression",
                        output_path=output_path,
                    )
            self.assertFalse(
                output_path.exists(),
                "No final model artifact may be written when upstream is MOCK",
            )

    # --- CP4 §4: placeholder feature source (P3-owned heuristic guard) -------
    # P1's documented fallback path (work-distribution.txt: neutral s_static
    # when statistical tests fail) can produce a schema-valid, correctly
    # labeled VERIFIED-REAL payload whose values are placeholder, not real
    # signal. The contract has no flag for this, so classifier.py rejects
    # any multi-layer model whose layers all produce an identical feature
    # vector as a placeholder/degenerate-data fingerprint.

    def test_train_final_classifier_rejects_placeholder_identical_layer_vectors(self):
        placeholder_layer = {
            "layer_name": "placeholder.layer0",
            "entropy": 0.5, "pov_chi2": 0.5, "lsb_kl": 0.5, "ks_stat": 0.5,
            "mean": 0.5, "std": 0.5, "skewness": 0.5, "kurtosis": 0.5,
            "sparsity": 0.5, "outlier_pct": 0.5,
        }
        placeholder_payload = {
            "producer": "P1",
            "mock_status": "VERIFIED-REAL",
            "contract_version": "1.0",
            "generation_commit": "TRAIN-GEN",
            "input_domain": "VISION",
            "is_quantized": False,
            "layer_count": 3,
            "static_features": [
                {**placeholder_layer, "layer_name": f"placeholder.layer{i}"}
                for i in range(3)
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            clean = Path(td) / "clean.safetensors"
            tampered = Path(td) / "tampered.safetensors"
            clean.write_bytes(b"x")
            tampered.write_bytes(b"x")
            output_path = Path(td) / "would_be_model.txt"
            with patch(
                "src.p1_static_engine.analyzer.intake_model",
                return_value=object(),
            ), patch(
                "src.p1_static_engine.analyzer.extract_features",
                return_value=placeholder_payload,
            ):
                with self.assertRaisesRegex(ValueError, "Placeholder/degenerate"):
                    train_final_classifier(
                        [clean],
                        [tampered],
                        generation_commit="TRAIN-GEN",
                        dataset_id="placeholder-regression",
                        output_path=output_path,
                    )
            self.assertFalse(output_path.exists())

    def test_train_final_classifier_accepts_real_varying_layers(self):
        """Sanity check: the placeholder guard must not reject genuine
        multi-layer models whose layers naturally vary (regression guard
        against over-triggering on real data)."""
        real_payload = _real_features_payload(
            [_tensor(20), _tensor(21), _tensor(22)], generation_commit="TRAIN-GEN"
        )
        with tempfile.TemporaryDirectory() as td:
            clean = Path(td) / "clean.safetensors"
            tampered = Path(td) / "tampered.safetensors"
            clean.write_bytes(b"x")
            tampered.write_bytes(b"x")
            output_path = Path(td) / "model.txt"
            with patch(
                "src.p1_static_engine.analyzer.intake_model",
                return_value=object(),
            ), patch(
                "src.p1_static_engine.analyzer.extract_features",
                return_value=real_payload,
            ):
                result = train_final_classifier(
                    [clean],
                    [tampered],
                    generation_commit="TRAIN-GEN",
                    dataset_id="placeholder-regression-sanity",
                    output_path=output_path,
                )
                self.assertTrue(output_path.exists())
        self.assertEqual(result["mock_status"], "VERIFIED-REAL")

    # --- CP4 §7: malformed-layer adversarial matrix --------------------------

    def test_feature_matrix_rejects_missing_feature_in_layer(self):
        features = _real_features_payload([_tensor(4), _tensor(44), _tensor(45)])
        del features["static_features"][0]["entropy"]
        with self.assertRaisesRegex(ValueError, "missing feature"):
            build_ml_results(features, "TEST-GEN")

    def test_feature_matrix_rejects_layer_count_mismatch(self):
        features = _real_features_payload([_tensor(4), _tensor(5), _tensor(46)])
        features["layer_count"] = 1
        with self.assertRaisesRegex(ValueError, "layer_count"):
            build_ml_results(features, "TEST-GEN")

    def test_feature_matrix_rejects_missing_layer_name(self):
        features = _real_features_payload([_tensor(4), _tensor(47), _tensor(48)])
        del features["static_features"][0]["layer_name"]
        with self.assertRaisesRegex(ValueError, "layer_name"):
            build_ml_results(features, "TEST-GEN")

    def test_feature_matrix_rejects_empty_static_features(self):
        features = _real_features_payload([_tensor(4), _tensor(49), _tensor(52)])
        features["static_features"] = []
        features["layer_count"] = 0
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            build_ml_results(features, "TEST-GEN")

    def test_feature_matrix_tolerates_extra_unknown_layer_fields(self):
        """Extra/unrecognized fields on a layer are informational only; the
        classifier reads exactly the canonical D1 fields by name. This is
        documented behavior, not a gap: unknown keys must not break or
        silently alter contract-valid scoring."""
        features = _real_features_payload([_tensor(4), _tensor(53), _tensor(54)])
        features["static_features"][0]["debug_note"] = "unexpected extra field"
        result = build_ml_results(features, "TEST-GEN")
        self.assertEqual(result["mock_status"], "VERIFIED-REAL")

    # --- CP4 §6: staleness on feature name/order change ----------------------

    def test_load_final_model_rejects_reordered_features(self):
        import lightgbm as lgb

        permuted = list(FEATURE_NAMES)
        permuted[0], permuted[1] = permuted[1], permuted[0]
        rng = np.random.default_rng(0)
        X = rng.normal(size=(10, len(permuted)))
        y = np.array([0, 1] * 5)
        booster = lgb.train(
            {"objective": "binary", "verbosity": -1},
            lgb.Dataset(X, label=y, feature_name=permuted),
            num_boost_round=2,
        )
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "reordered_model.txt"
            bad.write_text(booster.model_to_string(), encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "do not match D1"):
                _load_final_model(bad)

    def test_load_final_model_rejects_renamed_feature(self):
        import lightgbm as lgb

        renamed = list(FEATURE_NAMES)
        renamed[0] = "renamed_feature_not_in_d1"
        rng = np.random.default_rng(1)
        X = rng.normal(size=(10, len(renamed)))
        y = np.array([0, 1] * 5)
        booster = lgb.train(
            {"objective": "binary", "verbosity": -1},
            lgb.Dataset(X, label=y, feature_name=renamed),
            num_boost_round=2,
        )
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "renamed_model.txt"
            bad.write_text(booster.model_to_string(), encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "do not match D1"):
                _load_final_model(bad)

    # --- CP4 §7: malformed ml_results.json ------------------------------------

    def test_malformed_ml_results_payload_fails_contract_schema(self):
        with (CONTRACT_DIR / "ml_results.schema.json").open(encoding="utf-8") as fh:
            schema = json.load(fh)
        malformed = build_ml_results(_real_features_payload([_tensor(5), _tensor(55), _tensor(56)]), "TEST-GEN")
        del malformed["p_tamper"]  # required field per contract
        with self.assertRaises(Exception):
            Draft202012Validator(schema).validate(malformed)


def _quantized_payload(ks_values=(0.2, 0.7)) -> dict:
    layers = []
    for i, ks in enumerate(ks_values):
        layer = {"layer_name": f"q.layer{i}", "ks_stat": ks}
        for name in FP_ONLY_FEATURES:
            layer[name] = None
        layers.append(layer)
    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "TEST-GEN",
        "input_domain": "VISION",
        "is_quantized": True,
        "layer_count": len(layers),
        "static_features": layers,
    }


class TestQuantizedClassifierStage1(unittest.TestCase):
    """D11 Stage 1: quantized validator + train_quantized_classifier only."""

    def test_valid_quantized_input(self):
        matrix = _quantized_feature_matrix(_quantized_payload())
        self.assertEqual(matrix.shape, (2, 1))
        self.assertTrue(((matrix >= 0.0) & (matrix <= 1.0)).all())

    def test_fp_input_rejected(self):
        payload = _quantized_payload()
        payload["is_quantized"] = False
        with self.assertRaisesRegex(ValueError, "is_quantized"):
            _quantized_feature_matrix(payload)

    def test_missing_ks_stat_rejected(self):
        payload = _quantized_payload()
        del payload["static_features"][0]["ks_stat"]
        with self.assertRaisesRegex(ValueError, "ks_stat"):
            _quantized_feature_matrix(payload)

    def test_nan_inf_ks_stat_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            payload = _quantized_payload(ks_values=(bad,))
            with self.assertRaisesRegex(ValueError, "non-finite"):
                _quantized_feature_matrix(payload)

    def test_ks_stat_outside_range_rejected(self):
        for bad in (-0.01, 1.01):
            payload = _quantized_payload(ks_values=(bad,))
            with self.assertRaisesRegex(ValueError, "outside"):
                _quantized_feature_matrix(payload)

    def test_fp_only_feature_non_null_rejected(self):
        for name in FP_ONLY_FEATURES:
            payload = _quantized_payload()
            payload["static_features"][0][name] = 0.0
            with self.assertRaisesRegex(ValueError, name):
                _quantized_feature_matrix(payload)

    def test_feature_names_exactly_ks_stat(self):
        self.assertEqual(list(QUANTIZED_FEATURE_NAMES), ["ks_stat"])

    def test_separate_quantized_artifact_paths(self):
        self.assertEqual(
            DEFAULT_QUANTIZED_MODEL_PATH.name, "lightgbm_model_quantized.txt"
        )
        self.assertEqual(
            DEFAULT_QUANTIZED_PROVENANCE_PATH.name,
            "lightgbm_model_quantized.provenance.json",
        )
        self.assertNotEqual(str(DEFAULT_QUANTIZED_MODEL_PATH), str(DEFAULT_MODEL_PATH))

    def test_train_quantized_writes_separate_artifact_and_provenance(self):
        clean_payload = _quantized_payload(ks_values=(0.1, 0.2, 0.3))
        tampered_payload = _quantized_payload(ks_values=(0.8, 0.9, 0.95))
        with tempfile.TemporaryDirectory() as td:
            clean = Path(td) / "clean.safetensors"
            tampered = Path(td) / "tampered.safetensors"
            clean.write_bytes(b"x")
            tampered.write_bytes(b"x")
            model_out = Path(td) / "lightgbm_model_quantized.txt"
            prov_out = Path(td) / "lightgbm_model_quantized.provenance.json"
            with patch(
                "src.p3_ml_dashboard.classifier.extract_training_example",
                side_effect=[(clean_payload, "a" * 64), (tampered_payload, "b" * 64)],
            ):
                provenance = train_quantized_classifier(
                    [clean],
                    [tampered],
                    generation_commit="TEST-GEN",
                    dataset_id="quantized-stage1-test",
                    output_path=model_out,
                    provenance_path=prov_out,
                )
            self.assertTrue(model_out.is_file())
            self.assertGreater(model_out.stat().st_size, 0)
            self.assertTrue(prov_out.is_file())
            on_disk = json.loads(prov_out.read_text(encoding="utf-8"))
            self.assertEqual(on_disk, provenance)
            self.assertEqual(provenance["feature_names"], ["ks_stat"])
            self.assertEqual(provenance["mock_status"], "VERIFIED-REAL")
            self.assertEqual(provenance["generation_commit"], "TEST-GEN")
            self.assertEqual(provenance["dataset_id"], "quantized-stage1-test")
            self.assertIn("p1_extractor_sha256", provenance)
            self.assertIn("model_sha256", provenance)
            self.assertEqual(provenance["clean_rows"], 3)
            self.assertEqual(provenance["tampered_rows"], 3)
            self.assertEqual(provenance["training_rows"], 6)
            import lightgbm as lgb

            booster = lgb.Booster(model_file=str(model_out))
            self.assertEqual(booster.feature_name(), ["ks_stat"])


def _tiny_quantized_model(path: Path) -> None:
    """Train a minimal deterministic ks_stat-only booster (test fixture only)."""
    import lightgbm as lgb

    rng = np.random.default_rng(7)
    ks = rng.uniform(0.0, 1.0, size=(40, 1))
    y = (ks[:, 0] > 0.5).astype(np.int32)
    booster = lgb.train(
        {"objective": "binary", "verbosity": -1, "seed": 7, "deterministic": True,
         "force_col_wise": True, "min_data_in_leaf": 5},
        lgb.Dataset(ks, label=y, feature_name=["ks_stat"]),
        num_boost_round=10,
    )
    path.write_text(booster.model_to_string(), encoding="utf-8", newline="\n")


class TestQuantizedClassifierStage2(unittest.TestCase):
    """D11 Stage 2: quantized inference (p_l^Q -> max -> ks_stat TreeSHAP)."""

    def test_quantized_model_loading(self):
        import lightgbm as lgb

        with tempfile.TemporaryDirectory() as td:
            good = Path(td) / "q.txt"
            _tiny_quantized_model(good)
            model = _load_quantized_model(good)
            self.assertEqual(model.feature_name(), ["ks_stat"])
            with self.assertRaises(FileNotFoundError):
                _load_quantized_model(Path(td) / "missing.txt")
            bad = Path(td) / "fp.txt"
            rng = np.random.default_rng(0)
            X = rng.normal(size=(10, 10))
            y = np.array([0, 1] * 5)
            booster = lgb.train(
                {"objective": "binary", "verbosity": -1},
                lgb.Dataset(X, label=y, feature_name=list(FEATURE_NAMES)),
                num_boost_round=2,
            )
            bad.write_text(booster.model_to_string(), encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "D11"):
                _load_quantized_model(bad)

    def test_per_layer_max_argmax_shap_additivity(self):
        import lightgbm as lgb
        import shap

        payload = _quantized_payload(ks_values=(0.05, 0.5, 0.95))
        with tempfile.TemporaryDirectory() as td:
            model_file = Path(td) / "q.txt"
            _tiny_quantized_model(model_file)
            result = build_quantized_ml_results(payload, "TEST-GEN",
                                                model_path=model_file)
            booster = lgb.Booster(model_file=str(model_file))
            X = _quantized_feature_matrix(payload)
            expected_p = np.asarray(booster.predict(X), dtype=np.float64)
            self.assertAlmostEqual(result["p_tamper"], float(expected_p.max()))
            argmax = int(np.argmax(expected_p))
            self.assertEqual(list(result["shap_attributions"].keys()), ["ks_stat"])
            self.assertTrue(np.isfinite(list(result["shap_attributions"].values())).all())
            self.assertEqual(result["mock_status"], "VERIFIED-REAL")
            self.assertEqual(result["model_version"], QUANTIZED_MODEL_VERSION)
            explainer = shap.TreeExplainer(booster)
            raw = explainer.shap_values(X[argmax : argmax + 1])
            arr = np.asarray(raw[-1] if isinstance(raw, list) else raw)
            if arr.ndim == 3:
                arr = arr[..., -1]
            if arr.ndim == 2:
                arr = arr[0]
            base = float(np.asarray(explainer.expected_value).reshape(-1)[-1])
            margin = float(
                np.asarray(booster.predict(X[argmax : argmax + 1], raw_score=True))[0]
            )
            self.assertAlmostEqual(base + float(arr.sum()), margin, places=5)
            self.assertAlmostEqual(
                result["shap_attributions"]["ks_stat"], float(arr[0]), places=9
            )

    def test_invalid_quantized_input_rejected_no_fp_fallback(self):
        payload = _quantized_payload()
        with tempfile.TemporaryDirectory() as td:
            model_file = Path(td) / "q.txt"
            _tiny_quantized_model(model_file)
            bad = _quantized_payload()
            bad["static_features"][0]["entropy"] = 0.5
            with self.assertRaises(ValueError):
                build_quantized_ml_results(bad, "TEST-GEN", model_path=model_file)
            with self.assertRaisesRegex(ValueError, "stale"):
                build_quantized_ml_results(payload, "WRONG-GEN", model_path=model_file)
            fp_payload = _quantized_payload()
            fp_payload["is_quantized"] = False
            with self.assertRaisesRegex(ValueError, "is_quantized"):
                build_quantized_ml_results(fp_payload, "TEST-GEN",
                                           model_path=model_file)
            with self.assertRaises(FileNotFoundError):
                build_quantized_ml_results(
                    payload, "TEST-GEN", model_path=Path(td) / "missing.txt"
                )


if __name__ == "__main__":
    unittest.main()