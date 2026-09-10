# src/p2_behavioral_risk/prober.py

"""
P2 Option 2 - Simple Vision STRIP behavioral probe.

Purpose:
    Probe a trusted ResNet18 model for anomalous prediction stability.

Important:
    - Vision only
    - No NLP
    - No model loading
    - No model reloading
    - Uses the trusted model supplied through handoff.py
    - Bounded number of probes
    - Fail closed on invalid inference
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import torch

from .config import (
    BOUND_N,
    MAD_SCALE,
    STRIP_Z_SCALE,
    VISION_IMAGE_SIZE,
)
from .handoff import get_trusted_model


# ---------------------------------------------------------------------------
# Basic numeric helpers
# ---------------------------------------------------------------------------


def _is_finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _entropy(probabilities: torch.Tensor) -> float:
    """
    Shannon entropy of a probability vector.
    """

    if probabilities.ndim != 1:
        raise ValueError("Probability vector must be one-dimensional")

    if probabilities.numel() == 0:
        raise ValueError("Probability vector is empty")

    if not torch.isfinite(probabilities).all():
        raise ValueError("Probability vector contains NaN/Inf")

    if torch.any(probabilities < 0):
        raise ValueError("Probability vector contains negative values")

    total = probabilities.sum()

    if not torch.isfinite(total) or total <= 0:
        raise ValueError("Invalid probability normalization")

    probabilities = probabilities / total

    entropy = -(probabilities * torch.log(probabilities.clamp_min(1e-12))).sum()

    value = float(entropy.item())

    if not _is_finite(value):
        raise ValueError("Entropy became NaN/Inf")

    return value


# ---------------------------------------------------------------------------
# Probe generation
# ---------------------------------------------------------------------------


def generate_vision_probes(
    n: int = BOUND_N,
    image_size: int = VISION_IMAGE_SIZE,
    seed: int = 0,
) -> torch.Tensor:
    """
    Generate bounded synthetic Vision probes.

    Shape:
        [N, 3, H, W]

    These probes are deliberately model-independent and do not require
    external image datasets.
    """

    if n < 1:
        raise ValueError("Probe count must be >= 1")

    if n > BOUND_N:
        raise ValueError(
            f"Probe count {n} exceeds safety bound {BOUND_N}"
        )

    if image_size < 1:
        raise ValueError("Image size must be >= 1")

    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)

    probes = torch.rand(
        (n, 3, image_size, image_size),
        generator=generator,
        dtype=torch.float32,
    )

    if not torch.isfinite(probes).all():
        raise ValueError("Generated probes contain NaN/Inf")

    return probes


# ---------------------------------------------------------------------------
# Model inference
# ---------------------------------------------------------------------------


def _extract_logits(output: Any) -> torch.Tensor:
    """
    Extract logits from a standard torchvision-style model output.
    """

    if isinstance(output, torch.Tensor):
        logits = output

    elif hasattr(output, "logits"):
        logits = output.logits

    elif isinstance(output, (tuple, list)) and output:
        logits = output[0]

    else:
        raise ValueError(
            f"Unsupported model output type: {type(output).__name__}"
        )

    if not isinstance(logits, torch.Tensor):
        raise ValueError("Model output is not a tensor")

    if logits.ndim == 1:
        logits = logits.unsqueeze(0)

    if logits.ndim != 2:
        raise ValueError(
            f"Expected logits shape [N,C], got {tuple(logits.shape)}"
        )

    return logits


def _run_inference(model: torch.nn.Module, probes: torch.Tensor) -> torch.Tensor:
    """
    Run bounded inference on the already-trusted model.
    """

    if model is None:
        raise RuntimeError("Trusted model is None")

    if not isinstance(model, torch.nn.Module):
        raise TypeError(
            "Trusted model must be a torch.nn.Module"
        )

    model.eval()

    device = next(model.parameters(), torch.empty(0)).device

    probes = probes.to(device)

    with torch.inference_mode():
        output = model(probes)

    logits = _extract_logits(output)

    if not torch.isfinite(logits).all():
        raise ValueError("Model produced NaN/Inf logits")

    probabilities = torch.softmax(logits, dim=-1)

    if not torch.isfinite(probabilities).all():
        raise ValueError("Softmax produced NaN/Inf")

    if torch.any(probabilities < 0):
        raise ValueError("Softmax produced negative probabilities")

    row_sums = probabilities.sum(dim=-1)

    if not torch.allclose(
        row_sums,
        torch.ones_like(row_sums),
        atol=1e-4,
        rtol=1e-4,
    ):
        raise ValueError("Invalid probability normalization")

    return probabilities


# ---------------------------------------------------------------------------
# STRIP
# ---------------------------------------------------------------------------


def compute_strip_entropy(
    model: torch.nn.Module,
    probes: torch.Tensor,
) -> List[float]:
    """
    Compute prediction entropy for each probe.
    """

    probabilities = _run_inference(model, probes)

    entropies = []

    for row in probabilities:
        entropies.append(_entropy(row))

    return entropies


def _median(values: List[float]) -> float:
    if not values:
        raise ValueError("Cannot compute median of empty list")

    values = sorted(values)
    n = len(values)

    middle = n // 2

    if n % 2:
        return float(values[middle])

    return float((values[middle - 1] + values[middle]) / 2.0)


def _mad(values: List[float], median: Optional[float] = None) -> float:
    """
    Median absolute deviation.
    """

    if not values:
        raise ValueError("Cannot compute MAD of empty list")

    if median is None:
        median = _median(values)

    deviations = [
        abs(float(value) - median)
        for value in values
    ]

    return _median(deviations)


def normalize_h_strip(
    h_strip: float,
    baseline_entropies: List[float],
) -> Dict[str, float]:
    """
    D4 STRIP normalization.

    deviation = H_median - H_STRIP
    Z = deviation / (1.4826 * H_MAD)
    Z_clamped = max(0, Z)
    S_behavior = min(1, Z_clamped / 3)

    D7 edge cases:
        MAD == 0 and target == median -> score 0
        MAD == 0 and target != median -> invalid/degenerate
        fewer than 3 baseline values -> blocked
    """

    if len(baseline_entropies) < 3:
        raise ValueError(
            "BLOCKED: fewer than 3 baseline entropy values"
        )

    if not _is_finite(h_strip):
        raise ValueError("H_STRIP is NaN/Inf")

    if not all(_is_finite(v) for v in baseline_entropies):
        raise ValueError("Baseline entropy contains NaN/Inf")

    median = _median(baseline_entropies)
    mad = _mad(baseline_entropies, median)

    deviation = median - float(h_strip)

    if mad == 0.0:

        if h_strip == median:
            z = 0.0
            score = 0.0
        else:
            raise ValueError(
                "DEGENERATE_DEVIATION: MAD=0 but target differs from median"
            )

    else:
        z = deviation / (MAD_SCALE * mad)

        if not _is_finite(z):
            raise ValueError("STRIP Z-score is NaN/Inf")

        z_clamped = max(0.0, z)

        score = min(1.0, z_clamped / STRIP_Z_SCALE)

    return {
        "h_strip": float(h_strip),
        "h_median": float(median),
        "h_mad": float(mad),
        "deviation": float(deviation),
        "z_score": float(z),
        "s_behavior": float(score),
    }


# ---------------------------------------------------------------------------
# Public behavioral assessment
# ---------------------------------------------------------------------------


def run_behavioral_probe(
    model: Optional[torch.nn.Module] = None,
    *,
    is_quantized: bool = False,
    probe_count: int = BOUND_N,
    seed: int = 0,
) -> Dict[str, Any]:
    """
    Execute the Option 2 behavioral probe.

    Quantized models:
        Behavioral probing is bypassed.

    Non-quantized models:
        Generate probes -> inference -> entropy -> STRIP normalization.
    """

    if is_quantized:
        return {
            "enabled": False,
            "bypassed": True,
            "reason": "quantized_model",
            "s_behavior": None,
        }

    if model is None:
        model = get_trusted_model()

    probes = generate_vision_probes(
        n=probe_count,
        image_size=VISION_IMAGE_SIZE,
        seed=seed,
    )

    entropies = compute_strip_entropy(model, probes)

    if len(entropies) < 3:
        raise RuntimeError(
            "Behavioral probe requires at least 3 entropy values"
        )

    # Simple STRIP summary:
    # Use the median probe entropy as the observed H_STRIP.
    h_strip = _median(entropies)

    normalized = normalize_h_strip(
        h_strip=h_strip,
        baseline_entropies=entropies,
    )

    return {
        "enabled": True,
        "bypassed": False,
        "probe_count": len(entropies),
        "h_strip": normalized["h_strip"],
        "h_median": normalized["h_median"],
        "h_mad": normalized["h_mad"],
        "deviation": normalized["deviation"],
        "z_score": normalized["z_score"],
        "s_behavior": normalized["s_behavior"],
        "method": "vision_strip",
    }
