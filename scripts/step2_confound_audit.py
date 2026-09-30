from __future__ import annotations

import json
import math
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path("data/training")
MANIFEST = ROOT / "metadata" / "attack_manifest.json"

FAMILIES = ("S1", "S2", "S3")
TIERS = (0.005, 0.01, 0.02, 0.05)


def load_manifest():
    obj = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if isinstance(obj, list):
        return obj

    for key in ("records", "artifacts", "entries"):
        if isinstance(obj.get(key), list):
            return obj[key]

    raise RuntimeError("Cannot locate attack records")


def read_safetensors_header(path: Path) -> dict:
    with path.open("rb") as f:
        raw = f.read(8)

        if len(raw) != 8:
            raise RuntimeError(f"Bad safetensors header: {path}")

        header_len = struct.unpack("<Q", raw)[0]
        header = json.loads(f.read(header_len))

    return header


def tensor_type(name: str) -> str:
    n = name.lower()

    if ".conv" in n or n.startswith("conv"):
        return "conv"

    if n.startswith("fc.") or ".fc." in n:
        return "linear"

    if ".bn" in n or n.startswith("bn"):
        if "running_mean" in n:
            return "bn_running_mean"
        if "running_var" in n:
            return "bn_running_var"
        if n.endswith(".weight"):
            return "bn_weight"
        if n.endswith(".bias"):
            return "bn_bias"
        return "bn_other"

    if n.endswith(".bias"):
        return "bias"

    if n.endswith(".weight"):
        return "weight_other"

    return "other"


def depth(name: str) -> int:
    m = re.search(r"(?:^|\.)layer([1-4])(?:\.|$)", name)

    if m:
        return int(m.group(1))

    if name.startswith("conv1") or name.startswith("bn1"):
        return 0

    if name.startswith("fc"):
        return 5

    return -1


# ------------------------------------------------------------
# Select one primary artifact per source/family/tier.
# ------------------------------------------------------------

records = [
    r for r in load_manifest()
    if r.get("partition") == "DEVELOPMENT"
    and r.get("attack_family") in FAMILIES
    and float(r.get("attack_strength")) in TIERS
]

primary = {}

for r in records:
    key = (
        r["source_model_id"],
        r["attack_family"],
        float(r["attack_strength"]),
    )
    primary.setdefault(key, r)

records = list(primary.values())

print("============================================================")
print("STEP 2 - CONFOUND AUDIT")
print("============================================================")
print(f"artifact_models={len(records)}")


# ------------------------------------------------------------
# Build tensor-level dataset.
# Only metadata:
#   numel
#   layer type
#   network depth
# No tamper statistics.
# ------------------------------------------------------------

rows = []

for r in records:

    path = Path(r["file"])
    header = read_safetensors_header(path)
    modified = set(r["modified_tensors"])

    for name, meta in header.items():

        if name == "__metadata__":
            continue

        if meta.get("dtype") != "F32":
            continue

        shape = meta["shape"]
        numel = math.prod(shape)

        rows.append({
            "parent_lineage_id": r["parent_lineage_id"],
            "source_model_id": r["source_model_id"],
            "family": r["attack_family"],
            "tier": float(r["attack_strength"]),
            "tensor": name,

            # LABEL
            "label": int(name in modified),

            # CONFOUND FEATURES ONLY
            "log_numel": math.log1p(numel),
            "layer_type": tensor_type(name),
            "depth": depth(name),

            "numel": numel,
        })


print(f"tensor_layer_rows={len(rows)}")
print(
    f"positive_modified_tensors="
    f"{sum(x['label'] for x in rows)}"
)
print(
    f"negative_untouched_tensors="
    f"{sum(1-x['label'] for x in rows)}"
)


# ------------------------------------------------------------
# Matrix
# ------------------------------------------------------------

X = np.asarray(
    [
        [r["log_numel"], r["layer_type"], r["depth"]]
        for r in rows
    ],
    dtype=object,
)

y = np.asarray([r["label"] for r in rows], dtype=int)
groups = np.asarray(
    [r["parent_lineage_id"] for r in rows],
    dtype=object,
)

numeric = [0, 2]
categorical = [1]

pre = ColumnTransformer(
    [
        ("num", StandardScaler(), numeric),
        (
            "cat",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False
            ),
            categorical,
        ),
    ]
)

model = Pipeline(
    [
        ("pre", pre),
        (
            "clf",
            LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=20260929,
            ),
        ),
    ]
)


# ------------------------------------------------------------
# Grouped OOF
# ------------------------------------------------------------

unique_groups = np.unique(groups)
n_splits = min(3, len(unique_groups))

cv = GroupKFold(n_splits=n_splits)

scores = np.full(len(rows), np.nan, dtype=float)

print()
print("=== GROUPED FOLDS ===")

for fold, (train_idx, val_idx) in enumerate(
    cv.split(X, y, groups)
):
    model.fit(X[train_idx], y[train_idx])

    scores[val_idx] = model.predict_proba(
        X[val_idx]
    )[:, 1]

    held = sorted(set(groups[val_idx]))

    print(
        f"fold={fold} "
        f"held_out_lineages={held} "
        f"train_layers={len(train_idx)} "
        f"validation_layers={len(val_idx)}"
    )


if np.isnan(scores).any():
    raise RuntimeError("Missing OOF scores")


# ------------------------------------------------------------
# Per-family × tier ROC
# ------------------------------------------------------------

print()
print("=== CONFOUND-ONLY LAYER ROC ===")
print(
    "unit=tensor/layer; labels=actually modified tensor only"
)
print(
    "features=log(numel), layer_type, network_depth"
)
print()
print(
    "family tier   positives negatives layer_ROC"
)

cell_rocs = {}

for family in FAMILIES:
    for tier in TIERS:

        idx = np.asarray(
            [
                i
                for i, r in enumerate(rows)
                if r["family"] == family
                and r["tier"] == tier
            ],
            dtype=int,
        )

        yy = y[idx]
        ss = scores[idx]

        positives = int(yy.sum())
        negatives = int((1 - yy).sum())

        if len(np.unique(yy)) < 2:
            roc = float("nan")
        else:
            roc = roc_auc_score(yy, ss)

        cell_rocs[(family, tier)] = roc

        print(
            f"{family:<6} "
            f"{tier:>5.1%} "
            f"{positives:>9} "
            f"{negatives:>9} "
            f"{roc:>9.6f}"
        )


# ------------------------------------------------------------
# S3 target variability
# ------------------------------------------------------------

s3_targets = Counter()

for r in records:
    if r["attack_family"] == "S3":
        for name in r["modified_tensors"]:
            s3_targets[name] += 1

print()
print("=== S3 TARGET VARIABILITY ===")
print(
    f"S3_artifacts={sum(s3_targets.values())}"
)
print(
    f"unique_S3_target_tensors={len(s3_targets)}"
)

for name, count in s3_targets.most_common():
    print(f"{name}: {count}")


# ------------------------------------------------------------
# Modified vs untouched tensor-size distribution
# ------------------------------------------------------------

modified_sizes = np.asarray(
    [r["numel"] for r in rows if r["label"] == 1],
    dtype=float,
)

untouched_sizes = np.asarray(
    [r["numel"] for r in rows if r["label"] == 0],
    dtype=float,
)

print()
print("=== TENSOR SIZE CONFOUND ===")

print(
    "modified_tensor_numel "
    f"median={np.median(modified_sizes):.1f} "
    f"q25={np.quantile(modified_sizes,0.25):.1f} "
    f"q75={np.quantile(modified_sizes,0.75):.1f}"
)

print(
    "untouched_tensor_numel "
    f"median={np.median(untouched_sizes):.1f} "
    f"q25={np.quantile(untouched_sizes,0.25):.1f} "
    f"q75={np.quantile(untouched_sizes,0.75):.1f}"
)

ratio = (
    np.median(modified_sizes)
    / max(np.median(untouched_sizes), 1.0)
)

print(
    f"median_size_ratio_modified_to_untouched={ratio:.3f}x"
)


# ------------------------------------------------------------
# Simple decision
# ------------------------------------------------------------

finite_rocs = [
    value
    for value in cell_rocs.values()
    if np.isfinite(value)
]

max_roc = max(finite_rocs)
median_roc = float(np.median(finite_rocs))

print()
print("=== STEP 2 DECISION ===")
print(f"max_cell_layer_ROC={max_roc:.6f}")
print(f"median_cell_layer_ROC={median_roc:.6f}")

if max_roc >= 0.70:
    print(
        "RESULT=CONFOUND_SIGNAL_PRESENT"
    )
    print(
        "Old layer-level ROC cannot be treated as forensic "
        "evidence without controlling for tensor identity/size."
    )
else:
    print(
        "RESULT=NO_STRONG_CONFOUND_SIGNAL"
    )

print()
print("=== STEP 2 COMPLETE ===")
