# tests/test_d5_operator.py
"""
Locked D5 operator + eligibility proofs.

Contract (P1 Phase 1-3 canonical 10-feature set):
    Z(l,f)   = (x(l,f) - median(f)) / (1.4826 * MAD(f))
    e(l,f)   = abs(Z) / (1 + abs(Z))
    E(l)     = max over ELIGIBLE feature evidence only
    S_static = 1 - product over ELIGIBLE layers of (1 - E(l))

Eligibility rule: missing / None / non-finite / degenerate evidence stays
NON-ELIGIBLE and is never substituted with zero evidence.

Scope: D5 ONLY. This module deliberately contains:
  - no layer_id fixture or assertion,
  - no D6 input-order tie-break assertion (layer membership is proven via
    the aggregation input captured at np.prod, not via the D6 selection),
  - no MRS / D8 / quantized / P3 behavior.
"""

import inspect
import statistics
from unittest import mock

import numpy as np
import pytest

from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer

# ------------------------------------------------------------------ contract
CANONICAL = (
    "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean",
    "std", "skewness", "kurtosis", "sparsity", "outlier_pct",
)

_BASE = {
    "entropy": 1.5, "pov_chi2": 2.0, "lsb_kl": 0.1, "ks_stat": 0.5,
    "mean": 0.0, "std": 1.0, "skewness": 0.0, "kurtosis": 3.0,
    "sparsity": 0.0, "outlier_pct": 5.0,
}


def full_layer(name, **overrides):
    """Canonical 10-feature layer dict (never contains chi_square/kl_div)."""
    d = {"layer_name": name}
    d.update(_BASE)
    d.update(overrides)
    return d


def all_none_layer(name):
    d = {"layer_name": name}
    d.update({k: None for k in CANONICAL})
    return d


# ------------------------------------------- independent reference operators
# Restated from the LOCKED decision; pure-python, independent of the
# implementation under test.
def _eligible_e(x, values):
    """Locked feature evidence, or None when the evidence is non-eligible."""
    if x is None:
        return None
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values])
    if mad == 0.0:
        if x == med:
            return 0.0          # deterministic zero anomaly (eligible)
        return None             # DEGENERATE_DEVIATION -> non-eligible
    z = (x - med) / (1.4826 * mad)
    a = abs(z)
    return a / (1 + a)


def _layer_E(candidates):
    vals = [c for c in candidates if c is not None]
    return max(vals) if vals else None


def _S_static(e_list):
    p = 1.0
    for e in e_list:
        p *= (1.0 - e)
    return 1.0 - p


def _run(layers):
    """Run D5 and capture the exact layer_E factors fed to np.prod."""
    with mock.patch.object(np, "prod", wraps=np.prod) as spy:
        s_static, _highest = compute_s_static_and_layer(layers)
    factors = list(spy.call_args[0][0])
    return s_static, factors


# ------------------------------------------------- #1 / #2 canonical contract
def test_canonical_ten_feature_input_accepted():
    s_static, _ = compute_s_static_and_layer(
        [full_layer("L1", entropy=3.0),
         full_layer("L2", entropy=1.0),
         full_layer("L3", entropy=2.0)]
    )
    assert 0.0 <= s_static <= 1.0


def test_no_legacy_feature_names_in_d5_code():
    src = inspect.getsource(compute_s_static_and_layer)
    assert "chi_square" not in src
    assert "kl_div" not in src


# ---------------------------- #3 / #4 / #5 exact e, E and S_static operators
def test_exact_d5_operators_hand_calculated():
    # entropy:  median 1, MAD 1  ->  z(L3) ~= 1 -> e ~= 0.5 exactly-on-track
    #           z(L1) is NEGATIVE (proves abs(Z) in the feature operator)
    # pov_chi2: second positive candidate for L3 (proves E = max, not sum/min/mean)
    b_ent = 1.0 + 1.4826
    b_pov = 0.5 + 0.14826
    layers = [
        full_layer("L1", entropy=0.0, pov_chi2=0.4),
        full_layer("L2", entropy=1.0, pov_chi2=0.5),
        full_layer("L3", entropy=b_ent, pov_chi2=b_pov),
    ]
    # remaining 8 features are constant across layers -> eligible e == 0
    ent = [0.0, 1.0, b_ent]
    pov = [0.4, 0.5, b_pov]

    # fixture-intent sanity: locked Z for L3/entropy is ~1 (b_ent rounds
    # at [2,4) ulp precision, so allow 1 ulp) -> e ~= 0.5
    med_ent = statistics.median(ent)
    mad_ent = statistics.median([abs(v - med_ent) for v in ent])
    z3 = (b_ent - med_ent) / (1.4826 * mad_ent)
    assert abs(z3 - 1.0) < 1e-15
    assert abs(_eligible_e(b_ent, ent) - 0.5) < 1e-15

    expected_E = [
        _layer_E([_eligible_e(l["entropy"], ent),
                  _eligible_e(l["pov_chi2"], pov)] + [0.0] * 8)
        for l in layers
    ]
    expected = _S_static(expected_E)

    s_static, _ = compute_s_static_and_layer(layers)
    assert abs(s_static - expected) < 1e-12
    # max-semantics guard: E(L3)=0.5 (a sum of 1.0 would force S == 1.0)
    assert abs(s_static - 1.0) > 1e-6


# ------------------------------------------------- #6 missing evidence rules
def test_missing_feature_keys_are_non_eligible():
    # L4m carries ONLY layer_name + entropy: no KeyError, no zero substitution;
    # its evidence comes solely from the features it actually has.
    layers = [
        full_layer("L1", entropy=3.0),
        full_layer("L2", entropy=1.0),
        full_layer("L3", entropy=2.0),
        {"layer_name": "L4m", "entropy": 2.0},
    ]
    ent = [3.0, 1.0, 2.0, 2.0]
    e1 = _eligible_e(3.0, ent)
    expected = _S_static([
        _layer_E([e1] + [0.0] * 9),          # L1: entropy dominates, rest 0
        _layer_E([_eligible_e(1.0, ent)] + [0.0] * 9),
        _layer_E([_eligible_e(2.0, ent)] + [0.0] * 9),
        _layer_E([_eligible_e(2.0, ent)]),   # L4m: entropy only
    ])
    s_static, factors = _run(layers)
    assert abs(s_static - expected) < 1e-12
    assert len(factors) == 4   # partial-key layer stays eligible via entropy


# ------------------------------------- #7 / #9 / #12 mixed feature eligibility
def test_mixed_eligible_and_noneligible_features_use_only_eligible():
    # L1.outlier_pct : DEGENERATE (MAD=0, x != median) -> non-eligible
    # L4.outlier_pct : None (unavailable)               -> non-eligible
    # all other FP features: None everywhere            -> non-eligible
    driving = ("entropy", "sparsity", "outlier_pct")

    def layer(name, ent, sp, outl):
        d = {"layer_name": name, "entropy": ent, "sparsity": sp, "outlier_pct": outl}
        d.update({k: None for k in CANONICAL if k not in driving})
        return d

    layers = [
        layer("L1", 3.0, 0.1, 100.0),
        layer("L2", 1.0, 0.2, 0.0),
        layer("L3", 2.0, 0.15, 0.0),
        layer("L4", 2.0, 0.12, None),
    ]
    ent = [3.0, 1.0, 2.0, 2.0]
    sp = [0.1, 0.2, 0.15, 0.12]
    outl = [100.0, 0.0, 0.0]

    expected_E = []
    for i, lay in enumerate(layers):
        cands = [
            _eligible_e(lay["entropy"], ent),
            _eligible_e(lay["sparsity"], sp),
            _eligible_e(lay["outlier_pct"], outl) if i < 3 else None,
        ]
        expected_E.append(_layer_E(cands))
    assert all(e is not None for e in expected_E)  # every layer stays eligible

    expected = _S_static(expected_E)
    s_static, factors = _run(layers)
    assert abs(s_static - expected) < 1e-12
    assert len(factors) == 4
    assert np.isfinite(s_static)


# ------------------------------------------------- #8 non-finite excluded (never abort, never impute)
def test_non_finite_target_rejected():
    # NaN target is unavailable evidence for that feature only: L1 still
    # aggregates via its nine remaining finite features, and the NaN is
    # excluded from the entropy baseline. Must not abort D5.
    layers_nan = [
        full_layer("L1", entropy=float("nan")),
        full_layer("L2", entropy=1.0),
        full_layer("L3", entropy=2.0),
        full_layer("L4", entropy=3.0),
    ]
    layers_none = [
        full_layer("L1", entropy=None),
        full_layer("L2", entropy=1.0),
        full_layer("L3", entropy=2.0),
        full_layer("L4", entropy=3.0),
    ]
    s_nan, factors_nan = _run(layers_nan)
    s_none, factors_none = _run(layers_none)
    assert np.isfinite(s_nan)
    assert abs(s_nan - s_none) < 1e-12
    assert len(factors_nan) == 4


def test_non_finite_baseline_rejected():
    # +Inf in the baseline is excluded from eligible evidence; D5 must not
    # abort and must match the result with that entry marked unavailable.
    layers_inf = [
        full_layer("L1", entropy=float("inf")),
        full_layer("L2", entropy=1.0),
        full_layer("L3", entropy=2.0),
        full_layer("L4", entropy=3.0),
    ]
    layers_none = [
        full_layer("L1", entropy=None),
        full_layer("L2", entropy=1.0),
        full_layer("L3", entropy=2.0),
        full_layer("L4", entropy=3.0),
    ]
    s_inf, factors_inf = _run(layers_inf)
    s_none, _ = _run(layers_none)
    assert np.isfinite(s_inf)
    assert abs(s_inf - s_none) < 1e-12
    assert len(factors_inf) == 4


def test_inf_value_excluded_from_feature_evidence():
    # Focused regression: a single +Inf / -Inf must not abort D5 and must
    # contribute no evidence for that feature. KS-only quantized-style rows
    # keep working on the remaining finite evidence.
    layers = [
        {"layer_name": "Q1", "ks_stat": 0.10},
        {"layer_name": "Q2", "ks_stat": float("inf")},
        {"layer_name": "Q3", "ks_stat": 0.35},
        {"layer_name": "Q4", "ks_stat": 0.75},
    ]
    s_inf, factors_inf = _run(layers)
    s_ref, factors_ref = _run([
        {"layer_name": "Q1", "ks_stat": 0.10},
        {"layer_name": "Q2", "ks_stat": None},
        {"layer_name": "Q3", "ks_stat": 0.35},
        {"layer_name": "Q4", "ks_stat": 0.75},
    ])
    assert np.isfinite(s_inf)
    assert abs(s_inf - s_ref) < 1e-12
    # Finite KS-only payload without any Inf still aggregates normally.
    s_plain, factors_plain = _run([
        {"layer_name": "Q1", "ks_stat": 0.10},
        {"layer_name": "Q3", "ks_stat": 0.35},
        {"layer_name": "Q4", "ks_stat": 0.75},
    ])
    assert np.isfinite(s_plain)
    assert len(factors_plain) == 3


# ------------------------------ #9 / #10 degenerate layer excluded from E list
def test_fully_degenerate_layer_not_inserted_into_layer_e():
    # L4 differs from three identical layers in EVERY feature:
    # per-feature MAD == 0 with x != median -> DEGENERATE for L4 everywhere
    # -> zero eligible features -> NOT inserted (never E=0 evidence).
    shifted = {k: v + 1.0 for k, v in _BASE.items()}
    layers = [
        full_layer("L1"),
        full_layer("L2"),
        full_layer("L3"),
        full_layer("L4", **shifted),
    ]
    s_static, factors = _run(layers)
    assert len(factors) == 3          # only the eligible layers aggregate
    assert s_static == 0.0            # from 3 genuine zero-anomaly layers


# ------------------------------------------ #13 only eligible layers aggregate
def test_mixed_layers_aggregate_only_eligible_layers():
    # L0 has no eligible evidence at all and sits FIRST in the input list.
    # Layer membership is proven at the aggregation input (np.prod factors):
    # no D6 selection / tie-order is asserted here.
    layers = [
        all_none_layer("L0_no_evidence"),
        full_layer("L1"),
        full_layer("L2"),
        full_layer("L3"),
    ]
    s_static, factors = _run(layers)
    assert len(factors) == 3          # L0 not inserted
    assert s_static == 0.0


# ------------------------------------------------- #11 no fabricated S_static
@pytest.mark.parametrize("payload", [
    [all_none_layer("A"), all_none_layer("B"),
     all_none_layer("C"), all_none_layer("D")],   # all evidence unavailable
    [],                                            # no layers at all
    [{"layer_name": "A", "entropy": 1.0, "ks_stat": 1.0},   # baseline-starved
     {"layer_name": "B", "entropy": 1.0, "ks_stat": 1.0}],
])
def test_no_eligible_layers_fail_closed(payload):
    # Must raise the explicit unavailable signal, NOT return S_static = 0.0
    # as if zero were measured evidence.
    with pytest.raises(RuntimeError, match="No D7-valid layer evidence"):
        compute_s_static_and_layer(payload)
