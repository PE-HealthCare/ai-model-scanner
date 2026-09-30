from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np


# FP32 has 23 explicit mantissa bits.
MANTISSA_BITS = 23
SERIAL_M = 8

STAT_NAMES = (
    "monobit",
    "serial",
    "approx_entropy",
    "cumsum",
)

GLOBAL_BITPLANE_FEATURE_NAMES = tuple(
    f"mantissa_bit_{bit:02d}_{stat}"
    for bit in range(MANTISSA_BITS)
    for stat in STAT_NAMES
)

assert len(GLOBAL_BITPLANE_FEATURE_NAMES) == 92


def _as_bits(raw_u32: np.ndarray, bit: int) -> np.ndarray:
    """Return one logical FP32 mantissa bit-plane as uint8.

    bit=0 is the least-significant mantissa bit.
    bit=22 is the most-significant mantissa bit.

    Integer shifting is used rather than byte-order-dependent unpacking.
    """
    return ((raw_u32 >> np.uint32(bit)) & np.uint32(1)).astype(
        np.uint8, copy=False
    )


def _pattern_counts(bits: np.ndarray, m: int) -> np.ndarray:
    """Counts cyclic overlapping m-bit patterns."""
    bits = np.asarray(bits, dtype=np.uint8).reshape(-1)
    n = bits.size

    if n < m:
        raise ValueError(
            f"Need at least {m} bits for pattern statistic; received {n}"
        )

    # NIST-style cyclic continuation.
    extended = np.concatenate((bits, bits[: m - 1]))

    # m <= 9 in this extractor, so uint16 is sufficient.
    codes = np.zeros(n, dtype=np.uint16)

    for offset in range(m):
        codes <<= 1
        codes |= extended[offset : offset + n].astype(
            np.uint16, copy=False
        )

    return np.bincount(codes, minlength=1 << m).astype(np.float64)


def _psi(bits: np.ndarray, m: int) -> float:
    """Serial-test psi statistic."""
    n = bits.size
    counts = _pattern_counts(bits, m)

    return float(
        ((2.0**m) / float(n)) * np.sum(counts * counts)
        - float(n)
    )


def _pattern_entropy(bits: np.ndarray, m: int) -> float:
    """Entropy term used by the approximate-entropy statistic."""
    n = bits.size
    counts = _pattern_counts(bits, m)

    probabilities = counts[counts > 0.0] / float(n)

    return float(
        np.sum(probabilities * np.log(probabilities))
    )


def _bitplane_stats(bits: np.ndarray, serial_m: int = SERIAL_M):
    bits = np.asarray(bits, dtype=np.uint8).reshape(-1)
    n = bits.size

    if n < serial_m + 1:
        raise ValueError(
            f"Need at least {serial_m + 1} weights; received {n}"
        )

    ones = float(np.sum(bits))
    zeros = float(n) - ones

    # 1. Frequency / monobit statistic
    monobit = abs(ones - zeros) / np.sqrt(float(n))

    # 2. Serial-pattern statistic
    serial = _psi(bits, serial_m) - _psi(bits, serial_m - 1)

    # 3. Approximate entropy statistic
    phi_m = _pattern_entropy(bits, serial_m)
    phi_m1 = _pattern_entropy(bits, serial_m + 1)

    approximate_entropy = phi_m - phi_m1

    approx_entropy_stat = (
        2.0
        * float(n)
        * (np.log(2.0) - approximate_entropy)
    )

    # 4. Cumulative imbalance
    signed = bits.astype(np.int8) * 2 - 1
    cumulative = np.cumsum(signed, dtype=np.int64)

    cumsum_stat = float(
        np.max(np.abs(cumulative))
    )

    result = (
        float(monobit),
        float(serial),
        float(approx_entropy_stat),
        float(cumsum_stat),
    )

    if not np.all(np.isfinite(result)):
        raise ValueError("Non-finite global bit-plane statistic")

    return result


def extract_global_bitplane_from_uint32(
    raw_u32: np.ndarray,
    *,
    serial_m: int = SERIAL_M,
) -> Dict[str, float]:
    """Extract exactly 92 global FP32 mantissa bit-plane features.

    Input must contain the raw uint32 representations of FP32 weights.

    This is MODEL-LEVEL extraction: all supplied weights form one model-wide
    population. No layer probabilities or layer-to-model aggregation occurs.
    """
    raw_u32 = np.asarray(raw_u32, dtype=np.uint32).reshape(-1)

    if raw_u32.size < serial_m + 1:
        raise ValueError(
            "No sufficiently large FP32 population for global bit-plane extraction"
        )

    features: Dict[str, float] = {}

    for bit in range(MANTISSA_BITS):
        bits = _as_bits(raw_u32, bit)

        values = _bitplane_stats(
            bits,
            serial_m=serial_m,
        )

        for stat_name, value in zip(STAT_NAMES, values):
            features[
                f"mantissa_bit_{bit:02d}_{stat_name}"
            ] = value

    if tuple(features.keys()) != GLOBAL_BITPLANE_FEATURE_NAMES:
        raise AssertionError(
            "Global bit-plane feature order changed unexpectedly"
        )

    if len(features) != 92:
        raise AssertionError(
            f"Expected 92 features, got {len(features)}"
        )

    if not np.all(
        np.isfinite(np.asarray(list(features.values()), dtype=np.float64))
    ):
        raise ValueError("Global bit-plane feature vector is non-finite")

    return features


def extract_global_bitplane_from_safetensors(
    path: str | Path,
) -> dict:
    """Extract model-level global bit-plane features from SafeTensors.

    IMPORTANT:
    - Only true FP32 tensors participate.
    - FP16/BF16 tensors are NOT upcast and treated as FP32 bit patterns.
    - Integer/quantized tensors are excluded.

    Upcasting FP16 would manufacture zero FP32 low mantissa bits and would
    create an artificial signal unrelated to the stored artifact.
    """
    import torch
    from safetensors import safe_open

    path = Path(path)

    arrays = []
    fp32_tensor_count = 0
    fp32_element_count = 0
    skipped_tensor_count = 0

    with safe_open(str(path), framework="pt", device="cpu") as handle:
        for name in handle.keys():
            tensor = handle.get_tensor(name)

            if tensor.dtype != torch.float32:
                skipped_tensor_count += 1
                continue

            arr = (
                tensor.detach()
                .cpu()
                .contiguous()
                .numpy()
            )

            # Exact reinterpretation of the stored FP32 representation.
            raw = arr.view(np.uint32).reshape(-1)

            arrays.append(raw)
            fp32_tensor_count += 1
            fp32_element_count += int(raw.size)

    if not arrays:
        raise ValueError(
            f"{path}: no FP32 tensors available for the 92-feature "
            "global bit-plane branch"
        )

    raw_model = np.concatenate(arrays)

    features = extract_global_bitplane_from_uint32(raw_model)

    return {
        "artifact_path": str(path),
        "representation": "GLOBAL_BITPLANE_92_V1",
        "feature_count": 92,
        "feature_names": list(GLOBAL_BITPLANE_FEATURE_NAMES),
        "fp32_tensor_count": fp32_tensor_count,
        "fp32_element_count": fp32_element_count,
        "skipped_non_fp32_tensor_count": skipped_tensor_count,
        "features": features,
    }
