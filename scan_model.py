"""Root orchestration surface for the SigTensor scanning pipeline.

Two pipelines share one output contract (data/outputs/*.json):

Real pipeline (backend/ML, zero-trust):
    run_pipeline(model_path)
        SafeTensors artifact -> P1 zero-trust intake + static steganalysis
        features -> P3 tampering classification -> P2 risk aggregation
        -> validated JSON artifacts (mock_status="VERIFIED-REAL").

    CLI: python scan_model.py <model.safetensors>

Mock pipeline (Phase 1, preserved for tests and frontend smoke data):
    run_mock_pipeline() / python scan_model.py

Orchestration only: no detection, classification, or risk logic lives here
(enforced by tests.test_mock_pipeline.TestOrchestrationOwnership).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.common.utils import ROOT, get_generation_commit, validate_artifact
from src.p1_static_engine.analyzer import build_features, build_mock_features
from src.p2_behavioral_risk.prober import build_mock_risk_results, build_risk_results
from src.p3_ml_dashboard.classifier import build_ml_results, build_mock_ml_results

OUTPUT_DIR = ROOT / "data" / "outputs"
CONTRACT_DIR = ROOT / "contracts"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _validated_step(produce, out_name: str, schema_name: str, *args):
    """Run one stage, persist its artifact, and validate it against its contract.

    If persistence or validation fails, the artifact file is removed so a
    failed stage can never leave a stale/partial downstream artifact.
    """
    artifact_path = OUTPUT_DIR / out_name
    payload = produce(*args)
    try:
        _write_json(artifact_path, payload)
        validate_artifact(artifact_path, CONTRACT_DIR / schema_name)
    except Exception:
        artifact_path.unlink(missing_ok=True)
        raise
    return artifact_path


def run_pipeline(model_path: str | Path) -> dict[str, Path]:
    """End-to-end zero-trust scan of a SafeTensors artifact."""
    generation_commit = get_generation_commit()
    features_path = _validated_step(
        build_features, "features.json", "features.schema.json", model_path, generation_commit
    )
    features = json.loads(features_path.read_text(encoding="utf-8"))
    ml_path = _validated_step(
        lambda f, c: build_ml_results(f, c),
        "ml_results.json",
        "ml_results.schema.json",
        features,
        generation_commit,
    )
    ml_results = json.loads(ml_path.read_text(encoding="utf-8"))
    risk_path = _validated_step(
        lambda f, m, c: build_risk_results(f, m, c),
        "risk_results.json",
        "risk_results.schema.json",
        features,
        ml_results,
        generation_commit,
    )
    return {"features": features_path, "ml_results": ml_path, "risk_results": risk_path}


def run_mock_pipeline() -> dict[str, Path]:
    generation_commit = get_generation_commit()
    features = build_mock_features(generation_commit)
    features_path = OUTPUT_DIR / "features.json"
    _write_json(features_path, features)
    validate_artifact(features_path, CONTRACT_DIR / "features.schema.json")
    ml_results = build_mock_ml_results(features, generation_commit)
    ml_path = OUTPUT_DIR / "ml_results.json"
    _write_json(ml_path, ml_results)
    validate_artifact(ml_path, CONTRACT_DIR / "ml_results.schema.json")
    risk_results = build_mock_risk_results(ml_results, generation_commit)
    risk_path = OUTPUT_DIR / "risk_results.json"
    _write_json(risk_path, risk_results)
    validate_artifact(risk_path, CONTRACT_DIR / "risk_results.schema.json")
    return {"features": features_path, "ml_results": ml_path, "risk_results": risk_path}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        model_arg = Path(sys.argv[1])
        for name, path in run_pipeline(model_arg).items():
            print(f"{name}: {path}")
        print("SigTensor pipeline: PASS (artifacts contract-validated, mock_status=VERIFIED-REAL)")
    else:
        for name, path in run_mock_pipeline().items():
            print(f"{name}: {path}")
        print("Phase 1 mock pipeline: PASS (contract validation succeeded)")