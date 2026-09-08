import unittest
import numpy as np
import torch
import math
from src.p1_static_engine.analyzer import extract_features, TrustedModelContext

class MockModel:
    def __init__(self, tensors):
        self.tensors = tensors
    def state_dict(self):
        return self.tensors

class TestExtractor(unittest.TestCase):
    def test_fp32_features(self):
        # Need 3 layers minimum for KS pooled
        t1 = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0], dtype=torch.float32)
        t2 = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0], dtype=torch.float32)
        t3 = torch.tensor([10.0, 100.0, -50.0, 0.0, 0.0], dtype=torch.float32)
        
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        res = extract_features(ctx, "commit123")
        
        self.assertEqual(res["layer_count"], 3)
        self.assertEqual(res["mock_status"], "VERIFIED-REAL")
        
        l3_feats = res["static_features"][2]
        self.assertEqual(l3_feats["layer_name"], "l3")
        
        # Exact ordering
        expected_keys = ["layer_name", "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean", "std", "skewness", "kurtosis", "sparsity", "outlier_pct"]
        self.assertEqual(list(l3_feats.keys()), expected_keys)
        
        # Sparsity of l3
        self.assertAlmostEqual(l3_feats["sparsity"], 2.0 / 5.0)
        self.assertAlmostEqual(l3_feats["mean"], 12.0)
        self.assertTrue(0 <= l3_feats["outlier_pct"] <= 100)
        self.assertTrue(l3_feats["entropy"] > 0)
        self.assertTrue(l3_feats["ks_stat"] > 0)

    def test_fp16_features(self):
        t1 = torch.tensor([1.0, 2.0, 3.0], dtype=torch.float16)
        t2 = torch.tensor([2.0, 3.0, 4.0], dtype=torch.float16)
        t3 = torch.tensor([10.0, 100.0, -50.0], dtype=torch.float16)
        
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        res = extract_features(ctx, "commit123")
        self.assertIsNotNone(res["static_features"][0]["entropy"])
        
    def test_quantized_features(self):
        t1 = torch.tensor([1, 2, 3], dtype=torch.int8)
        t2 = torch.tensor([2, 3, 4], dtype=torch.int8)
        t3 = torch.tensor([10, 100, -50], dtype=torch.int8)
        
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", True)
        res = extract_features(ctx, "commit123")
        
        l1 = res["static_features"][0]
        self.assertTrue(math.isnan(l1["entropy"]))
        self.assertTrue(math.isnan(l1["mean"]))
        self.assertFalse(math.isnan(l1["ks_stat"]))

    def test_nan_rejection(self):
        t1 = torch.tensor([1.0, float('nan'), 3.0])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        t3 = torch.tensor([10.0, 100.0, -50.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "NaN or Inf"):
            extract_features(ctx, "commit123")
            
    def test_inf_rejection(self):
        t1 = torch.tensor([1.0, float('inf'), 3.0])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        t3 = torch.tensor([10.0, 100.0, -50.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "NaN or Inf"):
            extract_features(ctx, "commit123")
            
    def test_empty_tensor(self):
        t1 = torch.tensor([])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        t3 = torch.tensor([10.0, 100.0, -50.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "empty tensor"):
            extract_features(ctx, "commit123")
            
    def test_insufficient_layers(self):
        t1 = torch.tensor([1.0, 2.0, 3.0])
        t2 = torch.tensor([2.0, 3.0, 4.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2}), "resnet18", "VISION", False)
        with self.assertRaisesRegex(ValueError, "insufficient-baseline condition"):
            extract_features(ctx, "commit123")
            
    def test_constant_tensor(self):
        t1 = torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0])
        t2 = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0])
        t3 = torch.tensor([10.0, 100.0, -50.0, 0.0, 0.0])
        ctx = TrustedModelContext(MockModel({"l1": t1, "l2": t2, "l3": t3}), "resnet18", "VISION", False)
        res = extract_features(ctx, "commit123")
        
        l1 = res["static_features"][0]
        self.assertEqual(l1["std"], 0.0)
        self.assertTrue(math.isnan(l1["skewness"]))
        self.assertTrue(math.isnan(l1["kurtosis"]))
        self.assertEqual(l1["sparsity"], 0.0)
        
if __name__ == "__main__":
    unittest.main()
