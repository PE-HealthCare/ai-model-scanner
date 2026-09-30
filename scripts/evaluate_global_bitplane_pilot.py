from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
)
from sklearn.model_selection import GroupKFold


INPUT = Path("data/training/metadata/global_bitplane_pilot.json")
OUTPUT = Path("data/training/metadata/global_bitplane_pilot_eval.json")

SEED = 20260929

# One fixed configuration only.
# Reuse the already-selected bounded C09 settings.
MODEL_PARAMS = {
    "objective": "binary",
    "num_leaves": 15,
    "max_depth": 5,
    "min_child_samples": 20,
    "learning_rate": 0.03,
    "n_estimators": 200,
    "lambda_l1": 0.0,
    "lambda_l2": 0.1,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "random_state": SEED,
    "n_jobs": 1,
    "verbosity": -1,
}


obj = json.loads(INPUT.read_text(encoding="utf-8"))
records = obj["records"]

if len(records) != 48:
    raise RuntimeError(f"Expected 48 pilot artifacts, got {len(records)}")

feature_names = records[0]["feature_names"]

if len(feature_names) != 92:
    raise RuntimeError(f"Expected 92 features, got {len(feature_names)}")

for r in records:
    if r["feature_names"] != feature_names:
        raise RuntimeError("Feature order mismatch in pilot file")

X = np.asarray(
    [
        [r["features"][name] for name in feature_names]
        for r in records
    ],
    dtype=np.float64,
)

y = np.asarray([int(r["label"]) for r in records], dtype=np.int64)
groups = np.asarray([r["parent_lineage_id"] for r in records], dtype=object)
sources = np.asarray([r["source_model_id"] for r in records], dtype=object)
families = np.asarray([r["family"] for r in records], dtype=object)

assert X.shape == (48, 92)
assert np.all(np.isfinite(X))
assert set(np.unique(y)) == {0, 1}

print("=== PILOT DATA ===")
print(f"artifacts={len(y)}")
print(f"clean={(y == 0).sum()}")
print(f"tampered={(y == 1).sum()}")
print(f"parent_lineages={len(set(groups))}")
print(f"sources={len(set(sources))}")
print(f"positive_prevalence={y.mean():.6f}")
print(f"PR_no_skill_baseline={y.mean():.6f}")


def training_weights(train_idx):
    """
    Equal total influence by:
      parent lineage
      -> source within parent
      -> CLEAN/TAMPERED class within source
      -> artifact within source/class

    Prevents derivative count from dominating training.
    """
    idx = np.asarray(train_idx)
    w = np.zeros(len(idx), dtype=np.float64)

    train_groups = groups[idx]
    train_sources = sources[idx]
    train_y = y[idx]

    parent_values = sorted(set(train_groups))
    P = len(parent_values)

    for parent in parent_values:
        parent_mask = train_groups == parent
        parent_sources = sorted(set(train_sources[parent_mask]))
        S = len(parent_sources)

        for source in parent_sources:
            source_mask = parent_mask & (train_sources == source)

            for cls in (0, 1):
                class_mask = source_mask & (train_y == cls)
                positions = np.flatnonzero(class_mask)

                if len(positions) == 0:
                    continue

                per_row = 1.0 / (
                    P
                    * S
                    * 2
                    * len(positions)
                )

                w[positions] = per_row

    if np.any(w <= 0):
        raise RuntimeError("One or more training rows received zero weight")

    return w


gkf = GroupKFold(n_splits=3)
oof = np.full(len(y), np.nan, dtype=np.float64)

fold_results = []

print("\n=== GROUPED OOF ===")

for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups)):
    train_groups = set(groups[train_idx])
    val_groups = set(groups[val_idx])

    overlap = train_groups & val_groups
    if overlap:
        raise RuntimeError(f"Lineage leakage in fold {fold}: {overlap}")

    weights = training_weights(train_idx)

    model = LGBMClassifier(**MODEL_PARAMS)

    model.fit(
        X[train_idx],
        y[train_idx],
        sample_weight=weights,
    )

    scores = model.predict_proba(X[val_idx])[:, 1]
    oof[val_idx] = scores

    fold_auc = roc_auc_score(y[val_idx], scores)
    fold_pr = average_precision_score(y[val_idx], scores)

    result = {
        "fold": fold,
        "held_out_lineages": sorted(val_groups),
        "n_validation": len(val_idx),
        "clean_validation": int((y[val_idx] == 0).sum()),
        "tampered_validation": int((y[val_idx] == 1).sum()),
        "roc_auc": float(fold_auc),
        "pr_auc": float(fold_pr),
    }
    fold_results.append(result)

    print(f"\nFold {fold}")
    print(f"  held_out_lineages={sorted(val_groups)}")
    print(
        f"  validation={len(val_idx)} "
        f"(clean={(y[val_idx] == 0).sum()}, "
        f"tampered={(y[val_idx] == 1).sum()})"
    )
    print(f"  ROC-AUC={fold_auc:.6f}")
    print(f"  PR-AUC ={fold_pr:.6f}")


if np.isnan(oof).any():
    raise RuntimeError("Incomplete OOF predictions")


pooled_roc = roc_auc_score(y, oof)
pooled_pr = average_precision_score(y, oof)
prevalence = float(y.mean())

normalized_pr = (
    (pooled_pr - prevalence) / (1.0 - prevalence)
    if prevalence < 1.0
    else float("nan")
)

print("\n=== POOLED MODEL-LEVEL RESULT ===")
print(f"ROC-AUC={pooled_roc:.6f}")
print(f"PR-AUC={pooled_pr:.6f}")
print(f"PR-baseline={prevalence:.6f}")
print(f"normalized-PR-AUC={normalized_pr:.6f}")

print("\n=== SCORE DISTRIBUTIONS ===")

def summarize(mask):
    a = oof[mask]
    return {
        "n": int(len(a)),
        "min": float(np.min(a)),
        "q25": float(np.quantile(a, 0.25)),
        "median": float(np.median(a)),
        "q75": float(np.quantile(a, 0.75)),
        "max": float(np.max(a)),
        "mean": float(np.mean(a)),
    }

distribution_results = {}

for family in ("CLEAN", "S1", "S2", "S3"):
    mask = families == family
    s = summarize(mask)
    distribution_results[family] = s

    print(
        f"{family:5s} "
        f"n={s['n']:2d} "
        f"min={s['min']:.6f} "
        f"q25={s['q25']:.6f} "
        f"median={s['median']:.6f} "
        f"q75={s['q75']:.6f} "
        f"max={s['max']:.6f} "
        f"mean={s['mean']:.6f}"
    )


print("\n=== FAMILY ROC-AUC ===")
family_auc = {}

clean_mask = families == "CLEAN"

for family in ("S1", "S2", "S3"):
    attack_mask = families == family
    mask = clean_mask | attack_mask

    yy = (families[mask] != "CLEAN").astype(np.int64)
    ss = oof[mask]

    auc = roc_auc_score(yy, ss)
    family_auc[family] = float(auc)

    print(f"{family} vs CLEAN: ROC-AUC={auc:.6f}")


fold_rocs = np.asarray(
    [r["roc_auc"] for r in fold_results],
    dtype=np.float64,
)

print("\n=== STABILITY ===")
print(f"fold_ROC_mean={fold_rocs.mean():.6f}")
print(f"fold_ROC_std={fold_rocs.std():.6f}")
print(f"fold_ROC_min={fold_rocs.min():.6f}")
print(f"fold_ROC_max={fold_rocs.max():.6f}")


print("\n=== PILOT DECISION ===")

# This is NOT a final production threshold.
# It is just the frozen Phase-2 representation gate.
passes_gate = (
    pooled_roc >= 0.80
    and fold_rocs.min() >= 0.70
)

if passes_gate:
    decision = "KEEP_GLOBAL_BITPLANE_92"
    print("KEEP_GLOBAL_BITPLANE_92")
    print(
        "The representation passes the frozen development "
        "ranking gate on the hardest 0.5% pilot."
    )
else:
    decision = "DO_NOT_EXPAND_GLOBAL_BITPLANE_92_YET"
    print("DO_NOT_EXPAND_GLOBAL_BITPLANE_92_YET")
    print(
        "The representation does not yet pass the frozen "
        "development ranking gate."
    )


OUTPUT.write_text(
    json.dumps(
        {
            "representation": "GLOBAL_BITPLANE_92_V1",
            "model_params": MODEL_PARAMS,
            "artifact_count": len(y),
            "positive_prevalence": prevalence,
            "pooled_roc_auc": float(pooled_roc),
            "pooled_pr_auc": float(pooled_pr),
            "normalized_pr_auc": float(normalized_pr),
            "folds": fold_results,
            "family_roc_auc": family_auc,
            "score_distributions": distribution_results,
            "decision": decision,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(f"\nsaved={OUTPUT}")
