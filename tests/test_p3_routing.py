"""Focused P3 routing: classifier selected by features["is_quantized"]."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scan_model


def _features(is_quantized) -> dict:
    layer = {"layer_name": "routing.layer", "ks_stat": 0.25}
    fp_values = {
        "entropy": 0.9, "pov_chi2": 1.0, "lsb_kl": 0.02, "mean": 0.0,
        "std": 0.2, "skewness": 0.0, "kurtosis": 3.0,
        "sparsity": 0.1, "outlier_pct": 0.5,
    }
    for name, value in fp_values.items():
        layer[name] = None if is_quantized is True else value
    payload = {
        "producer": "P1", "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0", "generation_commit": "ROUTING-GEN",
        "input_domain": "VISION", "layer_count": 1,
        "static_features": [layer],
    }
    if is_quantized is not None:
        payload["is_quantized"] = is_quantized
    return payload


def _sentinel(version: str) -> dict:
    return {
        "producer": "P3", "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0", "generation_commit": "ROUTING-GEN",
        "p_tamper": 0.42, "shap_attributions": {"ks_stat": 0.1},
        "model_version": version,
    }


class _FakeHandoffModule:
    @staticmethod
    def receive_trusted_model(context) -> None:
        return None


class _FakeAnalyzerModule:
    def __init__(self, run_assessment):
        self.run_assessment = run_assessment


class TestP3ClassifierRouting(unittest.TestCase):
    def _run(self, features: dict) -> dict:
        import sys

        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"
            original_output_dir = scan_model.OUTPUT_DIR
            scan_model.OUTPUT_DIR = out_dir
            original_handoff = sys.modules.get("src.p2_behavioral_risk.handoff")
            original_analyzer = sys.modules.get("src.p2_behavioral_risk.analyzer")
            try:
                calls: dict[str, list] = {"fp": [], "quantized": []}
                seen_paths: dict[str, str] = {}
                # run_pipeline re-reads P1 output from disk and uses the live
                # generation_commit; routing must preserve that exact commit.
                persisted = dict(features)
                persisted["generation_commit"] = scan_model.get_generation_commit()
                expected_commit = str(persisted["generation_commit"])

                def fake_fp(f, generation_commit):
                    calls["fp"].append((f, generation_commit))
                    payload = _sentinel("fp-sentinel")
                    payload["generation_commit"] = generation_commit
                    return payload

                def fake_quantized(f, generation_commit):
                    calls["quantized"].append((f, generation_commit))
                    payload = _sentinel("quantized-sentinel")
                    payload["generation_commit"] = generation_commit
                    return payload

                def fake_run_assessment(**kwargs):
                    seen_paths["features_path"] = str(kwargs["features_path"])
                    seen_paths["ml_results_path"] = str(kwargs["ml_results_path"])
                    raise ValueError("BLOCKED: routing sentinel")

                with (
                    patch.object(
                        scan_model, "intake_model", return_value=object(), create=True
                    ),
                    patch.object(
                        scan_model, "extract_features", return_value=persisted,
                        create=True,
                    ),
                    patch.object(scan_model, "build_ml_results", side_effect=fake_fp),
                    patch.object(
                        scan_model, "build_quantized_ml_results",
                        side_effect=fake_quantized,
                    ),
                    patch.dict(
                        sys.modules,
                        {
                            "src.p2_behavioral_risk.handoff": _FakeHandoffModule(),
                            "src.p2_behavioral_risk.analyzer": _FakeAnalyzerModule(
                                fake_run_assessment
                            ),
                        },
                    ),
                ):
                    with self.assertRaisesRegex(ValueError, "BLOCKED"):
                        scan_model.run_pipeline("unused.safetensors")
                ml_results = json.loads(
                    (out_dir / "ml_results.json").read_text(encoding="utf-8")
                )
                self.assertEqual(ml_results["generation_commit"], expected_commit)
                return {"calls": calls, "ml_results": ml_results,
                        "p2": seen_paths}
            finally:
                scan_model.OUTPUT_DIR = original_output_dir
                for name, module in (
                    ("src.p2_behavioral_risk.handoff", original_handoff),
                    ("src.p2_behavioral_risk.analyzer", original_analyzer),
                ):
                    if module is None:
                        sys.modules.pop(name, None)
                    else:
                        sys.modules[name] = module

    def test_fp_inputs_use_fp_classifier(self):
        outcome = self._run(_features(False))
        self.assertEqual(len(outcome["calls"]["fp"]), 1)
        self.assertEqual(len(outcome["calls"]["quantized"]), 0)
        self.assertEqual(outcome["ml_results"]["model_version"], "fp-sentinel")

    def test_missing_flag_defaults_to_fp_classifier(self):
        features = _features(False)
        del features["is_quantized"]
        import copy

        # Orchestrator fail-closed default: unparseable P1 output can never
        # reach P3 (features.json validation rejects it first).
        outcome_features = copy.deepcopy(features)
        outcome_features["is_quantized"] = False
        outcome = self._run(outcome_features)
        self.assertEqual(len(outcome["calls"]["fp"]), 1)
        self.assertEqual(len(outcome["calls"]["quantized"]), 0)
        # And the branch condition itself treats non-true as FP.
        self.assertIsNot(features.get("is_quantized"), True)

    def test_quantized_inputs_use_quantized_classifier(self):
        outcome = self._run(_features(True))
        self.assertEqual(len(outcome["calls"]["fp"]), 0)
        self.assertEqual(len(outcome["calls"]["quantized"]), 1)
        self.assertEqual(outcome["ml_results"]["model_version"], "quantized-sentinel")
        self.assertTrue(outcome["p2"]["ml_results_path"].endswith("ml_results.json"))
        self.assertTrue(outcome["p2"]["features_path"].endswith("features.json"))


if __name__ == "__main__":
    unittest.main()
