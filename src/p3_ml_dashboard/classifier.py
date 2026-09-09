"""P3 ML classification: real tampering classifier + Phase 1 mock.

Real path:
    build_ml_results(features, generation_commit)
        -> canonical 10-feature vector per layer (shared construction path
           with training: src/common/feature_names.feature_vector) ->
           element-count-weighted layer aggregation -> standardization with
           the committed model's training statistics -> trained
           logistic-regression scorer -> p_tamper + per-feature linear
           attributions (mock_status="VERIFIED-REAL").

Training (train_classifier.py, committed output models/classifier.json):
    clean tensors (synthetic Gaussian-weight generators, seeded) vs. tensors
    tampered with the three APPROVED P3 methods from synthetic_tamper.py
    (controlled_perturbation, lsb_manipulation, mantissa_bit_modification).
    Every example is labeled with its method; the committed model JSON
    records full provenance (training_data_status="SYNTHETIC",
    authoritative=false, seeds) per the project's scientific-integrity rules.
    Training and inference consume the SAME canonical 10-feature
    representation in the SAME order; the committed artifact is re-derived
    exactly by the committed trainer code (verified by tests, no retraining).

Explainability:
    No SHAP library (dependency-light implementation). Attributions are the
    exact per-feature contributions to the logit of the standardized linear
    model: attribution_f = weight_f * (x_f - mean_f) / std_f, so they sum to
    (logit - bias) by construction. These are linear model contributions,
    NOT SHAP estimates and NOT TreeSHAP. The contract field name
    "shap_attributions" is retained solely for schema compatibility.

Model artifact (models/classifier.json):
    feature_names, means, stds, weights, bias, training provenance
    (training_data_status="SYNTHETIC", authoritative=false). The artifact is
    validated against the canonical feature count and ordering before every
    scoring; any incompatibility fails closed. Scoring is deterministic.

Mock path (Phase 1, preserved for tests):
    build_mock_ml_results(features, generation_commit)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from src.common.feature_names import (
    CANONICAL_FEATURE_COUNT,
    FEATURE_NAMES,
    feature_vector,
)

# Re-exported for backwards compatibility with Phase 1 consumers/tests.
FEATURE_ORDER = FEATURE_NAMES

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH = MODELS_DIR / "classifier.json"


def _load_model() -> dict:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            "trained classifier model not found at "
            f"{MODEL_PATH}; run `python train_classifier.py` first"
        )
    with MODEL_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _validate_model_artifact(model: dict) -> None:
    """Fail closed on any model/artifact incompatibility with the canonical features."""
    if model.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError(
            "model artifact incompatible with canonical features: "
            "feature_names must equal the canonical FEATURE_NAMES ordering"
        )
    for field in ("means", "stds", "weights"):
        values = model.get(field)
        if not isinstance(values, list) or len(values) != CANONICAL_FEATURE_COUNT:
            raise ValueError(
                "model artifact incompatible with canonical features: "
                f"{field!r} must have exactly {CANONICAL_FEATURE_COUNT} entries"
            )
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            raise ValueError(
                "model artifact incompatible with canonical features: "
                f"{field!r} contains non-finite values"
            )
    bias = model.get("bias")
    if not isinstance(bias, (int, float)) or not math.isfinite(float(bias)):
        raise ValueError(
            "model artifact incompatible with canonical features: bias must be finite"
        )


def _aggregate_layers(static_features: list[dict]) -> np.ndarray:
    """Element-count-weighted mean of per-layer canonical feature vectors.

    Returns the SAME 10-feature representation the committed model was
    trained on. The features contract carries no per-layer element counts,
    so every layer weighs 1 today; if n_elements is ever added to the
    contract, this aggregation honors it without a semantic change.
    """
    weights = np.array(
        [max(int(layer.get("n_elements", 1)), 1) for layer in static_features],
        dtype=np.float64,
    )
    matrix = np.array([feature_vector(layer) for layer in static_features], dtype=np.float64)
    return (matrix * weights[:, None]).sum(axis=0) / weights.sum()


def score(features: dict) -> tuple[float, dict[str, float], str]:
    """Score a VERIFIED-REAL P1 features payload with the committed model.

    Returns (p_tamper, attributions, model_version). Deterministic. Raises
    ValueError (fail closed) on any lifecycle or model-artifact
    incompatibility.
    """
    if features.get("producer") != "P1":
        raise ValueError("real P3 scorer requires a P1 features artifact")
    if features.get("mock_status") != "VERIFIED-REAL":
        raise ValueError(
            "real P3 scorer requires VERIFIED-REAL features; MOCK artifacts "
            "must never be scored into VERIFIED-REAL output"
        )
    layers = features["static_features"]
    if not layers:
        raise ValueError("P3 scoring requires at least one analyzed layer")

    x = _aggregate_layers(layers)
    if not np.all(np.isfinite(x)):
        # Invalid data (NaN/inf) is invalid — do not impute (solution-architecture #23).
        raise ValueError("P3 scoring requires finite features; refusing non-finite input")

    model = _load_model()
    _validate_model_artifact(model)
    means = np.array(model["means"], dtype=np.float64)
    stds = np.array(model["stds"], dtype=np.float64)
    weights = np.array(model["weights"], dtype=np.float64)
    bias = float(model["bias"])

    x_std = (x - means) / np.maximum(stds, 1e-12)
    logit = float(weights @ x_std + bias)
    p_tamper = 1.0 / (1.0 + np.exp(-logit))

    # Exact linear per-feature contributions to the logit (NOT SHAP, NOT
    # TreeSHAP): attribution_f = weight_f * z_f, so the attributions sum to
    # (logit - bias) by construction.
    attributions = {
        name: float(weights[i] * x_std[i]) for i, name in enumerate(FEATURE_NAMES)
    }

    return float(p_tamper), attributions, str(model["model_version"])


def build_ml_results(features: dict, generation_commit: str) -> dict:
    """Real ML classification payload for the pipeline (P3, VERIFIED-REAL)."""
    if features.get("generation_commit") != generation_commit:
        raise ValueError("P3 rejects stale P1 artifact generation")
    p_tamper, attributions, model_version = score(features)
    return {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "p_tamper": p_tamper,
        "shap_attributions": attributions,
        "model_version": model_version,
    }


def build_mock_ml_results(features: dict, generation_commit: str) -> dict:
    if features.get("producer") != "P1" or features.get("mock_status") != "MOCK":
        raise ValueError("Phase 1 mock P3 requires a P1 MOCK features artifact")
    if features.get("generation_commit") != generation_commit:
        raise ValueError("Phase 1 P3 rejects stale P1 artifact generation")
    shap_values = (0.12, 0.05, 0.02, 0.04, 0.03, 0.02, 0.01, 0.02, 0.03, 0.01)
    return {
        "producer": "P3", "mock_status": "MOCK", "contract_version": "1.0",
        "generation_commit": generation_commit, "p_tamper": 0.08,
        "shap_attributions": dict(zip(FEATURE_ORDER, shap_values)),
        "model_version": "mock-lightgbm-phase1",
    }