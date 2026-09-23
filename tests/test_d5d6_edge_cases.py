# tests/test_d5d6_edge_cases.py
"""Additional edge‑case tests for D5/D6 static aggregation and highest‑risk layer selection.
"""

import pytest
from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer


def make_layer(name, stats):
    """Helper to create a layer dict with required stats.
    ``stats`` is a dict mapping stat name to value.
    """
    base = {
        "layer_name": name,
        "entropy": 0.0,
        "pov_chi2": 0.0,
        "lsb_kl": 0.0,
        "ks_stat": 0.0,
        "mean": 0.0,
        "std": 0.0,
        "skewness": 0.0,
        "kurtosis": 0.0,
        "sparsity": 0.0,
        "outlier_pct": 0.0,
    }
    base.update(stats)
    return base


def test_insufficient_comparable_layers_raises():
    """D7 requires >2 comparable layers; with only two layers a RuntimeError should be raised.
    The error message must contain the phrase 'Insufficient baseline'.
    """
    layers = [
        make_layer("a", {"entropy": 1.0, "pov_chi2": 0.2, "lsb_kl": 0.1, "ks_stat": 0.2,
                         "mean": 0, "std": 1, "skewness": 0, "kurtosis": 3, "sparsity": 0,
                         "outlier_pct": 0}),
        make_layer("b", {"entropy": 2.0, "pov_chi2": 0.3, "lsb_kl": 0.2, "ks_stat": 0.4,
                         "mean": 0, "std": 1, "skewness": 0, "kurtosis": 3, "sparsity": 0,
                         "outlier_pct": 0}),
    ]
    with pytest.raises(RuntimeError, match="Insufficient baseline"):
        compute_s_static_and_layer(layers)


def test_d6_tie_breaking_deterministic_by_index():
    """When two or more layers have identical maximal E values, the highest‑risk layer must be
    the one with the smallest canonical index (i.e. the first in the input list).
    """
    identical_stats = {
        "entropy": 1.0,
        "pov_chi2": 0.5,
        "lsb_kl": 0.2,
        "ks_stat": 0.3,
        "mean": 0,
        "std": 1,
        "skewness": 0,
        "kurtosis": 3,
        "sparsity": 0,
        "outlier_pct": 0,
    }
    layers = [
        make_layer("first", identical_stats),
        make_layer("second", identical_stats),
        make_layer("third", identical_stats),
    ]
    _, highest = compute_s_static_and_layer(layers)
    assert highest == "first"


def test_canonical_order_is_respected():
    """If the input list is shuffled, the deterministic tie‑break still follows the list order.
    This test confirms that the function does *not* re‑order layers internally.
    """
    layer_a = make_layer("a", {"entropy": 1.0, "pov_chi2": 0.1, "lsb_kl": 0.1, "ks_stat": 0.1,
                                 "mean": 0, "std": 1, "skewness": 0, "kurtosis": 3,
                                 "sparsity": 0, "outlier_pct": 0})
    layer_b = make_layer("b", {"entropy": 2.0, "pov_chi2": 0.2, "lsb_kl": 0.2, "ks_stat": 0.2,
                                 "mean": 0, "std": 1, "skewness": 0, "kurtosis": 3,
                                 "sparsity": 0, "outlier_pct": 0})
    layer_c = make_layer("c", {"entropy": 0.5, "pov_chi2": 0.05, "lsb_kl": 0.05, "ks_stat": 0.05,
                                 "mean": 0, "std": 1, "skewness": 0, "kurtosis": 3,
                                 "sparsity": 0, "outlier_pct": 0})
    layers = [layer_b, layer_a, layer_c]
    _, highest = compute_s_static_and_layer(layers)
    assert highest == "b"
