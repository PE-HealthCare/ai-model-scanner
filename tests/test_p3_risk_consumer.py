"""Tests for P3 consumption of P2 risk_results contract."""

from __future__ import annotations

import unittest
from typing import Any

from src.p3_ml_dashboard.report import format_risk_summary


def _valid_risk_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "producer": "P2",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0.0",
        "generation_commit": "abc1234",
        "mrs_score": 42.5,
        "verdict": "REVIEW",
        "s_static": 0.35,
        "p_tamper": 0.45,
        "s_behavior": 0.20,
    }
    base.update(overrides)
    return base


class TestP3RiskConsumer(unittest.TestCase):
    def test_consumes_valid_p2_risk_results(self):
        payload = _valid_risk_payload()
        summary = format_risk_summary(payload)

        self.assertEqual(summary["producer"], "P2")
        self.assertEqual(summary["mock_status"], "VERIFIED-REAL")
        self.assertEqual(summary["verdict"], "REVIEW")
        self.assertAlmostEqual(summary["mrs_score"], 42.5)
        self.assertAlmostEqual(summary["s_static"], 0.35)
        self.assertAlmostEqual(summary["p_tamper"], 0.45)
        self.assertAlmostEqual(summary["s_behavior"], 0.20)
        self.assertEqual(summary["generation_commit"], "abc1234")
        self.assertEqual(summary["contract_version"], "1.0.0")

    def test_consumes_quantized_payload_with_null_s_behavior(self):
        payload = _valid_risk_payload(s_behavior=None)
        summary = format_risk_summary(payload)
        self.assertIsNone(summary["s_behavior"])
        self.assertEqual(summary["producer"], "P2")
        self.assertEqual(summary["verdict"], "REVIEW")
        self.assertAlmostEqual(summary["mrs_score"], 42.5)

    def test_rejects_non_p2_producer(self):
        payload = _valid_risk_payload(producer="P3")
        with self.assertRaisesRegex(ValueError, "must be 'P2'"):
            format_risk_summary(payload)

    def test_rejects_non_mapping(self):
        with self.assertRaisesRegex(ValueError, "must be a mapping"):
            format_risk_summary("not a mapping")  # type: ignore[arg-type]

    def test_rejects_invalid_mock_status_and_verdict(self):
        with self.assertRaisesRegex(ValueError, "Invalid mock_status"):
            format_risk_summary(_valid_risk_payload(mock_status="UNKNOWN"))
        with self.assertRaisesRegex(ValueError, "Invalid verdict"):
            format_risk_summary(_valid_risk_payload(verdict="INVALID"))

    def test_rejects_non_finite_and_out_of_bounds_numbers(self):
        for field, invalid_val in [
            ("mrs_score", -1.0),
            ("mrs_score", 100.1),
            ("mrs_score", float("nan")),
            ("mrs_score", True),
            ("s_static", -0.01),
            ("s_static", 1.01),
            ("s_static", float("inf")),
            ("p_tamper", -0.1),
            ("p_tamper", 1.1),
            ("p_tamper", False),
            ("s_behavior", -0.5),
            ("s_behavior", 1.5),
            ("s_behavior", float("nan")),
        ]:
            with self.subTest(field=field, val=invalid_val):
                with self.assertRaises(ValueError):
                    format_risk_summary(_valid_risk_payload(**{field: invalid_val}))

    def test_no_highest_risk_layer_in_risk_results_expected(self):
        payload = _valid_risk_payload()
        self.assertNotIn("highest_risk_layer", payload)
        summary = format_risk_summary(payload)
        self.assertNotIn("highest_risk_layer", summary)


if __name__ == "__main__":
    unittest.main()
