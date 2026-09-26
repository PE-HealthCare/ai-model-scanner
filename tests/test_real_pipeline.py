"""Integration coverage for the REAL pipeline path.

Direct intake and P1 extraction behaviors are covered by
tests/test_intake.py and tests/test_extractor.py respectively. This module
keeps only the end-to-end responsibility: a REAL ResNet18 SafeTensors
artifact progresses through the current production pipeline

    P1 intake_model() -> P1 extract_features() -> P3 build_ml_results()
    -> P2 run_assessment()

via the scan_model.run_pipeline() entry point.

P1 and P3 must complete with schema-valid VERIFIED-REAL artifacts sharing a
single generation_commit. The expected terminal behavior is the current P2
guard: run_pipeline() raises ValueError("BLOCKED") and no risk_results.json
remains.
"""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

import scan_model
from src.common.utils import ROOT

CONTRACT_DIR = ROOT / "contracts"
MODEL_PATH = ROOT / "data" / "models" / "resnet18_pretrained.safetensors"


def _load_and_validate(out_dir: Path, name: str, schema_name: str) -> dict:
    """Load a pipeline artifact from out_dir and validate it against its contract."""
    artifact = out_dir / name
    assert artifact.exists(), f"{name} was not produced in {out_dir}"
    with artifact.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    with (CONTRACT_DIR / schema_name).open(encoding="utf-8") as fh:
        Draft202012Validator(json.load(fh)).validate(payload)
    return payload


class TestRealPipeline(unittest.TestCase):
    """End-to-end: REAL ResNet18 through P1 -> P3 to the P2 terminal state."""

    def test_real_resnet18_progresses_p1_p3_then_reaches_p2_terminal_behavior(self):
        self.assertTrue(MODEL_PATH.exists(), f"real fixture missing: {MODEL_PATH}")
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "outputs"

            original_output_dir = scan_model.OUTPUT_DIR
            scan_model.OUTPUT_DIR = out_dir
            try:
                with self.assertRaisesRegex(ValueError, "BLOCKED"):
                    scan_model.run_pipeline(MODEL_PATH, declared_architecture="resnet18")
            finally:
                scan_model.OUTPUT_DIR = original_output_dir

            # P1 artifact: produced, schema-valid, VERIFIED-REAL.
            features = _load_and_validate(out_dir, "features.json", "features.schema.json")
            self.assertEqual(features["producer"], "P1")
            self.assertEqual(features["mock_status"], "VERIFIED-REAL")

            # P3 artifact: produced, schema-valid, VERIFIED-REAL.
            ml_results = _load_and_validate(out_dir, "ml_results.json", "ml_results.schema.json")
            self.assertEqual(ml_results["producer"], "P3")
            self.assertEqual(ml_results["mock_status"], "VERIFIED-REAL")
            self.assertEqual(ml_results["model_version"], "lightgbm-phase4-final")
            self.assertTrue(
                math.isfinite(ml_results["p_tamper"])
                and 0.0 <= ml_results["p_tamper"] <= 1.0
            )

            # No hardcoded generation_commit: P1 and P3 must agree on the
            # current generation identity.
            self.assertTrue(features["generation_commit"])
            self.assertEqual(ml_results["generation_commit"], features["generation_commit"])

            # P2 terminal behavior: the current P2 guard blocks, so no
            # risk_results.json may remain.
            self.assertFalse((out_dir / "risk_results.json").exists())


if __name__ == "__main__":
    unittest.main()
