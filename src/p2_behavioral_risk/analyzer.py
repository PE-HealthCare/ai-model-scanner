# src/p2_behavioral_risk/analyzer.py
import json
import os
import uuid
import hashlib
import subprocess
from datetime import datetime

from .adapters import load_features_json, load_ml_results_json
from .prober import get_behavioral_result
from .risk_aggregator import compute_s_static_and_layer, compute_mrs
from .output_writer import write_risk_results
from .config import BOUND_N

ASSUMPTIONS_LIMITATIONS = (
    "This assessment is based on static steganalysis and behavioral probing within the "
    "tool's detection scope. PASS does not guarantee absolute security or absence of "
    "all manipulation. Results are probabilistic and should be used as part of a broader "
    "security review."
)


def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    except Exception:
        return "unknown"


def get_file_hash(path):
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_calibration_data(calibration_path=None):
    if calibration_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        calibration_path = os.path.join(base, "data", "calibration", "calibration_data.json")
    try:
        with open(calibration_path, "r") as f:
            data = json.load(f)
        return data["calibration_data"]
    except FileNotFoundError:
        raise RuntimeError(f"Calibration data not found at {calibration_path}")


def run_assessment(features_path, ml_results_path, output_path=None,
                   model=None, calibration_path=None):
    """P2 Option 2 pipeline: real features + real ml_results → risk_results.json."""

    if output_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_path = os.path.join(base, "data", "outputs", "risk_results.json")

    calibration_data = load_calibration_data(calibration_path)

    print("Step 1: Loading features & ML results...")
    features = load_features_json(features_path)
    ml_results, shap_explanation = load_ml_results_json(ml_results_path)

    domain = features["domain"]
    is_quantized = features["is_quantized"]
    p_tamper = ml_results["p_tamper"]

    # ---- Model handoff (D2) ----
    if model is None:
        from .handoff import get_trusted_model
        try:
            model = get_trusted_model()
        except RuntimeError as e:
            raise RuntimeError(
                f"Authoritative P2 execution requires trusted P1 model. {e}"
            )

    print("Step 2: Running behavioral probing...")
    behav = get_behavioral_result(
        is_quantized=is_quantized,
        domain=domain,
        model=model,
        calibration_data=calibration_data,
        bound_n=BOUND_N,
    )
    s_behavior = behav["s_behavior"]

    if is_quantized:
        behavioral_note = "Probing skipped (quantized model)."
    elif s_behavior is None:
        # Fail closed BEFORE computing MRS – don't let None silently become 0
        raise RuntimeError(
        "Behavioral probing failed for non-quantized model. "
        "S_behavior is None – cannot produce authoritative risk score."
    )
    else:
        behavioral_note = f"H_STRIP={behav['h_strip']:.3f}, S_behavior={s_behavior:.3f}"

    print("Step 3: Computing S_static & highest-risk layer...")
    s_static, highest_layer = compute_s_static_and_layer(features["layer_features"])

    print("Step 4: Computing MRS & Verdict...")
    result = compute_mrs(s_static, p_tamper, s_behavior, is_quantized)

    final_output = {
        # Option 2 required fields
        "producer": "P2",
        "mock_status": ml_results.get("mock_status", "VERIFIED-REAL"),
        "contract_version": "1.0",
        "generation_commit": ml_results.get("generation_commit", get_git_commit()),
        "mrs_score": result["mrs"],
        "verdict": result["verdict"],
        "s_static": s_static,
        "p_tamper": p_tamper,
        "s_behavior": s_behavior,
        # Evidence
        "highest_risk_layer": highest_layer,
        "bypassed_behavior": behav["bypassed_behavior"],
        "shap_explanation": shap_explanation,
        "behavioral_note": behavioral_note,
        "assumptions_and_limitations": ASSUMPTIONS_LIMITATIONS,
        # Provenance
        "_provenance": {
            "execution_mode": "authoritative",
            "features_source": {
                "file": features_path,
                "producer": features.get("source_producer"),
                "mock_status": features.get("source_mock_status"),
                "hash": get_file_hash(features_path),
            },
            "ml_source": {
                "file": ml_results_path,
                "producer": ml_results.get("producer"),
                "mock_status": ml_results.get("mock_status"),
                "generation_commit": ml_results.get("generation_commit"),
                "hash": get_file_hash(ml_results_path),
            },
            "calibration_hash": get_file_hash(calibration_path),
            "run_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
        },
    }

    print(f"Step 5: Writing to {output_path}")
    write_risk_results(final_output, output_path)
    print(f"✅ Done! MRS={result['mrs']} Verdict={result['verdict']}")
    return final_output


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    run_assessment(
        features_path=os.path.join(base, "data", "outputs", "features.json"),
        ml_results_path=os.path.join(base, "data", "outputs", "ml_results.json"),
    )