import numpy as np
import lightgbm as lgb
import shap
import json
import warnings
from pathlib import Path

FEATURE_NAMES = ["entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean", "std", "skewness", "kurtosis", "sparsity", "outlier_pct"]

_cached_model = None

def get_model():
    global _cached_model
    if _cached_model is not None:
        return _cached_model
        
    # Hackathon prototype: Train deterministic synthetic model
    # Features: 10 dimensions. We create some synthetic data where clean=0, tampered=1.
    np.random.seed(42)
    X_clean = np.random.randn(50, 10)
    y_clean = np.zeros(50)
    
    # Tampered has higher entropy, KS, outlier_pct etc.
    X_tampered = np.random.randn(50, 10) + np.array([2.0, 1.0, 1.0, 2.0, 0, 0, 0, 0, -1.0, 3.0])
    y_tampered = np.ones(50)
    
    X = np.vstack([X_clean, X_tampered])
    y = np.concatenate([y_clean, y_tampered])
    
    dtrain = lgb.Dataset(X, label=y)
    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "verbosity": -1,
        "seed": 42
    }
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _cached_model = lgb.train(params, dtrain, num_boost_round=10)
        
    return _cached_model

def build_mock_ml_results(features: dict, generation_commit: str) -> dict:
    if features.get("generation_commit") != generation_commit:
        raise ValueError("Phase 4 P3 rejects stale P1 artifact generation")
    if features.get("mock_status") == "STALE":
        raise ValueError("Phase 4 P3 rejects stale features")
        
    # Check malformed
    if "static_features" not in features:
        raise ValueError("Malformed features missing static_features")
        
    layers = features["static_features"]
    if not layers:
        raise ValueError("Empty static_features")
        
    model = get_model()
    
    # Prototype: classify each layer, pick max p_tamper
    max_p = -1.0
    best_vector = None
    
    for layer in layers:
        vec = []
        for f in FEATURE_NAMES:
            if f not in layer:
                raise ValueError(f"Malformed layer missing feature {f}")
            val = layer[f]
            if val is None or (isinstance(val, float) and np.isnan(val)):
                vec.append(0.0) # Handle quantized or uncomputable safely for prototype
            else:
                vec.append(val)
        
        vec = np.array(vec)
        p = model.predict([vec])[0]
        if p > max_p:
            max_p = p
            best_vector = vec
            
    # Calculate TreeSHAP for the chosen vector
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(np.array([best_vector]))
    
    # explainer.shap_values for binary classification sometimes returns a list of 2 arrays (for LightGBM old versions) or a single array
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1][0]
    else:
        shap_vals = shap_vals[0]
        
    attributions = {name: float(val) for name, val in zip(FEATURE_NAMES, shap_vals)}
    
    is_mock = (features.get("mock_status") == "MOCK")
    
    return {
        "producer": "P3", 
        "mock_status": "MOCK" if is_mock else "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": generation_commit, 
        "p_tamper": float(max_p),
        "shap_attributions": attributions,
        "model_version": "prototype-lightgbm-phase4",
    }
