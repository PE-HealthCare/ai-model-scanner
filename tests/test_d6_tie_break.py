import pytest
from src.p2_behavioral_risk.risk_aggregator import compute_s_static_and_layer

def test_d6_tie_break_layer_id_ordering():
    # Two layers with identical evidence values
    layer_features = [
        {"layer_name": "layer_A", "entropy": 1.0, "chi_square": 1.0, "kl_div": 1.0, "ks_stat": 1.0, "layer_id": "0"},
        {"layer_name": "layer_B", "entropy": 1.0, "chi_square": 1.0, "kl_div": 1.0, "ks_stat": 1.0, "layer_id": "1"},
    ]
    _, highest = compute_s_static_and_layer(layer_features)
    assert highest == "layer_A"
