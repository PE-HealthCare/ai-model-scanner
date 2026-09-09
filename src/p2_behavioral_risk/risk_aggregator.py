# src/p2_behavioral_risk/risk_aggregator.py
import numpy as np
from .config import MAD_EPSILON


def mad_zscore(x, x_base, mock_mode=False):
    """
    Compute a robust Z‑score using Median Absolute Deviation (MAD).

    Frozen formula (do not modify):
        Z = (x - median(X_base)) / (1.4826 * MAD(X_base))

    Args:
        x: The value to score.
        x_base: Array of reference values (same statistic across all layers of THIS model).
        mock_mode: If False, raises error on unresolved D7 edge cases.
                   If True, uses placeholder for development.

    Returns:
        float Z‑score.

    Raises:
        RuntimeError: If denominator is too small and mock_mode=False (D7 unresolved).
    """
    x_base = np.asarray(x_base)
    med = np.median(x_base)
    mad = np.median(np.abs(x_base - med))
    denom = 1.4826 * mad

    if denom < MAD_EPSILON:
        if not mock_mode:
            raise RuntimeError(
                f"MAD denominator too small ({denom}). "
                "D7 behavior (zero/near-zero MAD) is unresolved. "
                "Set mock_mode=True only for development."
            )
        # Mock placeholder – DO NOT USE FOR PRODUCTION
        return 0.0

    return (x - med) / denom


def compute_s_static_and_layer(layer_features, mock_mode=False):
    """
    Compute S_static (model-level static risk) and highest_risk_layer.

    DECISION REQUIRED (D5): Exact per-layer → model-level aggregation.
    DECISION REQUIRED (D6): Exact highest-risk-layer selection.

    This function is a MOCK implementation – DO NOT USE IN PRODUCTION
    unless D5 and D6 are explicitly resolved by the team.

    Args:
        layer_features: List of dicts, each with:
            {"layer_name": str, "entropy": float, "chi_square": float,
             "kl_div": float, "ks_stat": float}
        mock_mode: If False, raises NotImplementedError.
                   If True, runs the placeholder aggregation.

    Returns:
        tuple: (s_static: float, highest_risk_layer: str)

    Raises:
        NotImplementedError: If mock_mode=False (D5/D6 unresolved).
    """
    if not mock_mode:
        raise NotImplementedError(
            "D5 (per-layer → model-level aggregation) and D6 (highest-risk-layer selection) "
            "are unresolved. Set mock_mode=True only for development."
        )

    # ============================================================
    # MOCK IMPLEMENTATION – DO NOT USE FOR PRODUCTION SCORING
    # This is a placeholder to keep the pipeline running during development.
    # The exact aggregation method must be locked by the team.
    # ============================================================

    stat_keys = ["entropy", "chi_square", "kl_div", "ks_stat"]
    per_layer_z_aggregates = []

    for stat in stat_keys:
        # Intra-model baseline: X_base comes from all layers of THIS model only.
        x_base = [lf[stat] for lf in layer_features]
        for i, lf in enumerate(layer_features):
            z = mad_zscore(lf[stat], x_base, mock_mode=True)  # pass mock_mode down
            if i >= len(per_layer_z_aggregates):
                per_layer_z_aggregates.append([])
            per_layer_z_aggregates[i].append(abs(z))

    # D5 PLACEHOLDER: Mean of absolute Z‑scores per layer, then max across layers.
    layer_scores = [np.mean(scores) for scores in per_layer_z_aggregates]
    model_raw = np.max(layer_scores)

    # Squash to [0,1] using an arbitrary divisor – this MUST be replaced.
    # DECISION REQUIRED (D5): Replace this placeholder with approved aggregation.
    s_static = float(np.clip(model_raw / 5.0, 0, 1))

    # D6 PLACEHOLDER: Layer with the highest aggregated score.
    highest_idx = int(np.argmax(layer_scores))
    highest_risk_layer = layer_features[highest_idx]["layer_name"]

    return s_static, highest_risk_layer


def compute_mrs(s_static, p_tamper, s_behavior=None, is_quantized=False):
    """
    Compute the Model Risk Score (MRS) and return verdict.

    FROZEN FORMULAS – DO NOT MODIFY.

    Non‑quantized:
        MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)

    Quantized:
        MRS = min(100, 55*S_static + 45*P_tamper)

    Verdict thresholds (frozen):
        0–34   → PASS
        35–69  → REVIEW
        70–100 → FAIL

    Args:
        s_static: Static risk score, ∈ [0,1].
        p_tamper: ML tampering probability, ∈ [0,1] (from P3).
        s_behavior: Behavioral score, ∈ [0,1] (or None if quantized).
        is_quantized: If True, uses quantized formula.

    Returns:
        dict: {"mrs": float, "verdict": str}
    """
    if is_quantized or s_behavior is None:
        mrs = min(100, 55 * s_static + 45 * p_tamper)
    else:
        mrs = min(100, 40 * s_static + 35 * p_tamper + 25 * s_behavior)

    if mrs <= 34:
        verdict = "PASS"
    elif mrs <= 69:
        verdict = "REVIEW"
    else:
        verdict = "FAIL"

    return {"mrs": round(mrs, 2), "verdict": verdict}