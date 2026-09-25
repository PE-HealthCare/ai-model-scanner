"""D6 locked-contract tests: authoritative identity is ``layer_name``.

Exact ties resolve by canonical lexical ordering of ``layer_name``
(docs/D6_HIGHEST_RISK_LAYER_DECISION.md Sections 3, 5.7, 13).
No ``layer_id`` field exists in production; no index/position identity.
"""

from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer


def _full_layer(name, value):
    return {
        "layer_name": name,
        "entropy": value,
        "pov_chi2": value,
        "lsb_kl": value,
        "ks_stat": value,
        "mean": value,
        "std": value,
        "skewness": value,
        "kurtosis": value,
        "sparsity": value,
        "outlier_pct": value,
    }


def test_d6_returns_p1_layer_name_for_a_unique_maximum():
    layers = [
        _full_layer("low", 1.0),
        _full_layer("middle", 2.0),
        _full_layer("target", 4.0),
    ]

    _, highest = compute_s_static_and_layer(layers)

    assert highest == "target"
    assert all("layer_id" not in layer for layer in layers)


def test_d6_exact_tie_z_layer_vs_a_layer_is_lexical_and_permutation_invariant():
    """Locked property: same tied evidence + different input order.

    order A: [z.layer, a.layer, m.low]
    order B: [a.layer, z.layer, m.low]
    Both must select 'a.layer' ('a.layer' < 'z.layer' lexically).
    """
    order_a = [
        _full_layer("z.layer", 4.0),
        _full_layer("a.layer", 4.0),
        _full_layer("m.low", 1.0),
    ]
    order_b = [order_a[1], order_a[0], order_a[2]]

    _, highest_a = compute_s_static_and_layer(order_a)
    _, highest_b = compute_s_static_and_layer(order_b)

    assert highest_a == "a.layer"
    assert highest_b == "a.layer"
    assert highest_a == highest_b
    assert all("layer_id" not in layer for layer in order_a + order_b)


def test_d6_tie_break_lexical_layer_name_permutation_invariant():
    """Exact ties are resolved using canonical lexical ordering of layer_name.

    Given layers with identical maximal evidence, 'layer_A' must be selected
    over 'layer_B' ('layer_A' < 'layer_B') regardless of input order.
    """
    # Case A: [layer_B, layer_A]
    layers_b_first = [
        _full_layer("layer_B", 4.0),
        _full_layer("layer_A", 4.0),
        _full_layer("layer_C_low", 1.0),
    ]
    _, highest_a = compute_s_static_and_layer(layers_b_first)
    assert highest_a == "layer_A"

    # Case B: [layer_A, layer_B]
    layers_a_first = [layers_b_first[1], layers_b_first[0], layers_b_first[2]]
    _, highest_b = compute_s_static_and_layer(layers_a_first)
    assert highest_b == "layer_A"
