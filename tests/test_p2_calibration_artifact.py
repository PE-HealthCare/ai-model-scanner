"""
Regression tests for the P2 D3/D4 calibration artifact.

Artifact: data/calibration/calibration_data.json

Guarded invariant: the authoritative D4 `median` and `mad` are derived from
the recorded calibration observations by the repository's own
`scripts/generate_calibration_data.compute_statistics`. If a statistic in the
artifact disagrees with that calculation, or if `mad` goes missing again, the
authoritative non-quantized path silently degrades into
"Calibration data missing required D4 field: mad". These tests fail loudly
instead.
"""

import json
import os
import statistics
import sys

import pytest
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_calibration_data import compute_statistics
from src.p2_behavioral_risk.adapters import load_calibration_data
from src.p2_behavioral_risk.prober import (
    generate_probes,
    get_behavioral_result,
    normalize_h_strip,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_PATH = os.path.join(
    ROOT, "data", "calibration", "calibration_data.json"
)

APPROVED_PROBE_COUNT = 32
MIN_OBSERVATIONS = 3

D4_AUTHORITATIVE_FIELDS = ("median", "mad")

# Statistics that compute_statistics fully determines from the observations.
REPLAYED_FIELDS = (
    "h_strip_values",
    "mean",
    "median",
    "mad",
    "std",
    "min",
    "max",
    "percentiles",
)


class TinyProbeModel(nn.Module):
    """Cheap probe-compatible stand-in (no large weight matrices)."""

    def forward(self, x):
        if x.dim() == 4:
            pooled = x.mean(dim=(1, 2, 3))
        else:
            pooled = x.float().mean(dim=1)

        return pooled.unsqueeze(1).repeat(1, 1000)


def load_artifact():
    with open(CALIBRATION_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def artifact_domains():
    return sorted(load_artifact()["calibration_data"])


# ============================================================
# Artifact structure and loadability
# ============================================================
def test_artifact_has_expected_top_level_keys():
    artifact = load_artifact()

    assert "calibration_data" in artifact
    assert "provenance" in artifact

def test_replay_provenance_does_not_claim_new_measurement():
    """The committed calibration artifact is a replay, not a fresh measurement."""
    provenance = load_artifact()["provenance"]

    assert provenance["new_measurement_performed"] is False
    assert provenance["observations_replayed"] == {
        "VISION": 30,
        "NLP": 30,
    }


def test_both_domains_present():
    assert artifact_domains() == ["NLP", "VISION"]


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_domain_block_is_loadable_by_p2_adapter(domain):
    calibration = load_calibration_data(CALIBRATION_PATH)

    assert domain in calibration
    assert isinstance(calibration[domain], dict)


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_d4_authoritative_fields_present_and_valid(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    for field in D4_AUTHORITATIVE_FIELDS:
        assert field in block, f"{domain} is missing required D4 field '{field}'"
        assert isinstance(block[field], (int, float))


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_median_and_mad_are_finite(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    assert torch.isfinite(torch.tensor(float(block["median"])))
    assert torch.isfinite(torch.tensor(float(block["mad"])))


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_mad_is_non_negative(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    assert block["mad"] >= 0.0


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_mad_is_not_degenerate_for_the_measured_baselines(domain):
    """Measured clean-reference baselines have non-zero spread."""
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    assert block["mad"] > 0.0


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_approved_probe_configuration(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    assert block["probe_count"] == APPROVED_PROBE_COUNT


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_observation_count_matches_repetitions(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    observations = block["h_strip_values"]

    assert len(observations) == block["repetitions"]
    assert len(observations) >= MIN_OBSERVATIONS


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_reference_model_identity_recorded(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]

    assert block.get("model_name")
    assert block.get("domain") == domain


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_observations_are_finite_numbers(domain):
    observations = load_calibration_data(CALIBRATION_PATH)[domain][
        "h_strip_values"
    ]

    for value in observations:
        assert isinstance(value, (int, float))
        assert torch.isfinite(torch.tensor(float(value)))


# ============================================================
# Regression guard: every statistic must be reproducible from the
# recorded observations by the repository's own calculation.
# ============================================================
@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_statistics_reproduce_from_recorded_observations(domain):
    block = load_calibration_data(CALIBRATION_PATH)[domain]
    recomputed = compute_statistics(block["h_strip_values"])

    for field in REPLAYED_FIELDS:
        assert block[field] == recomputed[field], (
            f"{domain}.{field} in the artifact disagrees with "
            "compute_statistics(recorded observations)"
        )


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_mad_equals_median_absolute_deviation_of_observations(domain):
    """
    Independent cross-check of the artifact's median/MAD.

    Uses the stdlib median (averaged middle values for an even sample count,
    matching the repository's np.median convention) rather than reusing
    compute_statistics, so the artifact cannot drift unnoticed.
    """
    block = load_calibration_data(CALIBRATION_PATH)[domain]
    observations = [float(value) for value in block["h_strip_values"]]

    median = statistics.median(observations)
    mad = statistics.median(
        [abs(value - median) for value in observations]
    )

    assert block["median"] == median
    assert block["mad"] == mad


# ============================================================
# Fail-closed behaviour
# ============================================================
def test_missing_mad_fails_closed():
    with pytest.raises(RuntimeError, match="mad"):
        normalize_h_strip(5.0, "VISION", {"VISION": {"median": 5.0}})


def test_malformed_artifact_fails_closed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not_calibration": {}}), encoding="utf-8")

    with pytest.raises(KeyError):
        load_calibration_data(str(bad))


def test_empty_calibration_block_fails_closed(tmp_path):
    bad = tmp_path / "empty.json"
    bad.write_text(json.dumps({"calibration_data": {}}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_calibration_data(str(bad))


def test_non_quantized_behavioral_path_fails_closed_without_mad():
    """The exact CP5 blocker: no MAD -> no S_behavior, no MRS."""
    with pytest.raises(RuntimeError, match="mad"):
        get_behavioral_result(
            is_quantized=False,
            domain="VISION",
            model=TinyProbeModel(),
            calibration_data={"VISION": {"median": 5.0}},
            bound_n=APPROVED_PROBE_COUNT,
            mock_mode=True,
        )


# ============================================================
# D7 zero-MAD behaviour is unchanged
# ============================================================
def test_zero_mad_target_equal_to_median_is_zero():
    assert normalize_h_strip(2.0, "VISION", {"VISION": {"median": 2.0, "mad": 0.0}}) == 0.0


def test_zero_mad_target_different_is_degenerate():
    with pytest.raises(RuntimeError, match="DEGENERATE_DEVIATION"):
        normalize_h_strip(1.0, "VISION", {"VISION": {"median": 2.0, "mad": 0.0}})


# ============================================================
# Probe routing
# ============================================================
def test_vision_probes_are_float_images():
    probes = generate_probes("VISION", n=APPROVED_PROBE_COUNT)

    assert tuple(probes.shape) == (APPROVED_PROBE_COUNT, 3, 224, 224)
    assert probes.dtype == torch.float32


def test_nlp_probes_are_integer_token_ids():
    probes = generate_probes("NLP", n=APPROVED_PROBE_COUNT)

    assert tuple(probes.shape) == (APPROVED_PROBE_COUNT, 32)
    assert probes.dtype == torch.int64


# ============================================================
# Non-quantized behavioural path executes against the real artifact
# ============================================================
@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_non_quantized_path_produces_bounded_s_behavior(domain):
    torch.manual_seed(11)

    result = get_behavioral_result(
        is_quantized=False,
        domain=domain,
        model=TinyProbeModel(),
        calibration_data=load_calibration_data(CALIBRATION_PATH),
        bound_n=APPROVED_PROBE_COUNT,
        mock_mode=True,
    )

    assert result["bypassed_behavior"] is False
    assert result["probe_count"] == APPROVED_PROBE_COUNT
    assert result["successful_probe_count"] == APPROVED_PROBE_COUNT
    assert result["failed_probe_count"] == 0
    assert 0.0 <= result["s_behavior"] <= 1.0
    assert torch.isfinite(torch.tensor(float(result["h_strip"])))


@pytest.mark.parametrize("domain", ["VISION", "NLP"])
def test_non_quantized_s_behavior_matches_locked_d4_formula(domain):
    torch.manual_seed(11)

    block = load_calibration_data(CALIBRATION_PATH)[domain]

    result = get_behavioral_result(
        is_quantized=False,
        domain=domain,
        model=TinyProbeModel(),
        calibration_data=load_calibration_data(CALIBRATION_PATH),
        bound_n=APPROVED_PROBE_COUNT,
        mock_mode=True,
    )

    deviation = block["median"] - result["h_strip"]
    z = deviation / (1.4826 * block["mad"])
    expected = min(1.0, max(0.0, z) / 3.0)

    assert result["s_behavior"] == expected