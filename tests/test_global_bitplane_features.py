import numpy as np
import pytest
import torch
from safetensors.torch import save_file

from src.p3_ml_dashboard.global_bitplane_features import (
    GLOBAL_BITPLANE_FEATURE_NAMES,
    extract_global_bitplane_from_safetensors,
    extract_global_bitplane_from_uint32,
)


def _random_fp32_u32(seed=42, n=4096):
    rng = np.random.default_rng(seed)

    x = rng.normal(
        loc=0.0,
        scale=0.1,
        size=n,
    ).astype(np.float32)

    return x.view(np.uint32).copy()


def test_exact_92_feature_contract():
    raw = _random_fp32_u32()

    result = extract_global_bitplane_from_uint32(raw)

    assert len(result) == 92
    assert tuple(result.keys()) == GLOBAL_BITPLANE_FEATURE_NAMES
    assert np.all(
        np.isfinite(
            np.asarray(list(result.values()), dtype=np.float64)
        )
    )


def test_deterministic():
    raw = _random_fp32_u32()

    a = extract_global_bitplane_from_uint32(raw)
    b = extract_global_bitplane_from_uint32(raw)

    assert a == b


def test_low_bit_tampering_changes_global_features():
    raw = _random_fp32_u32(n=8192)

    clean = extract_global_bitplane_from_uint32(raw)

    tampered = raw.copy()

    # Deliberately alter the LSB structure of half the weights.
    tampered[: tampered.size // 2] &= np.uint32(0xFFFFFFFE)

    attacked = extract_global_bitplane_from_uint32(tampered)

    assert attacked != clean

    # The directly manipulated mantissa bit must respond.
    changed = [
        name
        for name in GLOBAL_BITPLANE_FEATURE_NAMES
        if name.startswith("mantissa_bit_00_")
        and attacked[name] != clean[name]
    ]

    assert changed


def test_rejects_too_small_population():
    raw = np.zeros(4, dtype=np.uint32)

    with pytest.raises(ValueError):
        extract_global_bitplane_from_uint32(raw)


def test_safetensors_loader_uses_true_fp32_only(tmp_path):
    fp32 = torch.linspace(
        -1.0,
        1.0,
        4096,
        dtype=torch.float32,
    )

    fp16 = torch.linspace(
        -1.0,
        1.0,
        1024,
        dtype=torch.float16,
    )

    path = tmp_path / "test_model.safetensors"

    save_file(
        {
            "weight_fp32": fp32,
            "weight_fp16": fp16,
        },
        str(path),
    )

    result = extract_global_bitplane_from_safetensors(path)

    assert result["representation"] == "GLOBAL_BITPLANE_92_V1"
    assert result["feature_count"] == 92
    assert result["fp32_tensor_count"] == 1
    assert result["fp32_element_count"] == 4096
    assert result["skipped_non_fp32_tensor_count"] == 1
    assert len(result["features"]) == 92
