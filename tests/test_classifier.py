import unittest
from src.p3_ml_dashboard.classifier import build_ml_results, FEATURE_NAMES

class TestClassifier(unittest.TestCase):
    def test_prototype(self):
        features = {
            "producer": "P1",
            "mock_status": "VERIFIED-REAL",
            "contract_version": "1.0",
            "generation_commit": "TEST_COMMIT",
            "static_features": [
                {
                    "layer_name": "layer1",
                    "entropy": 0.5, "pov_chi2": 1.0, "lsb_kl": 0.0, "ks_stat": 0.1,
                    "mean": 0.0, "std": 1.0, "skewness": 0.0, "kurtosis": 3.0,
                    "sparsity": 0.1, "outlier_pct": 0.5
                }
            ]
        }
        
        res = build_ml_results(features, "TEST_COMMIT")
        self.assertEqual(res["producer"], "P3")
        self.assertEqual(res["mock_status"], "VERIFIED-REAL")
        self.assertTrue(0 <= res["p_tamper"] <= 1.0)
        self.assertEqual(len(res["shap_attributions"]), 10)
        
        # Verify ordering is preserved
        self.assertEqual(list(res["shap_attributions"].keys()), FEATURE_NAMES)

if __name__ == "__main__":
    unittest.main()
