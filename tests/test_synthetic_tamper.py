import numpy as np
import pytest

from src.p3_ml_dashboard.synthetic_tamper import (
    controlled_perturbation,
    lsb_manipulation,
    mantissa_bit_modification,
)


@pytest.fixture
def sample_float32():
    return np.array(
        [[1.0, 2.5, -3.2], [0.0, -0.1, 4.4]],
        dtype=np.float32,
    )


@pytest.fixture
def sample_float64():
    return np.array(
        [[10.0, -5.5], [3.14, 2.718]],
        dtype=np.float64,
    )


# ---------------------------------------------------------------------------
# Controlled perturbation
# ---------------------------------------------------------------------------

def test_controlled_perturbation_preserves_input_and_shape(sample_float32):
    original = sample_float32.copy()

    tampered, provenance = controlled_perturbation(
        sample_float32,
        epsilon=0.1,
        seed=42,
    )

    assert np.array_equal(sample_float32, original)
    assert tampered.shape == original.shape
    assert tampered.dtype == original.dtype


def test_controlled_perturbation_is_reproducible(sample_float32):
    first, _ = controlled_perturbation(
        sample_float32,
        epsilon=0.1,
        seed=42,
    )

    second, _ = controlled_perturbation(
        sample_float32,
        epsilon=0.1,
        seed=42,
    )

    assert np.array_equal(first, second)


def test_controlled_perturbation_changes_values(sample_float32):
    tampered, _ = controlled_perturbation(
        sample_float32,
        epsilon=0.5,
        seed=1,
    )

    assert not np.array_equal(sample_float32, tampered)


def test_controlled_perturbation_invalid_epsilon(sample_float32):
    with pytest.raises(ValueError):
        controlled_perturbation(sample_float32, epsilon=0)

    with pytest.raises(ValueError):
        controlled_perturbation(sample_float32, epsilon=-0.1)


def test_controlled_perturbation_rejects_invalid_input():
    with pytest.raises(TypeError):
        controlled_perturbation(
            np.arange(5, dtype=np.int32),
            epsilon=0.1,
        )


# ---------------------------------------------------------------------------
# LSB manipulation
# ---------------------------------------------------------------------------

def test_lsb_manipulation_preserves_input_shape_and_dtype(sample_float32):
    original = sample_float32.copy()

    tampered, _ = lsb_manipulation(sample_float32, bits=1)

    assert np.array_equal(sample_float32, original)
    assert tampered.shape == original.shape
    assert tampered.dtype == original.dtype


def test_lsb_manipulation_changes_bit_representation(sample_float32):
    tampered, _ = lsb_manipulation(sample_float32, bits=1)

    original_bits = sample_float32.view(np.uint32)
    tampered_bits = tampered.view(np.uint32)

    assert np.any(original_bits != tampered_bits)


def test_lsb_manipulation_is_deterministic(sample_float64):
    first, _ = lsb_manipulation(sample_float64, bits=2)
    second, _ = lsb_manipulation(sample_float64, bits=2)

    assert np.array_equal(first, second)


def test_lsb_manipulation_invalid_bits(sample_float32):
    with pytest.raises(ValueError):
        lsb_manipulation(sample_float32, bits=0)

    with pytest.raises(ValueError):
        lsb_manipulation(sample_float32, bits=33)


def test_lsb_manipulation_rejects_invalid_input():
    with pytest.raises(TypeError):
        lsb_manipulation(
            np.array([1, 2, 3], dtype=np.int32),
            bits=1,
        )


# ---------------------------------------------------------------------------
# Mantissa-bit modification
# ---------------------------------------------------------------------------

def test_mantissa_modification_preserves_input_shape_and_dtype(sample_float32):
    original = sample_float32.copy()

    tampered, _ = mantissa_bit_modification(
        sample_float32,
        bits=2,
        seed=123,
    )

    assert np.array_equal(sample_float32, original)
    assert tampered.shape == original.shape
    assert tampered.dtype == original.dtype


def test_mantissa_modification_changes_bit_representation(sample_float32):
    tampered, _ = mantissa_bit_modification(
        sample_float32,
        bits=2,
        seed=5,
    )

    original_bits = sample_float32.view(np.uint32)
    tampered_bits = tampered.view(np.uint32)

    assert np.any(original_bits != tampered_bits)


def test_mantissa_modification_is_reproducible(sample_float64):
    first, _ = mantissa_bit_modification(
        sample_float64,
        bits=3,
        seed=99,
    )

    second, _ = mantissa_bit_modification(
        sample_float64,
        bits=3,
        seed=99,
    )

    assert np.array_equal(first, second)


def test_mantissa_modification_invalid_bits(sample_float64):
    with pytest.raises(ValueError):
        mantissa_bit_modification(sample_float64, bits=0)

    with pytest.raises(ValueError):
        mantissa_bit_modification(sample_float64, bits=53)


def test_mantissa_modification_rejects_invalid_input():
    with pytest.raises(TypeError):
        mantissa_bit_modification(
            np.array([1, 2], dtype=np.int16),
            bits=1,
        )


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("function", "kwargs", "expected_method"),
    [
        (
            controlled_perturbation,
            {"epsilon": 0.1, "seed": 1},
            "controlled_perturbation",
        ),
        (
            lsb_manipulation,
            {"bits": 1},
            "lsb_manipulation",
        ),
        (
            mantissa_bit_modification,
            {"bits": 1, "seed": 1},
            "mantissa_bit_modification",
        ),
    ],
)
def test_provenance_marks_synthetic_preparatory_output(
    sample_float32,
    function,
    kwargs,
    expected_method,
):
    _, provenance = function(sample_float32, **kwargs)

    assert provenance["method"] == expected_method
    assert provenance["status"] == "PREPARATORY"
    assert provenance["synthetic_status"] == "SYNTHETIC"
    assert provenance["authoritative"] is False