import numpy as np
import pytest

from scripts import run_p2_learning_curve as curve
from scripts import run_p2_model_selection as selection


class _FeatureProbabilityModel:
    def predict_proba(self, x):
        p = np.asarray(x, dtype=np.float64)[:, 0]
        return np.column_stack((1.0 - p, p))


def _artifact(parent, family, values, partition="DEVELOPMENT"):
    return {
        "artifact_sha256": f"{parent}-{family}",
        "parent_lineage_id": parent,
        "attack_family": family,
        "partition": partition,
        "b1_rows": [{"score": value} for value in values],
    }


def test_tail_mass_is_q95_inclusive_and_normalized_by_layer_count():
    assert curve.tail_mass([0.2, 0.5, 0.5, 0.9], 0.5) == pytest.approx(0.75)
    assert curve.tail_mass([0.2, 0.5, 0.5, 0.9], 0.5) == curve.tail_mass([0.2, 0.5, 0.5, 0.9], 0.5)


def test_training_clean_tau_uses_only_training_clean_layers():
    training = [
        _artifact("train-a", "CLEAN", [0.1, 0.2]),
        _artifact("train-b", "CLEAN", [0.3, 0.4]),
        _artifact("train-a", "S1", [0.99]),
    ]
    tau = curve._training_clean_tau(_FeatureProbabilityModel(), training, ["score"], set())
    assert tau == pytest.approx(np.percentile([0.1, 0.2, 0.3, 0.4], 95.0))


def test_training_clean_tau_rejects_held_out_and_s4_contributions():
    with pytest.raises(AssertionError, match="Held-out lineage"):
        curve._training_clean_tau(_FeatureProbabilityModel(), [_artifact("held-out", "CLEAN", [0.2])], ["score"], {"held-out"})
    with pytest.raises(AssertionError, match="S4"):
        curve._training_clean_tau(_FeatureProbabilityModel(), [_artifact("train", "S4", [0.2])], ["score"], set())


def test_tail_mass_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        curve.tail_mass([], 0.5)
    with pytest.raises(ValueError):
        curve.tail_mass([0.1, np.nan], 0.5)
    with pytest.raises(ValueError):
        curve.tail_mass([0.1], 1.1)


def test_model_selection_space_is_exactly_twelve_preregistered_candidates():
    configs = selection.preregistered_configurations()
    assert len(configs) == 12
    assert [item["id"] for item in configs] == [f"C{i:02d}" for i in range(1, 13)]
    assert configs[0]["params"]["num_leaves"] == 15
    assert configs[0]["n_estimators"] == 120
    assert all(item["params"]["num_threads"] == 1 for item in configs)
