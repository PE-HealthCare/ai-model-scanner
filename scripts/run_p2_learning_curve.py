"""Development-only, lineage-grouped B0/B1 source-diversity learning curve."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

import lightgbm as lgb
import numpy as np
from sklearn.metrics import average_precision_score, balanced_accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.common.feature_names import B0_FEATURE_NAMES, B1_FEATURE_NAMES
from src.p3_ml_dashboard.classifier import aggregate_p_tamper

METADATA = ROOT / "data" / "training" / "metadata"
SEED = 20260929
THRESHOLD = 0.5
TAIL_PERCENTILE = 95.0
LGB_PARAMS = {
    "objective": "binary", "learning_rate": 0.05, "num_leaves": 15,
    "max_depth": 5, "min_child_samples": 40, "feature_fraction": 0.9,
    "bagging_fraction": 0.9, "bagging_freq": 1, "lambda_l1": 0.0,
    "lambda_l2": 1.0, "verbosity": -1, "seed": SEED,
    "feature_fraction_seed": SEED, "bagging_seed": SEED,
    "data_random_seed": SEED, "deterministic": True, "num_threads": 1,
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load() -> tuple[list[dict], dict, dict, str, str, str]:
    feature_path = METADATA / "feature_manifest.json"
    attack_path = METADATA / "attack_manifest.json"
    split_path = METADATA / "split_manifest.json"
    features = json.loads(feature_path.read_text(encoding="utf-8"))
    attacks = json.loads(attack_path.read_text(encoding="utf-8"))
    split = json.loads(split_path.read_text(encoding="utf-8"))
    attack_by_file = {item["file"]: item for item in attacks["artifacts"]}
    primary_files: set[str] = set()
    seen: set[tuple[str, str, float]] = set()
    for item in attacks["artifacts"]:
        if item["attack_family"] in {"S1", "S2", "S3"}:
            group = (item["source_model_id"], item["attack_family"], item["attack_strength"])
            if group not in seen:
                primary_files.add(item["file"])
                seen.add(group)
    rows = []
    for item in features["feature_rows"]:
        family = item["attack_family"]
        if item["partition"] != "DEVELOPMENT" or family == "S4":
            continue
        if family != "CLEAN" and family not in {"S1", "S2", "S3"}:
            raise ValueError(f"Unexpected attack family {family}")
        if not item.get("source_model_id") or not item.get("parent_lineage_id"):
            raise ValueError("Missing source or parent lineage metadata")
        expected_b0 = [
            {"layer_name": layer["layer_name"], **{name: layer[name] for name in B0_FEATURE_NAMES}}
            for layer in item["b1_rows"]
        ]
        if item["b0_rows"] != expected_b0:
            raise ValueError(f"B0 projection mismatch for {item['file']}")
        attack = attack_by_file.get(item["file"])
        if family != "CLEAN" and attack is None:
            raise AssertionError(f"Missing attack ground truth for {item['file']}")
        modified_tensors = set() if family == "CLEAN" else set(attack["modified_tensors"])
        if family != "CLEAN" and len(modified_tensors) != len(attack["modified_tensors"]):
            raise AssertionError(f"Duplicate modified-tensor identity in {item['file']}")
        if len({row["layer_name"] for row in item["b1_rows"]}) != len(item["b1_rows"]):
            raise AssertionError(f"Non-unique canonical layer identities in {item['file']}")
        layer_labels = [int(row["layer_name"] in modified_tensors) for row in item["b1_rows"]]
        if family == "CLEAN" and any(layer_labels):
            raise AssertionError("Clean artifact has a positive layer label")
        if family != "CLEAN":
            feature_layers = {row["layer_name"] for row in item["b1_rows"]}
            if not modified_tensors <= feature_layers:
                raise AssertionError(f"Attack metadata references unknown layer in {item['file']}")
            if {row["layer_name"] for row, label in zip(item["b1_rows"], layer_labels) if label} != modified_tensors:
                raise AssertionError(f"Modified-layer labels disagree with attack metadata in {item['file']}")
            if family == "S3" and sum(layer_labels) != len(modified_tensors):
                raise AssertionError(f"S3 does not have exactly its recorded modified layers positive: {item['file']}")
        rows.append({**item, "label": 0 if family == "CLEAN" else 1,
                     "layer_labels": layer_labels, "modified_tensors": sorted(modified_tensors),
                     "primary_evaluation": family == "CLEAN" or item["file"] in primary_files})
    if any(not np.isfinite(value) for item in rows for row in item["b1_rows"] for value in row.values() if isinstance(value, (float, int))):
        raise ValueError("Non-finite feature input")
    if any(item["partition"] != "DEVELOPMENT" or item["attack_family"] == "S4" for item in rows):
        raise AssertionError("Sealed or S4 artifact entered development experiment")
    development_lineages = set(split["development_parent_lineages"])
    final_test_lineages = set(split["final_test_parent_lineages"])
    if final_test_lineages & development_lineages or any(item["parent_lineage_id"] not in development_lineages for item in rows):
        raise AssertionError("Final-test parent lineage entered development experiment")
    return rows, features, split, _sha(feature_path), _sha(split_path), _sha(attack_path)


def _nested_lineages(rows: list[dict]) -> list[list[str]]:
    by_parent: dict[str, list[dict]] = defaultdict(list)
    for item in rows:
        by_parent[item["parent_lineage_id"]].append(item)
    # Include the multi-source parent first, then a stable hash ordering of
    # remaining independent groups. Every subsequent point is nested.
    largest = max(by_parent, key=lambda parent: (len({x["source_model_id"] for x in by_parent[parent]}), parent))
    remaining = sorted((p for p in by_parent if p != largest), key=lambda p: hashlib.sha256(f"{SEED}|{p}".encode()).hexdigest())
    ordered = [largest, *remaining]
    checkpoints = [n for n in (4, 6, len(ordered)) if n <= len(ordered)]
    return [ordered[:n] for n in dict.fromkeys(checkpoints)]


def _weights(artifacts: list[dict]) -> dict[str, np.ndarray]:
    """Equal parent -> source -> layer class -> artifact -> layer influence."""
    parents = sorted({a["parent_lineage_id"] for a in artifacts})
    by_parent_source_class: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    sources_by_parent: dict[str, set[str]] = defaultdict(set)
    for artifact in artifacts:
        sources_by_parent[artifact["parent_lineage_id"]].add(artifact["source_model_id"])
        for layer_class in set(artifact["layer_labels"]):
            by_parent_source_class[(artifact["parent_lineage_id"], artifact["source_model_id"], layer_class)].append(artifact)
    out = {}
    for artifact in artifacts:
        parent, source = artifact["parent_lineage_id"], artifact["source_model_id"]
        artifact_weights = np.zeros(len(artifact["layer_labels"]), dtype=np.float64)
        for layer_class in (0, 1):
            positions = np.flatnonzero(np.asarray(artifact["layer_labels"]) == layer_class)
            if not positions.size:
                continue
            peers = by_parent_source_class[(parent, source, layer_class)]
            if not peers:
                raise AssertionError("Missing hierarchical weight peer")
            # Every parent and source has equal influence. Within a source,
            # negative and modified-positive layers each receive one half;
            # artifacts and rows cannot gain influence by multiplicity.
            artifact_weights[positions] = 1.0 / (
                len(parents) * len(sources_by_parent[parent]) * 2 * len(peers) * positions.size
            )
        out[artifact["artifact_sha256"]] = artifact_weights
    return out


def _matrix(artifacts: list[dict], names: list[str], weights: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x, y, w = [], [], []
    for artifact in artifacts:
        rows = artifact["b1_rows"]
        x.extend([[row[name] for name in names] for row in rows])
        y.extend(artifact["layer_labels"])
        w.extend(weights[artifact["artifact_sha256"]])
    result = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.int8), np.asarray(w, dtype=np.float64)
    if not np.all(np.isfinite(result[0])):
        raise ValueError("Non-finite model input")
    return result


def _metrics(artifacts: list[dict], scores: dict[str, float]) -> dict:
    ordered = [item for item in artifacts if item["artifact_sha256"] in scores]
    y = np.asarray([item["label"] for item in ordered], dtype=np.int8)
    p = np.asarray([scores[item["artifact_sha256"]] for item in ordered], dtype=np.float64)
    pred = p >= THRESHOLD
    negatives = y == 0
    positives = y == 1
    result = {
        "artifact_count": int(y.size), "pr_auc": float(average_precision_score(y, p)), "roc_auc": float(roc_auc_score(y, p)),
        "f1": float(f1_score(y, pred, zero_division=0)), "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)), "recall": float(recall_score(y, pred, zero_division=0)),
        "fpr": float(np.mean(pred[negatives])) if negatives.any() else None,
        "fnr": float(np.mean(~pred[positives])) if positives.any() else None,
    }
    for strength in (0.005, 0.01, 0.02, 0.05):
        selected = [item for item in ordered if item["label"] and item["attack_strength"] == strength]
        result[f"recall_{strength:g}"] = float(np.mean([scores[item["artifact_sha256"]] >= THRESHOLD for item in selected])) if selected else None
    for family in ("S1", "S2", "S3"):
        selected = [item for item in ordered if item["attack_family"] == family]
        result[f"recall_{family}"] = float(np.mean([scores[item["artifact_sha256"]] >= THRESHOLD for item in selected])) if selected else None
    return result


def _binary_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    pred = p >= THRESHOLD
    return {
        "row_count": int(y.size), "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)), "f1": float(f1_score(y, pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
    }


def tail_mass(probabilities, tau: float) -> float:
    """Preregistered fraction of layer probabilities at/above a frozen tau."""
    p = np.asarray(probabilities, dtype=np.float64)
    if p.ndim != 1 or not p.size:
        raise ValueError("Tail mass requires at least one layer probability")
    if not np.all(np.isfinite(p)) or np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("Tail mass requires finite probabilities in [0, 1]")
    tau = float(tau)
    if not np.isfinite(tau) or not 0.0 <= tau <= 1.0:
        raise ValueError("Tail mass requires a finite tau in [0, 1]")
    return float(np.mean(p >= tau))


def _training_clean_tau(model, training: list[dict], names: list[str], held_out_lineages: set[str]) -> float:
    """Freeze the q95 reference from training-partition clean layers only."""
    probabilities = []
    for item in training:
        if item["partition"] != "DEVELOPMENT" or item["attack_family"] == "S4":
            raise AssertionError("Sealed or S4 artifact entered tail reference")
        if item["parent_lineage_id"] in held_out_lineages:
            raise AssertionError("Held-out lineage contributed to tail reference")
        if item["attack_family"] != "CLEAN":
            continue
        x = np.asarray([[row[name] for name in names] for row in item["b1_rows"]], dtype=np.float64)
        probabilities.extend(model.predict_proba(x)[:, 1].tolist())
    if not probabilities:
        raise AssertionError("No clean training layers available for tail reference")
    tau = float(np.percentile(np.asarray(probabilities, dtype=np.float64), TAIL_PERCENTILE))
    if not np.isfinite(tau) or not 0.0 <= tau <= 1.0:
        raise AssertionError("Tail reference is not a finite probability")
    return tau


def _ranking_metrics(artifacts: list[dict], scores: dict[str, float]) -> dict:
    """Threshold-free artifact ranking metrics for a fixed OOF score."""
    ordered = [item for item in artifacts if item["artifact_sha256"] in scores]
    y = np.asarray([item["label"] for item in ordered], dtype=np.int8)
    p = np.asarray([scores[item["artifact_sha256"]] for item in ordered], dtype=np.float64)
    if not np.all(np.isfinite(p)) or np.any((p < 0.0) | (p > 1.0)):
        raise AssertionError("Tail experiment emitted invalid score")
    if not (np.any(y == 0) and np.any(y == 1)):
        raise ValueError("Ranking metrics require both artifact classes")
    baseline = float(np.mean(y))
    pr_auc = float(average_precision_score(y, p))
    return {"artifact_count": int(y.size), "roc_auc": float(roc_auc_score(y, p)),
            "pr_auc": pr_auc, "pr_auc_baseline": baseline,
            "normalized_pr_auc": float((pr_auc - baseline) / (1.0 - baseline))}


def _distribution(scores: list[float]) -> dict:
    values = np.asarray(scores, dtype=np.float64)
    if not values.size or not np.all(np.isfinite(values)):
        raise ValueError("Distribution requires finite scores")
    return {"n": int(values.size), "min": float(values.min()), "q25": float(np.quantile(values, 0.25)),
            "median": float(np.median(values)), "q75": float(np.quantile(values, 0.75)),
            "max": float(values.max()), "mean": float(values.mean())}


def _evaluate(subset: list[dict], names: list[str]) -> dict:
    if set(names) - set(B1_FEATURE_NAMES):
        raise AssertionError("Only established B0/B1 feature columns may be classifier inputs")
    if {"modified_tensors", "attack_family", "attack_strength"} & set(names):
        raise AssertionError("Attack metadata must not be a classifier input")
    lineages = sorted({item["parent_lineage_id"] for item in subset})
    n_splits = min(3, len(lineages))
    if n_splits < 2:
        raise ValueError("At least two parent lineages required for grouped CV")
    groups = np.asarray([item["parent_lineage_id"] for item in subset])
    folds = GroupKFold(n_splits=n_splits)
    scores: dict[str, float] = {}
    fold_records = []
    oof_artifacts = []
    layer_y, layer_p = [], []
    indices = np.arange(len(subset))
    for fold, (train_idx, valid_idx) in enumerate(folds.split(indices, groups=groups)):
        train = [subset[i] for i in train_idx]
        validation_all = [subset[i] for i in valid_idx]
        validation = [item for item in validation_all if item["primary_evaluation"]]
        train_groups = {item["parent_lineage_id"] for item in train}
        valid_groups = {item["parent_lineage_id"] for item in validation_all}
        if train_groups & valid_groups:
            raise AssertionError("GroupKFold lineage leakage")
        weights = _weights(train)
        x_train, y_train, w_train = _matrix(train, names, weights)
        artifact_weight_totals = [float(weights[item["artifact_sha256"]].sum()) for item in train]
        parent_weight_totals = {
            parent: float(sum(weights[item["artifact_sha256"]].sum() for item in train if item["parent_lineage_id"] == parent))
            for parent in sorted(train_groups)
        }
        class_weight_totals = {
            "negative_layers": float(sum(weights[item["artifact_sha256"]][np.asarray(item["layer_labels"]) == 0].sum() for item in train)),
            "modified_positive_layers": float(sum(weights[item["artifact_sha256"]][np.asarray(item["layer_labels"]) == 1].sum() for item in train)),
        }
        model = lgb.LGBMClassifier(**LGB_PARAMS, n_estimators=120)
        # Column order is the persisted canonical ``names`` list; leave the
        # sklearn wrapper unnamed because validation is an ndarray as well.
        model.fit(x_train, y_train, sample_weight=w_train)
        for item in validation:
            x_valid = np.asarray([[row[name] for name in names] for row in item["b1_rows"]], dtype=np.float64)
            probabilities = model.predict_proba(x_valid)[:, 1]
            p_tamper, evidence_index = aggregate_p_tamper(probabilities)
            scores[item["artifact_sha256"]] = p_tamper
            ordered_probabilities = np.sort(probabilities)
            oof_artifacts.append({
                "artifact_sha256": item["artifact_sha256"], "source_model_id": item["source_model_id"],
                "parent_lineage_id": item["parent_lineage_id"], "attack_family": item["attack_family"],
                "attack_strength": item["attack_strength"], "label": item["label"], "p_tamper": p_tamper,
                "max_layer_name": item["b1_rows"][evidence_index]["layer_name"],
                "second_highest_layer_probability": float(ordered_probabilities[-2]),
                "median_layer_probability": float(np.median(probabilities)),
            })
            layer_y.extend(item["layer_labels"])
            layer_p.extend(probabilities.tolist())
        fold_records.append({"fold": fold, "train_parent_lineages": sorted(train_groups),
                             "validation_parent_lineages": sorted(valid_groups),
                             "training_artifacts": len(train), "validation_artifacts": len(validation),
                             "weighting": {"parent_totals": parent_weight_totals, "class_totals": class_weight_totals,
                                           "artifact_total_weight_min": min(artifact_weight_totals),
                                           "artifact_total_weight_max": max(artifact_weight_totals)},
                             "metrics": _metrics(validation, scores)})
    overall = _metrics([item for item in subset if item["primary_evaluation"]], scores)
    overall["fold_pr_auc"] = [fold["metrics"]["pr_auc"] for fold in fold_records]
    overall["fold_pr_auc_std"] = float(np.std(overall["fold_pr_auc"], ddof=0))
    return {"metrics": overall, "folds": fold_records, "oof_artifacts": oof_artifacts,
            "layer_metrics": _binary_metrics(np.asarray(layer_y, dtype=np.int8), np.asarray(layer_p, dtype=np.float64))}


def _tail_mass_evaluate(subset: list[dict], names: list[str]) -> dict:
    """Evaluate fixed q95 training-clean tail mass against unchanged max OOF scores."""
    if set(names) - set(B1_FEATURE_NAMES) or {"modified_tensors", "attack_family", "attack_strength"} & set(names):
        raise AssertionError("Tail experiment classifier inputs must be canonical B0/B1 features only")
    lineages = sorted({item["parent_lineage_id"] for item in subset})
    groups = np.asarray([item["parent_lineage_id"] for item in subset])
    indices = np.arange(len(subset))
    folds = GroupKFold(n_splits=min(3, len(lineages)))
    max_scores: dict[str, float] = {}
    tail_scores: dict[str, float] = {}
    oof = []
    fold_records = []
    for fold, (train_idx, valid_idx) in enumerate(folds.split(indices, groups=groups)):
        training = [subset[i] for i in train_idx]
        validation_all = [subset[i] for i in valid_idx]
        validation = [item for item in validation_all if item["primary_evaluation"]]
        training_lineages = {item["parent_lineage_id"] for item in training}
        validation_lineages = {item["parent_lineage_id"] for item in validation_all}
        if training_lineages & validation_lineages:
            raise AssertionError("GroupKFold lineage leakage")
        weights = _weights(training)
        x_train, y_train, w_train = _matrix(training, names, weights)
        model = lgb.LGBMClassifier(**LGB_PARAMS, n_estimators=120)
        model.fit(x_train, y_train, sample_weight=w_train)
        tau = _training_clean_tau(model, training, names, validation_lineages)
        fold_oof = []
        for item in validation:
            if item["partition"] != "DEVELOPMENT" or item["attack_family"] == "S4":
                raise AssertionError("Sealed or S4 artifact entered tail validation")
            x_valid = np.asarray([[row[name] for name in names] for row in item["b1_rows"]], dtype=np.float64)
            probabilities = model.predict_proba(x_valid)[:, 1]
            max_score, _ = aggregate_p_tamper(probabilities)
            tail_score = tail_mass(probabilities, tau)
            max_scores[item["artifact_sha256"]] = max_score
            tail_scores[item["artifact_sha256"]] = tail_score
            record = {"artifact_sha256": item["artifact_sha256"], "parent_lineage_id": item["parent_lineage_id"],
                      "attack_family": item["attack_family"], "attack_strength": item["attack_strength"],
                      "label": item["label"], "max": max_score, "tail_mass": tail_score}
            oof.append(record)
            fold_oof.append(record)
        fold_records.append({"fold": fold, "training_parent_lineages": sorted(training_lineages),
                             "validation_parent_lineages": sorted(validation_lineages), "tau_q95": tau,
                             "tail_mass_metrics": _ranking_metrics(validation, tail_scores),
                             "microsoft_in_validation": any("microsoft" in lineage.lower() for lineage in validation_lineages)})
    primary = [item for item in subset if item["primary_evaluation"]]
    if len(max_scores) != len(primary) or len(tail_scores) != len(primary):
        raise AssertionError("OOF score coverage is incomplete")
    def pair_metrics(selector):
        chosen = [item for item in primary if selector(item)]
        return _ranking_metrics(chosen, tail_scores)
    family = {}
    for value in ("S1", "S2", "S3"):
        chosen = [item for item in primary if item["attack_family"] in {"CLEAN", value}]
        family[value] = {"metrics": _ranking_metrics(chosen, tail_scores),
                         "clean_distribution": _distribution([tail_scores[x["artifact_sha256"]] for x in chosen if x["attack_family"] == "CLEAN"]),
                         "attack_distribution": _distribution([tail_scores[x["artifact_sha256"]] for x in chosen if x["attack_family"] == value])}
    strength = {}
    for value in (0.005, 0.01, 0.02, 0.05):
        chosen = [item for item in primary if item["attack_family"] == "CLEAN" or item["attack_strength"] == value]
        strength[f"{value:g}"] = _ranking_metrics(chosen, tail_scores)
    tail_rocs = [fold["tail_mass_metrics"]["roc_auc"] for fold in fold_records]
    return {"max": _ranking_metrics(primary, max_scores), "tail_mass": _ranking_metrics(primary, tail_scores),
            "family": family, "strength": strength, "folds": fold_records,
            "fold_roc_auc_mean": float(np.mean(tail_rocs)), "fold_roc_auc_std": float(np.std(tail_rocs, ddof=0)), "oof": oof}


def run_tail_mass_experiment() -> dict:
    """One preregistered q95 tail-mass aggregation experiment; production max is untouched."""
    rows, features, split, feature_sha, split_sha, attack_sha = _load()
    subsets = _nested_lineages(rows)
    subset = max(subsets, key=len)
    if set(subset) != {item["parent_lineage_id"] for item in rows}:
        raise AssertionError("Tail experiment must cover all development lineages only")
    b0 = _tail_mass_evaluate(rows, B0_FEATURE_NAMES)
    b1 = _tail_mass_evaluate(rows, B1_FEATURE_NAMES)
    memberships_b0 = [(x["training_parent_lineages"], x["validation_parent_lineages"]) for x in b0["folds"]]
    memberships_b1 = [(x["training_parent_lineages"], x["validation_parent_lineages"]) for x in b1["folds"]]
    if memberships_b0 != memberships_b1:
        raise AssertionError("B0/B1 fold membership differs")
    payload = {"version": "p2-tail-mass-q95-v1", "tail_percentile": TAIL_PERCENTILE,
               "tail_mass_definition": "mean(p_l >= Q95(training-clean layer probabilities))", "seed": SEED,
               "lightgbm_params": LGB_PARAMS, "b0": b0, "b1": b1,
               "feature_implementation_fingerprint": features["extractor_implementation_fingerprint"],
               "feature_manifest_sha256": feature_sha, "split_manifest_sha256": split_sha,
               "attack_manifest_sha256": attack_sha, "development_parent_lineages": split["development_parent_lineages"]}
    (METADATA / "tail_mass_experiment.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def run(smoke: bool = False) -> dict:
    rows, features, split, feature_sha, split_sha, attack_sha = _load()
    subsets = _nested_lineages(rows)
    if smoke:
        subsets = subsets[:1]
    points = []
    for lineages in subsets:
        subset = [item for item in rows if item["parent_lineage_id"] in lineages]
        point = {"parent_lineages": lineages, "parent_lineage_count": len(lineages),
                 "clean_source_population_count": len({x["source_model_id"] for x in subset}),
                 "artifact_count": len(subset), "primary_validation_artifact_count": sum(x["primary_evaluation"] for x in subset),
                 "B0": _evaluate(subset, B0_FEATURE_NAMES), "B1": _evaluate(subset, B1_FEATURE_NAMES)}
        points.append(point)
    payload = {"version": "p2-learning-curve-v2-corrected-layer-labels", "seed": SEED, "threshold": THRESHOLD,
               "lightgbm_params": LGB_PARAMS,
               "layer_supervision": "clean=0; synthetic modified_tensors=1; synthetic unmodified_tensors=0",
               "weighting_policy": "1/(P * sources_in_parent * 2 * artifacts_with_layer_class_for_parent_source * layers_of_class_in_artifact)",
               "b0_feature_order": B0_FEATURE_NAMES, "b1_feature_order": B1_FEATURE_NAMES,
               "feature_implementation_fingerprint": features["extractor_implementation_fingerprint"],
               "feature_manifest_sha256": feature_sha, "split_manifest_sha256": split_sha, "attack_manifest_sha256": attack_sha,
               "development_parent_lineages": split["development_parent_lineages"], "points": points}
    (METADATA / ("learning_curve_smoke_corrected_labels.json" if smoke else "learning_curve_corrected_labels.json")).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--tail-mass-experiment", action="store_true")
    args = parser.parse_args()
    if args.tail_mass_experiment:
        result = run_tail_mass_experiment()
        print(json.dumps({"output": "tail_mass_experiment.json", "b0_tail_roc_auc": result["b0"]["tail_mass"]["roc_auc"],
                          "b1_tail_roc_auc": result["b1"]["tail_mass"]["roc_auc"]}))
    else:
        result = run(args.smoke)
        print(json.dumps({"points": len(result["points"]), "output": "learning_curve_smoke_corrected_labels.json" if args.smoke else "learning_curve_corrected_labels.json"}))
