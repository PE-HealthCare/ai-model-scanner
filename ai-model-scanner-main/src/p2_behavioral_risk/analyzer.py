# src/p2_behavioral_risk/analyzer.py
from .adapters import load_features_json, load_ml_results_json
from .prober import get_behavioral_result
from .risk_aggregator import compute_s_static_and_layer, compute_mrs
from .output_writer import write_risk_results
from .stub_models import StubVisionModel

# Standard caveat (required by §7)
ASSUMPTIONS_LIMITATIONS = (
    "This assessment is based on static steganalysis and behavioral probing within the "
    "tool's detection scope. PASS does not guarantee absolute security or absence of "
    "all manipulation. Results are probabilistic and should be used as part of a broader "
    "security review."
)

def run_assessment(features_path, ml_results_path, output_path="ai-model-scanner-main\\data\\outputs\\risk_results.json", model=None):
    print("Step 1: Loading features & ML results...")
    features = load_features_json(features_path)
    ml_results, shap_explanation = load_ml_results_json(ml_results_path)
    
    domain = features["domain"]
    is_quantized = features["is_quantized"]
    
    if model is None:
        print("Using Stub Vision Model (swap later).")
        model = StubVisionModel()
    
    print("Step 2: Running behavioral probing...")
    behav = get_behavioral_result(is_quantized, domain, model)
    s_behavior = behav["s_behavior"]
    
    # NEW: Generate behavioral note
    if is_quantized:
        behavioral_note = "Probing skipped (quantized model)."
    elif s_behavior is None:
        behavioral_note = "Probing failed or no output."
    else:
        behavioral_note = f"STRIP H_STRIP = {s_behavior:.3f} (normalized)."
    
    print("Step 3: Computing S_static & highest risk layer...")
    s_static, highest_layer = compute_s_static_and_layer(features["layer_features"])
    
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
        # NEW: Required report fields
        "shap_explanation": shap_explanation,          # Passthrough from P3
        "behavioral_note": behavioral_note,            # §7 requirement
        "assumptions_and_limitations": ASSUMPTIONS_LIMITATIONS  # §7 requirement
    }
    
    print(f"Step 5: Writing to {output_path}")
    write_risk_results(final_output, output_path)
    print(f"✅ Done! Verdict: {result['verdict']}")
    return final_output

if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    run_assessment(
        features_path=os.path.join(base, "data/fixtures/fake_features_vision.json"),
        ml_results_path=os.path.join(base, "data/fixtures/fake_ml_results.json")
    )