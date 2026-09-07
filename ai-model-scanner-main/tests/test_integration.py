# tests/test_integration.py
import pytest
import json
import os
import tempfile
from src.p2_behavioral_risk.analyzer import run_assessment
from src.p2_behavioral_risk.adapters import load_features_json

def test_malformed_features_json():
    """§6: Malformed model → STOP, no fabricated report."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"wrong_key": "value"}, f)
        f.flush()
        with pytest.raises(KeyError):
            load_features_json(f.name)
    os.unlink(f.name)

def test_missing_ml_results():
    """§6: Missing artifact → STOP."""
    with pytest.raises(FileNotFoundError):
        run_assessment(
            features_path="data/fixtures/fake_features_vision.json",
            ml_results_path="data/fixtures/nonexistent.json"
        )

def test_malformed_ml_results():
    """§6: Malformed ml_results.json → STOP."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"wrong_key": "value"}, f)
        f.flush()
        with pytest.raises(KeyError):
            from src.p2_behavioral_risk.adapters import load_ml_results_json
            load_ml_results_json(f.name)
    os.unlink(f.name)

# Add similar tests for: P1 intake failure, P1 static failure, P3 classifier failure,
# P2 failure, stale artifact, mock artifact, malformed risk_results.json