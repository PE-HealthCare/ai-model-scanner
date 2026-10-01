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
import hashlib
import argparse
import time
from threading import RLock
from pathlib import Path

from src.common.utils import ROOT, get_generation_commit, validate_artifact
from src.p1_static_engine.analyzer import build_mock_features, extract_features, intake_model
from src.p3_ml_dashboard.classifier import (
    build_ml_results,
    build_mock_ml_results,
    build_quantized_ml_results,
)
from src.p3_ml_dashboard.structured_stego import scan as scan_structured

# P2 and the D2 bridge are imported lazily inside each pipeline: the recovered
# live P2 modules pull in the behavioral probing stack (torch/scipy) and the D2
# bridge pulls in safetensors. Local imports keep this orchestrator importable
# without the ML stack and keep every other stage's failure isolated.
SUPPORTED_ARCHITECTURES = ("resnet18",)

OUTPUT_DIR = ROOT / "data" / "outputs"
CONTRACT_DIR = ROOT / "contracts"
_SCAN_LOCK = RLock()  # P2's trusted handoff is process-local, not session-local.


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _validated_step(produce, out_name: str, schema_name: str, *args, output_dir=None):
    """Run one stage, persist its artifact, and validate it against its contract.

    If persistence or validation fails, the artifact file is removed so a
    failed stage can never leave a stale/partial downstream artifact.
    """
    artifact_path = (output_dir or OUTPUT_DIR) / out_name
    payload = produce(*args)
    try:
        _write_json(artifact_path, payload)
        validate_artifact(artifact_path, CONTRACT_DIR / schema_name)
    except Exception:
        artifact_path.unlink(missing_ok=True)
        raise
    return artifact_path


def _validated_p2_step(produce, out_name: str, schema_name: str, *, output_dir=None) -> Path:
    """Run a stage that persists its own artifact, then validate it.

    P2 writes risk_results.json itself (via its own analyzer), so there is no
    payload for the orchestrator to persist. The fail-closed cleanup of
    _validated_step is preserved: on failure the artifact is removed, so a
    failed stage can never leave a stale/partial downstream artifact behind.
    """
    artifact_path = (output_dir or OUTPUT_DIR) / out_name
    try:
        produce()
        validate_artifact(artifact_path, CONTRACT_DIR / schema_name)
    except Exception:
        artifact_path.unlink(missing_ok=True)
        raise
    return artifact_path


def _deliver_validated_risk_to_p3(
    risk_path: Path, ml_path: Path, features_path: Path
) -> dict:
    """Hand the validated P2 risk artifact to the existing P3 consumer.

    The P2 validation step above already schema-validated ``risk_results.json``;
    this helper only parses the validated files into in-memory mappings and
    passes them to the existing P3 mapping-level API. P3 itself never touches
    the filesystem here. Any parse or consumer failure propagates (fail-closed);
    nothing is silently swallowed and P2 validation is not duplicated.
    """
    risk_results = json.loads(risk_path.read_text(encoding="utf-8"))
    ml_results = json.loads(ml_path.read_text(encoding="utf-8"))
    features_doc = json.loads(features_path.read_text(encoding="utf-8"))
    static_features = features_doc.get("static_features")
    from src.p3_ml_dashboard.report import prepare_dashboard_results

    return prepare_dashboard_results(
        risk_results, ml_results, static_features
    )


def run_pipeline(
    model_path: str | Path,
    declared_architecture: str = "resnet18",
    *, output_dir: Path | None = None, evidence: dict | None = None,
) -> dict[str, object]:
    """Serialize the trusted handoff and optionally expose current-run evidence.

    Caller-owned evidence survives downstream failure; it is never read from a
    previous run. UI callers must supply a unique output directory.
    """
    with _SCAN_LOCK:
        try:
            return _run_pipeline(model_path, declared_architecture, output_dir=output_dir, evidence=evidence)
        except Exception:
            if evidence is not None:
                for state in evidence.get('stages', {}).values():
                    if state['status'] == 'pending':
                        state.update(status='skipped', reason='An upstream required stage failed.')
            raise


def _run_pipeline(
    model_path: str | Path,
    declared_architecture: str = "resnet18",
    *, output_dir: Path | None = None, evidence: dict | None = None,
) -> dict[str, object]:
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

    output_dir = Path(output_dir or OUTPUT_DIR)
    runtime = evidence if evidence is not None else {}
    runtime.clear()
    runtime["stages"] = {name: {"status": "pending"} for name in ("intake", "static", "ml", "behavior_risk", "dashboard")}
    def stage(name, operation):
        started = time.perf_counter()
        try:
            value = operation()
            runtime["stages"][name] = {"status": "complete", "seconds": time.perf_counter() - started}
            return value
        except Exception as exc:
            runtime["stages"][name] = {"status": "failed", "seconds": time.perf_counter() - started,
                                      "reason": str(exc), "error_type": type(exc).__name__}
            raise
    generation_commit = get_generation_commit()
    runtime["generation_commit"] = generation_commit
    context = stage("intake", lambda: intake_model(Path(model_path), declared_architecture))
    if evidence is not None:
        from safetensors import safe_open
        with safe_open(model_path, framework="pt", device="cpu") as handle:
            tensors = [{"name": name, "shape": handle.get_slice(name).get_shape(),
                        "dtype": handle.get_slice(name).get_dtype()} for name in handle.keys()]
        runtime["artifact"] = {"sha256": _sha256(Path(model_path)), "architecture": context.architecture,
                               "input_domain": context.input_domain, "is_quantized": context.is_quantized,
                               "tensor_count": len(tensors), "dtype": ", ".join(sorted({t["dtype"] for t in tensors if not t["name"].endswith("num_batches_tracked")})),
                               "tensors": tensors}

    # D2: deliver the exact P1 trusted context to P2's locked in-process
    # handoff. This is the only model transfer; P2 never reloads the artifact.
    from src.p2_behavioral_risk.handoff import receive_trusted_model

    receive_trusted_model(context)
    features_path = stage("static", lambda: _validated_step(
        lambda: extract_features(context, generation_commit), "features.json", "features.schema.json", output_dir=output_dir
    ))
    features = json.loads(features_path.read_text(encoding="utf-8"))
    runtime["features"] = features
    if features.get("is_quantized") is True:
        build_p3_results = build_quantized_ml_results
    else:
        build_p3_results = build_ml_results
    runtime["explanation"] = {}
    ml_path = stage("ml", lambda: _validated_step(
        lambda f, c: build_p3_results(f, c, **({"evidence": runtime["explanation"]} if evidence is not None else {})),
        "ml_results.json",
        "ml_results.schema.json",
        features,
        generation_commit,
        output_dir=output_dir,
    ))
    runtime["ml_results"] = json.loads(ml_path.read_text(encoding="utf-8"))

    # D2: the trusted context handed off above is the single trusted
    # representation of the artifact (nn.Module for FP, scanner-controlled
    # raw state-dict for D11 quantized). P2 retrieves it via the handoff
    # module and never reloads the model itself.
    # P2 persists risk_results.json itself; the orchestrator only validates it.
    from src.p2_behavioral_risk.analyzer import run_assessment

    runtime["p2_evidence"] = {}
    risk_path = stage("behavior_risk", lambda: _validated_p2_step(
        lambda: run_assessment(
            features_path=features_path,
            ml_results_path=ml_path,
            output_path=output_dir / "risk_results.json",
            mock_mode=False,
            **({"evidence": runtime["p2_evidence"]} if evidence is not None else {}),
        ),
        "risk_results.json",
        "risk_results.schema.json",
        output_dir=output_dir,
    ))
    runtime["risk_results"] = json.loads(risk_path.read_text(encoding="utf-8"))
    dashboard_results = stage("dashboard", lambda: _deliver_validated_risk_to_p3(
        risk_path, ml_path, features_path
    ))
    runtime["dashboard_results"] = dashboard_results
    return {
        "features": features_path,
        "ml_results": ml_path,
        "risk_results": risk_path,
        "dashboard_results": dashboard_results,
    }


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_structured_scan(model_path: str | Path, declared_architecture: str = "resnet18") -> dict:
    """Production Prompt-3D verdict: P1 intake plus frozen structured scanner.

    Legacy P_tamper, behavioral evidence, and MRS are deliberately not invoked.
    Any failure propagates to the CLI error path and therefore never becomes PASS.
    """
    path = Path(model_path)
    if declared_architecture not in SUPPORTED_ARCHITECTURES:
        raise ValueError(f"Unsupported declared architecture '{declared_architecture}'")
    context = intake_model(path, declared_architecture)
    # This detector consumes FP32 bit planes, not dequantized/cast approximations.
    # Reject unsupported floating representations instead of silently skipping them.
    from safetensors import safe_open
    if context.is_quantized:
        raise ValueError("Structured-LSB assessment is unavailable for quantized artifacts; FP32 is required.")
    with safe_open(path, framework="pt", device="cpu") as handle:
        from src.p1_static_engine.analyzer import CONTROL_DTYPES
        unsupported = {}
        for name in handle.keys():
            dtype = handle.get_slice(name).get_dtype()
            is_counter = name.endswith(".num_batches_tracked")
            if dtype != "F32" and not (is_counter and dtype in CONTROL_DTYPES):
                unsupported[name] = dtype
    if unsupported:
        raise ValueError("Structured-LSB assessment requires FP32 weights (P1-supported counters are allowed); unsupported tensor dtypes: "
                         + str(unsupported))
    import numpy as np
    with safe_open(path, framework="np", device="cpu") as handle:
        for name in handle.keys():
            if handle.get_slice(name).get_dtype() == "F32" and not np.isfinite(handle.get_tensor(name)).all():
                raise ValueError(f"Structured-LSB assessment requires finite weights: {name}")
    structured = scan_structured(path)
    state = context.model.state_dict() if context.model is not None else context.raw_state_dict
    dtype = "FP32" if not context.is_quantized else "quantized"
    return {
        "artifact": {"filename": path.name, "sha256": _sha256(path), "architecture": declared_architecture,
                     "input_domain": context.input_domain, "dtype": dtype, "is_quantized": bool(context.is_quantized),
                     "layer_count": len(state)},
        "intake": {"status": "PASS"},
        "structured_stego": structured,
        "static_evidence": {"status": "NOT_USED_FOR_VERDICT", "reason": "Frozen structured-LSB detector is authoritative."},
        "behavioral": {"validated_for_final_decision": False},
        "verdict": structured["verdict"],
    }


def _print_structured_summary(result: dict) -> None:
    artifact, structured = result["artifact"], result["structured_stego"]
    print("=" * 50); print("AI MODEL SECURITY SCAN"); print("=" * 50)
    print(f"Artifact: {artifact['filename']}")
    print(f"SHA256: {artifact['sha256']}")
    print(f"Architecture: {artifact['architecture']}")
    print(f"Input Domain: {artifact['input_domain']}")
    print(f"Dtype: {artifact['dtype']}; Quantized: {artifact['is_quantized']}")
    print(f"Layer count: {artifact['layer_count']}")
    print("Intake: PASS\nStructured Steganography Analysis")
    for name, value in structured["features"].items(): print(f"{name}: {value}")
    print(f"Score: {structured['score']}"); print(f"Threshold: {structured['threshold']}")
    print(f"Dominant Signal: {structured['dominant_signal']}")
    print(f"Verdict: {structured['verdict']}"); print(f"Final Verdict: {result['verdict']}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frozen structured-LSB SafeTensors scanner")
    parser.add_argument("model", type=Path)
    parser.add_argument("--architecture", default="resnet18")
    parser.add_argument("--json-output", type=Path, default=OUTPUT_DIR / "structured_scan_result.json")
    args = parser.parse_args()
    try:
        result = run_structured_scan(args.model, args.architecture)
        _write_json(args.json_output, result)
        _print_structured_summary(result)
        print(f"JSON result: {args.json_output}")
    except Exception as exc:
        error = {"intake": {"status": "REJECTED"}, "verdict": "REJECTED", "error": f"{type(exc).__name__}: {exc}"}
        _write_json(args.json_output, error)
        print(f"REJECTED: {error['error']}", file=sys.stderr)
        sys.exit(2)
