"""Deterministic Natural-Language TreeSHAP explanation layer (P3 owner).

Converts LightGBM TreeSHAP numeric attributions into deterministic, safe,
human-readable explanations following the frozen semantic specification.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from src.common.feature_names import FEATURE_NAMES

QUANTIZED_FEATURE_NAMES: tuple[str, ...] = ("ks_stat",)

CANONICAL_FEATURE_INDEX: dict[str, int] = {
    name: idx for idx, name in enumerate(FEATURE_NAMES)
}

FEATURE_UI_LABELS: dict[str, str] = {
    "entropy": "Byte Entropy",
    "pov_chi2": "LSB Chi-Square",
    "lsb_kl": "LSB KL-Divergence",
    "ks_stat": "Layer KS-Distance",
    "mean": "Weight Mean",
    "std": "Weight Std-Dev",
    "skewness": "Weight Skewness",
    "kurtosis": "Weight Kurtosis",
    "sparsity": "Weight Sparsity",
    "outlier_pct": "Tukey Outlier Pct",
}

FEATURE_POSITIVE_WORDING: dict[str, str] = {
    "entropy": (
        "Byte distribution entropy pushed the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "pov_chi2": (
        "LSB distribution chi-square deviation pushed the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "lsb_kl": (
        "LSB KL-divergence pushed the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "ks_stat": (
        "Relative divergence from pooled layer weight distributions pushed the "
        "prediction score toward the classifierâ€™s positive class relative to the model baseline"
    ),
    "mean": (
        "Layer weight mean shifted the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "std": (
        "Layer weight standard deviation shifted the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "skewness": (
        "Layer weight distribution skewness shifted the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "kurtosis": (
        "Layer weight distribution kurtosis shifted the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "sparsity": (
        "Layer zero-weight fraction shifted the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
    "outlier_pct": (
        "Percentage of extreme weight outliers shifted the prediction score toward the "
        "classifierâ€™s positive class relative to the model baseline"
    ),
}

FEATURE_NEGATIVE_WORDING: dict[str, str] = {
    "entropy": (
        "Byte distribution entropy pushed the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "pov_chi2": (
        "LSB distribution chi-square deviation pushed the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "lsb_kl": (
        "LSB KL-divergence pushed the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "ks_stat": (
        "Relative divergence from pooled layer weight distributions pushed the "
        "prediction score toward the classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "mean": (
        "Layer weight mean shifted the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "std": (
        "Layer weight standard deviation shifted the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "skewness": (
        "Layer weight distribution skewness shifted the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "kurtosis": (
        "Layer weight distribution kurtosis shifted the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "sparsity": (
        "Layer zero-weight fraction shifted the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
    "outlier_pct": (
        "Percentage of extreme weight outliers shifted the prediction score toward the "
        "classifierâ€™s negative/clean class relative to the model baseline"
    ),
}

@dataclass(frozen=True)
class FeatureAttributionExplanation:
    """Individual feature attribution explanation."""

    feature_name: str
    ui_label: str
    shap_value: float
    abs_shap_value: float
    direction: str  # "POSITIVE" | "NEGATIVE"
    explanation: str


@dataclass(frozen=True)
class TreeSHAPSummary:
    """Aggregated TreeSHAP explanation summary."""

    summary_text: str
    attributions: tuple[FeatureAttributionExplanation, ...]
    is_quantized: bool
    all_zero: bool


def _validate_inputs(
    shap_attributions: Mapping[str, float | int],
    is_quantized: bool,
    top_n: int | None,
) -> None:
    """Enforce strict fail-closed input validation."""
    if top_n is not None:
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
            raise ValueError(f"top_n must be a positive integer, got: {top_n!r}")

    if not isinstance(shap_attributions, Mapping) or not shap_attributions:
        raise ValueError("shap_attributions must be a non-empty mapping")

    keys = set(shap_attributions.keys())
    if is_quantized:
        expected_keys = set(QUANTIZED_FEATURE_NAMES)
        if keys != expected_keys:
            raise ValueError(
                f"Quantized shap_attributions keys must be exactly {QUANTIZED_FEATURE_NAMES}, "
                f"got: {sorted(keys)}"
            )
    else:
        expected_keys = set(FEATURE_NAMES)
        if keys != expected_keys:
            raise ValueError(
                f"shap_attributions keys must match canonical FEATURE_NAMES exactly. "
                f"Missing: {sorted(expected_keys - keys)}, Unexpected: {sorted(keys - expected_keys)}"
            )

    for key, val in shap_attributions.items():
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError(f"Attribution value for {key!r} must be numeric, got: {type(val)}")
        if not math.isfinite(val):
            raise ValueError(f"Attribution value for {key!r} must be finite, got: {val}")


def explain_shap_attributions(
    shap_attributions: Mapping[str, float | int],
    *,
    is_quantized: bool = False,
    top_n: int | None = None,
) -> TreeSHAPSummary:
    """Deterministically explain TreeSHAP attributions using approved semantic mappings."""
    _validate_inputs(shap_attributions, is_quantized, top_n)

    # Filter zero attributions
    non_zero_items = [
        (name, float(val))
        for name, val in shap_attributions.items()
        if abs(float(val)) > 0.0
    ]

    if not non_zero_items:
        return TreeSHAPSummary(
            summary_text=(
                "All feature attributions are zero; the prediction corresponds "
                "directly to the model baseline expected value."
            ),
            attributions=(),
            is_quantized=is_quantized,
            all_zero=True,
        )

    # Sort deterministically:
    # Primary sort: strictly descending abs(shap)
    # Tie-breaker: canonical Master Graph index
    def _sort_key(item: tuple[str, float]) -> tuple[float, int]:
        name, val = item
        return (-abs(val), CANONICAL_FEATURE_INDEX[name])

    sorted_items = sorted(non_zero_items, key=_sort_key)

    if top_n is not None:
        sorted_items = sorted_items[:top_n]

    explanations: list[FeatureAttributionExplanation] = []

    for name, val in sorted_items:
        abs_val = abs(val)
        ui_label = FEATURE_UI_LABELS[name]

        if val > 0:
            direction = "POSITIVE"
            wording = FEATURE_POSITIVE_WORDING[name]
            explanation_sentence = f"{wording} (SHAP: +{val:.4f})."
        else:
            direction = "NEGATIVE"
            wording = FEATURE_NEGATIVE_WORDING[name]
            explanation_sentence = f"{wording} (SHAP: -{abs_val:.4f})."

        explanations.append(
            FeatureAttributionExplanation(
                feature_name=name,
                ui_label=ui_label,
                shap_value=val,
                abs_shap_value=abs_val,
                direction=direction,
                explanation=explanation_sentence,
            )
        )

    # Build deterministic summary sentence
    if is_quantized:
        ks_expl = explanations[0]
        if ks_expl.direction == "POSITIVE":
            summary_text = (
                "For this quantized model, evaluation is based on Layer KS-Distance (ks_stat). "
                f"{FEATURE_POSITIVE_WORDING['ks_stat']}."
            )
        else:
            summary_text = (
                "For this quantized model, evaluation is based on Layer KS-Distance (ks_stat). "
                f"{FEATURE_NEGATIVE_WORDING['ks_stat']}."
            )
    else:
        # Determine the strongest positive and negative contributor(s)
        pos_values = [e.abs_shap_value for e in explanations if e.direction == "POSITIVE"]
        max_pos = max(pos_values) if pos_values else None
        top_positive_drivers = [
            e.ui_label
            for e in explanations
            if e.direction == "POSITIVE" and e.abs_shap_value == max_pos
        ]

        neg_values = [e.abs_shap_value for e in explanations if e.direction == "NEGATIVE"]
        max_neg = max(neg_values) if neg_values else None
        top_negative_drivers = [
            e.ui_label
            for e in explanations
            if e.direction == "NEGATIVE" and e.abs_shap_value == max_neg
        ]

        summary_clauses = []
        if top_positive_drivers:
            summary_clauses.append(
                f"Top positive attribution factor(s) shifting the score toward the classifierâ€™s "
                f"positive class relative to the model baseline: {', '.join(top_positive_drivers)}"
            )
        if top_negative_drivers:
            summary_clauses.append(
                f"Top negative attribution factor(s) shifting the score toward the classifierâ€™s "
                f"negative/clean class relative to the model baseline: {', '.join(top_negative_drivers)}"
            )
        summary_text = ". ".join(summary_clauses) + "."

    return TreeSHAPSummary(
        summary_text=summary_text,
        attributions=tuple(explanations),
        is_quantized=is_quantized,
        all_zero=False,
    )
