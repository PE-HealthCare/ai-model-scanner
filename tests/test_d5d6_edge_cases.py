"""D5/D6 edge-case tests under the locked P1/D6 contract.

Authoritative identity is ``layer_name``; exact ties are NOT asserted here
(they are covered lexically and permutation-invariantly in
tests/test_d6_tie_break.py). This module keeps D7/no-eligible coverage and
asserts no fabricated ``layer_id`` / index-based identity.
"""

import pytest

from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer


def make_layer(name, stats):
    """Helper to create a layer dict with required stats."""
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
    """D7 requires more than two comparable layers."""
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


def test_no_eligible_layers_fail_closed_without_fabricated_identity():
    """No D7-valid evidence must fail closed, never invent an identity."""
    layers = [
        make_layer("only-a", {"entropy": None, "pov_chi2": None, "lsb_kl": None,
                              "ks_stat": None, "mean": None, "std": None,
                              "skewness": None, "kurtosis": None,
                              "sparsity": None, "outlier_pct": None}),
        make_layer("only-b", {"entropy": None, "pov_chi2": None, "lsb_kl": None,
                              "ks_stat": None, "mean": None, "std": None,
                              "skewness": None, "kurtosis": None,
                              "sparsity": None, "outlier_pct": None}),
        make_layer("only-c", {"entropy": None, "pov_chi2": None, "lsb_kl": None,
                              "ks_stat": None, "mean": None, "std": None,
                              "skewness": None, "kurtosis": None,
                              "sparsity": None, "outlier_pct": None}),
    ]
    with pytest.raises(RuntimeError, match="No D7-valid layer evidence"):
        compute_s_static_and_layer(layers)
    assert all("layer_id" not in layer for layer in layers)


def test_all_non_finite_evidence_fails_closed_without_fabricated_identity():
    """All-NaN/Inf evidence must fail closed, never invent an identity."""
    layers = [
        make_layer("only-a", {"entropy": float("nan"), "pov_chi2": float("inf"), "lsb_kl": float("-inf"),
                              "ks_stat": float("nan"), "mean": float("inf"), "std": float("nan"),
                              "skewness": float("inf"), "kurtosis": float("nan"),
                              "sparsity": float("inf"), "outlier_pct": float("nan")}),
        make_layer("only-b", {"entropy": float("inf"), "pov_chi2": float("nan"), "lsb_kl": float("inf"),
                              "ks_stat": float("inf"), "mean": float("nan"), "std": float("inf"),
                              "skewness": float("nan"), "kurtosis": float("inf"),
                              "sparsity": float("nan"), "outlier_pct": float("inf")}),
        make_layer("only-c", {"entropy": float("-inf"), "pov_chi2": float("inf"), "lsb_kl": float("nan"),
                              "ks_stat": float("-inf"), "mean": float("inf"), "std": float("nan"),
                              "skewness": float("inf"), "kurtosis": float("nan"),
                              "sparsity": float("inf"), "outlier_pct": float("-inf")}),
    ]
    with pytest.raises(RuntimeError, match="No D7-valid layer evidence"):
        compute_s_static_and_layer(layers)
    assert all("layer_id" not in layer for layer in layers)


def test_unique_maximum_does_not_depend_on_input_position():
    """A unique maximum keeps its layer_name winner under reordering."""
    winner = make_layer("winner", {"entropy": 4.0, "pov_chi2": 4.0, "lsb_kl": 4.0,
                                   "ks_stat": 4.0, "mean": 4.0, "std": 4.0,
                                   "skewness": 4.0, "kurtosis": 4.0,
                                   "sparsity": 4.0, "outlier_pct": 4.0})
    other1 = make_layer("other1", {"entropy": 1.0, "pov_chi2": 1.0, "lsb_kl": 1.0,
                                   "ks_stat": 1.0, "mean": 1.0, "std": 1.0,
                                   "skewness": 1.0, "kurtosis": 1.0,
                                   "sparsity": 1.0, "outlier_pct": 1.0})
    other2 = make_layer("other2", {"entropy": 2.0, "pov_chi2": 2.0, "lsb_kl": 2.0,
                                   "ks_stat": 2.0, "mean": 2.0, "std": 2.0,
                                   "skewness": 2.0, "kurtosis": 2.0,
                                   "sparsity": 2.0, "outlier_pct": 2.0})
    _, highest_first = compute_s_static_and_layer([winner, other1, other2])
    _, highest_last = compute_s_static_and_layer([other1, other2, winner])
    assert highest_first == "winner"
    assert highest_last == "winner"
