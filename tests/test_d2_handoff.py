import unittest
from unittest.mock import patch

from src.p1_static_engine.analyzer import TrustedModelContext
import scan_model


class TestD2Handoff(unittest.TestCase):
    def test_same_context_object_reaches_p2(self):
        model = object()
        context = TrustedModelContext(model=model, architecture="resnet18", input_domain="VISION", is_quantized=False)
        received = scan_model.handoff_trusted_model(context)
        self.assertIs(received, context)
        self.assertIs(received.model, model)
        self.assertEqual(received.input_domain, "VISION")
        self.assertFalse(received.is_quantized)

    def test_quantization_metadata_survives_handoff(self):
        context = TrustedModelContext(model=object(), architecture="resnet18", input_domain="VISION", is_quantized=True)
        received = scan_model.handoff_trusted_model(context)
        self.assertIs(received, context)
        self.assertTrue(received.is_quantized)
        self.assertEqual(received.architecture, "resnet18")

    def test_failed_intake_prevents_p2_handoff(self):
        with patch.object(scan_model, "intake_model", side_effect=ValueError("intake failed")):
            with patch.object(scan_model, "handoff_trusted_model") as handoff:
                with self.assertRaises(ValueError):
                    scan_model.run_real_intake_handoff("missing.safetensors", "resnet18")
                handoff.assert_not_called()


if __name__ == "__main__":
    unittest.main()
