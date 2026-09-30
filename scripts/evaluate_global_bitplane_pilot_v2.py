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
OUTPUT = Path("data/training/metadata/global_bitplane_pilot_eval_v2.json")

SEED = 20260929


# ============================================================
# ONE FIXED SMALL-SAMPLE CONFIGURATION
# ============================================================
#
# This is NOT a search.
#
# The previous C09 config had min_child_samples=20, which is
# inappropriate for folds containing only ~24-36 artifact rows.
#
# This configuration is intentionally shallow and conservative.
#
MODEL_PARAMS = {
    "objective": "binary",
    "num_leaves": 7,
    "max_depth": 3,
    "min_child_samples": 2,
    "min_split_gain": 0.0,
    "learning_rate": 0.05,
    "n_estimators": 120,
    "lambda_l1": 0.0,
    "lambda_l2": 1.0,
    "feature_fraction": 1.0,
    "bagging_fraction": 1.0,
    "bagging_freq": 0,
    "max_bin": 63,
    "random_state": SEED,
    "n_jobs": 1,
    "verbosity": -1,
}


# ============================================================
# LOAD PILOT
# ============================================================

obj = json.loads(INPUT.read_text(encoding="utf-8"))
records = obj["records"]

feature_names = records[0]["feature_names"]

X = np.asarray(
    [
        [r["features"][name] for name in feature_names]
        for r in records
    ],
    dtype=np.float64,
)

y = np.asarray(
    [int(r["label"]) for r in records],
    dtype=np.int64,
)

groups = np.asarray(
    [r["parent_lineage_id"] for r in records],
    dtype=object,
)

sources = np.asarray(
    [r["source_model_id"] for r in records],
    dtype=object,
)

families = np.asarray(
    [r["family"] for r in records],
    dtype=object,
)


assert X.shape == (48, 92)
assert np.all(np.isfinite(X))
assert set(np.unique(y)) == {0, 1}


print("============================================================")
print("GLOBAL BIT-PLANE PILOT V2")
print("============================================================")

print("\n=== DATA ===")
print(f"artifacts={len(y)}")
print(f"clean={(y == 0).sum()}")
print(f"tampered={(y == 1).sum()}")
print(f"parent_lineages={len(set(groups))}")
print(f"sources={len(set(sources))}")
print(f"features={X.shape[1]}")


# ============================================================
# FEATURE SANITY
# ============================================================

print("\n=== FEATURE SANITY ===")

variances = np.var(X, axis=0)

nonconstant = variances > 0

print(f"nonconstant_features={int(nonconstant.sum())}/92")
print(f"constant_features={int((~nonconstant).sum())}/92")

unique_rows = np.unique(X, axis=0).shape[0]
print(f"unique_feature_vectors={unique_rows}/48")

top_var_idx = np.argsort(variances)[::-1][:10]

print("\nTop feature variances:")

for i in top_var_idx:
    print(
        f"  {feature_names[i]:40s} "
        f"variance={variances[i]:.6e}"
    )


# Check paired clean-vs-attack distances.
print("\n=== PAIRED SOURCE DISTANCES ===")

for family in ("S1", "S2", "S3"):
    distances = []

    for source in sorted(set(sources)):
        clean_idx = np.flatnonzero(
            (sources == source)
            & (families == "CLEAN")
        )

        attack_idx = np.flatnonzero(
            (sources == source)
            & (families == family)
        )

        if len(clean_idx) != 1 or len(attack_idx) != 1:
            continue

        diff = X[attack_idx[0]] - X[clean_idx[0]]
        distances.append(float(np.linalg.norm(diff)))

    if distances:
        print(
            f"{family}: "
            f"n={len(distances)} "
            f"min={np.min(distances):.6f} "
            f"median={np.median(distances):.6f} "
            f"max={np.max(distances):.6f}"
        )


# ============================================================
# TRAINING WEIGHTS
# ============================================================

def training_weights(train_idx):
    """
    Equalize influence across:
      parent lineage
        -> source
          -> class
            -> artifact

    This avoids attack derivatives dominating clean artifacts.
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

        parent_sources = sorted(
            set(train_sources[parent_mask])
        )

        S = len(parent_sources)

        for source in parent_sources:
            source_mask = (
                parent_mask
                & (train_sources == source)
            )

            for cls in (0, 1):
                class_mask = (
                    source_mask
                    & (train_y == cls)
                )

                pos = np.flatnonzero(class_mask)

                if not len(pos):
                    continue

                w[pos] = (
                    1.0
                    / P
                    / S
                    / 2.0
                    / len(pos)
                )

    if np.any(w <= 0):
        raise RuntimeError(
            "Zero training weight encountered"
        )

    return w


# ============================================================
# GROUPED OOF
# ============================================================

gkf = GroupKFold(n_splits=3)

oof = np.full(
    len(y),
    np.nan,
    dtype=np.float64,
)

fold_results = []


print("\n=== GROUPED OOF ===")


for fold, (train_idx, val_idx) in enumerate(
    gkf.split(X, y, groups)
):

    train_groups = set(groups[train_idx])
    val_groups = set(groups[val_idx])

    if train_groups & val_groups:
        raise RuntimeError(
            f"Lineage leakage in fold {fold}"
        )

    if len(np.unique(y[train_idx])) != 2:
        raise RuntimeError(
            f"Fold {fold} training lacks both classes"
        )

    if len(np.unique(y[val_idx])) != 2:
        raise RuntimeError(
            f"Fold {fold} validation lacks both classes"
        )

    weights = training_weights(train_idx)

    model = LGBMClassifier(**MODEL_PARAMS)

    model.fit(
        X[train_idx],
        y[train_idx],
        sample_weight=weights,
    )

    scores = model.predict_proba(
        X[val_idx]
    )[:, 1]

    oof[val_idx] = scores


    # --------------------------------------------------------
    # VERIFY THE MODEL ACTUALLY LEARNED SPLITS
    # --------------------------------------------------------

    booster = model.booster_

    split_importance = booster.feature_importance(
        importance_type="split"
    )

    split_count = int(split_importance.sum())

    used_features = int(
        np.count_nonzero(split_importance)
    )

    unique_scores = np.unique(scores).size


    fold_auc = roc_auc_score(
        y[val_idx],
        scores,
    )

    fold_pr = average_precision_score(
        y[val_idx],
        scores,
    )


    print(f"\nFold {fold}")
    print(
        f"  held_out_lineages="
        f"{sorted(val_groups)}"
    )

    print(
        f"  train={len(train_idx)} "
        f"validation={len(val_idx)}"
    )

    print(
        f"  train_clean="
        f"{int((y[train_idx] == 0).sum())} "
        f"train_tampered="
        f"{int((y[train_idx] == 1).sum())}"
    )

    print(
        f"  model_trees="
        f"{booster.num_trees()}"
    )

    print(
        f"  total_splits="
        f"{split_count}"
    )

    print(
        f"  features_used="
        f"{used_features}/92"
    )

    print(
        f"  unique_validation_scores="
        f"{unique_scores}/{len(val_idx)}"
    )

    print(
        f"  score_range="
        f"{scores.min():.6f}"
        f"..{scores.max():.6f}"
    )

    print(
        f"  ROC-AUC={fold_auc:.6f}"
    )

    print(
        f"  PR-AUC ={fold_pr:.6f}"
    )


    fold_results.append(
        {
            "fold": fold,
            "held_out_lineages":
                sorted(val_groups),
            "train_count":
                int(len(train_idx)),
            "validation_count":
                int(len(val_idx)),
            "tree_count":
                int(booster.num_trees()),
            "split_count":
                split_count,
            "features_used":
                used_features,
            "unique_validation_scores":
                int(unique_scores),
            "roc_auc":
                float(fold_auc),
            "pr_auc":
                float(fold_pr),
        }
    )


if np.isnan(oof).any():
    raise RuntimeError(
        "Incomplete OOF predictions"
    )


# ============================================================
# POOLED METRICS
# ============================================================

pooled_roc = roc_auc_score(
    y,
    oof,
)

pooled_pr = average_precision_score(
    y,
    oof,
)

prevalence = float(y.mean())

normalized_pr = (
    (pooled_pr - prevalence)
    / (1.0 - prevalence)
)


print("\n=== POOLED MODEL-LEVEL RESULT ===")

print(
    f"ROC-AUC={pooled_roc:.6f}"
)

print(
    f"PR-AUC={pooled_pr:.6f}"
)

print(
    f"PR-baseline={prevalence:.6f}"
)

print(
    f"normalized-PR-AUC="
    f"{normalized_pr:.6f}"
)

print(
    f"unique_OOF_scores="
    f"{np.unique(oof).size}/48"
)


# ============================================================
# SCORE DISTRIBUTIONS
# ============================================================

def summarize(mask):
    a = oof[mask]

    return {
        "n": int(len(a)),
        "min": float(np.min(a)),
        "q25": float(
            np.quantile(a, 0.25)
        ),
        "median": float(
            np.median(a)
        ),
        "q75": float(
            np.quantile(a, 0.75)
        ),
        "max": float(np.max(a)),
        "mean": float(np.mean(a)),
    }


print("\n=== SCORE DISTRIBUTIONS ===")

distribution_results = {}

for family in (
    "CLEAN",
    "S1",
    "S2",
    "S3",
):

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


# ============================================================
# FAMILY ROC
# ============================================================

print("\n=== FAMILY ROC-AUC ===")

family_auc = {}

clean_mask = families == "CLEAN"

for family in (
    "S1",
    "S2",
    "S3",
):

    attack_mask = families == family

    mask = clean_mask | attack_mask

    yy = (
        families[mask] != "CLEAN"
    ).astype(np.int64)

    ss = oof[mask]

    auc = roc_auc_score(
        yy,
        ss,
    )

    family_auc[family] = float(auc)

    print(
        f"{family} vs CLEAN: "
        f"ROC-AUC={auc:.6f}"
    )


# ============================================================
# FOLD STABILITY
# ============================================================

fold_rocs = np.asarray(
    [
        r["roc_auc"]
        for r in fold_results
    ],
    dtype=np.float64,
)


print("\n=== STABILITY ===")

print(
    f"fold_ROC_mean="
    f"{fold_rocs.mean():.6f}"
)

print(
    f"fold_ROC_std="
    f"{fold_rocs.std():.6f}"
)

print(
    f"fold_ROC_min="
    f"{fold_rocs.min():.6f}"
)

print(
    f"fold_ROC_max="
    f"{fold_rocs.max():.6f}"
)


# ============================================================
# TOP FEATURES USED
# ============================================================

print("\n=== TOP USED FEATURES ===")

# Fit once on development pilot only for diagnostics.
# This is NOT used for OOF scoring.

weights_all = training_weights(
    np.arange(len(y))
)

diagnostic_model = LGBMClassifier(
    **MODEL_PARAMS
)

diagnostic_model.fit(
    X,
    y,
    sample_weight=weights_all,
)

gains = diagnostic_model.booster_.feature_importance(
    importance_type="gain"
)

splits = diagnostic_model.booster_.feature_importance(
    importance_type="split"
)

order = np.argsort(gains)[::-1][:15]

for i in order:
    if gains[i] <= 0:
        continue

    print(
        f"{feature_names[i]:40s} "
        f"gain={gains[i]:.6f} "
        f"splits={int(splits[i])}"
    )


# ============================================================
# DECISION
# ============================================================

print("\n=== PILOT V2 DECISION ===")

all_models_split = all(
    r["split_count"] > 0
    for r in fold_results
)

all_nonconstant_predictions = all(
    r["unique_validation_scores"] > 1
    for r in fold_results
)


if not all_models_split:
    decision = (
        "IMPLEMENTATION_OR_TRAINING_BLOCKER"
    )

    print(decision)

    print(
        "At least one fold still produced no "
        "tree splits. Do not judge the "
        "representation yet."
    )

elif not all_nonconstant_predictions:
    decision = (
        "IMPLEMENTATION_OR_SCORE_BLOCKER"
    )

    print(decision)

    print(
        "Model learned splits but at least "
        "one validation fold still received "
        "constant scores."
    )

elif (
    pooled_roc >= 0.80
    and fold_rocs.min() >= 0.70
):
    decision = (
        "KEEP_GLOBAL_BITPLANE_92"
    )

    print(decision)

    print(
        "The representation passes the "
        "frozen Phase-2 development ranking "
        "gate on 0.5% attacks."
    )

else:
    decision = (
        "GLOBAL_BITPLANE_92_SIGNAL_PRESENT_"
        "BUT_GATE_NOT_MET"
    )

    print(decision)

    print(
        "The model is genuinely learning, "
        "but this 92-feature representation "
        "does not yet satisfy the frozen "
        "Phase-2 success gate."
    )


# ============================================================
# PERSIST
# ============================================================

OUTPUT.write_text(
    json.dumps(
        {
            "representation":
                "GLOBAL_BITPLANE_92_V1",

            "model_params":
                MODEL_PARAMS,

            "artifact_count":
                int(len(y)),

            "nonconstant_features":
                int(nonconstant.sum()),

            "unique_feature_vectors":
                int(unique_rows),

            "positive_prevalence":
                prevalence,

            "pooled_roc_auc":
                float(pooled_roc),

            "pooled_pr_auc":
                float(pooled_pr),

            "normalized_pr_auc":
                float(normalized_pr),

            "folds":
                fold_results,

            "family_roc_auc":
                family_auc,

            "score_distributions":
                distribution_results,

            "decision":
                decision,
        },
        indent=2,
    ),
    encoding="utf-8",
)


print(
    f"\nsaved={OUTPUT}"
)
