# src/p2_behavioral_risk/adapters.py
import json

def load_features_json(path):
    with open(path, 'r') as f:
        data = json.load(f)
    if "layer_features" not in data:
        raise KeyError(f"Missing 'layer_features' in {path}")
    if "domain" not in data:
        raise KeyError(f"Missing 'domain' in {path}")
    return data

def load_ml_results_json(path):
    with open(path, 'r') as f:
        data = json.load(f)
    if "p_tamper" not in data:
        raise KeyError(f"Missing 'p_tamper' in {path}")
    # NEW: Read SHAP evidence (passthrough to final report)
    shap_explanation = data.get("shap_explanation", {})  # P3 provides this
    return data, shap_explanation