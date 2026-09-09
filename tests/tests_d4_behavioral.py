"""
Tests for D4 STRIP behavioral normalization.

Locked formula:

deviation = H_median - H_STRIP

Z = deviation / (1.4826 * H_MAD)

Z_clamped = max(0, Z)

S_behavior = min(1, Z_clamped / 3)

Therefore:
- H_STRIP == median -> 0
- H_STRIP > median -> 0
- H_STRIP < median -> positive risk
"""

import pytest

from src.p2_behavioral_risk.prober import normalize_h_strip


def vision_calibration():
    return {
        "VISION": {
            "median": 2.0,
            "mad": 0.5,
        }
    }


def test_d4_entropy_at_median_is_zero():
    score = normalize_h_strip(
        2.0,
        "VISION",
        vision_calibration(),
    )

    assert score == 0.0


def test_d4_lower_entropy_increases_risk():
    score = normalize_h_strip(
        1.0,
        "VISION",
        vision_calibration(),
    )

    assert score > 0.0


def test_d4_higher_entropy_is_zero():
    score = normalize_h_strip(
        3.0,
        "VISION",
        vision_calibration(),
    )

    assert score == 0.0


def test_d4_score_is_bounded():
    score = normalize_h_strip(
        -100.0,
        "VISION",
        vision_calibration(),
    )

    assert 0.0 <= score <= 1.0


def test_d4_zero_mad_equal_median_is_zero():
    calibration = {
        "VISION": {
            "median": 2.0,
            "mad": 0.0,
        }
    }

    score = normalize_h_strip(
        2.0,
        "VISION",
        calibration,
    )

    assert score == 0.0


def test_d4_zero_mad_different_target_is_degenerate():
    calibration = {
        "VISION": {
            "median": 2.0,
            "mad": 0.0,
        }
    }

    with pytest.raises(
        RuntimeError,
        match="DEGENERATE_DEVIATION",
    ):
        normalize_h_strip(
            1.0,
            "VISION",
            calibration,
        )


def test_d4_rejects_invalid_h_strip():
    calibration = vision_calibration()

    with pytest.raises(ValueError):
        normalize_h_strip(
            float("nan"),
            "VISION",
            calibration,
        )


def test_d4_rejects_missing_calibration():
    with pytest.raises(RuntimeError):
        normalize_h_strip(
            1.0,
            "VISION",
            {},
        )


def test_d4_rejects_invalid_mad():
    calibration = {
        "VISION": {
            "median": 2.0,
            "mad": float("nan"),
        }
    }

    with pytest.raises(ValueError):
        normalize_h_strip(
            1.0,
            "VISION",
            calibration,
        )


def test_d4_rejects_missing_mad():
    calibration = {
        "VISION": {
            "median": 2.0,
        }
    }

    with pytest.raises(RuntimeError):
        normalize_h_strip(
            1.0,
            "VISION",
            calibration,
        )
