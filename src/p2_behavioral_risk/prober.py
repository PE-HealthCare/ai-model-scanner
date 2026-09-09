"""P2 risk aggregation: real MRS scoring + Phase 1 mock.

Real path:
    build_risk_results(features, ml_results, generation_commit)
        -> s_static  : data-driven static steganalysis risk in [0, 1],
                       derived from the ACTUAL per-layer features (no
                       hardcoded constants);
        -> p_tamper  : P3 classifier probability, passed through;
        -> s_behavior: None when no behavioral evidence exists. The contract
                       allows null and we honor that — missing evidence is
                       NEVER fabricated and NEVER silently treated as zero
                       risk.

Behavioral-evidence routing (see compute_mrs) between the two FROZEN
formulas (REQUIREMENTS.md REQ-054 / solution-architecture.md #24 /
AGENT_RULES.md #4). This is evidence-state routing plus an incomplete-
evidence guard, NOT a new MRS formula and NOT an architectural formula
change:

    quantized     + s_behavior=None  -> documented bypass:
                                        MRS = min(100, 55*s_static + 45*p_tamper)
    quantized     + s_behavior set   -> rejected (probing is skipped by design)
    non-quantized + s_behavior=None  -> BLOCKED: incomplete evidence. The
                                        pipeline raises and STOPS: NO MRS, NO
                                        verdict, NO risk_results artifact; the
                                        frozen formulas are NEVER renormalized
                                        and their weights are NEVER
                                        redistributed.
    non-quantized + valid s_behavior -> MRS = min(100, 40*s_static +
                                        35*p_tamper + 25*s_behavior)

Verdict thresholds (preserved): PASS < 35 <= REVIEW < 70 <= FAIL.

s_static derivation (documented, deterministic):
Each of three canonical anomaly indicators is aggregated across layers
(element-count weighted) and mapped to [0, 1] with documented reference
ranges; the mean of the three clipped risks forms s_static:
    lsb_kl  : natural weights sit around 0.1-0.3 bits; LSB steganography
              drives the LSB toward uniform (KL -> 0).
              Risk decreases from 1 at lsb_kl=0 to 0 at lsb_kl>=0.05.
    ks_stat : max ECDF deviation vs fitted Gaussian; > 0.25 is a strong
              distributional anomaly at n >= 512.
              Risk increases from 0 at ks_stat<=0.05 to 1 at ks_stat>=0.25.
    pov_chi2: ~1 means Gaussian-like; anomalies inflate it.
              Risk = min(sqrt(pov_chi2) / 10^(1.5), 1): 0 at 1, ~0.32 at
              10, 1.0 at ~316.

Mock path (Phase 1, preserved for tests):
    build_mock_risk_results(ml_results, generation_commit)
"""

from __future__ import annotations

import math

# Documented reference ranges for s_static mapping (see module docstring).
_LSB_KL_RISK_HIGH_AT = 0.0   # lsb_kl at/below this -> static risk 1.0
_LSB_KL_RISK_ZERO_AT = 0.05  # lsb_kl at/above this -> static risk 0.0
_KS_RISK_ZERO_AT = 0.05      # ks_stat at/below this -> static risk 0.0
_KS_RISK_FULL_AT = 0.25      # ks_stat at/above this -> static risk 1.0
_POV_CHI2_SATURATION = 10.0 ** 1.5  # pov_chi2 at/above this -> static risk 1.0


def _layer_aggregate(static_features: list[dict], name: str) -> float:
    weights = [max(int(layer.get("n_elements", 1)), 1) for layer in static_features]
    total = float(sum(weights))
    return sum(float(layer[name]) * w for layer, w in zip(static_features, weights)) / total


def compute_s_static(static_features: list[dict]) -> float:
    """Deterministic data-driven static risk score in [0, 1]."""
    lsb_kl = _layer_aggregate(static_features, "lsb_kl")
    ks_stat = _layer_aggregate(static_features, "ks_stat")
    pov_chi2 = _layer_aggregate(static_features, "pov_chi2")

    r_lsb = (_LSB_KL_RISK_ZERO_AT - lsb_kl) / (_LSB_KL_RISK_ZERO_AT - _LSB_KL_RISK_HIGH_AT)
    r_ks = (ks_stat - _KS_RISK_ZERO_AT) / (_KS_RISK_FULL_AT - _KS_RISK_ZERO_AT)
    r_pov = math.sqrt(max(pov_chi2, 1.0)) / _POV_CHI2_SATURATION

    s_static = (
        min(max(r_lsb, 0.0), 1.0) + min(max(r_ks, 0.0), 1.0) + min(max(r_pov, 0.0), 1.0)
    ) / 3.0
    if math.isnan(s_static):  # defensive: malformed inputs must not yield NaN
        raise ValueError("s_static computed to NaN; refusing to emit a risk artifact")
    return float(s_static)


def compute_mrs(
    s_static: float,
    p_tamper: float,
    s_behavior: float | None,
    is_quantized: bool,
) -> float:
    """Route the behavioral-evidence state onto the FROZEN MRS formulas.

    This is not a new formula and not an architectural formula change: it
    applies exactly the two frozen formulas (non-quantized 40/35/25,
    quantized 55/45) and guards the incomplete-evidence state mandated by
    Phase 5 PLAN #8 ("STOP / non-zero status / NO MRS / NO verdict / NO
    fabricated risk_results.json / No fallback score may be invented").
    Deterministic in all reachable states.
    """
    if is_quantized:
        if s_behavior is not None:
            raise ValueError(
                "BLOCKED: behavioral evidence is not permitted for a quantized "
                "model; the quantized bypass skips probing, so s_behavior must "
                "be null"
            )
        # Frozen quantized formula (no behavioral component).
        return min(100.0, 55.0 * s_static + 45.0 * p_tamper)

    if s_behavior is None:
        # Incomplete-evidence guard — a pipeline stop, NOT an MRS scoring case:
        # required behavioral evidence is missing for an applicable
        # non-quantized model. No MRS, no verdict, no risk_results artifact;
        # the frozen formulas are never renormalized and their weights are
        # never redistributed, and no S_behavior value is fabricated.
        raise ValueError(
            "BLOCKED: required behavioral evidence (S_behavior) is missing for "
            "a non-quantized model; pipeline stops with NO MRS, NO verdict and "
            "NO risk_results artifact (no renormalization, no weight "
            "redistribution)"
        )
    if not (math.isfinite(s_behavior) and 0.0 <= s_behavior <= 1.0):
        raise ValueError(
            f"BLOCKED: S_behavior must be a finite number in [0, 1], got {s_behavior!r}"
        )
    # Frozen non-quantized formula.
    return min(100.0, 40.0 * s_static + 35.0 * p_tamper + 25.0 * s_behavior)


def build_risk_results(features: dict, ml_results: dict, generation_commit: str) -> dict:
    """Real risk aggregation payload for the pipeline (P2, VERIFIED-REAL)."""
    if features.get("producer") != "P1" or features.get("mock_status") != "VERIFIED-REAL":
        raise ValueError("P2 real aggregation requires P1 VERIFIED-REAL features")
    if features.get("generation_commit") != generation_commit:
        raise ValueError("P2 rejects stale P1 artifact generation")
    if ml_results.get("producer") != "P3" or ml_results.get("mock_status") != "VERIFIED-REAL":
        raise ValueError("P2 real aggregation requires P3 VERIFIED-REAL ml_results")
    if ml_results.get("generation_commit") != generation_commit:
        raise ValueError("P2 rejects stale P3 artifact generation")

    static_features = features["static_features"]
    if not static_features:
        raise ValueError("P2 requires at least one analyzed layer")
    for layer in static_features:
        missing = [n for n in ("lsb_kl", "ks_stat", "pov_chi2") if n not in layer]
        if missing:
            raise ValueError(f"layer {layer.get('layer_name')!r} missing features {missing}")

    s_static = compute_s_static(static_features)
    p_tamper = float(ml_results["p_tamper"])
    s_behavior = None  # no behavioral prober exists yet: NO fabricated evidence

    is_quantized = features.get("is_quantized")
    if not isinstance(is_quantized, bool):
        raise ValueError("P2 requires the P1 boolean is_quantized tag to route MRS")

    mrs_score = compute_mrs(s_static, p_tamper, s_behavior, is_quantized)
    verdict = "PASS" if mrs_score < 35 else "REVIEW" if mrs_score < 70 else "FAIL"

    return {
        "producer": "P2",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit,
        "mrs_score": float(min(mrs_score, 100.0)),
        "verdict": verdict,
        "s_static": s_static,
        "p_tamper": p_tamper,
        "s_behavior": s_behavior,
    }


def build_mock_risk_results(ml_results: dict, generation_commit: str) -> dict:
    if ml_results.get("producer") != "P3" or ml_results.get("mock_status") != "MOCK":
        raise ValueError("Phase 1 mock P2 requires a P3 MOCK ML artifact")
    if ml_results.get("generation_commit") != generation_commit:
        raise ValueError("Phase 1 P2 rejects stale P3 artifact generation")
    s_static, s_behavior = 0.10, 0.05
    p_tamper = float(ml_results["p_tamper"])
    mrs_score = min(100.0, 40 * s_static + 35 * p_tamper + 25 * s_behavior)
    verdict = "PASS" if mrs_score < 35 else "REVIEW" if mrs_score < 70 else "FAIL"
    return {
        "producer": "P2", "mock_status": "MOCK", "contract_version": "1.0", "generation_commit": generation_commit,
        "mrs_score": mrs_score, "verdict": verdict, "s_static": s_static, "p_tamper": p_tamper, "s_behavior": s_behavior,
    }