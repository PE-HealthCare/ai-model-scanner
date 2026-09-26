"""Tests for the P3-owned D6 highest-risk-layer selector."""

from __future__ import annotations

import unittest
from typing import Any

from src.p3_ml_dashboard.d6_layer import select_highest_risk_layer

STAT_KEYS = (
    "entropy",
    "pov_chi2",
    "lsb_kl",
    "ks_stat",
    "mean",
    "std",
    "skewness",
    "kurtosis",
    "sparsity",
    "outlier_pct",
)


def _layer(name: str, values: dict[str, Any]) -> dict[str, Any]:
    layer: dict[str, Any] = {"layer_name": name}
    for key in STAT_KEYS:
        layer[key] = values.get(key)
    return layer


def _quantized_layer(name: str, ks_stat: Any) -> dict[str, Any]:
    return _layer(name, {"ks_stat": ks_stat})


class TestP3D6LayerSelector(unittest.TestCase):
    def test_unique_maximum_selects_expected_layer(self):
        layers = [
            _layer("layer.a", {"ks_stat": 0.10, "entropy": 1.0}),
            _layer("layer.b", {"ks_stat": 0.30, "entropy": 2.0}),
            _layer("layer.c", {"ks_stat": 0.90, "entropy": 4.0}),
        ]
        result = select_highest_risk_layer(layers)
        self.assertEqual(result["highest_risk_layer"], "layer.c")
        self.assertIsInstance(result["evidence"], float)
        self.assertGreaterEqual(result["evidence"], 0.0)
        self.assertLessEqual(result["evidence"], 1.0)

    def test_exact_tie_resolves_lexically_and_permutation_invariant(self):
        order_a = [
            _layer("z.layer", {"ks_stat": 0.90}),
            _layer("a.layer", {"ks_stat": 0.90}),
            _layer("m.low", {"ks_stat": 0.10}),
        ]
        order_b = [order_a[1], order_a[0], order_a[2]]
        first = select_highest_risk_layer(order_a)
        second = select_highest_risk_layer(order_b)
        self.assertEqual(first["highest_risk_layer"], "a.layer")
        self.assertEqual(second["highest_risk_layer"], "a.layer")

    def test_no_eligible_evidence_reports_unavailable(self):
        layers = [
            _layer("only-a", {}),
            _layer("only-b", {}),
            _layer("only-c", {}),
        ]
        result = select_highest_risk_layer(layers)
        self.assertEqual(result, {"highest_risk_layer": "unavailable", "evidence": None})

    def test_null_nan_inf_are_never_imputed(self):
        layers = [
            _layer("a", {"ks_stat": None, "entropy": float("nan")}),
            _layer("b", {"ks_stat": float("inf"), "entropy": float("-inf")}),
            _layer("c", {"ks_stat": None, "entropy": None}),
        ]
        self.assertEqual(
            select_highest_risk_layer(layers),
            {"highest_risk_layer": "unavailable", "evidence": None},
        )

    def test_zero_mad_degenerate_is_excluded(self):
        layers = [
            _layer("same-a", {"ks_stat": 0.50}),
            _layer("same-b", {"ks_stat": 0.50}),
            _layer("same-c", {"ks_stat": 0.50}),
            _layer("deviant", {"ks_stat": 0.90}),
        ]
        result = select_highest_risk_layer(layers)
        # Baseline median/MAD are 0.50/0.0: equal-median layers keep Z = 0
        # (E = 0), while the off-median deviant is DEGENERATE_DEVIATION and
        # excluded — so it must never win despite standing out numerically.
        self.assertEqual(result, {"highest_risk_layer": "same-a", "evidence": 0.0})

    def test_zero_mad_equal_median_is_eligible(self):
        layers = [
            _layer("same-a", {"ks_stat": 0.50}),
            _layer("same-b", {"ks_stat": 0.50}),
            _layer("same-c", {"ks_stat": 0.50}),
        ]
        result = select_highest_risk_layer(layers)
        self.assertEqual(result["highest_risk_layer"], "same-a")
        self.assertEqual(result["evidence"], 0.0)

    def test_baseline_of_two_or_fewer_is_unavailable(self):
        self.assertEqual(
            select_highest_risk_layer(
                [_layer("a", {"ks_stat": 0.10}), _layer("b", {"ks_stat": 0.90})]
            ),
            {"highest_risk_layer": "unavailable", "evidence": None},
        )

    def test_quantized_ks_stat_only_follows_same_rule(self):
        layers = [
            _quantized_layer("q1", 0.10),
            _quantized_layer("q2", 0.35),
            _quantized_layer("q3", 0.90),
        ]
        result = select_highest_risk_layer(layers)
        self.assertEqual(result["highest_risk_layer"], "q3")

    def test_bool_values_are_rejected_as_evidence(self):
        layers = [
            _layer("a", {"ks_stat": True}),
            _layer("b", {"ks_stat": False}),
            _layer("c", {"ks_stat": True}),
        ]
        self.assertEqual(
            select_highest_risk_layer(layers),
            {"highest_risk_layer": "unavailable", "evidence": None},
        )

    def test_repeated_execution_is_deterministic(self):
        layers = [
            _layer("layer.a", {"ks_stat": 0.10, "entropy": 1.0}),
            _layer("layer.b", {"ks_stat": 0.30, "entropy": 2.0}),
            _layer("layer.c", {"ks_stat": 0.90, "entropy": 4.0}),
        ]
        first = select_highest_risk_layer(layers)
        second = select_highest_risk_layer(list(reversed(layers)))
        # Unique maximum survives reversal; ties would resolve lexically.
        self.assertEqual(first["highest_risk_layer"], "layer.c")
        self.assertEqual(second["highest_risk_layer"], "layer.c")
        self.assertEqual(first, select_highest_risk_layer(layers))


if __name__ == "__main__":
    unittest.main()
