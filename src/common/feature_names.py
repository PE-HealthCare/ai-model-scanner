"""Canonical static feature names — single source of truth.

The "Master Graph" ordering encoded in contracts/features.schema.json.
Imported by P1 (feature extraction) and P3 (classification) so ordering can
never silently drift between pipeline stages.
"""

from __future__ import annotations

FEATURE_NAMES: tuple[str, ...] = (
    "entropy",
    "pov_chi2",
    "lsb_kl",
    "ks_stat",
    "mean",
    "std",
    "skewness",
    "kurtosis",
    "sparsity",
    "outlier_pct",
)

CANONICAL_FEATURE_COUNT = len(FEATURE_NAMES)


def feature_vector(feature_mapping: dict) -> list[float]:
    """Canonical ordered feature vector from one per-layer feature mapping.

    Single shared construction path for training (train_classifier.py) and
    inference (classifier.score()): the ordering is fixed by FEATURE_NAMES
    and must match contracts/features.schema.json,
    contracts/ml_results.schema.json and models/classifier.json.
    """
    return [float(feature_mapping[name]) for name in FEATURE_NAMES]