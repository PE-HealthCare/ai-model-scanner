import json


def load_features_json(path):
    import math
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    required = [
        "input_domain",
        "is_quantized",
        "layer_count",
        "static_features",
        "producer",
        "mock_status",
        "contract_version",
        "generation_commit",
    ]

    for key in required:
        if key not in data:
            raise KeyError(f"Missing required key '{key}' in features.json")

    if data["producer"] != "P1":
        raise ValueError(f"features.json producer must be P1, got {data['producer']}")

    if data["mock_status"] == "STALE":
        raise RuntimeError("P1 features.json is STALE")

    if data["input_domain"] not in {"VISION", "NLP"}:
        raise ValueError(f"Unsupported domain: {data['input_domain']}")

    if not isinstance(data["is_quantized"], bool):
        raise TypeError("'is_quantized' must be boolean")
    # Store quantized flag for later validation
    is_quantized = data["is_quantized"]

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
            "mean",
            "std",
            "skewness",
            "kurtosis",
            "sparsity",
            "outlier_pct"
        ]

        for key in required_layer:
            if key not in layer:
                raise KeyError(
                    f"Missing required layer field '{key}'"
                )

        parsed_layer = {"layer_name": layer["layer_name"]}
        for stat in required_layer[1:]:
            val = layer[stat]
            if is_quantized and stat != "ks_stat":
                # D11 quantized contract: the nine FP-only features are
                # unavailable. JSON null is the only accepted representation —
                # never zero, NaN, or a fabricated/FP-derived substitute.
                if val is None:
                    parsed_layer[stat] = None
                    continue
                raise ValueError(
                    "Non‑finite or invalid value: FP-only feature "
                    f"'{stat}' must be null for quantized input"
                )
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                raise ValueError("Non‑finite or invalid value")
            if stat == "ks_stat":
                # Authoritative P1/schema/D11 contract: ks_stat is a finite
                # numeric KS statistic in [0,1]. Fail closed on out-of-range
                # values; never clamp, zero-fill, or substitute.
                if not math.isfinite(float(val)) or not 0.0 <= float(val) <= 1.0:
                    raise ValueError("Non‑finite or invalid value: 'ks_stat' must be in [0,1]")
            parsed_layer[stat] = float(val)

        layer_features.append(parsed_layer)

    return {
        "domain": data["input_domain"],
        "is_quantized": data["is_quantized"],
        "layer_features": layer_features,
        "source_producer": data["producer"],
        "source_mock_status": data["mock_status"],
        "source_contract_version": data["contract_version"],
        "generation_commit": data["generation_commit"],
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


def load_calibration_data(path):
    """
    Load the P2 calibration artifact used by D4 normalization.

    The artifact is scanner-controlled and MUST NOT be derived from the
    uploaded model. Only the domain calibration block is returned; the
    per-domain median/MAD validation stays in ``normalize_h_strip`` so a
    missing D4 field fails closed at scoring time instead of being
    silently substituted.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "calibration_data" not in data:
        raise KeyError(
            "Missing required key 'calibration_data' in calibration artifact"
        )

    calibration_data = data["calibration_data"]

    if not isinstance(calibration_data, dict) or not calibration_data:
        raise ValueError(
            "Calibration artifact contains no domain calibration data"
        )

    return calibration_data