# src/p2_behavioral_risk/risk_aggregator.py

import numpy as np


STATIC_FEATURES = (
    "entropy",
    "pov_chi2",
    "lsb_kl",
    "ks_stat",
)


# ============================================================
# D7 – MAD Z-SCORE
# ============================================================

def mad_zscore(x, baseline):
    """
    D7 LOCKED.

    Z = (x - median) / (1.4826 * MAD)

    Rules:
    - invalid numeric input -> reject
    - <= 2 baseline observations -> unavailable
    - MAD == 0 and x == median -> 0
    - MAD == 0 and x != median -> DEGENERATE_DEVIATION
    - no epsilon
    """

    x = float(x)
    baseline = np.asarray(baseline, dtype=np.float64)

    if baseline.size == 0:
        raise RuntimeError("No baseline values available.")

    if baseline.size <= 2:
        raise RuntimeError(
            "Insufficient comparable layers for MAD baseline."
        )

    if not np.isfinite(x):
        raise ValueError("Target value contains NaN or Inf.")

    if not np.all(np.isfinite(baseline)):
        raise ValueError(
            "MAD baseline contains NaN or Inf."
        )

    median = float(np.median(baseline))
    mad = float(np.median(np.abs(baseline - median)))

    if mad == 0.0:
        if x == median:
            return 0.0

        raise RuntimeError(
            "DEGENERATE_DEVIATION: zero MAD and target "
            "differs from median."
        )

    z = (x - median) / (1.4826 * mad)

    if not np.isfinite(z):
        raise ValueError("MAD Z-score is non-finite.")

    return float(z)


# ============================================================
# D7 – FEATURE EVIDENCE
# ============================================================

def compute_layer_evidence(layer_features):
    """
    Produce D7-valid per-layer evidence.

    Returns:
        list of dictionaries containing:
          layer_id
          layer_name
          feature_evidence
          E
          valid
    """

    if len(layer_features) <= 2:
        raise RuntimeError(
            "D7 baseline unavailable: fewer than 3 layers."
        )

    results = []

    for index, layer in enumerate(layer_features):

        layer_id = layer.get("layer_id", str(index))
        layer_name = layer["layer_name"]

        feature_evidence = {}
        valid_z_values = []

        for feature in STATIC_FEATURES:

            if feature not in layer:
                raise KeyError(
                    f"Missing static feature '{feature}' "
                    f"for layer '{layer_name}'."
                )

            x = layer[feature]

            if not np.isfinite(float(x)):
                raise ValueError(
                    f"Invalid {feature} in layer '{layer_name}'."
                )

            baseline = []

            for other in layer_features:
                if feature not in other:
                    raise KeyError(
                        f"Missing feature '{feature}' in baseline."
                    )

                value = other[feature]

                if not np.isfinite(float(value)):
                    # Invalid evidence is NOT converted to zero.
                    continue

                baseline.append(float(value))

            if len(baseline) <= 2:
                raise RuntimeError(
                    f"Insufficient valid baseline for feature "
                    f"'{feature}'."
                )

            try:
                z = mad_zscore(x, baseline)
            except RuntimeError as exc:
                if "DEGENERATE_DEVIATION" in str(exc):
                    # This feature is not valid evidence.
                    feature_evidence[feature] = {
                        "status": "DEGENERATE_DEVIATION",
                        "z": None,
                        "e": None,
                    }
                    continue

                raise

            e = abs(z) / (1.0 + abs(z))

            if not np.isfinite(e):
                raise ValueError(
                    f"Non-finite evidence for {layer_name}/{feature}."
                )

            feature_evidence[feature] = {
                "status": "VALID",
                "z": float(z),
                "e": float(e),
            }

            valid_z_values.append(e)

        if not valid_z_values:
            results.append({
                "layer_id": layer_id,
                "layer_name": layer_name,
                "feature_evidence": feature_evidence,
                "E": None,
                "valid": False,
            })
            continue

        E = max(valid_z_values)

        results.append({
            "layer_id": layer_id,
            "layer_name": layer_name,
            "feature_evidence": feature_evidence,
            "E": float(E),
            "valid": True,
        })

    return results


# ============================================================
# D5 – STATIC AGGREGATION
# ============================================================

def compute_s_static(layer_evidence):
    """
    D5 LOCKED.

    S_static = 1 - Π_l (1 - E(l))

    Only D7-valid layers participate.
    """

    valid_layers = [
        layer for layer in layer_evidence
        if layer["valid"]
        and layer["E"] is not None
        and np.isfinite(layer["E"])
    ]

    if not valid_layers:
        raise RuntimeError(
            "No D7-valid layer evidence available for D5."
        )

    s_static = 1.0

    for layer in valid_layers:
        E = float(layer["E"])
        s_static *= (1.0 - E)

    s_static = 1.0 - s_static

    if not np.isfinite(s_static):
        raise ValueError("S_static is non-finite.")

    return float(np.clip(s_static, 0.0, 1.0))


# ============================================================
# D6 – HIGHEST RISK LAYER
# ============================================================

def get_highest_risk_layer(layer_evidence):
    """
    D6 LOCKED.

    Highest risk = argmax E(l).

    Exact ties are resolved using canonical layer_id ordering.
    """

    eligible = [
        layer for layer in layer_evidence
        if layer["valid"]
        and layer["E"] is not None
        and np.isfinite(layer["E"])
    ]

    if not eligible:
        return None

    max_E = max(layer["E"] for layer in eligible)

    tied = [
        layer for layer in eligible
        if layer["E"] == max_E
    ]

    tied.sort(key=lambda layer: str(layer["layer_id"]))

    return tied[0]["layer_name"]


# ============================================================
# D5 + D6 PUBLIC ENTRY POINT
# ============================================================

def compute_s_static_and_layer(layer_features):
    """
    Compute D7 evidence, D5 S_static and D6 highest-risk layer.
    """

    layer_evidence = compute_layer_evidence(layer_features)

    s_static = compute_s_static(layer_evidence)

    highest_risk_layer = get_highest_risk_layer(
        layer_evidence
    )

    return s_static, highest_risk_layer


# ============================================================
# MRS + VERDICT
# ============================================================

def compute_mrs(
    s_static,
    p_tamper,
    s_behavior=None,
    is_quantized=False,
):
    """
    MRS LOCKED.

    Non-quantized:
        40*S_static + 35*P_tamper + 25*S_behavior

    Quantized:
        55*S_static + 45*P_tamper
    """

    s_static = float(s_static)
    p_tamper = float(p_tamper)

    if not 0.0 <= s_static <= 1.0:
        raise ValueError("s_static must be in [0,1].")

    if not 0.0 <= p_tamper <= 1.0:
        raise ValueError("p_tamper must be in [0,1].")

    if is_quantized:

        mrs = min(
            100.0,
            55.0 * s_static +
            45.0 * p_tamper,
        )

    else:

        if s_behavior is None:
            raise RuntimeError(
                "Non-quantized model requires S_behavior."
            )

        s_behavior = float(s_behavior)

        if not 0.0 <= s_behavior <= 1.0:
            raise ValueError(
                "s_behavior must be in [0,1]."
            )

        mrs = min(
            100.0,
            40.0 * s_static +
            35.0 * p_tamper +
            25.0 * s_behavior,
        )

    if mrs <= 34:
        verdict = "PASS"
    elif mrs <= 69:
        verdict = "REVIEW"
    else:
        verdict = "FAIL"

    return {
        "mrs_score": round(float(mrs), 2),
        "verdict": verdict,
    }
