import json


def load_features_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required = [
        "input_domain",
        "is_quantized",
        "layer_count",
        "static_features",
    ]

    for key in required:
        if key not in data:
            raise KeyError(f"Missing required key '{key}' in features.json")

    if data["input_domain"] not in {"VISION", "NLP"}:
        raise ValueError(f"Unsupported domain: {data['input_domain']}")

    if not isinstance(data["is_quantized"], bool):
        raise TypeError("'is_quantized' must be boolean")

    if not isinstance(data["static_features"], list):
        raise TypeError("'static_features' must be a list")

    if data["layer_count"] != len(data["static_features"]):
        raise ValueError(
            "layer_count does not match static_features length"
        )

    layer_features = []

    for layer in data["static_features"]:
        required_layer = [
            "layer_name",
            "entropy",
            "pov_chi2",
            "lsb_kl",
            "ks_stat",
        ]

        for key in required_layer:
            if key not in layer:
                raise KeyError(
                    f"Missing required layer field '{key}'"
                )

        layer_features.append({
            "layer_name": layer["layer_name"],
            "entropy": layer["entropy"],
            "chi_square": layer["pov_chi2"],
            "kl_div": layer["lsb_kl"],
            "ks_stat": layer["ks_stat"],
        })

    return {
        "domain": data["input_domain"],
        "is_quantized": data["is_quantized"],
        "layer_features": layer_features,
        "source_producer": data["producer"],
        "source_mock_status": data["mock_status"],
        "source_contract_version": data["contract_version"],
        "source_generation_commit": data["generation_commit"],
    }


def load_ml_results_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required = [
        "producer",
        "mock_status",
        "contract_version",
        "generation_commit",
        "p_tamper",
        "shap_attributions",
        "model_version",
    ]

    for key in required:
        if key not in data:
            raise KeyError(f"Missing required key '{key}' in ml_results.json")

    if data["producer"] != "P3":
        raise ValueError("ml_results.json producer must be P3")

    if data["mock_status"] == "STALE":
        raise RuntimeError("P3 ml_results.json is STALE")

    if not 0.0 <= data["p_tamper"] <= 1.0:
        raise ValueError("p_tamper must be in [0,1]")

    return data, data["shap_attributions"]