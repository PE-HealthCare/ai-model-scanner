"""
Tests for D7 MAD-based anomaly handling.
"""

import numpy as np
import pytest

from src.p2_behavioral_risk.risk_aggregator import mad_zscore


def test_mad_zscore_normal():
    baseline = [
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
    ]

    z = mad_zscore(
        5.0,
        baseline,
    )

    assert np.isfinite(z)


def test_mad_zero_equal_median():
    baseline = [
        1.0,
        1.0,
        1.0,
        1.0,
    ]

    z = mad_zscore(
        1.0,
        baseline,
    )

    assert z == 0.0


def test_mad_zero_different_target():
    baseline = [
        1.0,
        1.0,
        1.0,
        1.0,
    ]

    with pytest.raises(
        RuntimeError,
        match="DEGENERATE_DEVIATION",
    ):
        mad_zscore(
            2.0,
            baseline,
        )


def test_mad_rejects_nan():
    baseline = [
        1.0,
        2.0,
        3.0,
        np.nan,
    ]

    with pytest.raises(ValueError):
        mad_zscore(
            2.0,
            baseline,
        )


def test_mad_rejects_inf():
    baseline = [
        1.0,
        2.0,
        3.0,
        np.inf,
    ]

    with pytest.raises(ValueError):
        mad_zscore(
            2.0,
            baseline,
        )


def test_mad_rejects_nan_target():
    baseline = [
        1.0,
        2.0,
        3.0,
        4.0,
    ]

    with pytest.raises(ValueError):
        mad_zscore(
            np.nan,
            baseline,
        )


def test_mad_requires_three_layers():
    baseline = [
        1.0,
        2.0,
    ]

    with pytest.raises(RuntimeError):
        mad_zscore(
            3.0,
            baseline,
        )


def test_mad_requires_non_empty_baseline():
    with pytest.raises(RuntimeError):
        mad_zscore(
            1.0,
            [],
        )


def test_mad_near_zero_positive_is_used():
    baseline = [
        1.0,
        1.000001,
        1.000002,
        1.000003,
    ]

    z = mad_zscore(
        1.000004,
        baseline,
    )

    assert np.isfinite(z)
