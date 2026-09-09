# src/p2_behavioral_risk/analyzer.py

import json
import os
from .adapters import load_features_json, load_ml_results_json
from .prober import get_behavioral_result
from .risk_aggregator import compute_s_static_and_layer, compute_mrs
from .output_writer import write_risk_results
from .stub_models import StubVisionModel
from .config import BOUND_N

# Standard caveat (required by §7)
ASSUMPTIONS_LIMITATIONS = (
    "This assessment is based on static steganalysis and behavioral probing within the "
    "tool's detection scope. PASS does not guarantee absolute security or absence of "
    "all manipulation. Results are probabilistic and should be used as part of a broader "
    "security review."
)

def load_calibration_data(calibration_path="data/calibration/calibration_data.json"):
    """Load the D3/D4 calibration values."""
    try:
        with open(calibration_path, 'r') as f:
            data = json.load(f)
        return data["calibration_data"]  # dict with "VISION" and "NLP" keys
    except FileNotFoundError:
        # If calibration file is missing, raise a clear error
        raise RuntimeError(
            "Calibration data not found. Run scripts/generate_calibration_data.py first."
        )

def run_assessment(features_path, ml_results_path, output_path=None,
                   model=None, mock_mode=True, calibration_path=None):
    """
    Run the full P2 assessment.

    Args:
        features_path: Path to P1's features.json.
        ml_results_path: Path to P3's ml_results.json.
        output_path: Where to write risk_results.json.
        model: PyTorch model (if None, uses StubVisionModel).
        mock_mode: If True, uses placeholders for unresolved decisions.
        calibration_path: Path to calibration JSON (if None, uses default).
    """
    if output_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        output_path = os.path.join(base, "data", "outputs", "risk_results.json")

    # Load calibration data
    if calibration_path is None:
        calibration_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data/calibration/calibration_data.json"
        )
    calibration_data = load_calibration_data(calibration_path)

    print("Step 1: Loading features & ML results...")
    features = load_features_json(features_path)
    ml_results, shap_explanation = load_ml_results_json(ml_results_path)

    domain = features["domain"]
    is_quantized = features["is_quantized"]

    if model is None:
        print("Using Stub Vision Model (swap later).")
        model = StubVisionModel()

    print("Step 2: Running behavioral probing...")
    behav = get_behavioral_result(
        is_quantized=is_quantized,
        domain=domain,
        model=model,
        calibration_data=calibration_data,   # <-- NEW
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

    print("Step 3: Computing S_static & highest risk layer...")
    s_static, highest_layer = compute_s_static_and_layer(
        features["layer_features"],
        mock_mode=mock_mode
    )

    p_tamper = ml_results["p_tamper"]

    print("Step 4: Computing MRS & Verdict...")
    result = compute_mrs(s_static, p_tamper, s_behavior, is_quantized)

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
        "_provenance": {
            "mock_mode": mock_mode,
            "d4_resolved": not mock_mode,   # will be True once mock_mode=False
            "calibration_domain": domain,
            "run_id": str(uuid.uuid4()) if mock_mode else "production"
        }
    }

    print(f"Step 5: Writing to {output_path}")
    write_risk_results(final_output, output_path)
    print(f"✅ Done! Verdict: {result['verdict']}")
    return final_output

if __name__ == "__main__":
    import uuid
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    run_assessment(
        features_path=os.path.join(base, "data/fixtures/fake_features_vision.json"),
        ml_results_path=os.path.join(base, "data/fixtures/fake_ml_results.json"),
        mock_mode=True  # keep True until D4 is approved; then change to False
    )