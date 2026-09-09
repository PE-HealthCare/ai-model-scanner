"""
Tests for D8 generation_commit consistency.
"""

import pytest

from src.p2_behavioral_risk.analyzer import (
    P2AnalyzerError,
    _require_generation_commit,
)


def test_generation_commit_match_accepted():
    features = {
        "generation_commit": "ABC123",
    }

    ml_results = {
        "generation_commit": "ABC123",
    }

    result = _require_generation_commit(
        features,
        ml_results,
    )

    assert result == "ABC123"


def test_generation_commit_mismatch_rejected():
    features = {
        "generation_commit": "AAA",
    }

    ml_results = {
        "generation_commit": "BBB",
    }

    with pytest.raises(
        P2AnalyzerError,
        match="D8 BLOCKED",
    ):
        _require_generation_commit(
            features,
            ml_results,
        )


def test_missing_features_commit_rejected():
    features = {}

    ml_results = {
        "generation_commit": "AAA",
    }

    with pytest.raises(
        P2AnalyzerError,
        match="D8 BLOCKED",
    ):
        _require_generation_commit(
            features,
            ml_results,
        )


def test_missing_ml_commit_rejected():
    features = {
        "generation_commit": "AAA",
    }

    ml_results = {}

    with pytest.raises(
        P2AnalyzerError,
        match="D8 BLOCKED",
    ):
        _require_generation_commit(
            features,
            ml_results,
        )
