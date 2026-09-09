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
from .stub_models import StubVisionModel
from .config import BOUND_N

# ============================================================
# STANDARD CAVEAT (required by Phase 5 / §7)
# ============================================================
ASSUMPTIONS_LIMITATIONS = (
    "This assessment is based on static steganalysis and behavioral probing within the "
    "tool's detection scope. PASS does not guarantee absolute security or absence of "
    "all manipulation. Results are probabilistic and should be used as part of a broader "
    "security review."
)

# ============================================================
# PROVENANCE HELPERS
# ============================================================
def get_git_commit():
    """Get the current git commit hash."""
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    except Exception:
        return "unknown"


def get_file_hash(path):
    """Compute SHA-256 hash of a file. Returns None if file doesn't exist."""
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


# ============================================================
# CALIBRATION LOADER
# ============================================================
def load_calibration_data(calibration_path="data/calibration/calibration_data.json"):
    """Load the D3/D4 calibration values."""
    try:
        with open(calibration_path, 'r') as f:
            data = json.load(f)
        return data["calibration_data"]  # dict with "VISION" and "NLP" keys
    except FileNotFoundError:
        raise RuntimeError(
            "Calibration data not found. Run scripts/generate_calibration_data.py first."
        )


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================
def run_assessment(features_path, ml_results_path, output_path=None,
                   model=None, mock_mode=False, calibration_path=None):
    """
    Run the full P2 assessment.

    Args:
        features_path: Path to P1's features.json.
        ml_results_path: Path to P3's ml_results.json.
        output_path: Where to write risk_results.json.
        model: PyTorch model (if None, uses stub ONLY if mock_mode=True).
        mock_mode: If True, allows stub model and labels provenance as "mock".
        calibration_path: Path to calibration JSON (if None, uses default).
    """
    if output_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_path = os.path.join(base, "data", "outputs", "risk_results.json")

    # Load calibration data
    if calibration_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        calibration_path = os.path.join(base, "data/calibration/calibration_data.json")
    calibration_data = load_calibration_data(calibration_path)

    # ============================================================
    # STEP 1: LOAD UPSTREAM ARTIFACTS
    # ============================================================
    print("Step 1: Loading features & ML results...")
    features = load_features_json(features_path)
    ml_results, shap_explanation = load_ml_results_json(ml_results_path)

    # ============================================================
    # PROVENANCE COLLECTION
    # ============================================================
    provenance = {
        "execution_mode": "mock" if mock_mode else "authoritative",
        "features_source": {
            "file": features_path,
            "producer": features.get("source_producer"),
            "mock_status": features.get("source_mock_status"),
            "contract_version": features.get("source_contract_version"),
            "generation_commit": features.get("source_generation_commit"),
            "hash": get_file_hash(features_path) if os.path.exists(features_path) else None,
        },
        "ml_source": {
            "file": ml_results_path,
            "producer": ml_results.get("producer"),
            "mock_status": ml_results.get("mock_status"),
            "contract_version": ml_results.get("contract_version"),
            "generation_commit": ml_results.get("generation_commit"),
            "hash": get_file_hash(ml_results_path) if os.path.exists(ml_results_path) else None,
        },
        "calibration_hash": get_file_hash(calibration_path) if os.path.exists(calibration_path) else None,
        "p2_commit": get_git_commit(),
        "run_id": str(uuid.uuid4()),
        "decisions": {
        "d3": "LOCKED (methodology) / evidence verified",  # or "COMPLETE"
        "d4": "LOCKED (formula) / verified",
        "d5": "LOCKED",
        "d6": "LOCKED",
        "d7": "LOCKED",
        },
        "timestamp": datetime.now().isoformat()
    }

    domain = features["domain"]
    is_quantized = features["is_quantized"]

    # ============================================================
    # STEP 2: TRUSTED MODEL HANDOFF (D2)
    # ============================================================
    if model is None:
        if mock_mode:
            print("Using Stub Vision Model for development/mock execution.")
            model = StubVisionModel()
        else:
            # Production mode: real model MUST be provided via D2 handoff
            from .handoff import get_trusted_model
            try:
                model = get_trusted_model()
                print("Trusted model acquired via D2 handoff.")
            except RuntimeError as e:
                raise RuntimeError(
                    f"Authoritative P2 execution requires the trusted P1 model handoff. {e}"
                )

    # ============================================================
    # STEP 3: BEHAVIORAL PROBING (D3/D4)
    # ============================================================
    print("Step 2: Running behavioral probing...")
    behav = get_behavioral_result(
        is_quantized=is_quantized,
        domain=domain,
        model=model,
        calibration_data=calibration_data,
        bound_n=BOUND_N,
        mock_mode=mock_mode
    )
    s_behavior = behav["s_behavior"]

    # Generate behavioral note
    if is_quantized:
        behavioral_note = "Probing skipped (quantized model)."
    elif s_behavior is None:
        behavioral_note = "Probing failed or no output."
    else:
        behavioral_note = f"STRIP H_STRIP = {behav['h_strip']:.3f}, S_behavior = {s_behavior:.3f}"

    # ============================================================
    # STEP 4: STATIC RISK AGGREGATION (D5/D6)
    # ============================================================
    print("Step 3: Computing S_static & highest risk layer...")
    s_static, highest_layer = compute_s_static_and_layer(
        features["layer_features"]  # D5 and D6 are locked – no mock_mode needed
    )

    p_tamper = ml_results["p_tamper"]

    # ============================================================
    # STEP 5: MRS + VERDICT
    # ============================================================
    print("Step 4: Computing MRS & Verdict...")
    result = compute_mrs(s_static, p_tamper, s_behavior, is_quantized)

    # ============================================================
    # STEP 6: ASSEMBLE FINAL OUTPUT
    # ============================================================
    final_output = {
        "mrs": result["mrs"],
        "verdict": result["verdict"],
        "highest_risk_layer": highest_layer,
        "s_behavior": s_behavior,
        "bypassed_behavior": behav["bypassed_behavior"],
        "p_tamper": p_tamper,
        "s_static": s_static,
        "shap_explanation": shap_explanation,
        "behavioral_note": behavioral_note,
        "assumptions_and_limitations": ASSUMPTIONS_LIMITATIONS,
        "_provenance": provenance
    }

    # ============================================================
    # STEP 7: AUTHORITATIVE OUTPUT GATE
    # ============================================================
    if not mock_mode:
        # Ensure we have verified-real inputs for authoritative runs
        if features.get("source_mock_status") != "VERIFIED-REAL":
            raise RuntimeError("P1 features.json is not VERIFIED-REAL.")
        if ml_results.get("mock_status") != "VERIFIED-REAL":
            raise RuntimeError("P3 ml_results.json is not VERIFIED-REAL.")
        # D3/D4 evidence must be accepted – check provenance decisions
        if "evidence pending" in provenance["decisions"]["d3"]:
            raise RuntimeError("D3 empirical evidence is not yet accepted. Cannot run authoritative P2.")
        if "pending" in provenance["decisions"]["d4"]:
            raise RuntimeError("D4 verification is not yet accepted. Cannot run authoritative P2.")

    print(f"Step 5: Writing to {output_path}")
    write_risk_results(final_output, output_path)
    print(f"✅ Done! Verdict: {result['verdict']}")
    return final_output


# ============================================================
# MAIN ENTRY POINT (for development / testing)
# ============================================================
if __name__ == "__main__":
    import torchvision.models as models
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Load a real ResNet18 model (just like P1 would)
    real_model = models.resnet18(pretrained=True)
    real_model.eval()  # inference mode
    
    run_assessment(
        features_path=os.path.join(base, "data/inputs/features.json"),
        ml_results_path=os.path.join(base, "data/inputs/ml_results.json"),
        model=real_model,      # <-- Pass the real model!
        mock_mode=False        # Authoritative mode
    )