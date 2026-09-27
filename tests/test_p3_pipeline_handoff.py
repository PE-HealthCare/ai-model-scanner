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


if __name__ == "__main__":
    unittest.main()
