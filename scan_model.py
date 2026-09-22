"""Root orchestration surface for the SigTensor scanning pipeline.

Two pipelines share one output contract (data/outputs/*.json):

Real pipeline (backend/ML, zero-trust):
    run_pipeline(model_path, declared_architecture="resnet18")
        SafeTensors artifact -> P1 zero-trust intake + static steganalysis
        features -> P3 tampering classification -> D2 declared-resnet18 trusted
        construction + in-process handoff -> P2 behavioral probing and risk
        aggregation (P2 persists risk_results.json itself)
        -> validated JSON artifacts (mock_status="VERIFIED-REAL").

    The architecture is always DECLARED by the caller and never detected: the
    only construction path is the approved resnet18 one, and D2 validates the
    state_dict against it. P2 never reloads the model (D2 handoff).

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
from src.p1_static_engine.analyzer import extract_features, intake_model
from src.p3_ml_dashboard.classifier import build_ml_results, build_mock_ml_results

# P2 and the D2 bridge are imported lazily inside each pipeline: the recovered
# live P2 modules pull in the behavioral probing stack (torch/scipy) and the D2
# bridge pulls in safetensors. Local imports keep this orchestrator importable
# without the ML stack and keep every other stage's failure isolated.
SUPPORTED_ARCHITECTURES = ("resnet18",)

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


def _validated_p2_step(produce, out_name: str, schema_name: str) -> Path:
    """Run a stage that persists its own artifact, then validate it.

    P2 writes risk_results.json itself (via its own analyzer), so there is no
    payload for the orchestrator to persist. The fail-closed cleanup of
    _validated_step is preserved: on failure the artifact is removed, so a
    failed stage can never leave a stale/partial downstream artifact behind.
    """
    artifact_path = OUTPUT_DIR / out_name
    try:
        produce()
        validate_artifact(artifact_path, CONTRACT_DIR / schema_name)
    except Exception:
        artifact_path.unlink(missing_ok=True)
        raise
    return artifact_path


def run_pipeline(
    model_path: str | Path,
    declared_architecture: str = "resnet18",
) -> dict[str, Path]:
    """End-to-end zero-trust scan of a SafeTensors artifact.

    ``declared_architecture`` is an explicit declaration, never a detected
    guess: the caller states what the artifact is and D2 validates the loaded
    state_dict against the canonical construction for that declaration.
    """
    if declared_architecture not in SUPPORTED_ARCHITECTURES:
        raise ValueError(
            f"Unsupported declared architecture '{declared_architecture}': "
            f"supported: {list(SUPPORTED_ARCHITECTURES)}"
        )

    generation_commit = get_generation_commit()
    context = intake_model(Path(model_path), declared_architecture)

    # D2: deliver the exact P1 trusted context to P2's locked in-process
    # handoff. This is the only model transfer; P2 never reloads the artifact.
    from src.p2_behavioral_risk.handoff import receive_trusted_model

    receive_trusted_model(context)
    features = extract_features(context, generation_commit)
    features_path = _validated_step(
        lambda: features, "features.json", "features.schema.json"
    )
    features = json.loads(features_path.read_text(encoding="utf-8"))
    ml_path = _validated_step(
        lambda f, c: build_ml_results(f, c),
        "ml_results.json",
        "ml_results.schema.json",
        features,
        generation_commit,
    )

    # D2: the trusted context handed off above is the single trusted
    # representation of the artifact (nn.Module for FP, scanner-controlled
    # raw state-dict for D11 quantized). P2 retrieves it via the handoff
    # module and never reloads the model itself.
    # P2 persists risk_results.json itself; the orchestrator only validates it.
    from src.p2_behavioral_risk.analyzer import run_assessment

    risk_path = _validated_p2_step(
        lambda: run_assessment(
            features_path=features_path,
            ml_results_path=ml_path,
            output_path=OUTPUT_DIR / "risk_results.json",
            mock_mode=False,
        ),
        "risk_results.json",
        "risk_results.schema.json",
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
    # P2 mock stage: mock mode is owned by the recovered live P2 analyzer. It
    # requires P2's domain stub models, which are outside this recovery's scope,
    # so this stage fails closed rather than fabricating a risk artifact.
    from src.p2_behavioral_risk.analyzer import run_assessment

    risk_path = _validated_p2_step(
        lambda: run_assessment(
            features_path=features_path,
            ml_results_path=ml_path,
            output_path=OUTPUT_DIR / "risk_results.json",
            mock_mode=True,
        ),
        "risk_results.json",
        "risk_results.schema.json",
    )
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