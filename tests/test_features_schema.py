import json
import unittest

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from src.common.utils import ROOT
from src.p1_static_engine.analyzer import build_mock_features
from src.p1_static_engine.analyzer import TrustedModelContext, extract_features
import torch


class TestFeaturesSchemaLayerBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "contracts" / "features.schema.json").open(encoding="utf-8") as fh:
            cls.schema = json.load(fh)

    def test_three_layer_mock_is_schema_valid(self):
        features = build_mock_features("TEST")
        Draft202012Validator(self.schema).validate(features)
        self.assertEqual(features["layer_count"], 3)
        self.assertEqual(len(features["static_features"]), 3)

    def test_two_layer_features_are_schema_invalid(self):
        features = build_mock_features("TEST")
        features["layer_count"] = 2
        features["static_features"] = features["static_features"][:2]

        with self.assertRaises(ValidationError):
            Draft202012Validator(self.schema).validate(features)

    def test_b1_extension_is_schema_valid_without_changing_b0_mock_contract(self):
        class Model:
            def state_dict(self):
                return {
                    "l1": torch.tensor([1., 2., 3.]),
                    "l2": torch.tensor([2., 3., 4.]),
                    "l3": torch.tensor([3., 4., 5.]),
                }

        features = extract_features(
            TrustedModelContext(Model(), "resnet18", "VISION", False),
            "TEST", feature_set="b1",
        )
        Draft202012Validator(self.schema).validate(features)


if __name__ == "__main__":
    unittest.main()
