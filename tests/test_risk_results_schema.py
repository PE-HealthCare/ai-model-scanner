import json
import os
import tempfile
import pytest
from src.p2_behavioral_risk.output_writer import write_risk_results

# Helper to construct a minimal valid risk_results dict
def _valid_data(extra: dict = None):
    base = {
        "producer": "P2",
        "mock_status": "MOCK",
        "contract_version": "1.0",
        "generation_commit": "abc123",
        "mrs_score": 42.0,
        "verdict": "PASS",
        "s_static": 0.5,
        "p_tamper": 0.3,
        "s_behavior": 0.2,
    }
    if extra:
        base.update(extra)
    return base

def _temp_path():
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    os.close(fd)
    return path

def test_write_risk_results_valid():
    data = _valid_data()
    path = _temp_path()
    try:
        write_risk_results(data, path)
        with open(path) as f:
            out = json.load(f)
        assert out == data
    finally:
        os.unlink(path)

def test_write_risk_results_missing_required_field():
    data = _valid_data()
    data.pop("producer")  # remove a required field
    path = _temp_path()
    try:
        with pytest.raises(ValueError) as exc:
            write_risk_results(data, path)
        assert "missing required fields" in str(exc.value)
    finally:
        os.unlink(path)

def test_write_risk_results_extra_field_rejected():
    data = _valid_data({"unexpected": 123})  # extra field not allowed by schema
    path = _temp_path()
    try:
        with pytest.raises(ValueError) as exc:
            write_risk_results(data, path)
        # Expect implementation to reject extra fields per schema
        assert "unexpected" in str(exc.value)
    finally:
        os.unlink(path)

def test_write_risk_results_non_finite_numeric_rejected():
    data = _valid_data({"mrs_score": float('nan')})
    path = _temp_path()
    try:
        with pytest.raises(ValueError) as exc:
            write_risk_results(data, path)
        assert "Non-finite" in str(exc.value)
    finally:
        os.unlink(path)
