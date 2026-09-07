# src/p2_behavioral_risk/risk_aggregator.py
import numpy as np
from .config import MAD_EPSILON

def mad_zscore(x, x_base):
    """Step 7: Frozen MAD formula. x_base = same statistic across all layers of THIS model."""
    x_base = np.asarray(x_base)
    med = np.median(x_base)
    mad = np.median(np.abs(x_base - med))
    denom = 1.4826 * mad
    if denom < MAD_EPSILON:
        # DECISION REQUIRED (D7): Near-zero MAD guard.
        return 0.0  
    return (x - med) / denom

def compute_s_static_and_layer(layer_features):
    """
    Step 7b: Computes S_static and highest_risk_layer.
    D5 (aggregation) and D6 (layer selection) are placeholders.
    """
    stat_keys = ["entropy", "chi_square", "kl_div", "ks_stat"]
    per_layer_z_aggregates = []

    for stat in stat_keys:
        # X_base = distribution of this statistic across all layers of this exact model.
        x_base = [lf[stat] for lf in layer_features]
        for i, lf in enumerate(layer_features):
            z = mad_zscore(lf[stat], x_base)
            if i >= len(per_layer_z_aggregates):
                per_layer_z_aggregates.append([])
            per_layer_z_aggregates[i].append(abs(z))

    # D5 PLACEHOLDER: Mean of absolute Z-scores per layer.
    layer_scores = [np.mean(scores) for scores in per_layer_z_aggregates]
    
    # Squash to [0,1] using a placeholder divisor (D5 pending).
    model_raw = np.max(layer_scores)
    s_static = float(np.clip(model_raw / 5.0, 0, 1))
    
    # D6 PLACEHOLDER: Highest risk = max score.
    highest_idx = int(np.argmax(layer_scores))
    highest_risk_layer = layer_features[highest_idx]["layer_name"]
    
    return s_static, highest_risk_layer

def compute_mrs(s_static, p_tamper, s_behavior=None, is_quantized=False):
    """Step 8: Frozen MRS formulas. 100% safe to build."""
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