"""Canonical static feature names — single source of truth.

The "Master Graph" ordering encoded in contracts/features.schema.json.
Imported by P1 (feature extraction) and P3 (classification) so ordering can
never silently drift between pipeline stages.
"""

from __future__ import annotations

B0_FEATURE_NAMES: tuple[str, ...] = (
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

# Compatibility alias: existing classifier artifacts use this ten-column B0
# contract.  Do not widen it when adding forensic representations.
FEATURE_NAMES = B0_FEATURE_NAMES
CANONICAL_FEATURE_COUNT = len(B0_FEATURE_NAMES)

B1_ADDITIONAL_FEATURE_NAMES: tuple[str, ...] = (
    # Distribution
    "q01", "q05", "q25", "q50", "q75", "q95", "q99", "iqr",
    "coefficient_of_variation",
    # Floating-point structure
    "sign_bit_fraction", "exponent_mean", "exponent_std",
    "mantissa_lsb_imbalance", "low_bit_transition_rate",
    # Deterministic local / position-sensitive statistics
    "window_byte_entropy_mean", "local_byte_lag1_autocorrelation",
    "local_byte_kl_mean", "local_low_bit_deviation_mean",
)

B1_FEATURE_NAMES: tuple[str, ...] = B0_FEATURE_NAMES + B1_ADDITIONAL_FEATURE_NAMES


def feature_vector(feature_mapping: dict, *, feature_set: str = "b0") -> list[float]:
    """Canonical ordered feature vector from one per-layer feature mapping.

    Single shared construction path for training (train_classifier.py) and
    inference (classifier.score()): the ordering is fixed by FEATURE_NAMES
    and must match contracts/features.schema.json,
    contracts/ml_results.schema.json and models/classifier.json.
    """
    if feature_set == "b0":
        names = B0_FEATURE_NAMES
    elif feature_set == "b1":
        names = B1_FEATURE_NAMES
    else:
        raise ValueError(f"Unknown feature set: {feature_set}")
    return [float(feature_mapping[name]) for name in names]
