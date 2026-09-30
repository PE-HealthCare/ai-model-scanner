"""Fixed development-only artifact-level LightGBM baseline for global 92 features."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.p3_ml_dashboard.global_bitplane_features import GLOBAL_BITPLANE_FEATURE_NAMES

INPUT = ROOT / "data" / "training" / "metadata" / "global_bitplane_development.json"
OUTPUT = ROOT / "data" / "training" / "metadata" / "global_bitplane_development_oof.json"
PARAMS = {"objective": "binary", "num_leaves": 7, "max_depth": 3,
          "min_child_samples": 2, "learning_rate": 0.05, "n_estimators": 120,
          "lambda_l2": 1.0, "feature_fraction": 1.0, "bagging_fraction": 1.0,
          "bagging_freq": 0, "max_bin": 63, "seed": 20260929, "n_jobs": 1,
          "verbosity": -1, "deterministic": True}


def _distribution(values: np.ndarray) -> dict:
    return {"min": float(values.min()), "median": float(np.median(values)),
            "mean": float(values.mean()), "max": float(values.max())}


def run() -> dict:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    records = payload["records"]
    if not payload.get("complete") or len(records) != 169:
        raise AssertionError("Step-4 global development dataset is incomplete")
    if any(x["partition"] != "DEVELOPMENT" or x["attack_family"] not in {"CLEAN", "S1", "S2", "S3"} for x in records):
        raise AssertionError("Final-test or S4 artifact entered baseline")
    if tuple(payload["feature_names"]) != GLOBAL_BITPLANE_FEATURE_NAMES:
        raise AssertionError("Global 92 feature order mismatch")
    if len({x["artifact_sha256"] for x in records}) != len(records):
        raise AssertionError("Duplicate artifact SHA")
    x = np.asarray([[item["features"][name] for name in GLOBAL_BITPLANE_FEATURE_NAMES] for item in records], dtype=np.float64)
    y = np.asarray([item["label"] for item in records], dtype=np.int8)
    groups = np.asarray([item["parent_lineage_id"] for item in records])
    if x.shape != (169, 92) or not np.all(np.isfinite(x)) or set(y) != {0, 1}:
        raise AssertionError("Invalid global baseline input")
    scores = np.empty(len(records), dtype=np.float64)
    fold_rows = []
    for fold, (train_idx, valid_idx) in enumerate(GroupKFold(n_splits=3).split(x, y, groups)):
        train_groups, valid_groups = set(groups[train_idx]), set(groups[valid_idx])
        if train_groups & valid_groups:
            raise AssertionError("Parent-lineage leakage")
        model = lgb.LGBMClassifier(**PARAMS).fit(x[train_idx], y[train_idx])
        scores[valid_idx] = model.predict_proba(x[valid_idx])[:, 1]
        fold_rows.append({"fold": fold, "validation_parent_lineages": sorted(valid_groups),
                          "artifact_count": int(valid_idx.size),
                          "roc_auc": float(roc_auc_score(y[valid_idx], scores[valid_idx]))})
    if not np.all(np.isfinite(scores)) or np.any((scores < 0) | (scores > 1)):
        raise AssertionError("Invalid OOF score")
    clean, tampered = scores[y == 0], scores[y == 1]
    result = {"version": "p2-global-bitplane-oof-v1", "input": str(INPUT.relative_to(ROOT)),
              "feature_count": 92, "feature_names": list(GLOBAL_BITPLANE_FEATURE_NAMES), "lightgbm_params": PARAMS,
              "artifact_count": int(y.size), "clean_count": int((y == 0).sum()), "tampered_count": int((y == 1).sum()),
              "lineage_count": len(set(groups)), "fold_count": 3,
              "pooled_artifact_ROC_AUC": float(roc_auc_score(y, scores)),
              "pooled_artifact_PR_AUC": float(average_precision_score(y, scores)), "PR_baseline": float(y.mean()),
              "folds": fold_rows, "clean_score": _distribution(clean), "tampered_score": _distribution(tampered),
              "predictions": [{"artifact_sha256": item["artifact_sha256"], "parent_lineage_id": item["parent_lineage_id"],
                               "label": int(label), "oof_probability": float(score), "fold": next(f["fold"] for f in fold_rows if item["parent_lineage_id"] in f["validation_parent_lineages"])}
                              for item, label, score in zip(records, y, scores)]}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
