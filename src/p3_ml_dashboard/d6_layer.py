"""P3-owned D6 highest-risk-layer selector.

Consumes existing P1 ``static_features[]`` records (``contracts/features.schema.json``)
and implements the locked rule in ``docs/D6_HIGHEST_RISK_LAYER_DECISION.md``:

* ``layer_name`` is the sole authoritative layer identity.
* Per-feature intra-model MAD baseline over finite numeric values only.
* ``E(l, f) = |Z| / (1 + |Z|)`` with ``Z = (x - median) / (1.4826 * MAD)``.
* ``E(l) = max`` eligible feature evidence for that layer.
* Selection is ``argmax_l E(l)``; exact ties resolve to the lexically
  smallest ``layer_name``.
* No eligible layer reports ``highest_risk_layer = "unavailable"``.

This selector performs no detection, classification, risk aggregation, or
MRS/verdict computation, and never consults TreeSHAP, ``p_tamper``,
``s_behavior``, indexes, or input ordering.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from src.common.feature_names import FEATURE_NAMES

_MAD_SCALE = 1.4826


def _is_finite_number(value: object) -> bool:
    """Return True only for real finite numeric evidence (bools rejected)."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def select_highest_risk_layer(
    static_features: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Select the highest-risk layer from P1 per-layer static evidence.

    Parameters
    ----------
    static_features:
        Sequence of P1 ``static_features[]`` mappings, each carrying the
        authoritative ``layer_name`` string plus the canonical statistics.

    Returns
    -------
    dict[str, object]
        ``{"highest_risk_layer": str, "evidence": float | None}`` where
        ``evidence`` is the winning ``E(l)`` value, or ``None`` together with
        ``"unavailable"`` when no layer has eligible evidence.
    """
    if not isinstance(static_features, Sequence) or isinstance(static_features, (str, bytes)):
        raise ValueError("static_features must be a sequence of layer mappings")

    layers = list(static_features)
    if not layers:
        return {"highest_risk_layer": "unavailable", "evidence": None}

    best_name: str | None = None
    best_evidence: float | None = None

    for layer in layers:
        if not isinstance(layer, Mapping):
            raise ValueError("each static_features entry must be a mapping")
        layer_name = layer.get("layer_name")
        if not isinstance(layer_name, str) or not layer_name:
            raise ValueError("each layer must carry a non-empty 'layer_name' string")

        layer_best: float | None = None
        for feature in FEATURE_NAMES:
            value = layer.get(feature)
            if not _is_finite_number(value):
                continue
            assert isinstance(value, (int, float))
            baseline = [
                float(candidate.get(feature))
                for candidate in layers
                if isinstance(candidate, Mapping) and _is_finite_number(candidate.get(feature))
            ]
            if len(baseline) <= 2:
                continue
            ordered = sorted(baseline)
            count = len(ordered)
            median = (
                ordered[count // 2]
                if count % 2 == 1
                else (ordered[count // 2 - 1] + ordered[count // 2]) / 2.0
            )
            deviations = sorted(abs(item - median) for item in ordered)
            mad = (
                deviations[count // 2]
                if count % 2 == 1
                else (deviations[count // 2 - 1] + deviations[count // 2]) / 2.0
            )
            target = float(value)
            if mad == 0.0:
                if target == median:
                    z_score = 0.0
                else:
                    continue
            else:
                z_score = (target - median) / (_MAD_SCALE * mad)
                if not math.isfinite(z_score):
                    continue
            evidence = abs(z_score) / (1.0 + abs(z_score))
            if layer_best is None or evidence > layer_best:
                layer_best = evidence

        if layer_best is None:
            continue
        if (
            best_evidence is None
            or layer_best > best_evidence
            or (
                layer_best == best_evidence
                and best_name is not None
                and layer_name < best_name
            )
        ):
            best_name = layer_name
            best_evidence = layer_best

    if best_name is None or best_evidence is None:
        return {"highest_risk_layer": "unavailable", "evidence": None}
    return {"highest_risk_layer": best_name, "evidence": float(best_evidence)}
