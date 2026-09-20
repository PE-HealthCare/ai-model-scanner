# tests/test_p2_adversarial.py
import sys
import os
import json
import tempfile
import pytest
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.p2_behavioral_risk.analyzer import run_assessment
from src.p2_behavioral_risk.risk_aggregator import mad_zscore, compute_s_static_and_layer
from src.p2_behavioral_risk.adapters import load_features_json, load_ml_results_json

# ============================================================
# Helper to create temporary JSON files and clean up
# ============================================================
def create_temp_json(data):
    """Create a temporary JSON file, return path, and ensure file is closed."""
    fd, path = tempfile.mkstemp(suffix='.json', text=True)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    return path

# ============================================================
# 1. D7 Edge Cases (mad_zscore)
# ============================================================
def test_mad_zscore_normal():
    # Baseline [1,2,3,4,5] -> median=3, MAD=1, Z=(5-3)/(1.4826*1)=1.34898
    result = mad_zscore(5.0, [1, 2, 3, 4, 5])
    assert result == pytest.approx(1.3489815189531904)

def test_mad_zscore_zero_mad_equal():
    assert mad_zscore(3.0, [3, 3, 3]) == 0.0

def test_mad_zscore_zero_mad_deviate():
    with pytest.raises(RuntimeError, match="DEGENERATE_DEVIATION"):
        mad_zscore(4.0, [3, 3, 3])

def test_mad_zscore_insufficient_layers():
    with pytest.raises(RuntimeError, match="Insufficient comparable layers"):
        mad_zscore(2.0, [1, 2])

def test_mad_zscore_nan_baseline():
    with pytest.raises(ValueError, match="NaN or Inf"):
        mad_zscore(1.0, [1, float('nan'), 3])

def test_mad_zscore_nan_target():
    with pytest.raises(ValueError, match="NaN or Inf"):
        mad_zscore(float('nan'), [1, 2, 3])

# ============================================================
# 2. D5/D6 – compute_s_static_and_layer (now with 3 layers to pass D7)
# ============================================================
def test_s_static_range():
    # Use 3 layers to satisfy D7's >2 layers requirement
    layers = [
        {"layer_name": "a", "entropy": 1.0, "chi_square": 0.5, "kl_div": 0.1, "ks_stat": 0.2},
        {"layer_name": "b", "entropy": 2.0, "chi_square": 0.8, "kl_div": 0.3, "ks_stat": 0.4},
        {"layer_name": "c", "entropy": 1.5, "chi_square": 0.6, "kl_div": 0.2, "ks_stat": 0.3},
    ]
    s, layer = compute_s_static_and_layer(layers)
    assert 0.0 <= s <= 1.0
    assert layer in ["a", "b", "c"]

# ============================================================
# 3. Upstream Failure Scenarios (must STOP, no fabricated output)
# ============================================================
def test_malformed_features_json():
    path = create_temp_json({"wrong": "data"})
    try:
        with pytest.raises(KeyError):
            load_features_json(path)
    finally:
        os.unlink(path)

def test_missing_p_tamper():
    path = create_temp_json({
        "producer": "P3",
        "mock_status": "MOCK",
        "contract_version": "1.0",
        "generation_commit": "abc",
        "shap_attributions": {},
        "model_version": "v1"
    })
    try:
        with pytest.raises(KeyError, match="p_tamper"):
            load_ml_results_json(path)
    finally:
        os.unlink(path)

def test_stale_ml_artifact():
    # Create valid minimal features.json with all required fields (including provenance)
    features_data = {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "abc123",
        "input_domain": "VISION",
        "is_quantized": False,
        "layer_count": 1,
        "static_features": [
            {
                "layer_name": "a",
                "entropy": 1.0,
                "pov_chi2": 0.5,
                "lsb_kl": 0.1,
                "ks_stat": 0.2,
                "mean": 0.0,
                "std": 1.0,
                "skewness": 0.0,
                "kurtosis": 3.0,
                "sparsity": 0.0,
                "outlier_pct": 0.0
            }
        ]
    }
    ml_data = {
        "producer": "P3",
        "mock_status": "STALE",
        "contract_version": "1.0",
        "generation_commit": "abc",
        "p_tamper": 0.5,
        "shap_attributions": {},
        "model_version": "v1"
    }
    features_path = create_temp_json(features_data)
    ml_path = create_temp_json(ml_data)
    try:
        # Match the actual error message raised by the analyzer
        with pytest.raises(RuntimeError, match="STALE"):
            run_assessment(features_path, ml_path, mock_mode=False)
    finally:
        os.unlink(features_path)
        os.unlink(ml_path)

# ============================================================
# 4. Quantized Path: must bypass behavioral probing
# ============================================================
def test_quantized_bypass():
    from src.p2_behavioral_risk.prober import get_behavioral_result
    result = get_behavioral_result(
        is_quantized=True,
        domain="VISION",
        model=None,
        calibration_data={"VISION": {"mean": 1.0, "std": 0.5}},
        mock_mode=True
    )
    assert result["bypassed_behavior"] is True
    assert result["s_behavior"] is None
    assert result["probe_count"] == 0

# ============================================================
# 5. Upstream Failure → STOP, NO MRS, NO verdict
# ============================================================
def test_upstream_failure_blocks_output():
    with pytest.raises(FileNotFoundError):
        run_assessment("nonexistent_features.json", "nonexistent_ml.json", mock_mode=False)