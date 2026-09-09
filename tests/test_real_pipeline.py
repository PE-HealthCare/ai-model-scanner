"""Focused tests for the REAL pipeline path.

Covers the zero-trust intake, real P1 feature extraction against the features
contract, and the approved terminal state of the current pipeline:

    P1 VERIFIED-REAL -> P3 VERIFIED-REAL -> P2 BLOCKED (no risk_results.json)

No behavioral probing exists (Phase 5 / D3-D4 unresolved): a non-quantized
real scan MUST terminate at the P2 BLOCKED guard. That is the approved
architecture behavior, not a failure of these tests.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator

import scan_model
from src.common.utils import ROOT
from src.common.feature_names import FEATURE_NAMES
from src.p1_static_engine.analyzer import build_features, extract_layer_features
from src.p1_static_engine.intake import (
    ArtifactRejected,
    load_safetensors,
    write_safetensors,
)

CONTRACT_DIR = ROOT / "contracts"


def _write_raw_safetensors(path: Path, header: dict, blob: bytes) -> Path:
    """Write raw SafeTensors-shaped bytes for rejection tests (trusted fixture)."""
    header_bytes = json.dumps(header).encode("utf-8")
    with path.open("wb") as fh:
        fh.write(len(header_bytes).to_bytes(8, "little"))
        fh.write(header_bytes)
        fh.write(blob)
    return path


def _float_fixture(path: Path) -> Path:
    """Trusted locally generated float32 fixture (>= 16 elements per tensor)."""
    rng = np.random.default_rng(42)
    return write_safetensors(
        path,
        {
            "model.layer_b": rng.normal(0.0, 0.1, (32, 64)).astype(np.float32),
            "model.layer_a": rng.normal(0.0, 0.2, (16, 16)).astype(np.float32),
        },
    )


class TestZeroTrustIntake(unittest.TestCase):
    """E1-E3: the intake fails closed on unsupported or unsafe artifacts."""

    def test_rejects_non_float_dtype(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write_raw_safetensors(
                Path(td) / "int8.safetensors",
                {"weights": {"dtype": "I32", "shape": [2, 2], "data_offsets": [0, 16]}},
                b"\x00" * 16,
            )
            with self.assertRaises(ArtifactRejected):
                load_safetensors(path)

    def test_rejects_malformed_and_unsafe_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            tiny = td_path / "tiny.safetensors"
            tiny.write_bytes(b"\x00\x00\x00\x00")
            with self.assertRaises(ArtifactRejected):
                load_safetensors(tiny)

            lying_header = td_path / "lying.safetensors"
            lying_header.write_bytes((10**9).to_bytes(8, "little") + b"{}")
            with self.assertRaises(ArtifactRejected):
                load_safetensors(lying_header)

            bad_json = td_path / "bad_json.safetensors"
            header = b"{not json"
            bad_json.write_bytes(len(header).to_bytes(8, "little") + header)
            with self.assertRaises(ArtifactRejected):
                load_safetensors(bad_json)

            bad_offsets = td_path / "bad_offsets.safetensors"
            _write_raw_safetensors(
                bad_offsets,
                {"w": {"dtype": "F32", "shape": [4], "data_offsets": [0, 999]}},
                b"\x00" * 16,
            )
            with self.assertRaises(ArtifactRejected):
                load_safetensors(bad_offsets)

            with self.assertRaises(FileNotFoundError):
                load_safetensors(td_path / "missing.safetensors")

    def test_rejects_tensor_too_small_for_statistics(self):
        with self.assertRaisesRegex(ValueError, "too small for statistical analysis"):
            extract_layer_features(np.zeros(8, dtype=np.float32))
        with tempfile.TemporaryDirectory() as td:
            path = write_safetensors(
                Path(td) / "small.safetensors", {"tiny": np.zeros(4, dtype=np.float32)}
            )
            with self.assertRaisesRegex(ValueError, "too small for statistical analysis"):
                build_features(path, "TEST-GEN")


class TestRealFeatureExtraction(unittest.TestCase):
    """E4: real extraction succeeds and satisfies the features contract."""

    def test_real_feature_extraction_matches_contract(self):
        with tempfile.TemporaryDirectory() as td:
            model_path = _float_fixture(Path(td) / "clean.safetensors")
            features = build_features(model_path, "TEST-GEN")

        with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as fh:
            schema = json.load(fh)
        Draft202012Validator(schema).validate(features)

        self.assertEqual(features["producer"], "P1")
        self.assertEqual(features["mock_status"], "VERIFIED-REAL")
        self.assertFalse(features["is_quantized"])
        self.assertEqual(features["layer_count"], 2)
        self.assertEqual(
            [layer["layer_name"] for layer in features["static_features"]],
            ["model.layer_a", "model.layer_b"],  # deterministic sorted-name order
        )
        self.assertEqual(list(features["static_features"][0].keys())[1:], list(FEATURE_NAMES))


class TestRealPipelineTerminalState(unittest.TestCase):
    """E5-E7: P1 and P3 complete; P2 raises the approved BLOCKED; no risk artifact."""

    def test_pipeline_progresses_p1_p3_then_blocks_at_p2_without_risk_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            model_path = _float_fixture(td_path / "model.safetensors")
            out_dir = td_path / "outputs"

            original_output_dir = scan_model.OUTPUT_DIR
            scan_model.OUTPUT_DIR = out_dir
            try:
                with self.assertRaisesRegex(ValueError, "BLOCKED"):
                    scan_model.run_pipeline(model_path)
            finally:
                scan_model.OUTPUT_DIR = original_output_dir

            # E5: P1 artifact exists for this run, VERIFIED-REAL and contract-valid.
            features = json.loads((out_dir / "features.json").read_text(encoding="utf-8"))
            with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as fh:
                Draft202012Validator(json.load(fh)).validate(features)
            self.assertEqual(features["mock_status"], "VERIFIED-REAL")

            # E5: P3 artifact exists for this run, VERIFIED-REAL and contract-valid.
            ml_results = json.loads((out_dir / "ml_results.json").read_text(encoding="utf-8"))
            with (CONTRACT_DIR / "ml_results.schema.json").open(encoding="utf-8") as fh:
                Draft202012Validator(json.load(fh)).validate(ml_results)
            self.assertEqual(ml_results["mock_status"], "VERIFIED-REAL")
            self.assertEqual(ml_results["model_version"], "sigtensor-logreg-synthetic-v1")
            self.assertTrue(0.0 <= ml_results["p_tamper"] <= 1.0)

            # E7: approved terminal state — NO risk artifact for this run.
            self.assertFalse((out_dir / "risk_results.json").exists())


if __name__ == "__main__":
    unittest.main()
