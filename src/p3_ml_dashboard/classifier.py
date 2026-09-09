"""Phase 4 P3 LightGBM classifier and TreeSHAP producer."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Sequence
import lightgbm as lgb
import numpy as np
import shap

FEATURE_NAMES=("entropy","pov_chi2","lsb_kl","ks_stat","mean","std","skewness","kurtosis","sparsity","outlier_pct")
DEFAULT_MODEL_PATH=Path("artifacts/lightgbm_model.txt")

def _require_feature_contract(features:dict)->list[dict]:
    if features.get("producer")!="P1": raise ValueError("Phase 4 P3 requires a P1 producer")
    if features.get("mock_status")!="VERIFIED-REAL": raise ValueError("Final classifier requires VERIFIED-REAL P1 feature data")
    layers=features.get("static_features")
    if not isinstance(layers,list) or not layers: raise ValueError("Malformed features: static_features must be a non-empty list")
    if features.get("layer_count")!=len(layers): raise ValueError("Malformed features: layer_count does not match static_features")
    return layers

def _feature_matrix(features:dict)->np.ndarray:
    rows=[]
    for layer in _require_feature_contract(features):
        if not isinstance(layer,dict) or not isinstance(layer.get("layer_name"),str): raise ValueError("Malformed layer: layer_name is required")
        row=[]
        for name in FEATURE_NAMES:
            if name not in layer: raise ValueError(f"Malformed layer missing feature {name}")
            value=layer[name]
            if isinstance(value,bool) or not isinstance(value,(int,float)): raise ValueError(f"Invalid feature value for {name}")
            value=float(value)
            if not np.isfinite(value): raise ValueError(f"Invalid non-finite feature value for {name}")
            row.append(value)
        rows.append(row)
    matrix=np.asarray(rows,dtype=np.float64)
    if matrix.ndim!=2 or matrix.shape[1]!=len(FEATURE_NAMES): raise ValueError("Feature matrix does not match D1 feature contract")
    return matrix

def _sha256_file(path:Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def _sha256_text(text:str)->str: return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _p1_source_hash()->str:
    from src.p1_static_engine import analyzer as p1_analyzer
    return _sha256_file(Path(p1_analyzer.__file__).resolve())

def extract_training_example(model_path:str|Path,declared_architecture:str,generation_commit:str)->tuple[dict,str]:
    """Use the real P1 intake and feature extractor for one training model."""
    from src.p1_static_engine.analyzer import extract_features,intake_model
    path=Path(model_path)
    context=intake_model(path,declared_architecture=declared_architecture)
    features=extract_features(context,generation_commit=generation_commit)
    if features.get("mock_status")!="VERIFIED-REAL": raise ValueError("P1 training extraction did not produce VERIFIED-REAL features")
    return features,_sha256_file(path)

def train_final_classifier(clean_models:Sequence[str|Path],tampered_models:Sequence[str|Path],*,declared_architecture:str,generation_commit:str,dataset_id:str,output_path:str|Path=DEFAULT_MODEL_PATH)->dict:
    """Train the final LightGBM artifact using only real P1-extracted features."""
    if not clean_models or not tampered_models: raise ValueError("Final training requires both clean and tampered model sets")
    if not dataset_id or not dataset_id.strip(): raise ValueError("dataset_id is required for training provenance")
    if not generation_commit: raise ValueError("generation_commit is required")
    matrices=[]; labels=[]; source_hashes=[]
    for path in clean_models:
        features,source_hash=extract_training_example(path,declared_architecture,generation_commit)
        matrices.append(_feature_matrix(features)); labels.append(np.zeros(len(features["static_features"]),dtype=np.int32)); source_hashes.append(source_hash)
    for path in tampered_models:
        features,source_hash=extract_training_example(path,declared_architecture,generation_commit)
        matrices.append(_feature_matrix(features)); labels.append(np.ones(len(features["static_features"]),dtype=np.int32)); source_hashes.append(source_hash)
    X,y=np.vstack(matrices),np.concatenate(labels)
    if len(np.unique(y))!=2: raise ValueError("Training corpus must contain both clean and tampered labels")
    params={"objective":"binary","metric":"binary_logloss","verbosity":-1,"seed":42,"feature_pre_filter":False}
    booster=lgb.train(params,lgb.Dataset(X,label=y,feature_name=list(FEATURE_NAMES)),num_boost_round=100)
    model_text=booster.model_to_string(); output=Path(output_path); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(model_text,encoding="utf-8")
    return {"dataset_id":dataset_id,"dataset_source_sha256":_sha256_text("\n".join(sorted(source_hashes))),"p1_extractor_sha256":_p1_source_hash(),"generation_commit":generation_commit,"contract_version":"1.0","feature_names":list(FEATURE_NAMES),"model_sha256":_sha256_text(model_text),"mock_status":"VERIFIED-REAL"}

def _load_final_model(model_path:str|Path=DEFAULT_MODEL_PATH)->lgb.Booster:
    path=Path(model_path)
    if not path.is_file(): raise FileNotFoundError(f"Final classifier artifact not found: {path}")
    try: model=lgb.Booster(model_file=str(path))
    except Exception as exc: raise ValueError("Invalid LightGBM classifier artifact") from exc
    if model.feature_name()!=list(FEATURE_NAMES): raise ValueError("Classifier feature names/order do not match D1")
    return model

def build_ml_results(features:dict,generation_commit:str,*,model_path:str|Path=DEFAULT_MODEL_PATH)->dict:
    """Produce ml_results.json content from verified-real P1 features."""
    if features.get("generation_commit")!=generation_commit: raise ValueError("Phase 4 P3 rejects stale P1 artifact generation")
    X=_feature_matrix(features); model=_load_final_model(model_path); probabilities=np.asarray(model.predict(X),dtype=np.float64)
    if probabilities.size==0 or not np.isfinite(probabilities).all() or np.any((probabilities<0.0)|(probabilities>1.0)): raise ValueError("Classifier produced invalid P_tamper values")
    if len(probabilities)!=1: raise RuntimeError("DECISION REQUIRED: model-level P_tamper aggregation across P1 layers is not defined by the approved Phase 4 contract")
    shap_values=np.asarray(shap.TreeExplainer(model).shap_values(X[:1]))
    if isinstance(shap_values,list): shap_values=np.asarray(shap_values[-1])
    if shap_values.ndim==2: shap_values=shap_values[0]
    if shap_values.shape!=(len(FEATURE_NAMES),) or not np.isfinite(shap_values).all(): raise ValueError("TreeSHAP output does not match D1")
    return {"producer":"P3","mock_status":"VERIFIED-REAL","contract_version":"1.0","generation_commit":generation_commit,"p_tamper":float(probabilities[0]),"shap_attributions":{n:float(v) for n,v in zip(FEATURE_NAMES,shap_values)},"model_version":"lightgbm-phase4-final"}

def build_mock_ml_results(features:dict,generation_commit:str)->dict:
    """Legacy Phase-1 mock producer retained only for mock-pipeline tests."""
    if features.get("producer")!="P1" or features.get("mock_status")!="MOCK": raise ValueError("Phase 1 mock P3 requires a P1 MOCK features artifact")
    if features.get("generation_commit")!=generation_commit: raise ValueError("Phase 1 P3 rejects stale P1 artifact generation")
    values=(0.12,0.05,0.02,0.04,0.03,0.02,0.01,0.02,0.03,0.01)
    return {"producer":"P3","mock_status":"MOCK","contract_version":"1.0","generation_commit":generation_commit,"p_tamper":0.08,"shap_attributions":dict(zip(FEATURE_NAMES,values)),"model_version":"mock-lightgbm-phase1"}
