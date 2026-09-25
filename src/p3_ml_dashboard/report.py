"""P3 presentation layer: deterministic TreeSHAP report section (Sub-step 6).

Orchestration-safe thin wrapper over the frozen
:func:`src.p3_ml_dashboard.tree_shap_explainer.explain_shap_attributions`.

Ownership:
    * P3 owns this formatter. It performs no detection, classification,
      risk aggregation, MRS/verdict computation, or D6 highest-risk-layer
      selection.
    * ``scan_model.py`` remains orchestration-only and may call
      :func:`format_treemap_section` purely for display.

Semantic constraints (frozen Sub-steps 1-4):
    * Attribution-only wording: positive/negative SHAP describes movement of
      the classifier raw margin relative to baseline, never proof that a
      feature is malicious, abnormal, tampered, compromised, or safe.
    * The public ``ml_results.json`` contract exposes no classifier
      evidence-layer identity, so this module never invents or displays one.
    * Quantized payloads remain ``ks_stat``-only for attribution.
"""

from __future__ import annotations

import math
from typing import Mapping

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.tree_shap_explainer import (
    QUANTIZED_FEATURE_NAMES,
    explain_shap_attributions,
)


def _resolve_is_quantized(shap_keys: set[str]) -> bool:
    """Derive the explainer path deterministically from attribution keys."""
    if shap_keys == set(QUANTIZED_FEATURE_NAMES):
        return True
    if shap_keys == set(FEATURE_NAMES):
        return False
    # Defer to the frozen explainer's fail-closed validation for any other
    # key set by attempting the FP path (it raises a descriptive ValueError).
    return False


def format_treemap_section(
    ml_results: Mapping[str, object],
    *,
    top_n: int | None = None,
) -> str:
    """Format a concise human-readable TreeSHAP report section.

    Parameters
    ----------
    ml_results:
        Validated ``ml_results`` payload mapping containing at minimum a
        ``shap_attributions`` mapping. ``p_tamper`` is echoed verbatim as a
        classifier score when present; it is never reinterpreted here.
    top_n:
        Optional positive integer forwarded to the frozen explainer to bound
        the ranked attribution list.

    Returns
    -------
    str
        Deterministic plain-text TreeSHAP section.
    """
    if not isinstance(ml_results, Mapping):
        raise ValueError("ml_results must be a mapping")
    shap_attributions = ml_results.get("shap_attributions")
    if not isinstance(shap_attributions, Mapping):
        raise ValueError("ml_results must contain a 'shap_attributions' mapping")
    if top_n is not None:
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
            raise ValueError(f"top_n must be a positive integer, got: {top_n!r}")

    is_quantized = _resolve_is_quantized(set(shap_attributions.keys()))
    summary = explain_shap_attributions(
        shap_attributions,
        is_quantized=is_quantized,
        top_n=top_n,
    )

    lines: list[str] = [
        "P3 TreeSHAP attribution (classifier evidence only)",
    ]
    p_tamper = ml_results.get("p_tamper")
    if isinstance(p_tamper, bool):
        raise ValueError("p_tamper must be numeric, got bool")
    if p_tamper is not None:
        if not isinstance(p_tamper, (int, float)) or not math.isfinite(p_tamper):
            raise ValueError("p_tamper must be a finite number")
        lines.append(f"p_tamper (model-level classifier score): {float(p_tamper):.4f}")
    lines.append(f"Summary: {summary.summary_text}")
    if summary.all_zero:
        lines.append("Ranked attributions: none (all values 0.0)")
    else:
        lines.append("Ranked attributions:")
        for rank, attr in enumerate(summary.attributions, 1):
            sign = "+" if attr.shap_value > 0 else "-"
            lines.append(
                f"  {rank}. {attr.ui_label} ({attr.feature_name}): "
                f"{sign}{attr.abs_shap_value:.4f} [{attr.direction}]"
            )
            lines.append(f"     {attr.explanation}")
    return "\n".join(lines)
