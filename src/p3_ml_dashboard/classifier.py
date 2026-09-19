"""P3 ML classification: authoritative CP4 LightGBM + TreeSHAP path + Phase 1 mock.

Real path (authoritative CP4 implementation, ported from
origin/phase-4/ml-classification-final `src/p3_ml_dashboard/classifier.py`
and adapted to the CURRENT branch P1 interface):

    train_final_classifier(clean_models, tampered_models, ...)
        -> per-layer canonical 10-feature rows extracted through the REAL P1
           extractor (src.p1_static_engine.analyzer.build_features)
        -> LightGBM binary booster -> artifacts/lightgbm_model.txt
        -> provenance record (dataset/source/extractor/model SHA-256)

    build_ml_results(features, generation_commit)
        -> contract-validated VERIFIED-REAL P1 features -> exact D1 feature
           matrix -> per-layer LightGBM probabilities p_l -> locked D10
           model-level aggregation P_tamper = max(p_l) -> TreeSHAP for the
           D10 classifier-evidence layer l_ML = argmax(p_l) -> ml_results
           payload (mock_status="VERIFIED-REAL").

Decision boundaries preserved (docs/DECISION_STATUS.md + the D10 decision
document docs/D10_P3_REMAINING_WORK_CROSS_VERIFICATION.md):
    - D5 owns S_static; D6 owns highest-risk-layer selection; D10 owns the
      model-level P_tamper aggregation; TreeSHAP explains classifier
      evidence only and never selects the D6 layer.
    - The public ml_results schema stays closed: no
      classifier_evidence_layer field is added (D10 decision doc #8).
    - Quantized classifier support remains blocked at the upstream P1
      contract boundary (D10 decision doc #6); no quantized path is
      fabricated here.

Dependencies: LightGBM/SHAP are D9-locked direct dependencies
(lightgbm==4.3.0, shap==0.45.1). They are imported lazily so the Phase-1
mock path stays importable everywhere, but the real path FAILS CLOSED with
an explicit message when they are missing. There is no substitute model and
no logistic-regression fallback anywhere in this module; the interim
logistic-regression production path has been fully replaced.

Model artifact (artifacts/lightgbm_model.txt):
    Generated only by train_final_classifier from real P1-extracted
    features. Loading is fail-closed: a missing file, an unparseable model,
    or a feature-name/order mismatch against the canonical FEATURE_NAMES is
    rejected before any prediction. Provenance/checksum metadata is
    persisted beside the artifact
    (artifacts/lightgbm_model.provenance.json, per artifacts/AGENT_RULES.md
    section 4).

Mock path (Phase 1, preserved for tests):
    build_mock_ml_results(features, generation_commit)
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Sequence

import numpy as np

from src.common.feature_names import (
    CANONICAL_FEATURE_COUNT,
    FEATURE_NAMES,
)
from src.common.utils import ROOT

# Re-exported for backwards compatibility with Phase 1 consumers/tests.
FEATURE_ORDER = FEATURE_NAMES

# Legacy interim logistic-regression artifact location (non-authoritative;
# kept only so train_classifier.py continues to function).
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH = MODELS_DIR / "classifier.json"

# Authoritative CP4 model artifact (artifacts/AGENT_RULES.md).
DEFAULT_MODEL_PATH = ROOT / "artifacts" / "lightgbm_model.txt"
DEFAULT_PROVENANCE_PATH = ROOT / "artifacts" / "lightgbm_model.provenance.json"
MODEL_VERSION = "lightgbm-phase4-final"

# Authoritative LightGBM training parameters (ported from
# origin/phase-4/ml-classification-final) plus explicit CPU determinism
# flags required by the Phase 4 reproducibility rule (no semantic change).
LGBM_TRAIN_PARAMS = {
    "objective": "binary",
    "metric": "binary_logloss",
    "verbosity": -1,
    "seed": 42,
    "feature_pre_filter": False,
    "deterministic": True,
    "force_col_wise": True,
}
NUM_BOOST_ROUND = 100


def _import_lightgbm():
    """Fail-closed LightGBM import (D9-locked direct dependency)."""
    try:
        import lightgbm as lgb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "LightGBM is required for the authoritative CP4 P3 classifier "
            "(D9-locked direct dependency: lightgbm==4.3.0). Install the "
            "approved D9 environment; substitute models are not permitted."
        ) from exc
    return lgb


def _import_shap():
    """Fail-closed SHAP import (D9-locked direct dependency)."""
    try:
        import shap
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "shap is required for authoritative TreeSHAP explainability "
            "(D9-locked direct dependency: shap==0.45.1). Install the "
            "approved D9 environment; linear-contribution placeholders are "
            "not permitted."
        ) from exc
    return shap


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _p1_source_hash() -> str:
    """SHA-256 of the real P1 extractor source used for training provenance."""
    from src.p1_static_engine import analyzer as p1_analyzer

    return _sha256_file(Path(p1_analyzer.__file__).resolve())


def _require_feature_contract(features: dict) -> list[dict]:
    if features.get("producer") != "P1":
        raise ValueError("Phase 4 P3 requires a P1 producer")
    if features.get("mock_status") != "VERIFIED-REAL":
        raise ValueError("Final classifier requires VERIFIED-REAL P1 feature data")
    layers = features.get("static_features")
    if not isinstance(layers, list) or not layers:
        raise ValueError("Malformed features: static_features must be a non-empty list")
    if features.get("layer_count") != len(layers):
        raise ValueError("Malformed features: layer_count does not match static_features")
    return layers


def _feature_matrix(features: dict) -> np.ndarray:
    rows = []
    for layer in _require_feature_contract(features):
        if not isinstance(layer, dict) or not isinstance(layer.get("layer_name"), str):
            raise ValueError("Malformed layer: layer_name is required")
        row = []
        for name in FEATURE_NAMES:
            if name not in layer:
                raise ValueError(f"Malformed layer missing feature {name}")
            value = layer[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Invalid feature value for {name}")
            value = float(value)
            if not np.isfinite(value):
                raise ValueError(f"Invalid non-finite feature value for {name}")
            row.append(value)
        rows.append(row)
    matrix = np.asarray(rows, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != CANONICAL_FEATURE_COUNT:
        raise ValueError("Feature matrix does not match D1 feature contract")
    return matrix


def extract_training_example(model_path: str | Path, generation_commit: str) -> tuple[dict, str]:
    """Extract one training model's features through the REAL P1 path.

    Adapted from origin/phase-4/ml-classification-final to the CURRENT P1
    interface (zero-trust intake + build_features); this branch's P1 API has
    no declared-architecture parameter.
    """
    from src.p1_static_engine.analyzer import build_features

    path = Path(model_path)
    features = build_features(path, generation_commit)
    if features.get("mock_status") != "VERIFIED-REAL":
        raise ValueError("P1 training extraction did not produce VERIFIED-REAL features")
    return features, _sha256_file(path)


def train_final_classifier(
    clean_models: Sequence[str | Path],
    tampered_models: Sequence[str | Path],
    *,
    generation_commit: str,
    dataset_id: str,
    output_path: str | Path = DEFAULT_MODEL_PATH,
) -> dict:
    """Train the authoritative LightGBM artifact from real P1-extracted features.

    D10 training contract (docs/D10_P3_REMAINING_WORK_CROSS_VERIFICATION.md
    #4): model-level clean/tampered labels are applied to layer-level feature
    rows; every row is extracted through the verified-real P1 extractor.
    Writes the LightGBM booster to `output_path` and returns its provenance
    record.
    """
    lgb = _import_lightgbm()
    if not clean_models or not tampered_models:
        raise ValueError("Final training requires both clean and tampered model sets")
    if not dataset_id or not dataset_id.strip():
        raise ValueError("dataset_id is required for training provenance")
    if not generation_commit:
        raise ValueError("generation_commit is required for training provenance")

    matrices: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    source_hashes: list[str] = []

    for path in clean_models:
        features, source_hash = extract_training_example(path, generation_commit)
        matrices.append(_feature_matrix(features))
        labels.append(np.zeros(len(features["static_features"]), dtype=np.int32))
        source_hashes.append(source_hash)

    for path in tampered_models:
        features, source_hash = extract_training_example(path, generation_commit)
        matrices.append(_feature_matrix(features))
        labels.append(np.ones(len(features["static_features"]), dtype=np.int32))
        source_hashes.append(source_hash)

    X = np.vstack(matrices)
    y = np.concatenate(labels)
    if len(np.unique(y)) != 2:
        raise ValueError("Training corpus must contain both clean and tampered labels")

    booster = lgb.train(
        LGBM_TRAIN_PARAMS,
        lgb.Dataset(X, label=y, feature_name=list(FEATURE_NAMES)),
        num_boost_round=NUM_BOOST_ROUND,
    )
    model_text = booster.model_to_string()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" is REQUIRED: LightGBM's C++ model parser rejects CRLF
    # line endings (Windows text-mode write would otherwise translate to
    # CRLF and the parser aborts the process). Matches the LF artifact
    # produced by the authoritative reference implementation on Linux.
    output.write_text(model_text, encoding="utf-8", newline="\n")

    return {
        "dataset_id": dataset_id,
        "dataset_source_sha256": _sha256_text("\n".join(sorted(source_hashes))),
        "p1_extractor_sha256": _p1_source_hash(),
        "generation_commit": generation_commit,
        "contract_version": "1.0",
        "feature_names": list(FEATURE_NAMES),
        "model_version": MODEL_VERSION,
        "model_sha256": _sha256_text(model_text),
        "training_rows": int(X.shape[0]),
        "clean_rows": int((y == 0).sum()),
        "tampered_rows": int((y == 1).sum()),
        "mock_status": "VERIFIED-REAL",
    }


def _load_final_model(model_path: str | Path = DEFAULT_MODEL_PATH):
    """Fail-closed load of the authoritative LightGBM artifact."""
    lgb = _import_lightgbm()
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Final classifier artifact not found: {path}")
    try:
        model = lgb.Booster(model_file=str(path))
    except Exception as exc:
        raise ValueError("Invalid LightGBM classifier artifact") from exc
    if model.feature_name() != list(FEATURE_NAMES):
        raise ValueError("Classifier feature names/order do not match D1")
    return model


def aggregate_p_tamper(probabilities) -> tuple[float, int]:
    """Locked D10 aggregation: P_tamper = max(p_l) over per-layer probabilities.

    Returns (p_tamper, classifier_evidence_layer_index). The index selects
    the TreeSHAP evidence layer ONLY; it is never added to the public
    ml_results contract (D10 decision doc #8).
    """
    p = np.asarray(probabilities, dtype=np.float64)
    if p.ndim != 1 or p.size == 0:
        raise ValueError("D10 aggregation requires at least one layer probability")
    if not np.all(np.isfinite(p)):
        raise ValueError("D10 aggregation requires finite per-layer probabilities")
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("D10 aggregation requires per-layer probabilities in [0, 1]")
    idx = int(np.argmax(p))
    return float(p[idx]), idx


def build_ml_results(
    features: dict,
    generation_commit: str,
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> dict:
    """Authoritative CP4 payload: LightGBM p_l -> D10 max(p_l) -> TreeSHAP(argmax layer).

    Fail-closed end to end: stale generation rejection, canonical feature
    matrix validation, artifact validation, finite [0,1] per-layer
    probabilities, and a TreeSHAP/additivity correspondence check against the
    actual LightGBM margin of the explained layer.
    """
    shap = _import_shap()
    if features.get("generation_commit") != generation_commit:
        raise ValueError("Phase 4 P3 rejects stale P1 artifact generation")
    X = _feature_matrix(features)
    model = _load_final_model(model_path)

    probabilities = np.asarray(model.predict(X), dtype=np.float64)
    if probabilities.shape[0] != X.shape[0]:
        raise ValueError(
            "Classifier produced an unexpected number of per-layer predictions"
        )
    if not np.isfinite(probabilities).all() or np.any(
        (probabilities < 0.0) | (probabilities > 1.0)
    ):
        raise ValueError("Classifier produced invalid P_tamper values")

    # Locked D10 rule: P_tamper = max(p_l); explain l_ML = argmax(p_l).
    p_tamper, evidence_layer = aggregate_p_tamper(probabilities)

    explainer = shap.TreeExplainer(model)
    raw = explainer.shap_values(X[evidence_layer : evidence_layer + 1])
    shap_values = np.asarray(raw[-1] if isinstance(raw, list) else raw)
    if shap_values.ndim == 3:
        shap_values = shap_values[..., -1]  # positive-class contributions (binary)
    if shap_values.ndim == 2:
        shap_values = shap_values[0]
    if shap_values.shape != (len(FEATURE_NAMES),) or not np.isfinite(shap_values).all():
        raise ValueError("TreeSHAP output does not match D1")

    # Explanations must correspond to the actual model prediction of the
    # explained layer: expected_value + sum(shap) == raw LightGBM margin.
    expected_value = np.asarray(explainer.expected_value).reshape(-1)
    base = float(expected_value[-1]) if expected_value.size > 1 else float(expected_value[0])
    raw_margin = float(
        np.asarray(
            model.predict(X[evidence_layer : evidence_layer + 1], raw_score=True),
            dtype=np.float64,
        )[0]
    )
    if not math.isclose(base + float(shap_values.sum()), raw_margin, rel_tol=1e-6, abs_tol=1e-6):
        raise ValueError("TreeSHAP explanation does not correspond to the model prediction")

    return {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "p_tamper": p_tamper,
        "shap_attributions": {
            name: float(value) for name, value in zip(FEATURE_NAMES, shap_values)
        },
        "model_version": MODEL_VERSION,
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