import json
import unittest

from jsonschema import Draft202012Validator

from src.common.utils import ROOT
from src.p1_static_engine.analyzer import build_mock_features


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

        with self.assertRaises(Exception):
            Draft202012Validator(self.schema).validate(features)


if __name__ == "__main__":
    unittest.main()
