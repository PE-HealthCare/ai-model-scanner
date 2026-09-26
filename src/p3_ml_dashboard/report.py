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
from typing import Mapping, Sequence

from src.common.feature_names import FEATURE_NAMES
from src.p3_ml_dashboard.d6_layer import select_highest_risk_layer
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


def format_risk_summary(risk_results: Mapping[str, object]) -> dict[str, object]:
    """Validate and present a parsed P2 risk_results payload for P3 presentation.

    P3 is consumer-only: it performs no risk aggregation, no MRS calculation,
    and no verdict assignment. Supplied decision values are preserved without
    recalculation or alteration, while numeric values may be normalized to float
    for the presentation mapping.

    Parameters
    ----------
    risk_results:
        Parsed mapping conforming to contracts/risk_results.schema.json.

    Returns
    -------
    dict[str, object]
        Normalized presentation dictionary containing the 9 contract fields.
    """
    if not isinstance(risk_results, Mapping):
        raise ValueError("risk_results must be a mapping")

    producer = risk_results.get("producer")
    if producer != "P2":
        raise ValueError(f"risk_results producer must be 'P2', got: {producer!r}")

    mock_status = risk_results.get("mock_status")
    if mock_status not in {"MOCK", "VERIFIED-REAL", "STALE"}:
        raise ValueError(f"Invalid mock_status: {mock_status!r}")

    verdict = risk_results.get("verdict")
    if verdict not in {"PASS", "REVIEW", "FAIL"}:
        raise ValueError(f"Invalid verdict: {verdict!r}")

    mrs_score = risk_results.get("mrs_score")
    if isinstance(mrs_score, bool) or not isinstance(mrs_score, (int, float)) or not math.isfinite(mrs_score):
        raise ValueError(f"mrs_score must be a finite number, got: {mrs_score!r}")
    if not (0.0 <= float(mrs_score) <= 100.0):
        raise ValueError(f"mrs_score out of range [0, 100]: {mrs_score}")

    s_static = risk_results.get("s_static")
    if isinstance(s_static, bool) or not isinstance(s_static, (int, float)) or not math.isfinite(s_static):
        raise ValueError(f"s_static must be a finite number, got: {s_static!r}")
    if not (0.0 <= float(s_static) <= 1.0):
        raise ValueError(f"s_static out of range [0, 1]: {s_static}")

    p_tamper = risk_results.get("p_tamper")
    if isinstance(p_tamper, bool) or not isinstance(p_tamper, (int, float)) or not math.isfinite(p_tamper):
        raise ValueError(f"p_tamper must be a finite number, got: {p_tamper!r}")
    if not (0.0 <= float(p_tamper) <= 1.0):
        raise ValueError(f"p_tamper out of range [0, 1]: {p_tamper}")

    s_behavior = risk_results.get("s_behavior")
    if s_behavior is not None:
        if isinstance(s_behavior, bool) or not isinstance(s_behavior, (int, float)) or not math.isfinite(s_behavior):
            raise ValueError(f"s_behavior must be a finite number or None, got: {s_behavior!r}")
        if not (0.0 <= float(s_behavior) <= 1.0):
            raise ValueError(f"s_behavior out of range [0, 1]: {s_behavior}")
        normalized_s_behavior: float | None = float(s_behavior)
    else:
        normalized_s_behavior = None

    contract_version = risk_results.get("contract_version")
    if not isinstance(contract_version, str) or not contract_version:
        raise ValueError("contract_version must be a non-empty string")

    generation_commit = risk_results.get("generation_commit")
    if not isinstance(generation_commit, str) or not generation_commit:
        raise ValueError("generation_commit must be a non-empty string")

    return {
        "producer": "P2",
        "mock_status": str(mock_status),
        "contract_version": str(contract_version),
        "generation_commit": str(generation_commit),
        "mrs_score": float(mrs_score),
        "verdict": str(verdict),
        "s_static": float(s_static),
        "p_tamper": float(p_tamper),
        "s_behavior": normalized_s_behavior,
    }


def prepare_dashboard_results(
    risk_results: Mapping[str, object],
    ml_results: Mapping[str, object],
    static_features: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Combine and validate P2 risk_results and P3 ml_results for dashboard display.

    Parameters
    ----------
    risk_results:
        Mapping conforming to contracts/risk_results.schema.json.
    ml_results:
        Mapping conforming to contracts/ml_results.schema.json.
    static_features:
        Optional P1 ``static_features[]`` records (``contracts/features.schema.json``).
        When provided, the P3-owned D6 selector derives the highest-risk layer;
        when omitted, the D6 result is reported as ``unavailable``.

    Returns
    -------
    dict[str, object]
        Dashboard context mapping containing:
        - "risk_summary": validated risk summary from format_risk_summary
        - "ml_results": verified ml_results mapping
        - "highest_risk_layer": authoritative layer_name or "unavailable"
        - "highest_risk_evidence": winning E(l) or None
    """
    if not isinstance(ml_results, Mapping):
        raise ValueError("ml_results must be a mapping")

    risk_summary = format_risk_summary(risk_results)

    ml_producer = ml_results.get("producer")
    if ml_producer != "P3":
        raise ValueError(f"ml_results producer must be 'P3', got: {ml_producer!r}")

    ml_status = ml_results.get("mock_status")
    if ml_status not in {"MOCK", "VERIFIED-REAL", "STALE"}:
        raise ValueError(f"Invalid ml_results mock_status: {ml_status!r}")

    ml_commit = ml_results.get("generation_commit")
    if not isinstance(ml_commit, str) or not ml_commit:
        raise ValueError("ml_results generation_commit must be a non-empty string")

    p_tamper = ml_results.get("p_tamper")
    if isinstance(p_tamper, bool) or not isinstance(p_tamper, (int, float)) or not math.isfinite(p_tamper):
        raise ValueError(f"ml_results p_tamper must be a finite number, got: {p_tamper!r}")
    if not (0.0 <= float(p_tamper) <= 1.0):
        raise ValueError(f"ml_results p_tamper out of range [0, 1]: {p_tamper}")

    shap_attributions = ml_results.get("shap_attributions")
    if not isinstance(shap_attributions, Mapping):
        raise ValueError("ml_results must contain a 'shap_attributions' mapping")

    model_version = ml_results.get("model_version")
    if not isinstance(model_version, str) or not model_version:
        raise ValueError("ml_results model_version must be a non-empty string")

    if static_features is None:
        d6_result: dict[str, object] = {"highest_risk_layer": "unavailable", "evidence": None}
    else:
        d6_result = select_highest_risk_layer(static_features)

    return {
        "risk_summary": risk_summary,
        "ml_results": dict(ml_results),
        "highest_risk_layer": d6_result["highest_risk_layer"],
        "highest_risk_evidence": d6_result["evidence"],
    }


def format_results_summary(prepared: Mapping[str, object]) -> str:
    """Format prepared dashboard results as deterministic plain text.

    P3 is presentation-only: every value is echoed from the already-validated
    ``prepared`` context (see :func:`prepare_dashboard_results`). Nothing is
    recomputed here — no MRS, verdict, risk aggregation, or D6
    highest-risk-layer selection. TreeSHAP evidence is delegated verbatim to
    :func:`format_treemap_section`.
    """
    if not isinstance(prepared, Mapping):
        raise ValueError("prepared dashboard results must be a mapping")
    risk_summary = prepared.get("risk_summary")
    if not isinstance(risk_summary, Mapping):
        raise ValueError("prepared dashboard results must contain a 'risk_summary' mapping")
    ml_results = prepared.get("ml_results")
    if not isinstance(ml_results, Mapping):
        raise ValueError("prepared dashboard results must contain an 'ml_results' mapping")

    for key in (
        "producer",
        "mock_status",
        "contract_version",
        "generation_commit",
        "mrs_score",
        "verdict",
        "s_static",
        "p_tamper",
        "s_behavior",
    ):
        if key not in risk_summary:
            raise ValueError(f"risk_summary missing required field: {key!r}")

    s_behavior = risk_summary.get("s_behavior")
    if s_behavior is None:
        behavior_line = "Behavioral score (S_behavior): N/A (quantized — behavioral probing skipped)"
    else:
        behavior_line = f"Behavioral score (S_behavior): {float(s_behavior):.4f}"

    highest_layer = prepared.get("highest_risk_layer", "unavailable")
    highest_evidence = prepared.get("highest_risk_evidence")
    if highest_layer == "unavailable" or highest_evidence is None:
        highest_line = "Highest-risk layer: unavailable (no eligible per-layer evidence)"
    else:
        highest_line = f"Highest-risk layer: {highest_layer} (D6 evidence E(l)={float(highest_evidence):.4f})"

    lines = [
        "Scan results (P2 risk + P3 classifier evidence)",
        f"Verdict: {risk_summary.get('verdict')}",
        f"MRS: {float(risk_summary.get('mrs_score')):.2f}",
        f"Static score (S_static): {float(risk_summary.get('s_static')):.4f}",
        f"Tamper score (P_tamper, risk): {float(risk_summary.get('p_tamper')):.4f}",
        behavior_line,
        (
            f"Provenance: producer={risk_summary.get('producer')} "
            f"mock_status={risk_summary.get('mock_status')} "
            f"contract_version={risk_summary.get('contract_version')} "
            f"generation_commit={risk_summary.get('generation_commit')}"
        ),
        (
            f"ML evidence: model_version={ml_results.get('model_version')} "
            f"generation_commit={ml_results.get('generation_commit')}"
        ),
        "Highest-risk layer: not available in current contracts",
        highest_line,
        format_treemap_section(ml_results),
    ]
    return "\n".join(lines)
