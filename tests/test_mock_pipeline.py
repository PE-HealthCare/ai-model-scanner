import unittest
import json
import os
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from src.common.utils import validate_artifact, ROOT
from src.p1_static_engine.analyzer import build_mock_features
from src.p2_behavioral_risk.prober import build_mock_risk_results
from src.p3_ml_dashboard.classifier import build_mock_ml_results
import scan_model

CONTRACT_DIR = ROOT / "contracts"
OUTPUT_DIR = ROOT / "data" / "outputs"

class TestContracts(unittest.TestCase):
    def setUp(self):
        with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as f:
            self.features_schema = json.load(f)
        with (CONTRACT_DIR / "ml_results.schema.json").open(encoding="utf-8") as f:
            self.ml_schema = json.load(f)
        with (CONTRACT_DIR / "risk_results.schema.json").open(encoding="utf-8") as f:
            self.risk_schema = json.load(f)

    def test_valid_existing_artifacts(self):
        """Test successful validation of existing committed mock artifacts."""
        validate_artifact(OUTPUT_DIR / "features.json", CONTRACT_DIR / "features.schema.json")
        validate_artifact(OUTPUT_DIR / "ml_results.json", CONTRACT_DIR / "ml_results.schema.json")
        validate_artifact(OUTPUT_DIR / "risk_results.json", CONTRACT_DIR / "risk_results.schema.json")
        self.assertTrue(True)

    def test_missing_required_field(self):
        """Test rejection of missing required field."""
        invalid_features = build_mock_features("TEST")
        del invalid_features["layer_count"]
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.features_schema).validate(invalid_features)

    def test_unexpected_field(self):
        """Test rejection of unexpected field."""
        invalid_features = build_mock_features("TEST")
        invalid_features["unexpected_field"] = "value"
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.features_schema).validate(invalid_features)

    def test_wrong_field_type(self):
        """Test rejection of wrong field type."""
        invalid_features = build_mock_features("TEST")
        invalid_features["layer_count"] = "two"
        with self.assertRaises(ValidationError):
            Draft202012Validator(self.features_schema).validate(invalid_features)

    def test_malformed_json(self):
        """Test rejection of malformed JSON artifact."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            tmp.write("{ invalid json")
            tmp_name = tmp.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                validate_artifact(Path(tmp_name), CONTRACT_DIR / "features.schema.json")
        finally:
            os.remove(tmp_name)

    def test_schema_mismatch(self):
        """Test for an artifact/schema mismatch using the existing validation mechanism."""
        features = build_mock_features("TEST")
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            json.dump(features, tmp)
            tmp_name = tmp.name
        try:
            with self.assertRaises(ValidationError):
                validate_artifact(Path(tmp_name), CONTRACT_DIR / "ml_results.schema.json")
        finally:
            os.remove(tmp_name)

    def test_wrong_feature_ordering(self):
        """Test that wrong feature ordering is rejected by the test suite where contractually represented."""
        expected_order = [
            "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean",
            "std", "skewness", "kurtosis", "sparsity", "outlier_pct"
        ]

        # Contractual representation in ML schema enum
        enum_order = self.ml_schema["properties"]["shap_attributions"]["propertyNames"]["enum"]
        self.assertEqual(enum_order, expected_order, "Schema enum ordering does not match Master Graph")

        # Contractual representation in Features schema required fields
        features_required_order = self.features_schema["properties"]["static_features"]["items"]["required"][1:]
        self.assertEqual(features_required_order, expected_order, "Schema required properties ordering does not match Master Graph")

        # Implementation order preservation (this test guards against silent ordering changes)
        features = build_mock_features("TEST")
        actual_feature_keys = list(features["static_features"][0].keys())[1:]
        self.assertEqual(actual_feature_keys, expected_order, "Producer output ordering does not match Master Graph")

        ml_results = build_mock_ml_results(features, "TEST")
        actual_shap_keys = list(ml_results["shap_attributions"].keys())
        self.assertEqual(actual_shap_keys, expected_order, "Producer output shap ordering does not match Master Graph")


class TestMockRealLifecycle(unittest.TestCase):
    def test_mock_status_enforced(self):
        """Verify existing mock artifacts remain MOCK and are rejected if changed."""
        features = build_mock_features("TEST")
        self.assertEqual(features["mock_status"], "MOCK")

        # P3 mock consumer rejects non-MOCK P1 artifact
        features["mock_status"] = "VERIFIED-REAL"
        with self.assertRaisesRegex(ValueError, "P1 MOCK"):
            build_mock_ml_results(features, "TEST")

    def test_p2_rejects_non_mock_p3(self):
        """Verify P2 mock consumer rejects a non-MOCK P3 artifact."""
        features = build_mock_features("TEST")
        ml_results = build_mock_ml_results(features, "TEST")
        ml_results["mock_status"] = "VERIFIED-REAL"
        with self.assertRaisesRegex(ValueError, "P3 MOCK"):
            build_mock_risk_results(ml_results, "TEST")





class TestArtifactFailureModes(unittest.TestCase):
    def test_missing_artifacts(self):
        """Test missing artifact files."""
        with self.assertRaises(FileNotFoundError):
            validate_artifact(Path("non_existent_features.json"), CONTRACT_DIR / "features.schema.json")
        with self.assertRaises(FileNotFoundError):
            validate_artifact(Path("non_existent_ml_results.json"), CONTRACT_DIR / "ml_results.schema.json")
        with self.assertRaises(FileNotFoundError):
            validate_artifact(Path("non_existent_risk_results.json"), CONTRACT_DIR / "risk_results.schema.json")

    def test_corrupted_artifact(self):
        """Test corrupted JSON artifact."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
            tmp.write('{"producer": "P1", "mock_status"')
            tmp_name = tmp.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                validate_artifact(Path(tmp_name), CONTRACT_DIR / "features.schema.json")
        finally:
            os.remove(tmp_name)

    def test_stale_artifact_status(self):
        """Test that an explicitly STALE artifact is rejected."""
        features = build_mock_features("TEST")
        features["mock_status"] = "STALE"
        with self.assertRaisesRegex(ValueError, "P1 MOCK"):
            build_mock_ml_results(features, "TEST")

    def test_stale_provenance_d8(self):
        """Test that a stale generation_commit mismatch is rejected."""
        features = build_mock_features("TEST_COMMIT_1")
        with self.assertRaisesRegex(ValueError, "stale P1 artifact generation"):
            build_mock_ml_results(features, "TEST_COMMIT_2")

        ml_results = build_mock_ml_results(features, "TEST_COMMIT_1")
        with self.assertRaisesRegex(ValueError, "stale P3 artifact generation"):
            build_mock_risk_results(ml_results, "TEST_COMMIT_2")


class TestPipelineFailurePropagation(unittest.TestCase):
    def test_p1_failure_prevents_downstream(self):
        """Test P1 failure prevents P3/P2 execution."""
        original_build = scan_model.build_mock_features
        def failing_build(*args):
            raise RuntimeError("P1 Failure")

        scan_model.build_mock_features = failing_build
        try:
            with self.assertRaisesRegex(RuntimeError, "P1 Failure"):
                scan_model.run_mock_pipeline()
        finally:
            scan_model.build_mock_features = original_build

    def test_p3_failure_prevents_downstream(self):
        """Test P3 failure prevents downstream P2 execution."""
        original_build = scan_model.build_mock_ml_results
        def failing_build(*args):
            raise RuntimeError("P3 Failure")

        scan_model.build_mock_ml_results = failing_build
        try:
            with self.assertRaisesRegex(RuntimeError, "P3 Failure"):
                scan_model.run_mock_pipeline()
        finally:
            scan_model.build_mock_ml_results = original_build

    def test_p2_failure_stops_pipeline(self):
        """Test P2 failure does not produce fabricated successful result."""
        original_build = scan_model.build_mock_risk_results
        def failing_build(*args):
            raise RuntimeError("P2 Failure")

        scan_model.build_mock_risk_results = failing_build
        try:
            with self.assertRaisesRegex(RuntimeError, "P2 Failure"):
                scan_model.run_mock_pipeline()
        finally:
            scan_model.build_mock_risk_results = original_build

    def test_missing_upstream_output_halts(self):
        """Test malformed/missing upstream output stops downstream processing."""
        # Ensure output files don't exist from previous runs
        if scan_model.OUTPUT_DIR.exists():
            for f in scan_model.OUTPUT_DIR.glob("*.json"):
                f.unlink()

        original_write = scan_model._write_json
        def failing_write(path, payload):
            pass # pretend we didn't write it, so validation fails

        scan_model._write_json = failing_write
        try:
            with self.assertRaises(FileNotFoundError):
                scan_model.run_mock_pipeline()
        finally:
            scan_model._write_json = original_write


class TestOrchestrationOwnership(unittest.TestCase):
    def test_scan_model_orchestration_only(self):
        """
        Statically verify that scan_model.py remains orchestration only and does
        not duplicate subsystem logic.
        """
        with open(ROOT / "scan_model.py", "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("build_mock_features", code)
        self.assertIn("build_mock_ml_results", code)
        self.assertIn("build_mock_risk_results", code)

        # scan_model.py should not contain math operations for risk or final verdict assignments
        self.assertNotIn("verdict =", code)
        self.assertNotIn("mrs_score =", code)


class TestSecurity(unittest.TestCase):
    def test_security_constraints(self):
        """
        Verify the Phase 1 implementation does not:
        - execute uploaded model code (exec/eval)
        - load unrestricted pickle
        - import uploader-controlled modules
        - perform arbitrary network access
        """
        forbidden_terms = ["eval(", "exec(", "pickle.load", "importlib.import_module", "requests.get", "urllib"]

        python_files = [
            ROOT / "scan_model.py",
            ROOT / "src" / "common" / "utils.py",
            ROOT / "src" / "p1_static_engine" / "analyzer.py",
            ROOT / "src" / "p2_behavioral_risk" / "prober.py",
            ROOT / "src" / "p3_ml_dashboard" / "classifier.py",
        ]

        for py_file in python_files:
            if not py_file.exists():
                continue
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
            for term in forbidden_terms:
                self.assertNotIn(term, content, f"Forbidden term {term} found in {py_file}")

if __name__ == "__main__":
    unittest.main()
