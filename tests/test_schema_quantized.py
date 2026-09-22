import unittest
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

CONTRACT_DIR = Path("contracts")

class TestSchemaQuantized(unittest.TestCase):
    def setUp(self):
        with (CONTRACT_DIR / "features.schema.json").open(encoding="utf-8") as f:
            self.schema = json.load(f)
        self.validator = Draft202012Validator(self.schema)

        self.valid_base = {
            "producer": "P1",
            "mock_status": "VERIFIED-REAL",
            "contract_version": "1.0",
            "generation_commit": "abcdef1",
            "input_domain": "VISION",
            "is_quantized": True,
            "layer_count": 1,
            "static_features": [
                {
                    "layer_name": "l1",
                    "entropy": None,
                    "pov_chi2": None,
                    "lsb_kl": None,
                    "mean": None,
                    "std": None,
                    "skewness": None,
                    "kurtosis": None,
                    "sparsity": None,
                    "outlier_pct": None,
                    "ks_stat": 0.5
                }
            ]
        }

    def test_valid_quantized(self):
        self.validator.validate(self.valid_base)

    def test_rejects_nan_in_ks_stat(self):
        data = json.loads(json.dumps(self.valid_base))
        # JSON standard doesn't have NaN. If it's serialized as string "NaN", schema must reject it.
        # If it's serialized as a native NaN literal, standard parsers fail anyway.
        data["static_features"][0]["ks_stat"] = "NaN"
        with self.assertRaises(ValidationError):
            self.validator.validate(data)

    def test_rejects_fabricated_fp_field(self):
        data = json.loads(json.dumps(self.valid_base))
        data["static_features"][0]["entropy"] = 0.5
        with self.assertRaises(ValidationError):
            self.validator.validate(data)

    def test_rejects_missing_ks_stat(self):
        data = json.loads(json.dumps(self.valid_base))
        del data["static_features"][0]["ks_stat"]
        with self.assertRaises(ValidationError):
            self.validator.validate(data)

    def test_rejects_non_finite_ks_stat(self):
        data = json.loads(json.dumps(self.valid_base))
        data["static_features"][0]["ks_stat"] = float("inf")
        with self.assertRaises(ValidationError):
            self.validator.validate(data)

if __name__ == "__main__":
    unittest.main()
