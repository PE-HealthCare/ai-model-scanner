"""Phase 1 mock feature producer owned by P1."""

from __future__ import annotations


def build_mock_features(generation_commit: str) -> dict:
    return {
        "producer": "P1", "mock_status": "MOCK", "contract_version": "1.0",
        "generation_commit": generation_commit, "input_domain": "VISION", "is_quantized": False, "layer_count": 2,
        "static_features": [
            {"layer_name": "mock.layer1", "entropy": 0.98, "pov_chi2": 1.05, "lsb_kl": 0.02, "ks_stat": 0.12, "sparsity": 0.08, "outlier_pct": 0.30},
            {"layer_name": "mock.layer2", "entropy": 0.95, "pov_chi2": 1.10, "lsb_kl": 0.03, "ks_stat": 0.15, "sparsity": 0.10, "outlier_pct": 0.40},
        ],
    }
