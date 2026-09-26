"""P2 D5/D6 contract tests using a self-contained synthetic fixture.

This module is artifact-independent: it does NOT read `data/inputs/`
(which does not exist in the current recovery-mainline structure) and does
NOT read `data/outputs/features.json` (a generated P1 artifact). A P2 unit
test must not depend on a generated artifact, so the layer evidence is
defined inline and deterministically below.

Locked contracts exercised (production implementation unchanged):

  D5  S_static = 1 - prod(1 - E_l), with E_l = max_f |Z_lf| / (1 + |Z_lf|)
  D6  highest_risk_layer = argmax_l (E_l), reported by production identity
      `layer_name` (there is no `layer_id` and no positional identity)
  D7  Z = (x - median) / (1.4826 * MAD)

Fixture design
--------------
Three layers are used because D7 requires more than two comparable baseline
observations; two layers are rejected as insufficient evidence. Only
`ks_stat` carries evidence. The other nine FP measurements are JSON `null`,
which the production code treats as *unavailable* and skips. They are never
zero-imputed: substituting 0 would fabricate evidence and would change the
aggregate.

Baseline semantics: for a given statistic the production intra-model
baseline is every layer holding a finite value for that statistic, including
the target layer itself. That behaviour is preserved as-is here; this test
asserts against it rather than redesigning it.

Expected-value derivation (independent of the production code)
------------------------------------------------------------
For the ks_stat values [0.10, 0.30, 0.90]:

    median  = 0.30
    MAD     = median(|0.10-0.30|, |0.30-0.30|, |0.90-0.30|) = 0.20
    Z       = (x - 0.30) / (1.4826 * 0.20)
    E_l     = |Z| / (1 + |Z|)

        layer1: Z = -0.6744907594765952  E = 0.40280351244662854
        layer2: Z =  0.0                 E = 0.0
        layer3: Z =  2.0234722784297863  E = 0.6692544505420962

    S_static = 1 - (1 - E1)(1 - E2)(1 - E3) = 0.8024799195898299
    highest-risk layer = layer3 (unique maximum, no tie)

Exact-tie and permutation-invariance behaviour is covered by the dedicated
tests/test_d6_tie_break.py and is deliberately not duplicated here.
"""

import math

import pytest

from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer

# The full canonical static-feature contract. Only `ks_stat` is given a
# value below; the rest are genuinely unavailable and therefore null.
FP_ONLY_STATS = (
    "entropy",
    "pov_chi2",
    "lsb_kl",
    "mean",
    "std",
    "skewness",
    "kurtosis",
    "sparsity",
    "outlier_pct",
)

# ks_stat values, chosen so the MAD baseline is non-degenerate and the
# per-layer evidence has a single unique maximum.
KS_BY_LAYER = (
    ("synthetic.layer1", 0.10),
    ("synthetic.layer2", 0.30),
    ("synthetic.layer3", 0.90),
)

EXPECTED_S_STATIC = 0.8024799195898299
EXPECTED_HIGHEST_RISK_LAYER = "synthetic.layer3"


def _layer_features():
    """Deterministic P2 layer evidence: identity plus one eligible statistic.

    `layer_name` is the production layer identity. The nine FP-only
    measurements are None (unavailable), never 0.
    """
    layers = []
    for layer_name, ks_stat in KS_BY_LAYER:
        layer = {"layer_name": layer_name, "ks_stat": ks_stat}
        for stat in FP_ONLY_STATS:
            layer[stat] = None
        layers.append(layer)
    return layers


def test_d5_s_static_matches_independent_derivation():
    """D5: S_static equals 1 - prod(1 - E_l) computed from the fixture."""
    layers = _layer_features()
    s_static, _ = compute_s_static_and_layer(layers)

    assert isinstance(s_static, float)
    assert math.isfinite(s_static)
    # Independently derived in the module docstring from the fixture values;
    # NOT obtained by calling the production MAD/aggregation code.
    assert s_static == pytest.approx(EXPECTED_S_STATIC, abs=1e-12)


def test_d6_returns_expected_layer_name():
    """D6: the highest-risk layer is reported by `layer_name` identity."""
    layers = _layer_features()
    _, highest_risk_layer = compute_s_static_and_layer(layers)

    # layer3 has the unique maximum E_l (0.6692...), so it must be selected
    # and reported under its production identity string.
    assert highest_risk_layer == EXPECTED_HIGHEST_RISK_LAYER
    assert highest_risk_layer in {name for name, _ in KS_BY_LAYER}


def test_d5_is_deterministic_and_order_stable_for_unique_maximum():
    """The same fixture always yields the same aggregate and identity."""
    first_s, first_layer = compute_s_static_and_layer(_layer_features())
    second_s, second_layer = compute_s_static_and_layer(_layer_features())

    assert second_s == first_s
    assert second_layer == first_layer == EXPECTED_HIGHEST_RISK_LAYER

def test_d5_fails_closed_when_no_layer_has_eligible_evidence():
    """D5 must fail closed when every layer has only unavailable evidence."""
    layers = []
    for layer_name, _ in KS_BY_LAYER:
        layer = {"layer_name": layer_name, "ks_stat": None}
        for stat in FP_ONLY_STATS:
            layer[stat] = None
        layers.append(layer)

    with pytest.raises(RuntimeError, match="No D7-valid layer evidence available for D5"):
        compute_s_static_and_layer(layers)
