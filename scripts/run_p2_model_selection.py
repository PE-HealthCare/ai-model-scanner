"""One bounded, development-only LightGBM model-selection gate for Prompt 2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import run_p2_learning_curve as curve
from src.common.feature_names import B0_FEATURE_NAMES, B1_FEATURE_NAMES
from src.p3_ml_dashboard.classifier import aggregate_p_tamper

METADATA = ROOT / "data" / "training" / "metadata"
SEED = curve.SEED

# Preregistered before scoring.  Feature/bagging fractions and all random
# seeds remain the fixed Gate 2C values; only the listed six capacity knobs vary.
CONFIGURATIONS = (
    ("C01", 15, 5, 40, 0.05, 120, 1.0),  # original fixed configuration
    ("C02", 7, 3, 40, 0.05, 120, 1.0),
    ("C03", 15, 5, 20, 0.05, 120, 1.0),
    ("C04", 15, 5, 10, 0.05, 120, 1.0),
    ("C05", 31, 6, 20, 0.05, 120, 1.0),
    ("C06", 31, 6, 10, 0.05, 120, 1.0),
    ("C07", 31, 6, 20, 0.03, 200, 1.0),
    ("C08", 31, 6, 10, 0.03, 200, 1.0),
    ("C09", 15, 5, 20, 0.03, 200, 0.1),
    ("C10", 15, 5, 20, 0.03, 200, 5.0),
    ("C11", 7, 3, 10, 0.10, 80, 1.0),
    ("C12", 31, 6, 40, 0.05, 120, 5.0),
)


def preregistered_configurations() -> list[dict]:
    """Return the exact 12 candidates in deterministic declared order."""
    if len(CONFIGURATIONS) != 12 or len({item[0] for item in CONFIGURATIONS}) != 12:
        raise AssertionError("Model-selection gate must contain exactly 12 unique configurations")
    result = []
    for config_id, leaves, depth, min_child, learning_rate, estimators, l2 in CONFIGURATIONS:
        params = dict(curve.LGB_PARAMS, num_leaves=leaves, max_depth=depth,
                      min_child_samples=min_child, learning_rate=learning_rate, lambda_l2=l2)
        result.append({"id": config_id, "params": params, "n_estimators": estimators})
    return result


def _ranking(y: np.ndarray, scores: np.ndarray) -> dict:
    if not (np.any(y == 0) and np.any(y == 1)):
        raise ValueError("Both classes are required for ranking metrics")
    pr_auc = float(average_precision_score(y, scores))
    baseline = float(np.mean(y))
    return {"roc_auc": float(roc_auc_score(y, scores)), "pr_auc": pr_auc,
            "pr_auc_baseline": baseline, "normalized_pr_auc": float((pr_auc - baseline) / (1.0 - baseline))}


def _layer_metrics(records: list[dict]) -> dict:
    y = np.asarray([item["layer_label"] for item in records], dtype=np.int8)
    p = np.asarray([item["probability"] for item in records], dtype=np.float64)
    result = _ranking(y, p)
    result.update({"row_count": int(y.size), "balanced_accuracy_at_0_5": float(balanced_accuracy_score(y, p >= 0.5))})
    return result


def _artifact_metrics(records: list[dict]) -> dict:
    y = np.asarray([item["artifact_label"] for item in records], dtype=np.int8)
    p = np.asarray([item["max_probability"] for item in records], dtype=np.float64)
    result = _ranking(y, p)
    result["artifact_count"] = int(y.size)
    return result


def _evaluate(rows: list[dict], names: list[str], candidate: dict) -> dict:
    groups = np.asarray([item["parent_lineage_id"] for item in rows])
    indices = np.arange(len(rows))
    folds = GroupKFold(n_splits=3)
    layer_records, artifact_records, fold_records = [], [], []
    for fold, (train_idx, valid_idx) in enumerate(folds.split(indices, groups=groups)):
        training = [rows[i] for i in train_idx]
        validation_all = [rows[i] for i in valid_idx]
        validation = [item for item in validation_all if item["primary_evaluation"]]
        train_groups = {item["parent_lineage_id"] for item in training}
        valid_groups = {item["parent_lineage_id"] for item in validation_all}
        if train_groups & valid_groups:
            raise AssertionError("Grouped CV lineage leakage")
        if any(item["partition"] != "DEVELOPMENT" or item["attack_family"] == "S4" for item in training + validation):
            raise AssertionError("Sealed or S4 artifact entered model selection")
        weights = curve._weights(training)
        x_train, y_train, w_train = curve._matrix(training, names, weights)
        model = lgb.LGBMClassifier(**candidate["params"], n_estimators=candidate["n_estimators"])
        model.fit(x_train, y_train, sample_weight=w_train)
        fold_layers, fold_artifacts = [], []
        for item in validation:
            x = np.asarray([[row[name] for name in names] for row in item["b1_rows"]], dtype=np.float64)
            probability = model.predict_proba(x)[:, 1]
            margin = model.predict(x, raw_score=True)
            max_probability, _ = aggregate_p_tamper(probability)
            artifact = {"artifact_sha256": item["artifact_sha256"], "parent_lineage_id": item["parent_lineage_id"],
                        "attack_family": item["attack_family"], "attack_strength": item["attack_strength"],
                        "artifact_label": item["label"], "max_probability": max_probability, "fold": fold}
            fold_artifacts.append(artifact)
            for layer_label, p, raw in zip(item["layer_labels"], probability, margin):
                fold_layers.append({"artifact_sha256": item["artifact_sha256"], "parent_lineage_id": item["parent_lineage_id"],
                                    "attack_family": item["attack_family"], "attack_strength": item["attack_strength"],
                                    "layer_label": int(layer_label), "probability": float(p), "margin": float(raw), "fold": fold})
        layer_records.extend(fold_layers)
        artifact_records.extend(fold_artifacts)
        fold_records.append({"fold": fold, "training_parent_lineages": sorted(train_groups),
                             "validation_parent_lineages": sorted(valid_groups), "best_iteration": int(model.best_iteration_ or candidate["n_estimators"]),
                             "layer_metrics": _layer_metrics(fold_layers), "artifact_metrics": _artifact_metrics(fold_artifacts),
                             "microsoft_in_validation": any("microsoft" in value.lower() for value in valid_groups)})
    family, strength = {}, {}
    for value in ("S1", "S2", "S3"):
        selected = [x for x in layer_records if x["attack_family"] == value]
        family[value] = _layer_metrics(selected)
    for value in (0.005, 0.01, 0.02, 0.05):
        selected = [x for x in layer_records if x["attack_family"] != "CLEAN" and x["attack_strength"] == value]
        strength[f"{value:g}"] = _layer_metrics(selected)
    return {"layer_metrics": _layer_metrics(layer_records), "artifact_metrics": _artifact_metrics(artifact_records),
            "folds": fold_records, "family_layer_metrics": family, "strength_layer_metrics": strength,
            "raw_records": layer_records}


def _raw_score_check(records: list[dict]) -> dict:
    probability = np.asarray([x["probability"] for x in records], dtype=np.float64)
    margin = np.asarray([x["margin"] for x in records], dtype=np.float64)
    y = np.asarray([x["layer_label"] for x in records], dtype=np.int8)
    pairs = {}
    for p, raw in zip(probability, margin):
        pairs.setdefault(p.tobytes(), set()).add(raw.tobytes())
    exact_ties = all(len(values) == 1 for values in pairs.values())
    return {"layer_roc_auc_probability": float(roc_auc_score(y, probability)), "layer_roc_auc_raw_margin": float(roc_auc_score(y, margin)),
            "unique_probability_values": int(np.unique(probability).size), "unique_probability_fraction": float(np.unique(probability).size / probability.size),
            "unique_raw_margin_values": int(np.unique(margin).size), "unique_raw_margin_fraction": float(np.unique(margin).size / margin.size),
            "probability_ties_remain_raw_margin_ties": exact_ties,
            "spearman_rho": float(spearmanr(probability, margin).statistic)}


def select_candidate(results: dict[str, list[dict]]) -> dict:
    """Preregistered selection: consistent layer ROC gain, then stated tie-breakers."""
    candidates = []
    for representation, values in results.items():
        baseline = next(item for item in values if item["id"] == "C01")
        baseline_folds = np.asarray([x["layer_metrics"]["roc_auc"] for x in baseline["folds"]])
        for item in values:
            folds = np.asarray([x["layer_metrics"]["roc_auc"] for x in item["folds"]])
            mean = float(folds.mean())
            std = float(folds.std(ddof=0))
            deltas = folds - baseline_folds
            # C01 is the deterministic fallback; every other candidate must
            # improve its representation's mean and at least two held-out folds.
            consistent = item["id"] == "C01" or (mean > float(baseline_folds.mean()) and int(np.sum(deltas > 0.0)) >= 2)
            complexity = (item["configuration"]["params"]["num_leaves"], item["configuration"]["params"]["max_depth"],
                          item["configuration"]["n_estimators"], -item["configuration"]["params"]["min_child_samples"],
                          item["configuration"]["params"]["lambda_l2"])
            candidates.append({"representation": representation, "id": item["id"], "mean_layer_roc_auc": mean,
                               "std_layer_roc_auc": std, "artifact_roc_auc": item["artifact_metrics"]["roc_auc"],
                               "fold_layer_roc_auc_deltas_vs_c01": deltas.tolist(), "consistent_improvement": consistent,
                               "complexity": complexity, "item": item})
    eligible = [item for item in candidates if item["consistent_improvement"]]
    # Ordered exactly by mean layer ROC, lower fold variability, artifact ROC,
    # then lower declared complexity. B0 resolves an otherwise exact tie only.
    selected = sorted(eligible, key=lambda x: (-x["mean_layer_roc_auc"], x["std_layer_roc_auc"],
                                                 -x["artifact_roc_auc"], x["complexity"], x["representation"]))[0]
    return {key: value for key, value in selected.items() if key != "item"}


def run() -> dict:
    rows, features, split, feature_sha, split_sha, attack_sha = curve._load()
    configs = preregistered_configurations()
    config_path = METADATA / "model_selection_configurations.json"
    config_path.write_text(json.dumps({"version": "p2-model-selection-v1", "seed": SEED, "configurations": configs}, indent=2) + "\n", encoding="utf-8")
    results = {"B0": [], "B1": []}
    for representation, names in (("B0", B0_FEATURE_NAMES), ("B1", B1_FEATURE_NAMES)):
        for candidate in configs:
            outcome = _evaluate(rows, names, candidate)
            outcome["id"] = candidate["id"]
            outcome["configuration"] = candidate
            results[representation].append(outcome)
    for representation in results:
        if [x["id"] for x in results[representation]] != [x["id"] for x in configs]:
            raise AssertionError("A preregistered candidate was skipped or added")
    memberships = [[(f["training_parent_lineages"], f["validation_parent_lineages"]) for f in x["folds"]] for x in results["B0"] + results["B1"]]
    if any(item != memberships[0] for item in memberships[1:]):
        raise AssertionError("Candidate or representation changed grouped fold membership")
    raw = {rep: _raw_score_check(next(x for x in values if x["id"] == "C01")["raw_records"]) for rep, values in results.items()}
    selected = select_candidate(results)
    for values in results.values():
        for item in values:
            item.pop("raw_records")
    payload = {"version": "p2-model-selection-v1", "seed": SEED, "configurations": configs, "raw_score_check": raw,
               "results": results, "selected": selected, "feature_implementation_fingerprint": features["extractor_implementation_fingerprint"],
               "feature_manifest_sha256": feature_sha, "split_manifest_sha256": split_sha, "attack_manifest_sha256": attack_sha,
               "development_parent_lineages": split["development_parent_lineages"]}
    (METADATA / "model_selection_results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(json.dumps({"configurations": len(result["configurations"]), "output": "model_selection_results.json"}))
