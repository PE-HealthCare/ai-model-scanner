# tests/test_quantized_features.py
"""Tests for quantized‑feature handling in load_features_json.

The contract (D11) states that for a quantized model only `ks_stat` must be
numeric; the other nine FP‑only features may be `null`. These tests verify that
`load_features_json` respects that rule and that invalid numeric values are
rejected.
"""

import os
import json
import tempfile

import pytest

from src.p2_behavioral_risk.adapters import load_features_json


def _temp_json(data):
    """Create a temporary JSON file containing *data* and return its path.
    The caller is responsible for deleting the file.
    """
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def _base_feature_dict(is_quantized: bool, layer_values: dict):
    base = {
        "input_domain": "VISION",
        "is_quantized": is_quantized,
        "layer_count": 1,
        "static_features": [layer_values],
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "abc123",
    }
    return base


def test_quantized_features_allow_nulls():
    layer = {
        "layer_name": "layer1",
        "entropy": None,
        "pov_chi2": None,
        "lsb_kl": None,
        "ks_stat": 0.42,
        "mean": None,
        "std": None,
        "skewness": None,
        "kurtosis": None,
        "sparsity": None,
        "outlier_pct": None,
    }
    data = _base_feature_dict(is_quantized=True, layer_values=layer)
    path = _temp_json(data)
    try:
        result = load_features_json(path)
        parsed_layer = result["layer_features"][0]
        assert parsed_layer["ks_stat"] == 0.42
        for key, value in parsed_layer.items():
            if key not in {"layer_name", "ks_stat"}:
                assert value is None
    finally:
        os.unlink(path)


def test_quantized_invalid_fp_feature_raises():
    layer = {
        "layer_name": "layer1",
        "entropy": "bad",
        "pov_chi2": None,
        "lsb_kl": None,
        "ks_stat": 0.5,
        "mean": None,
        "std": None,
        "skewness": None,
        "kurtosis": None,
        "sparsity": None,
        "outlier_pct": None,
    }
    data = _base_feature_dict(is_quantized=True, layer_values=layer)
    path = _temp_json(data)
    try:
        with pytest.raises(ValueError, match="Non‑finite or invalid value"):
            load_features_json(path)
    finally:
        os.unlink(path)


def test_quantized_missing_ks_stat_raises():
    layer = {
        "layer_name": "layer1",
        "entropy": None,
        "pov_chi2": None,
        "lsb_kl": None,
        "ks_stat": None,
        "mean": None,
        "std": None,
        "skewness": None,
        "kurtosis": None,
        "sparsity": None,
        "outlier_pct": None,
    }
    data = _base_feature_dict(is_quantized=True, layer_values=layer)
    path = _temp_json(data)
    try:
        with pytest.raises(ValueError, match="Non‑finite or invalid value"):
            load_features_json(path)
    finally:
        os.unlink(path)


def test_non_quantized_null_features_rejected():
    layer = {
        "layer_name": "layer1",
        "entropy": None,
        "pov_chi2": 0.1,
        "lsb_kl": 0.2,
        "ks_stat": 0.3,
        "mean": 0.4,
        "std": 0.5,
        "skewness": 0.6,
        "kurtosis": 0.7,
        "sparsity": 0.8,
        "outlier_pct": 0.9,
    }
    data = _base_feature_dict(is_quantized=False, layer_values=layer)
    path = _temp_json(data)
    try:
        with pytest.raises(ValueError, match="Non‑finite or invalid value"):
            load_features_json(path)
    finally:
        os.unlink(path)


def _quantized_layer_with_ks(ks_value):
    return {
        "layer_name": "layer1",
        "entropy": None,
        "pov_chi2": None,
        "lsb_kl": None,
        "ks_stat": ks_value,
        "mean": None,
        "std": None,
        "skewness": None,
        "kurtosis": None,
        "sparsity": None,
        "outlier_pct": None,
    }


@pytest.mark.parametrize("bad_ks", [-0.2, 1.5, 2.0])
def test_quantized_ks_stat_out_of_range_rejected(bad_ks):
    """ks_stat must be finite and within [0,1]; never clamped or substituted."""
    data = _base_feature_dict(
        is_quantized=True, layer_values=_quantized_layer_with_ks(bad_ks)
    )
    path = _temp_json(data)
    try:
        with pytest.raises(ValueError, match="Non‑finite or invalid value"):
            load_features_json(path)
    finally:
        os.unlink(path)


@pytest.mark.parametrize("good_ks", [0.0, 1.0])
def test_quantized_ks_stat_boundaries_accepted(good_ks):
    """Boundary values 0.0 and 1.0 remain valid quantized ks_stat evidence."""
    data = _base_feature_dict(
        is_quantized=True, layer_values=_quantized_layer_with_ks(good_ks)
    )
    path = _temp_json(data)
    try:
        result = load_features_json(path)
        parsed_layer = result["layer_features"][0]
        assert parsed_layer["ks_stat"] == pytest.approx(float(good_ks))
        for key, value in parsed_layer.items():
            if key not in {"layer_name", "ks_stat"}:
                assert value is None
    finally:
        os.unlink(path)
