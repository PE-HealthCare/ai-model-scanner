"""Prompt-2 Steps 4--9: development-only static model-level evaluations."""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time

import lightgbm as lgb
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.common.feature_names import B1_FEATURE_NAMES
from src.p3_ml_dashboard.global_bitplane_features import (
    GLOBAL_BITPLANE_FEATURE_NAMES,
    extract_global_bitplane_from_safetensors,
)

METADATA = ROOT / "data" / "training" / "metadata"
GLOBAL_OUT = METADATA / "global_bitplane_development.json"
PILOT = METADATA / "global_bitplane_pilot.json"
FIXED_PARAMS = {"objective": "binary", "num_leaves": 7, "max_depth": 3,
                "min_child_samples": 2, "learning_rate": 0.05, "n_estimators": 120,
                "lambda_l2": 1.0, "feature_fraction": 1.0, "bagging_fraction": 1.0,
                "bagging_freq": 0, "max_bin": 63, "seed": 20260929, "n_jobs": 1,
                "verbosity": -1, "deterministic": True}
FAMILIES = ("S1", "S2", "S3")
STRENGTHS = (0.005, 0.01, 0.02, 0.05)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _write(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _compute_global(path_text: str, expected_sha: str) -> dict:
    """Worker-only extraction; shared manifest persistence stays in parent."""
    path = Path(path_text)
    if _sha(path) != expected_sha:
        raise AssertionError(f"Artifact SHA mismatch: {path}")
    result = extract_global_bitplane_from_safetensors(path)
    result["artifact_sha256"] = expected_sha
    return result


def _targets() -> list[dict]:
    """Select exactly development clean + primary S1/S2/S3 records by SHA."""
    sources = json.loads((METADATA / "source_manifest.json").read_text(encoding="utf-8"))
    split = json.loads((METADATA / "split_manifest.json").read_text(encoding="utf-8"))
    attacks = json.loads((METADATA / "attack_manifest.json").read_text(encoding="utf-8"))
    development = set(split["development_parent_lineages"])
    final = set(split["final_test_parent_lineages"])
    if development & final:
        raise AssertionError("Split has parent-lineage overlap")
    rows = []
    for item in sources["records"]:
        if not item.get("accepted") or item["parent_lineage_id"] not in development:
            continue
        path = ROOT / item["file"]
        rows.append({"file": str(path.relative_to(ROOT)), "artifact_sha256": item["file_sha256"],
                     "source_model_id": item["source_model_id"], "parent_lineage_id": item["parent_lineage_id"],
                     "partition": "DEVELOPMENT", "attack_family": "CLEAN", "attack_strength": None,
                     "seed": None, "label": 0})
    primary: set[tuple[str, str, float]] = set()
    for item in attacks["artifacts"]:
        if item["partition"] != "DEVELOPMENT" or item["attack_family"] not in FAMILIES:
            continue
        if item["parent_lineage_id"] not in development:
            raise AssertionError("Final lineage in development attack record")
        key = (item["source_model_id"], item["attack_family"], item["attack_strength"])
        if key in primary:  # second-location augmentation seed
            continue
        primary.add(key)
        rows.append({"file": item["file"], "artifact_sha256": item["derivative_sha256"],
                     "source_model_id": item["source_model_id"], "parent_lineage_id": item["parent_lineage_id"],
                     "partition": item["partition"], "attack_family": item["attack_family"],
                     "attack_strength": item["attack_strength"], "seed": item["seed"], "label": 1,
                     "clean_parent_sha256": item["clean_parent_sha256"]})
    expected = 13 + len(FAMILIES) * len(STRENGTHS) * 13
    if len(rows) != expected or len({x["artifact_sha256"] for x in rows}) != expected:
        raise AssertionError(f"Expected exactly {expected} development primary artifacts, got {len(rows)}")
    if any(x["partition"] != "DEVELOPMENT" or x["attack_family"] == "S4" for x in rows):
        raise AssertionError("Final-test or S4 entered targets")
    return sorted(rows, key=lambda x: (x["attack_family"], x["attack_strength"] is not None, x["attack_strength"] or 0.0, x["source_model_id"]))


def extract_global_development() -> dict:
    """Resumable Step-4 extraction, with pilot cache validated by SHA."""
    started = time.perf_counter()
    targets = _targets()
    prior = json.loads(GLOBAL_OUT.read_text(encoding="utf-8")) if GLOBAL_OUT.exists() else {"records": []}
    cached = {x["artifact_sha256"]: x for x in prior.get("records", [])}
    # Pilot entries lack a persisted SHA, so fingerprint their actual paths once.
    if PILOT.exists():
        for item in json.loads(PILOT.read_text(encoding="utf-8"))["records"]:
            path = ROOT / item["artifact_path"]
            if path.exists():
                cached.setdefault(_sha(path), {"artifact_sha256": _sha(path), "features": item["features"],
                                                "feature_names": item["feature_names"], "fp32_tensor_count": None,
                                                "fp32_element_count": None, "skipped_non_fp32_tensor_count": None})
    completed, pending, hits, invalid = {}, [], 0, 0
    for target in targets:
        cached_item = cached.get(target["artifact_sha256"])
        path = ROOT / target["file"]
        valid = (cached_item is not None and cached_item.get("artifact_sha256") == target["artifact_sha256"]
                 and tuple(cached_item.get("feature_names", [])) == GLOBAL_BITPLANE_FEATURE_NAMES
                 and len(cached_item.get("features", {})) == 92
                 and np.all(np.isfinite(np.asarray(list(cached_item.get("features", {}).values()), dtype=np.float64)))
                 and _sha(path) == target["artifact_sha256"])
        if valid:
            completed[target["artifact_sha256"]] = cached_item
            hits += 1
        else:
            if cached_item is not None:
                invalid += 1
            pending.append(target)
    def persist():
        records = [{**target, **{k: completed[target["artifact_sha256"]][k] for k in ("artifact_sha256", "feature_names", "features", "fp32_tensor_count", "fp32_element_count", "skipped_non_fp32_tensor_count")}}
                   for target in targets if target["artifact_sha256"] in completed]
        payload = {"version": "p2-global-bitplane-development-v1", "representation": "GLOBAL_BITPLANE_92_V1",
                   "feature_names": list(GLOBAL_BITPLANE_FEATURE_NAMES), "records": records,
                   "complete": False, "cache_hits": hits, "newly_extracted": len(completed) - hits,
                   "invalid_cache_recomputed": invalid}
        _write(GLOBAL_OUT, payload)
        return records, payload
    records, payload = persist()
    with ProcessPoolExecutor(max_workers=1) as pool:
        futures = {pool.submit(_compute_global, str(ROOT / target["file"]), target["artifact_sha256"]): target for target in pending}
        for future in as_completed(futures):
            target = futures[future]; result = future.result()
            if tuple(result["feature_names"]) != GLOBAL_BITPLANE_FEATURE_NAMES or len(result["features"]) != 92:
                raise AssertionError("Global feature contract mismatch")
            completed[target["artifact_sha256"]] = result
            records, payload = persist()
    counts = Counter(x["attack_family"] for x in records)
    by_strength = Counter(str(x["attack_strength"]) for x in records if x["attack_strength"] is not None)
    payload.update({"complete": True, "artifact_count": len(records), "counts": dict(counts),
                    "counts_by_strength": dict(by_strength), "lineage_count": len({x["parent_lineage_id"] for x in records}),
                    "cache_hits": hits, "newly_extracted": len(completed) - hits, "invalid_cache_recomputed": invalid,
                    "runtime_seconds": time.perf_counter() - started})
    _write(GLOBAL_OUT, payload)
    return payload


def _metrics(records: list[dict], scores: dict[str, float]) -> dict:
    y = np.asarray([x["label"] for x in records], dtype=np.int8)
    p = np.asarray([scores[x["artifact_sha256"]] for x in records], dtype=np.float64)
    if not np.all(np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise AssertionError("Invalid artifact score")
    if not (np.any(y == 0) and np.any(y == 1)):
        raise ValueError("Both artifact classes required")
    ap = float(average_precision_score(y, p)); baseline = float(y.mean())
    return {"artifact_count": int(y.size), "roc_auc": float(roc_auc_score(y, p)), "pr_auc": ap,
            "pr_auc_baseline": baseline, "normalized_pr_auc": float((ap - baseline) / (1 - baseline)),
            "score_distribution_clean": _distribution(p[y == 0]), "score_distribution_tampered": _distribution(p[y == 1])}


def _distribution(values: np.ndarray) -> dict:
    return {"n": int(values.size), "min": float(values.min()), "q25": float(np.quantile(values, .25)),
            "median": float(np.median(values)), "q75": float(np.quantile(values, .75)),
            "max": float(values.max()), "mean": float(values.mean())}


def evaluate_artifact_features(records: list[dict], feature_names: list[str]) -> dict:
    """Fixed Step-5 grouped-CV model-level LightGBM evaluation."""
    if any(set(x["features"]) != set(feature_names) for x in records):
        raise AssertionError("Unexpected artifact feature names")
    if len(feature_names) not in (92, 168):
        raise AssertionError("Only authorized model-level representations are allowed")
    groups = np.asarray([x["parent_lineage_id"] for x in records])
    folds = GroupKFold(n_splits=3); scores = {}; fold_rows = []
    index = np.arange(len(records))
    for fold, (tr, va) in enumerate(folds.split(index, groups=groups)):
        train, valid = [records[i] for i in tr], [records[i] for i in va]
        train_parents, valid_parents = {x["parent_lineage_id"] for x in train}, {x["parent_lineage_id"] for x in valid}
        if train_parents & valid_parents:
            raise AssertionError("Parent-lineage leakage")
        x_train = np.asarray([[x["features"][name] for name in feature_names] for x in train], dtype=np.float64)
        y_train = np.asarray([x["label"] for x in train], dtype=np.int8)
        x_valid = np.asarray([[x["features"][name] for name in feature_names] for x in valid], dtype=np.float64)
        model = lgb.LGBMClassifier(**FIXED_PARAMS).fit(x_train, y_train)
        probability = model.predict_proba(x_valid)[:, 1]
        scores.update({item["artifact_sha256"]: float(p) for item, p in zip(valid, probability)})
        fold_rows.append({"fold": fold, "validation_parent_lineages": sorted(valid_parents), "metrics": _metrics(valid, scores)})
    family = {}; tier = {}
    for name in FAMILIES:
        family[name] = _metrics([x for x in records if x["attack_family"] in {"CLEAN", name}], scores)
        for strength in STRENGTHS:
            tier[f"{name}_{strength:g}"] = _metrics([x for x in records if x["attack_family"] == "CLEAN" or (x["attack_family"] == name and x["attack_strength"] == strength)], scores)
    return {"fixed_lightgbm": FIXED_PARAMS, "overall": _metrics(records, scores), "folds": fold_rows,
            "family": family, "family_tier": tier}


def model_relative_b1_records(targets: list[dict]) -> tuple[list[dict], list[str]]:
    manifest = json.loads((METADATA / "feature_manifest.json").read_text(encoding="utf-8"))
    cached = {x["artifact_sha256"]: x for x in manifest["feature_rows"]}
    suffixes = ("max_abs_z", "q99_abs_z", "q95_abs_z", "mean_top5_abs_z", "fraction_abs_z_gt_3", "fraction_abs_z_gt_5")
    names = [f"{feature}__{suffix}" for feature in B1_FEATURE_NAMES for suffix in suffixes]
    output = []
    for target in targets:
        item = cached.get(target["artifact_sha256"])
        if item is None or item["partition"] != "DEVELOPMENT" or item["attack_family"] != target["attack_family"]:
            raise AssertionError("Missing or incompatible cached B1 artifact")
        matrix = np.asarray([[row[name] for name in B1_FEATURE_NAMES] for row in item["b1_rows"]], dtype=np.float64)
        if not np.all(np.isfinite(matrix)):
            raise AssertionError("Non-finite B1 cache")
        median = np.median(matrix, axis=0); mad = np.median(np.abs(matrix - median), axis=0)
        scale = 1.4826 * mad; std = np.std(matrix, axis=0)
        scale = np.where(scale == 0.0, std, scale); scale = np.where(scale == 0.0, 1.0, scale)
        z = np.abs((matrix - median) / scale)
        features = {}
        for i, feature in enumerate(B1_FEATURE_NAMES):
            values = z[:, i]; top = np.sort(values)[-min(5, values.size):]
            features.update({f"{feature}__max_abs_z": float(values.max()), f"{feature}__q99_abs_z": float(np.quantile(values, .99)),
                             f"{feature}__q95_abs_z": float(np.quantile(values, .95)), f"{feature}__mean_top5_abs_z": float(top.mean()),
                             f"{feature}__fraction_abs_z_gt_3": float(np.mean(values > 3.0)), f"{feature}__fraction_abs_z_gt_5": float(np.mean(values > 5.0))})
        if len(features) != 168 or not np.all(np.isfinite(list(features.values()))):
            raise AssertionError("Invalid 168-feature model-relative B1 vector")
        output.append({**target, "features": features})
    return output, names


def decision(metrics: dict, keep: str, middle: str, stop: str) -> str:
    rocs = [x["metrics"]["roc_auc"] for x in metrics["folds"]]
    if metrics["overall"]["roc_auc"] >= .80 and all(x >= .70 for x in rocs): return keep
    if metrics["overall"]["roc_auc"] >= .65: return middle
    return stop


def run() -> dict:
    global_data = extract_global_development()
    global_eval = evaluate_artifact_features(global_data["records"], list(GLOBAL_BITPLANE_FEATURE_NAMES))
    global_decision = decision(global_eval, "KEEP_GLOBAL_92", "GLOBAL_SIGNAL_PRESENT_BUT_INSUFFICIENT", "STOP_GLOBAL_92")
    result = {"step4": global_data, "step5_6_7": global_eval, "step8": global_decision}
    if global_decision != "KEEP_GLOBAL_92":
        relative_records, relative_names = model_relative_b1_records(global_data["records"])
        relative_eval = evaluate_artifact_features(relative_records, relative_names)
        result["step9"] = {"representation": "MODEL_RELATIVE_B1_168_V1", "feature_names": relative_names,
                           "evaluation": relative_eval,
                           "decision": decision(relative_eval, "KEEP_MODEL_RELATIVE_B1", "MODEL_RELATIVE_SIGNAL_PRESENT_BUT_INSUFFICIENT", "STOP_STATIC_MODEL_LEVEL_ML")}
    _write(METADATA / "static_model_level_results.json", result)
    return result


if __name__ == "__main__":
    result = extract_global_development()
    print(json.dumps({"step4": result["artifact_count"], "complete": result["complete"]}))
