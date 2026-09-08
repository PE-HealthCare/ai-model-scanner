import unittest
from src.p1_static_engine.analyzer import extract_features, TrustedModelContext
import torch

class TestExtractor(unittest.TestCase):
    def test_extract_features_blocked(self):
        class MockModel:
            def state_dict(self):
                return {"layer1": torch.zeros(10)}
        ctx = TrustedModelContext(MockModel(), "resnet18", "VISION", False)
        
        with self.assertRaisesRegex(NotImplementedError, "BLOCKED: .*semantics"):
            extract_features(ctx, "commit123")

    def test_quantized_ks_only(self):
        class MockModel:
            def state_dict(self):
                return {"layer1": torch.zeros(10)}
        ctx = TrustedModelContext(MockModel(), "resnet18", "VISION", True)
        
        with self.assertRaisesRegex(NotImplementedError, "BLOCKED: .*semantics"):
            extract_features(ctx, "commit123")
            
if __name__ == "__main__":
    unittest.main()
