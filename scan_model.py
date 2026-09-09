"""Root pipeline orchestration surface with zero-trust D2 handoff boundary."""

from __future__ import annotations
# scan_model.py (updated)
from src.p2_behavioral_risk.handoff import receive_trusted_model
# ... rest of the orchestration
import json
from pathlib import Path

from src.common.utils import ROOT, get_generation_commit, validate_artifact
from src.p1_static_engine.analyzer import TrustedModelContext, build_mock_features, intake_model
from src.p2_behavioral_risk.prober import build_mock_risk_results, receive_trusted_model
from src.p3_ml_dashboard.classifier import build_mock_ml_results

OUTPUT_DIR = ROOT / "data" / "outputs"
CONTRACT_DIR = ROOT / "contracts"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def handoff_trusted_model(context: TrustedModelContext) -> TrustedModelContext:
    """Pass the exact in-memory P1 context to P2; no artifact reload occurs."""
    return receive_trusted_model(context)


def run_real_intake_handoff(model_path: str | Path, declared_architecture: str) -> TrustedModelContext:
    """Execute P1 intake and hand the same trusted context directly to P2."""
    context = intake_model(Path(model_path), declared_architecture=declared_architecture)
    if context is None:
        raise ValueError("Integrity violated: intake did not produce a trusted context")
    return handoff_trusted_model(context)


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
    for name, path in run_mock_pipeline().items():
        print(f"{name}: {path}")
    print("Phase 1 mock pipeline: PASS (contract validation succeeded)")
