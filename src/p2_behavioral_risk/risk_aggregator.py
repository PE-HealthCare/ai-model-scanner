# src/p2_behavioral_risk/risk_aggregator.py
import numpy as np

# ============================================================
# D7 – MAD Z-Score (LOCKED)
# ============================================================
def mad_zscore(x, x_base):
    """
    D7 – Frozen MAD Z-score calculation.
    Returns Z = (x - median) / (1.4826 * MAD)
    with explicit degenerate-case handling.
    """
    x = float(x)
    x_base = np.asarray(x_base, dtype=np.float64)

    if x_base.size == 0:
        raise RuntimeError("No baseline values available.")
    if not np.all(np.isfinite(x_base)):
        raise ValueError("MAD baseline contains NaN or Inf – no imputation permitted.")
    if not np.isfinite(x):
        raise ValueError("Target value contains NaN or Inf.")
    if x_base.size <= 2:
        raise RuntimeError("Insufficient comparable layers for MAD baseline.")

    med = float(np.median(x_base))
    mad = float(np.median(np.abs(x_base - med)))

    if mad == 0.0:
        if x == med:
            return 0.0  # deterministic zero anomaly
        raise RuntimeError("DEGENERATE_DEVIATION: zero MAD and target differs from median.")
    # Nonzero MAD – use actual value (no epsilon)
    return float((x - med) / (1.4826 * mad))


# ============================================================
# D5/D6 – S_static & Highest‑Risk Layer (LOCKED)
# ============================================================
def compute_s_static_and_layer(layer_features):
    """
    D5: S_static = 1 - Π_l (1 - E_l)
         where E_l = max_f ( |Z_lf| / (1 + |Z_lf|) )
    D6: highest_risk_layer = argmax_l (E_l)
    """
    stat_keys = [
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
    layer_E = []
    
    # NOTE: the P1 contract supplies `layer_name` only. There is no
    # authoritative upstream layer identity or guaranteed canonical layer
    # ordering; list position is NOT layer identity (see the D6 selection
    # note below).
    # Validate sufficient comparable layers for D7 when full stats are present
    full_stats = set(stat_keys)
    provides_full = any(full_stats.issubset(set(layer.keys())) for layer in layer_features)
    if provides_full and len(layer_features) <= 2:
        raise RuntimeError("Insufficient baseline for MAD computation")
    for index, layer in enumerate(layer_features):
        # D5 eligibility: None = no eligible feature evidence computed yet.
        # Zero must NEVER substitute for unavailable/invalid/blocked/degenerate evidence.
        max_e = None
        for stat in stat_keys:
            # Skip stats not present in the layer (e.g., minimal test fixtures)
            if stat not in layer:
                continue
            # Skip stats with null (None) values – treat as unavailable evidence
            if layer[stat] is None:
                continue
            x = layer[stat]
            # Build intra-model baseline for this stat, using only layers that
            # have the stat with a finite numeric value. None/NaN/+/‑Inf are
            # unavailable evidence and are excluded, never zero-imputed.
            if not isinstance(x, (int, float)) or not np.isfinite(x):
                continue
            x_base = [lf[stat] for lf in layer_features if stat in lf and isinstance(lf[stat], (int, float)) and np.isfinite(lf[stat])]
            if len(x_base) <= 2:
                # Not enough baseline values – skip this feature
                continue
            try:
                z = mad_zscore(x, x_base)   # D7
            except RuntimeError as exc:
                if "DEGENERATE_DEVIATION" in str(exc):
                    continue
                raise
            e = abs(z) / (1 + abs(z))
            if max_e is None or e > max_e:
                max_e = e
        # D5: a layer enters layer_E only with at least one eligible feature
        # evidence value. A layer with zero eligible features stays
        # NON-ELIGIBLE and is NOT appended.
        if max_e is None:
            continue
        layer_E.append((index, layer["layer_name"], max_e))

    if not layer_E:
        # D5 fail-closed: no eligible layer evidence — explicit unavailable
        # representation; never fabricate S_static from zero evidence.
        raise RuntimeError("No D7-valid layer evidence available for D5.")

    S_static = 1.0 - np.prod([1.0 - item[2] for item in layer_E])
    
    # D6: highest_risk_layer = argmax_l (E_l)
    # UNRESOLVED upstream interface issue: exact ties cannot be resolved
    # canonically because the contract provides no authoritative layer
    # identity and no canonical layer order. For run-to-run determinism only,
    # an exact tie currently returns the first maximum in contract-supplied
    # order. This is NOT a canonical tie-break decision and must not be
    # presented as one; resolving it requires an upstream contract change.
    max_e_val = max([item[2] for item in layer_E])
    tied = [item for item in layer_E if item[2] == max_e_val]
    tied.sort(key=lambda x: x[0])
    highest_risk_layer = tied[0][1]

    return S_static, highest_risk_layer


# ============================================================
# MRS + Verdict (FROZEN)
# ============================================================
def compute_mrs(s_static, p_tamper, s_behavior=None, is_quantized=False):
    """
    Compute MRS and verdict. FROZEN formulas.
    Fail-closed: non-quantized without S_behavior raises error.
    """
    s_static = float(s_static)
    p_tamper = float(p_tamper)

    if not 0.0 <= s_static <= 1.0:
        raise ValueError("s_static must be in [0,1].")

    if not 0.0 <= p_tamper <= 1.0:
        raise ValueError("p_tamper must be in [0,1].")

    if is_quantized:
        # Quantized: S_behavior is intentionally absent
        mrs = min(100, 55 * s_static + 45 * p_tamper)
    else:
        # Non-quantized: S_behavior MUST be present
        if s_behavior is None:
            raise RuntimeError(
                "Non-quantized model is missing S_behavior. "
                "Behavioral probing failed – refusing to fabricate a score."
            )

        s_behavior = float(s_behavior)

        if not 0.0 <= s_behavior <= 1.0:
            raise ValueError("s_behavior must be in [0,1].")

        mrs = min(100, 40 * s_static + 35 * p_tamper + 25 * s_behavior)

    if mrs <= 34:
        verdict = "PASS"
    elif mrs <= 69:
        verdict = "REVIEW"
    else:
        verdict = "FAIL"

    return {"mrs_score": round(mrs, 2), "verdict": verdict}

# import numpy as np


# STATIC_FEATURES = (
#     "entropy",
#     "pov_chi2",
#     "lsb_kl",
#     "ks_stat",
# )


# # ============================================================
# # D7 – MAD Z-SCORE
# # ============================================================

# def mad_zscore(x, baseline):
#     """
#     D7 LOCKED.

#     Z = (x - median) / (1.4826 * MAD)

#     Rules:
#     - invalid numeric input -> reject
#     - <= 2 baseline observations -> unavailable
#     - MAD == 0 and x == median -> 0
#     - MAD == 0 and x != median -> DEGENERATE_DEVIATION
#     - no epsilon
#     """

#     x = float(x)
#     baseline = np.asarray(baseline, dtype=np.float64)

#     if baseline.size == 0:
#         raise RuntimeError("No baseline values available.")

#     if baseline.size <= 2:
#         raise RuntimeError(
#             "Insufficient comparable layers for MAD baseline."
#         )

#     if not np.isfinite(x):
#         raise ValueError("Target value contains NaN or Inf.")

#     if not np.all(np.isfinite(baseline)):
#         raise ValueError(
#             "MAD baseline contains NaN or Inf."
#         )

#     median = float(np.median(baseline))
#     mad = float(np.median(np.abs(baseline - median)))

#     if mad == 0.0:
#         if x == median:
#             return 0.0

#         raise RuntimeError(
#             "DEGENERATE_DEVIATION: zero MAD and target "
#             "differs from median."
#         )

#     z = (x - median) / (1.4826 * mad)

#     if not np.isfinite(z):
#         raise ValueError("MAD Z-score is non-finite.")

#     return float(z)


# # ============================================================
# # D7 – FEATURE EVIDENCE
# # ============================================================

# def compute_layer_evidence(layer_features):
#     """
#     Produce D7-valid per-layer evidence.

#     Returns:
#         list of dictionaries containing:
#           layer_id
#           layer_name
#           feature_evidence
#           E
#           valid
#     """

#     if len(layer_features) <= 2:
#         raise RuntimeError(
#             "D7 baseline unavailable: fewer than 3 layers."
#         )

#     results = []

#     for index, layer in enumerate(layer_features):

#         layer_id = layer.get("layer_id", str(index))
#         layer_name = layer["layer_name"]

#         feature_evidence = {}
#         valid_z_values = []

#         for feature in STATIC_FEATURES:

#             if feature not in layer:
#                 raise KeyError(
#                     f"Missing static feature '{feature}' "
#                     f"for layer '{layer_name}'."
#                 )

#             x = layer[feature]

#             if not np.isfinite(float(x)):
#                 raise ValueError(
#                     f"Invalid {feature} in layer '{layer_name}'."
#                 )

#             baseline = []

#             for other in layer_features:
#                 if feature not in other:
#                     raise KeyError(
#                         f"Missing feature '{feature}' in baseline."
#                     )

#                 value = other[feature]

#                 if not np.isfinite(float(value)):
#                     # Invalid evidence is NOT converted to zero.
#                     continue

#                 baseline.append(float(value))

#             if len(baseline) <= 2:
#                 raise RuntimeError(
#                     f"Insufficient valid baseline for feature "
#                     f"'{feature}'."
#                 )

#             try:
#                 z = mad_zscore(x, baseline)
#             except RuntimeError as exc:
#                 if "DEGENERATE_DEVIATION" in str(exc):
#                     # This feature is not valid evidence.
#                     feature_evidence[feature] = {
#                         "status": "DEGENERATE_DEVIATION",
#                         "z": None,
#                         "e": None,
#                     }
#                     continue

#                 raise

#             e = abs(z) / (1.0 + abs(z))

#             if not np.isfinite(e):
#                 raise ValueError(
#                     f"Non-finite evidence for {layer_name}/{feature}."
#                 )

#             feature_evidence[feature] = {
#                 "status": "VALID",
#                 "z": float(z),
#                 "e": float(e),
#             }

#             valid_z_values.append(e)

#         if not valid_z_values:
#             results.append({
#                 "layer_id": layer_id,
#                 "layer_name": layer_name,
#                 "feature_evidence": feature_evidence,
#                 "E": None,
#                 "valid": False,
#             })
#             continue

#         E = max(valid_z_values)

#         results.append({
#             "layer_id": layer_id,
#             "layer_name": layer_name,
#             "feature_evidence": feature_evidence,
#             "E": float(E),
#             "valid": True,
#         })

#     return results


# # ============================================================
# # D5 – STATIC AGGREGATION
# # ============================================================

# def compute_s_static(layer_evidence):
#     """
#     D5 LOCKED.

#     S_static = 1 - Π_l (1 - E(l))

#     Only D7-valid layers participate.
#     """

#     valid_layers = [
#         layer for layer in layer_evidence
#         if layer["valid"]
#         and layer["E"] is not None
#         and np.isfinite(layer["E"])
#     ]

#     if not valid_layers:
#         raise RuntimeError(
#             "No D7-valid layer evidence available for D5."
#         )

#     s_static = 1.0

#     for layer in valid_layers:
#         E = float(layer["E"])
#         s_static *= (1.0 - E)

#     s_static = 1.0 - s_static

#     if not np.isfinite(s_static):
#         raise ValueError("S_static is non-finite.")

#     return float(np.clip(s_static, 0.0, 1.0))


# # ============================================================
# # D6 – HIGHEST RISK LAYER
# # ============================================================

# def get_highest_risk_layer(layer_evidence):
#     """
#     D6 LOCKED.

#     Highest risk = argmax E(l).

#     Exact ties are resolved using canonical layer_id ordering.
#     """

#     eligible = [
#         layer for layer in layer_evidence
#         if layer["valid"]
#         and layer["E"] is not None
#         and np.isfinite(layer["E"])
#     ]

#     if not eligible:
#         return None

#     max_E = max(layer["E"] for layer in eligible)

#     tied = [
#         layer for layer in eligible
#         if layer["E"] == max_E
#     ]

#     tied.sort(key=lambda layer: str(layer["layer_id"]))

#     return tied[0]["layer_name"]


# # ============================================================
# # D5 + D6 PUBLIC ENTRY POINT
# # ============================================================

# def compute_s_static_and_layer(layer_features):
#     """
#     Compute D7 evidence, D5 S_static and D6 highest-risk layer.
#     """

#     layer_evidence = compute_layer_evidence(layer_features)

#     s_static = compute_s_static(layer_evidence)

#     highest_risk_layer = get_highest_risk_layer(
#         layer_evidence
#     )

#     return s_static, highest_risk_layer


# # ============================================================
# # MRS + VERDICT
# # ============================================================

# def compute_mrs(
#     s_static,
#     p_tamper,
#     s_behavior=None,
#     is_quantized=False,
# ):
#     """
#     MRS LOCKED.

#     Non-quantized:
#         40*S_static + 35*P_tamper + 25*S_behavior

#     Quantized:
#         55*S_static + 45*P_tamper
#     """

#     s_static = float(s_static)
#     p_tamper = float(p_tamper)

#     if not 0.0 <= s_static <= 1.0:
#         raise ValueError("s_static must be in [0,1].")

#     if not 0.0 <= p_tamper <= 1.0:
#         raise ValueError("p_tamper must be in [0,1].")

#     if is_quantized:

#         mrs = min(
#             100.0,
#             55.0 * s_static +
#             45.0 * p_tamper,
#         )

#     else:

#         if s_behavior is None:
#             raise RuntimeError(
#                 "Non-quantized model requires S_behavior."
#             )

#         s_behavior = float(s_behavior)

#         if not 0.0 <= s_behavior <= 1.0:
#             raise ValueError(
#                 "s_behavior must be in [0,1]."
#             )

#         mrs = min(
#             100.0,
#             40.0 * s_static +
#             35.0 * p_tamper +
#             25.0 * s_behavior,
#         )

#     if mrs <= 34:
#         verdict = "PASS"
#     elif mrs <= 69:
#         verdict = "REVIEW"
#     else:
#         verdict = "FAIL"

#     return {
#         "mrs_score": round(float(mrs), 2),
#         "verdict": verdict,
#     }
