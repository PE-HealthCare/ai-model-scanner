# tests/test_d5d6.py
import json
import numpy as np
from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer

def test_d5d6():
    with open("data/inputs/features.json") as f:
        data = json.load(f)
    features = data["static_features"]  # raw list
    # Convert to P2 format (your adapter already does this)
    layer_features = [
        {
            "layer_name": layer["layer_name"],
            "entropy": layer["entropy"],
            "chi_square": layer["pov_chi2"],
            "kl_div": layer["lsb_kl"],
            "ks_stat": layer["ks_stat"]
        }
        for layer in features
    ]
    s_static, highest_layer = compute_s_static_and_layer(layer_features)
    print(f"S_static = {s_static}")
    print(f"Highest risk layer = {highest_layer}")
    assert 0.0 <= s_static <= 1.0
    assert isinstance(highest_layer, str)