"""Phase 1 mock ML producer/consumer owned by P3."""

FEATURE_NAMES = ("entropy", "pov_chi2", "lsb_kl", "ks_stat", "sparsity", "outlier_pct")


def build_mock_ml_results(features: dict, generation_commit: str) -> dict:
    if features.get("producer") != "P1" or features.get("mock_status") != "MOCK":
        raise ValueError("Phase 1 mock P3 requires a P1 MOCK features artifact")
    return {
        "producer": "P3", "mock_status": "MOCK", "contract_version": "1.0", "generation_commit": generation_commit,
        "p_tamper": 0.08,
        "shap_attributions": {name: value for name, value in zip(FEATURE_NAMES, (0.12, 0.05, 0.02, 0.04, 0.03, 0.01))},
        "model_version": "mock-lightgbm-phase1",
    }
