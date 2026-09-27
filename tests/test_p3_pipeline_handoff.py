"""Tests that run_pipeline hands the validated P2 artifact to P3.

Proves the physical handoff: the validated ``risk_results.json`` file is
parsed by the orchestrator and the resulting mapping is passed into the
existing P3 consumer API.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scan_model
from src.p3_ml_dashboard.d6_layer import select_highest_risk_layer
from src.p3_ml_dashboard.report import (
    prepare_dashboard_results as _real_prepare_dashboard_results,
)


def _handoff_features(payload_commit: str) -> dict:
    def _layer(name: str, ks_stat: float) -> dict:
        return {
            "layer_name": name,
            "ks_stat": ks_stat,
            "entropy": 0.9,
            "pov_chi2": 1.0,
            "lsb_kl": 0.02,
            "mean": 0.0,
            "std": 0.2,
            "skewness": 0.0,
            "kurtosis": 3.0,
            "sparsity": 0.1,
            "outlier_pct": 0.5,
        }

    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": payload_commit,
        "input_domain": "VISION",
        "is_quantized": False,
        "layer_count": 3,
        "static_features": [
            _layer("handoff.layer.a", 0.25),
            _layer("handoff.layer.b", 0.30),
            _layer("handoff.layer.c", 0.20),
        ],
    }


def _handoff_ml(payload_commit: str) -> dict:
    return {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": payload_commit,
        "p_tamper": 0.42,
        "shap_attributions": {"ks_stat": 0.1},
        "model_version": "handoff-sentinel",
    }


class _FakeHandoffModule:
    @staticmethod
    def receive_trusted_model(context) -> None:
        return None


class _FakeAnalyzerModule:
    def __init__(self, run_assessment):
        self.run_assessment = run_assessment

def _quantized_handoff_features(payload_commit: str) -> dict:
    def _layer(name: str, ks_stat: float) -> dict:
        return {
            "layer_name": name,
            "ks_stat": ks_stat,
            # Locked D11 quantized contract: FP-only static fields must be absent/None.
            "entropy": None,
            "pov_chi2": None,
            "lsb_kl": None,
            "mean": None,
            "std": None,
            "skewness": None,
            "kurtosis": None,
            "sparsity": None,
            "outlier_pct": None,
        }

    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": payload_commit,
        "input_domain": "VISION",
        "is_quantized": True,
        "layer_count": 3,
        "static_features": [
            _layer("handoff.q.layer.a", 0.30),
            _layer("handoff.q.layer.b", 0.45),
            _layer("handoff.q.layer.c", 0.25),
        ],
    }


def _risk_payload(payload_commit: str, **overrides) -> dict:
    payload = {
        "producer": "P2",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": payload_commit,
        "mrs_score": 42.5,
        "verdict": "REVIEW",
        "s_static": 0.35,
        "p_tamper": 0.45,
        "s_behavior": 0.20,
    }
    payload.update(overrides)
    return payload


class _PipelineHandoffDriver:
    """Run scan_model.run_pipeline with persisted P1/P3/P2 artifacts in tmp."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.seen: dict[str, object] = {}
        self.prepare_calls = 0
        self.original_output_dir = scan_model.OUTPUT_DIR
        scan_model.OUTPUT_DIR = out_dir
        self.original_handoff = sys.modules.get("src.p2_behavioral_risk.handoff")
        self.original_analyzer = sys.modules.get("src.p2_behavioral_risk.analyzer")

    def restore(self) -> None:
        scan_model.OUTPUT_DIR = self.original_output_dir
        for name, module in (
            ("src.p2_behavioral_risk.handoff", self.original_handoff),
            ("src.p2_behavioral_risk.analyzer", self.original_analyzer),
        ):
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def run(
        self,
        *,
        features: dict,
        risk_payload: dict,
        ml_builder=None,
        prepare=None,
    ) -> dict:
        def fake_run_assessment(**kwargs):
            out = Path(str(kwargs["output_path"]))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(risk_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            return dict(risk_payload)

        def default_ml_builder(persisted_features, payload_commit):
            return _handoff_ml(payload_commit)

        def default_prepare(risk_results, ml_results, static_features=None):
            return _real_prepare_dashboard_results(
                risk_results, ml_results, static_features
            )

        ml_side_effect = ml_builder or default_ml_builder
        prepare_side_effect = prepare or default_prepare

        def counting_prepare(risk_results, ml_results, static_features=None):
            self.prepare_calls += 1
            return prepare_side_effect(
                risk_results, ml_results, static_features
            )

        with (
            patch.object(
                scan_model, "intake_model", return_value=object(), create=True
            ),
            patch.object(
                scan_model, "extract_features",
                return_value=copy.deepcopy(features), create=True,
            ),
            patch.object(scan_model, "build_ml_results", side_effect=ml_side_effect),
            patch.object(
                scan_model, "build_quantized_ml_results", side_effect=ml_side_effect
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
            patch(
                "src.p3_ml_dashboard.report.prepare_dashboard_results",
                side_effect=counting_prepare,
            ),
        ):
            return scan_model.run_pipeline("unused.safetensors")


class TestP2ToP3RuntimeHandoff(unittest.TestCase):
    def test_validated_risk_file_reaches_p3_consumer(self):
        seen: dict[str, object] = {}
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"
            orig_dir = scan_model.OUTPUT_DIR
            scan_model.OUTPUT_DIR = out_dir
            orig_h = sys.modules.get("src.p2_behavioral_risk.handoff")
            orig_a = sys.modules.get("src.p2_behavioral_risk.analyzer")
            try:
                persisted = copy.deepcopy(
                    _handoff_features(scan_model.get_generation_commit())
                )
                exp_commit = str(persisted["generation_commit"])
                risk_payload = {
                    "producer": "P2",
                    "mock_status": "VERIFIED-REAL",
                    "contract_version": "1.0",
                    "generation_commit": exp_commit,
                    "mrs_score": 42.5,
                    "verdict": "REVIEW",
                    "s_static": 0.35,
                    "p_tamper": 0.45,
                    "s_behavior": 0.20,
                }

                def fake_run_assessment(**kwargs):
                    out = Path(str(kwargs["output_path"]))
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(
                        json.dumps(risk_payload, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    return dict(risk_payload)

                def fake_fp(features, generation_commit):
                    return _handoff_ml(generation_commit)

                def capture_prepare(rr, mr, static_features=None):
                    seen["risk_results"] = rr
                    seen["ml_results"] = mr
                    seen["static"] = static_features
                    return {"sentinel": True}

                with (
                    patch.object(
                        scan_model, "intake_model", return_value=object(), create=True
                    ),
                    patch.object(
                        scan_model, "extract_features",
                        return_value=persisted, create=True,
                    ),
                    patch.object(scan_model, "build_ml_results", side_effect=fake_fp),
                    patch.dict(
                        sys.modules,
                        {
                            "src.p2_behavioral_risk.handoff": _FakeHandoffModule(),
                            "src.p2_behavioral_risk.analyzer": _FakeAnalyzerModule(
                                fake_run_assessment
                            ),
                        },
                    ),
                    patch(
                        "src.p3_ml_dashboard.report.prepare_dashboard_results",
                        side_effect=capture_prepare,
                    ),
                ):
                    outcome = scan_model.run_pipeline("unused.safetensors")

                on_disk = json.loads(
                    (out_dir / "risk_results.json").read_text(encoding="utf-8")
                )
                self.assertEqual(seen["risk_results"], on_disk)
                self.assertEqual(seen["risk_results"], risk_payload)
                self.assertEqual(
                    seen["ml_results"],
                    json.loads(
                        (out_dir / "ml_results.json").read_text(encoding="utf-8")
                    ),
                )
                feats = json.loads(
                    (out_dir / "features.json").read_text(encoding="utf-8")
                )
                self.assertEqual(seen["static"], feats["static_features"])
                self.assertEqual(outcome["dashboard_results"], {"sentinel": True})
                self.assertEqual(outcome["risk_results"], out_dir / "risk_results.json")
            finally:
                scan_model.OUTPUT_DIR = orig_dir
                for nm, mod in (
                    ("src.p2_behavioral_risk.handoff", orig_h),
                    ("src.p2_behavioral_risk.analyzer", orig_a),
                ):
                    if mod is None:
                        sys.modules.pop(nm, None)
                    else:
                        sys.modules[nm] = mod


    def test_quantized_handoff_allows_s_behavior_none(self):
        """Quantized handoff: persisted s_behavior=None reaches P3 intact."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"
            driver = _PipelineHandoffDriver(out_dir)
            try:
                features = _quantized_handoff_features(
                    scan_model.get_generation_commit()
                )
                risk_payload = _risk_payload(
                    str(features["generation_commit"]),
                    s_behavior=None,
                    mrs_score=55.0,
                    s_static=0.55,
                    p_tamper=0.45,
                )

                seen: dict[str, object] = {}

                def capture_prepare(risk_results, ml_results, static_features=None):
                    seen["risk_results"] = risk_results
                    return _real_prepare_dashboard_results(
                        risk_results, ml_results, static_features
                    )

                outcome = driver.run(
                    features=features,
                    risk_payload=risk_payload,
                    prepare=capture_prepare,
                )
                on_disk = json.loads(
                    (out_dir / "risk_results.json").read_text(encoding="utf-8")
                )
                self.assertIsNone(on_disk["s_behavior"])
                self.assertEqual(seen["risk_results"], on_disk)
                dashboard = outcome["dashboard_results"]
                self.assertIsInstance(dashboard, dict)
                self.assertIsNone(dashboard["risk_summary"]["s_behavior"])
            finally:
                driver.restore()

    def test_d6_selected_layer_reaches_dashboard_result(self):
        """D6 layer/evidence derived from validated P1 features reaches P3."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"
            driver = _PipelineHandoffDriver(out_dir)
            try:
                features = _handoff_features(scan_model.get_generation_commit())
                risk_payload = _risk_payload(str(features["generation_commit"]))

                outcome = driver.run(
                    features=features,
                    risk_payload=risk_payload,
                )
                dashboard = outcome["dashboard_results"]
                expected = select_highest_risk_layer(features["static_features"])
                self.assertEqual(
                    dashboard["highest_risk_layer"], expected["highest_risk_layer"]
                )
                self.assertEqual(
                    dashboard["highest_risk_evidence"], expected["evidence"]
                )
                self.assertIsInstance(dashboard["highest_risk_layer"], str)
                self.assertNotEqual(dashboard["highest_risk_layer"], "unavailable")
            finally:
                driver.restore()

    def test_blocked_invalid_risk_fails_closed_before_p3(self):
        """Invalid risk evidence blocks delivery and leaves no risk artifact."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"
            driver = _PipelineHandoffDriver(out_dir)
            try:
                features = _handoff_features(scan_model.get_generation_commit())
                bad_payload = _risk_payload(
                    str(features["generation_commit"]),
                    mrs_score=150.0,
                )

                with self.assertRaises(Exception):
                    driver.run(features=features, risk_payload=bad_payload)
                self.assertFalse((out_dir / "risk_results.json").exists())
                self.assertEqual(driver.prepare_calls, 0)
            finally:
                driver.restore()

    def test_repeated_identical_handoff_is_deterministic(self):
        """The same validated evidence produces byte-identical dashboard output."""
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"
            driver = _PipelineHandoffDriver(out_dir)
            try:
                features = _handoff_features(scan_model.get_generation_commit())
                risk_payload = _risk_payload(str(features["generation_commit"]))
                first = driver.run(
                    features=features,
                    risk_payload=risk_payload,
                )
                second = driver.run(
                    features=features,
                    risk_payload=risk_payload,
                )
                self.assertEqual(first, second)
            finally:
                driver.restore()



if __name__ == "__main__":
    unittest.main()
