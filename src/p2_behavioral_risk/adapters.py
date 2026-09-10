# src/p2_behavioral_risk/adapters.py
import json


def load_features_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data["input_domain"] != "VISION":
        raise ValueError(
        f"P2 Option 2 supports VISION models only. Got: {data['input_domain']}"
    )

    # Accept either "input_domain" or "domain"
    domain = data.get("input_domain") or data.get("domain")
    if not domain:
        raise KeyError("Missing 'input_domain' (or 'domain') in features.json")

    if domain != "VISION":
        raise ValueError(f"P2 Option 2 supports VISION only. Got: {domain}")

    # Accept either "static_features" or "layer_features"
    layers = data.get("static_features") or data.get("layer_features")
    if not isinstance(layers, list):
        raise TypeError("'static_features' (or 'layer_features') must be a list")

    if "is_quantized" not in data:
        raise KeyError("Missing 'is_quantized' in features.json")

    if not isinstance(data["is_quantized"], bool):
        raise TypeError("'is_quantized' must be boolean")

    layer_features = []
    for layer in layers:
        required_layer = ["layer_name", "entropy", "pov_chi2", "lsb_kl", "ks_stat"]
        for key in required_layer:
            if key not in layer:
                raise KeyError(f"Missing required layer field '{key}'")
        layer_features.append({
            "layer_name": layer["layer_name"],
            "entropy": layer["entropy"],
            "chi_square": layer["pov_chi2"],
            "kl_div": layer["lsb_kl"],
            "ks_stat": layer["ks_stat"],
        })

    return {
        "domain": domain,
        "is_quantized": data["is_quantized"],
        "layer_features": layer_features,
        "source_producer": data.get("producer", "P1"),
        "source_mock_status": data.get("mock_status", "UNKNOWN"),
        "source_contract_version": data.get("contract_version", "1.0"),
        "source_generation_commit": data.get("generation_commit", "unknown"),
    }


def load_ml_results_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required = ["producer", "p_tamper"]
    for key in required:
        if key not in data:
            raise KeyError(f"Missing required key '{key}' in ml_results.json")

    if data["producer"] != "P3":
        raise ValueError("ml_results.json producer must be P3")

    if not (0.0 <= data["p_tamper"] <= 1.0):
        raise ValueError("p_tamper must be in [0,1]")

    shap = data.get("shap_attributions", {})
    return data, shap