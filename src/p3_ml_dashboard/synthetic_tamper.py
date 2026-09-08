"""
PREPARATORY synthetic tampering utilities for P3.

NON-AUTHORITATIVE.
NOT FOR FINAL TRAINING UNTIL CP3 PASS.

This module implements exactly the three synthetic tampering methods
required by the approved project pipeline:

1. controlled perturbation
2. LSB manipulation
3. mantissa-bit modification

All functions operate only on in-memory NumPy arrays. They do not load
models, execute models, invoke P1 extraction, train LightGBM, or produce
pipeline artifacts.

Each function returns:
    (tampered_array, provenance)

The caller's original array is never mutated.
"""

from typing import Dict, Optional, Tuple, Union

import numpy as np


STATUS = "PREPARATORY"
SYNTHETIC_STATUS = "SYNTHETIC"


def _validate_float_array(arr: np.ndarray) -> None:
    """Validate that arr is a NumPy array with a supported floating dtype."""
    if not isinstance(arr, np.ndarray):
        raise TypeError("Input must be a NumPy ndarray.")

    if not np.issubdtype(arr.dtype, np.floating):
        raise TypeError(
            f"Unsupported dtype {arr.dtype!r}. "
            "Only floating-point arrays are allowed."
        )

    if arr.dtype not in (np.float32, np.float64):
        raise TypeError(
            f"Unsupported floating dtype {arr.dtype!r}. "
            "Only float32 and float64 are supported."
        )


def _make_rng(
    seed: Optional[Union[int, np.random.Generator]] = None,
) -> np.random.Generator:
    """Return a reproducible NumPy random generator."""
    if isinstance(seed, np.random.Generator):
        return seed

    return np.random.default_rng(seed)


def _provenance(
    method: str,
    parameters: dict,
    seed: Optional[Union[int, np.random.Generator]],
) -> dict:
    """Create consistent preparatory synthetic provenance metadata."""
    return {
        "method": method,
        "parameters": parameters,
        "seed": seed if isinstance(seed, int) else None,
        "status": STATUS,
        "synthetic_status": SYNTHETIC_STATUS,
        "authoritative": False,
    }


def controlled_perturbation(
    arr: np.ndarray,
    epsilon: float,
    seed: Optional[Union[int, np.random.Generator]] = None,
) -> Tuple[np.ndarray, Dict]:
    """
    Apply controlled zero-mean Gaussian perturbation.

    epsilon is the standard deviation of the perturbation and must be > 0.
    """
    _validate_float_array(arr)

    if not isinstance(epsilon, (int, float)) or isinstance(epsilon, bool):
        raise ValueError("'epsilon' must be a positive number.")

    if epsilon <= 0:
        raise ValueError("'epsilon' must be a positive number.")

    rng = _make_rng(seed)

    tampered = arr.copy()
    noise = rng.normal(
        loc=0.0,
        scale=float(epsilon),
        size=arr.shape,
    ).astype(arr.dtype)

    tampered += noise

    return tampered, _provenance(
        method="controlled_perturbation",
        parameters={"epsilon": float(epsilon)},
        seed=seed,
    )


def lsb_manipulation(
    arr: np.ndarray,
    bits: int = 1,
) -> Tuple[np.ndarray, Dict]:
    """
    Flip the least-significant bits of each floating-point value.

    This is a pure bit-level operation. No artificial numeric perturbation
    is added after modification.
    """
    _validate_float_array(arr)

    if not isinstance(bits, int) or isinstance(bits, bool) or bits <= 0:
        raise ValueError("'bits' must be a positive integer.")

    if arr.dtype == np.float32:
        int_type = np.uint32
        bit_width = 32
    else:
        int_type = np.uint64
        bit_width = 64

    if bits > bit_width:
        raise ValueError(
            f"'bits' ({bits}) exceeds the bit width ({bit_width})."
        )

    tampered = arr.copy()
    view = tampered.view(int_type)

    mask = (1 << bits) - 1
    view ^= int_type(mask)

    return tampered, _provenance(
        method="lsb_manipulation",
        parameters={"bits": bits},
        seed=None,
    )


def mantissa_bit_modification(
    arr: np.ndarray,
    bits: int = 1,
    seed: Optional[Union[int, np.random.Generator]] = None,
) -> Tuple[np.ndarray, Dict]:
    """
    Modify selected bits within the IEEE-754 mantissa.

    The modification is restricted to mantissa bits and never changes the
    sign or exponent fields.
    """
    _validate_float_array(arr)

    if not isinstance(bits, int) or isinstance(bits, bool) or bits <= 0:
        raise ValueError("'bits' must be a positive integer.")

    if arr.dtype == np.float32:
        int_type = np.uint32
        mantissa_width = 23
    else:
        int_type = np.uint64
        mantissa_width = 52

    if bits > mantissa_width:
        raise ValueError(
            f"'bits' ({bits}) exceeds mantissa width ({mantissa_width})."
        )

    rng = _make_rng(seed)

    tampered = arr.copy()
    view = tampered.view(int_type)

    # Select random mantissa positions for each element.
    # Only positions 0..mantissa_width-1 are ever modified.
    positions = rng.integers(
        low=0,
        high=mantissa_width,
        size=(bits,) + arr.shape,
    )

    mask = np.zeros(arr.shape, dtype=int_type)

    for position_array in positions:
        mask |= (int_type(1) << position_array.astype(int_type))

    # Ensure every selected mask contains at least one changed mantissa bit.
    mask[mask == 0] = int_type(1)

    view ^= mask

    return tampered, _provenance(
        method="mantissa_bit_modification",
        parameters={"bits": bits},
        seed=seed,
    )