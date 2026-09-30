from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import GroupKFold


INPUT = Path("data/training/metadata/global_bitplane_pilot.json")
OUTPUT = Path(
    "data/training/metadata/"
    "global_bitplane_clean_relative_eval.json"
)

SEED = 20260929

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
# LOAD
# ============================================================

obj = json.loads(INPUT.read_text(encoding="utf-8"))
records = obj["records"]

feature_names = records[0]["feature_names"]

X_raw = np.asarray(
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

assert X_raw.shape == (48, 92)
assert np.all(np.isfinite(X_raw))


print("============================================================")
print("CLEAN-RELATIVE GLOBAL BIT-PLANE RESCUE")
print("============================================================")

print("\n=== DATA ===")
print(f"artifacts={len(y)}")
print(f"clean={(y == 0).sum()}")
print(f"tampered={(y == 1).sum()}")
print(f"features={X_raw.shape[1]}")
print(f"parent_lineages={len(set(groups))}")


# ============================================================
# WEIGHTS
# ============================================================

def training_weights(train_idx):
    idx = np.asarray(train_idx)

    local_groups = groups[idx]
    local_sources = sources[idx]
    local_y = y[idx]

    w = np.zeros(len(idx), dtype=np.float64)

    parent_values = sorted(set(local_groups))
    P = len(parent_values)

    for parent in parent_values:

        p_mask = local_groups == parent

        parent_sources = sorted(
            set(local_sources[p_mask])
        )

        S = len(parent_sources)

        for source in parent_sources:

            s_mask = (
                p_mask
                & (local_sources == source)
            )

            for cls in (0, 1):

                c_mask = (
                    s_mask
                    & (local_y == cls)
                )

                pos = np.flatnonzero(c_mask)

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
            "One or more rows received zero weight"
        )

    return w


# ============================================================
# CLEAN-RELATIVE TRANSFORMATION
# ============================================================

def fit_clean_reference(X_train, y_train):

    clean = X_train[y_train == 0]

    if len(clean) < 2:
        raise RuntimeError(
            "Not enough clean training models "
            "to establish reference."
        )

    median = np.median(clean, axis=0)

    mad = np.median(
        np.abs(clean - median),
        axis=0,
    )

    robust_scale = 1.4826 * mad

    # Some features can have zero MAD with such a small
    # clean reference population.
    #
    # Fallback 1: standard deviation of clean TRAINING only.
    std = np.std(clean, axis=0)

    mad_zero = robust_scale <= 1e-12

    robust_scale[mad_zero] = std[mad_zero]

    # Fallback 2: truly constant clean feature.
    still_zero = robust_scale <= 1e-12

    robust_scale[still_zero] = 1.0

    return {
        "median": median,
        "scale": robust_scale,
        "clean_count": len(clean),
        "mad_fallback_count": int(
            np.count_nonzero(mad_zero)
        ),
        "constant_fallback_count": int(
            np.count_nonzero(still_zero)
        ),
    }


def transform_to_anomaly(X, ref):

    z = (
        X - ref["median"]
    ) / ref["scale"]

    # KEY REPRESENTATION CHANGE:
    #
    # not signed normalized value,
    # but magnitude of deviation from CLEAN.
    anomaly = np.abs(z)

    if not np.all(np.isfinite(anomaly)):
        raise RuntimeError(
            "Non-finite anomaly representation"
        )

    return anomaly


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
    gkf.split(X_raw, y, groups)
):

    train_groups = set(groups[train_idx])
    val_groups = set(groups[val_idx])

    if train_groups & val_groups:
        raise RuntimeError(
            f"LINEAGE LEAKAGE in fold {fold}"
        )

    # --------------------------------------------------------
    # CRITICAL:
    # clean baseline fitted ONLY from training rows.
    # --------------------------------------------------------

    ref = fit_clean_reference(
        X_raw[train_idx],
        y[train_idx],
    )

    X_train = transform_to_anomaly(
        X_raw[train_idx],
        ref,
    )

    X_val = transform_to_anomaly(
        X_raw[val_idx],
        ref,
    )

    weights = training_weights(train_idx)

    model = LGBMClassifier(
        **MODEL_PARAMS
    )

    model.fit(
        X_train,
        y[train_idx],
        sample_weight=weights,
    )

    scores = model.predict_proba(
        X_val
    )[:, 1]

    oof[val_idx] = scores

    booster = model.booster_

    split_importance = (
        booster.feature_importance(
            importance_type="split"
        )
    )

    split_count = int(
        split_importance.sum()
    )

    used_features = int(
        np.count_nonzero(
            split_importance
        )
    )

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
        f"  clean_reference_models="
        f"{ref['clean_count']}"
    )

    print(
        f"  MAD->STD fallbacks="
        f"{ref['mad_fallback_count']}/92"
    )

    print(
        f"  constant fallbacks="
        f"{ref['constant_fallback_count']}/92"
    )

    print(
        f"  total_splits={split_count}"
    )

    print(
        f"  features_used="
        f"{used_features}/92"
    )

    print(
        f"  unique_validation_scores="
        f"{np.unique(scores).size}/"
        f"{len(scores)}"
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
            "clean_reference_count":
                ref["clean_count"],
            "mad_fallback_count":
                ref["mad_fallback_count"],
            "constant_fallback_count":
                ref["constant_fallback_count"],
            "split_count":
                split_count,
            "features_used":
                used_features,
            "unique_scores":
                int(np.unique(scores).size),
            "roc_auc":
                float(fold_auc),
            "pr_auc":
                float(fold_pr),
        }
    )


if np.isnan(oof).any():
    raise RuntimeError(
        "OOF predictions incomplete"
    )


# ============================================================
# OVERALL
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
    pooled_pr - prevalence
) / (
    1.0 - prevalence
)


print("\n=== POOLED RESULT ===")

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


# ============================================================
# FAMILY PERFORMANCE
# ============================================================

print("\n=== FAMILY ROC-AUC ===")

family_auc = {}

clean_mask = families == "CLEAN"

for family in ("S1", "S2", "S3"):

    mask = (
        clean_mask
        | (families == family)
    )

    yy = (
        families[mask] != "CLEAN"
    ).astype(np.int64)

    auc = roc_auc_score(
        yy,
        oof[mask],
    )

    family_auc[family] = float(auc)

    print(
        f"{family} vs CLEAN: "
        f"ROC-AUC={auc:.6f}"
    )


# ============================================================
# DISTRIBUTIONS
# ============================================================

print("\n=== SCORE DISTRIBUTIONS ===")

for family in (
    "CLEAN",
    "S1",
    "S2",
    "S3",
):

    a = oof[
        families == family
    ]

    print(
        f"{family:5s} "
        f"min={a.min():.6f} "
        f"median={np.median(a):.6f} "
        f"max={a.max():.6f} "
        f"mean={a.mean():.6f}"
    )


# ============================================================
# STABILITY
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
    f"fold_ROC_min="
    f"{fold_rocs.min():.6f}"
)

print(
    f"fold_ROC_max="
    f"{fold_rocs.max():.6f}"
)


# ============================================================
# FULL-DEVELOPMENT DIAGNOSTIC FEATURE IMPORTANCE
# ============================================================

print("\n=== TOP CLEAN-RELATIVE FEATURES ===")

ref_all = fit_clean_reference(
    X_raw,
    y,
)

X_all_anomaly = transform_to_anomaly(
    X_raw,
    ref_all,
)

weights_all = training_weights(
    np.arange(len(y))
)

diagnostic = LGBMClassifier(
    **MODEL_PARAMS
)

diagnostic.fit(
    X_all_anomaly,
    y,
    sample_weight=weights_all,
)

gain = (
    diagnostic.booster_
    .feature_importance(
        importance_type="gain"
    )
)

split = (
    diagnostic.booster_
    .feature_importance(
        importance_type="split"
    )
)

order = np.argsort(gain)[::-1][:15]

for i in order:

    if gain[i] <= 0:
        continue

    print(
        f"{feature_names[i]:40s} "
        f"gain={gain[i]:.6f} "
        f"splits={int(split[i])}"
    )


# ============================================================
# FINAL RESCUE DECISION
# ============================================================

print("\n=== FINAL B2 RESCUE DECISION ===")


if (
    pooled_roc >= 0.80
    and fold_rocs.min() >= 0.70
):

    decision = (
        "KEEP_CLEAN_RELATIVE_GLOBAL_BITPLANE"
    )

    print(decision)

    print(
        "Clean-relative anomaly representation "
        "passes the frozen pilot ranking gate."
    )

elif pooled_roc >= 0.65:

    decision = (
        "B2_IMPROVED_BUT_NOT_STRONG_ENOUGH"
    )

    print(decision)

    print(
        "Clean-relative transformation recovered "
        "real model-level signal, but it does not "
        "pass the frozen success gate."
    )

else:

    decision = (
        "STOP_B2_AND_MOVE_TO_B1_MODEL_RELATIVE"
    )

    print(decision)

    print(
        "The final clean-relative rescue attempt "
        "did not recover sufficient held-out "
        "model-level discrimination."
    )


OUTPUT.write_text(
    json.dumps(
        {
            "representation":
                "GLOBAL_BITPLANE_92_"
                "CLEAN_RELATIVE_ABS_MAD_V1",

            "model_params":
                MODEL_PARAMS,

            "pooled_roc_auc":
                float(pooled_roc),

            "pooled_pr_auc":
                float(pooled_pr),

            "normalized_pr_auc":
                float(normalized_pr),

            "family_roc_auc":
                family_auc,

            "folds":
                fold_results,

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
