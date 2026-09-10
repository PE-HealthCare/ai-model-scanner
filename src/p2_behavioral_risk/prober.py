"""
P2 Behavioral Risk Prober
Hackathon Option 2

Scope:
- Vision / ResNet18 only
- Simple STRIP-style behavioral probing
- Maximum 32 probes
- Shannon entropy -> H_STRIP
- Calibration-based S_behavior
- Quantized models bypass behavioral probing
- Fail closed on invalid inference/probabilities

P2 does NOT reload the untrusted SafeTensors artifact.
The trusted model must be handed to P2 by the trusted handoff layer.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import torch

from .config import BOUND_N
from .handoff import TrustedModelContext


# ---------------------------------------------------------------------
# Trusted model handoff
# ---------------------------------------------------------------------

def receive_trusted_model(
    context: TrustedModelContext,
) -> TrustedModelContext:
    """
    Accept an already-created trusted model context.

    P2 must not reload the untrusted SafeTensors artifact.
    """
    if not isinstance(context, TrustedModelContext):
        raise ValueError(
            "P2 requires a valid TrustedModelContext."
        )

    return context


# ---------------------------------------------------------------------
# Probe generation
# ---------------------------------------------------------------------

def generate_probes(
    domain: str,
    n: int = BOUND_N,
) -> torch.Tensor:
    """
    Generate bounded Vision probes.

    Option 2 is Vision-only. The probes are deliberately simple
    and deterministic in shape so the behavioral path remains
    lightweight and reproducible.

    Returns:
        Tensor with shape [n, 3, 224, 224].
    """

    if domain != "VISION":
        raise ValueError(
            f"P2 Option 2 supports VISION only. Got: {domain}"
        )

    if n <= 0:
        raise ValueError("Probe count must be positive.")

    n = min(int(n), BOUND_N)

    # Deterministic probe generation.
    #
    # These are neutral image-like tensors. The model is evaluated
    # on bounded inputs without introducing another learned model.
    generator = torch.Generator()
    generator.manual_seed(42)

    probes = torch.rand(
        (n, 3, 224, 224),
        generator=generator,
        dtype=torch.float32,
    )

    return probes


# ---------------------------------------------------------------------
# Probability validation
# ---------------------------------------------------------------------

def validate_probability_vector(
    probs: Any,
) -> np.ndarray:
    """
    Validate one probability vector.

    Fail closed if:
    - empty
    - NaN / Inf
    - outside [0, 1]
    - does not sum approximately to 1
    """

    probs = np.asarray(probs, dtype=np.float64)

    if probs.size == 0:
        raise ValueError(
            "Empty probability vector."
        )

    if not np.all(np.isfinite(probs)):
        raise ValueError(
            "Probability vector contains NaN or Inf."
        )

    if np.any(probs < 0.0) or np.any(probs > 1.0):
        raise ValueError(
            "Probability vector contains values outside [0, 1]."
        )

    total = float(np.sum(probs))

    if not np.isfinite(total):
        raise ValueError(
            "Probability vector has a non-finite sum."
        )

    if not np.isclose(total, 1.0, atol=1e-5):
        raise ValueError(
            f"Probability vector does not sum to 1.0: {total}"
        )

    return probs


# ---------------------------------------------------------------------
# Bounded inference
# ---------------------------------------------------------------------

def run_bounded_inference(
    model: torch.nn.Module,
    probes: torch.Tensor,
    bound_n: int = BOUND_N,
) -> torch.Tensor:
    """
    Run at most bound_n inference passes.

    Fail closed:
    - no valid output -> RuntimeError
    - any individual pass fails -> RuntimeError
    - invalid output is not silently skipped
    """

    if model is None:
        raise RuntimeError(
            "Trusted model is missing."
        )

    if probes is None or probes.numel() == 0:
        raise RuntimeError(
            "No behavioral probes were generated."
        )

    if bound_n <= 0:
        raise ValueError(
            "Inference bound must be positive."
        )

    model.eval()

    outputs: List[torch.Tensor] = []

    limit = min(
        int(bound_n),
        int(len(probes)),
        BOUND_N,
    )

    failed_passes = 0
    errors: List[str] = []

    with torch.no_grad():
        for i in range(limit):
            try:
                batch = probes[i:i + 1]

                logits = model(batch)

                if not isinstance(logits, torch.Tensor):
                    raise TypeError(
                        "Model output is not a torch.Tensor."
                    )

                if logits.numel() == 0:
                    raise ValueError(
                        "Model returned empty logits."
                    )

                if not torch.all(torch.isfinite(logits)):
                    raise ValueError(
                        "Model returned NaN/Inf logits."
                    )

                # Standard classification output.
                if logits.ndim == 1:
                    logits = logits.unsqueeze(0)

                if logits.ndim != 2:
                    raise ValueError(
                        f"Expected 2D classification logits, "
                        f"got shape {tuple(logits.shape)}"
                    )

                probs = torch.softmax(logits, dim=-1)

                if not torch.all(torch.isfinite(probs)):
                    raise ValueError(
                        "Softmax produced NaN/Inf."
                    )

                outputs.append(probs)

            except Exception as exc:
                failed_passes += 1
                errors.append(
                    f"Pass {i}: {type(exc).__name__}: {exc}"
                )

    if not outputs:
        raise RuntimeError(
            "All behavioral inference passes failed. "
            f"Errors: {errors}"
        )

    if failed_passes > 0:
        raise RuntimeError(
            f"{failed_passes} of {limit} behavioral "
            f"inference passes failed. "
            f"Errors: {errors}"
        )

    return torch.cat(outputs, dim=0)


# ---------------------------------------------------------------------
# Shannon entropy
# ---------------------------------------------------------------------

def shannon_entropy(
    probs: np.ndarray,
) -> float:
    """
    Shannon entropy:

        H(p) = -sum(p * log2(p))

    Zero-probability terms contribute zero.
    """

    probs = validate_probability_vector(probs)

    positive = probs[probs > 0.0]

    if positive.size == 0:
        return 0.0

    value = float(
        -np.sum(
            positive * np.log2(positive)
        )
    )

    if not np.isfinite(value):
        raise ValueError(
            "Computed entropy is NaN/Inf."
        )

    return value


def compute_h_strip(
    softmax_outputs: torch.Tensor,
) -> float:
    """
    Compute H_STRIP as the mean Shannon entropy across
    all behavioral probes.
    """

    if softmax_outputs is None:
        raise ValueError(
            "Softmax outputs are missing."
        )

    if softmax_outputs.numel() == 0:
        raise ValueError(
            "Empty softmax outputs."
        )

    probs = (
        softmax_outputs
        .detach()
        .cpu()
        .numpy()
    )

    entropies = [
        shannon_entropy(row)
        for row in probs
    ]

    if not entropies:
        raise ValueError(
            "No entropy values were produced."
        )

    h_strip = float(np.mean(entropies))

    if not np.isfinite(h_strip):
        raise ValueError(
            "H_STRIP is NaN/Inf."
        )

    return h_strip


# ---------------------------------------------------------------------
# Behavioral normalization
# ---------------------------------------------------------------------

def normalize_h_strip(
    h_strip: float,
    domain: str,
    calibration_data: Dict[str, Any],
) -> float:
    """
    Convert H_STRIP into S_behavior.

    Option 2 uses calibration-relative deviation.

    Locked form:

        deviation = H_median - H_STRIP
        Z = deviation / (1.4826 * H_MAD)
        Z_clamped = max(0, Z)
        S_behavior = min(1, Z_clamped / 3)

    Edge cases:
    - fewer than 3 baseline values -> blocked
    - MAD == 0 and target == median -> 0
    - MAD == 0 and target != median -> blocked
    - NaN/Inf -> blocked
    """

    if domain != "VISION":
        raise ValueError(
            f"P2 Option 2 supports VISION only. Got: {domain}"
        )

    if not np.isfinite(h_strip):
        raise ValueError(
            "H_STRIP contains NaN/Inf."
        )

    if not isinstance(calibration_data, dict):
        raise ValueError(
            "Calibration data is missing or invalid."
        )

    if domain not in calibration_data:
        raise KeyError(
            f"No calibration data for domain '{domain}'."
        )

    calibration = calibration_data[domain]

    # Preferred locked representation.
    if all(
        key in calibration
        for key in ("median", "mad")
    ):
        median = float(calibration["median"])
        mad = float(calibration["mad"])

    # Compatibility path if the existing calibration artifact
    # still stores baseline values.
    elif "baseline" in calibration:
        baseline = np.asarray(
            calibration["baseline"],
            dtype=np.float64,
        )

        if baseline.size < 3:
            raise RuntimeError(
                "Fewer than 3 baseline values available."
            )

        if not np.all(np.isfinite(baseline)):
            raise ValueError(
                "Calibration baseline contains NaN/Inf."
            )

        median = float(np.median(baseline))
        mad = float(
            np.median(
                np.abs(baseline - median)
            )
        )

    elif "values" in calibration:
        baseline = np.asarray(
            calibration["values"],
            dtype=np.float64,
        )

        if baseline.size < 3:
            raise RuntimeError(
                "Fewer than 3 calibration values available."
            )

        if not np.all(np.isfinite(baseline)):
            raise ValueError(
                "Calibration values contain NaN/Inf."
            )

        median = float(np.median(baseline))
        mad = float(
            np.median(
                np.abs(baseline - median)
            )
        )

    else:
        raise KeyError(
            "Calibration must contain median/mad "
            "or baseline/values."
        )

    if not np.isfinite(median) or not np.isfinite(mad):
        raise ValueError(
            "Calibration median/MAD contains NaN/Inf."
        )

    if mad == 0.0:
        if h_strip == median:
            return 0.0

        raise RuntimeError(
            "DEGENERATE_DEVIATION: zero MAD and "
            "H_STRIP differs from calibration median."
        )

    deviation = median - h_strip

    z = deviation / (1.4826 * mad)

    if not np.isfinite(z):
        raise ValueError(
            "Behavioral Z-score is NaN/Inf."
        )

    z_clamped = max(0.0, z)

    s_behavior = min(
        1.0,
        z_clamped / 3.0,
    )

    if not np.isfinite(s_behavior):
        raise ValueError(
            "S_behavior is NaN/Inf."
        )

    return float(s_behavior)


# ---------------------------------------------------------------------
# Complete behavioral assessment
# ---------------------------------------------------------------------

def get_behavioral_result(
    is_quantized: bool,
    domain: str,
    model: torch.nn.Module | None,
    calibration_data: Dict[str, Any],
    bound_n: int = BOUND_N,
) -> Dict[str, Any]:
    """
    Complete Option 2 behavioral assessment.

    Quantized:
        behavioral probing is intentionally bypassed.

    Non-quantized:
        Vision STRIP is executed.
    """

    if not isinstance(is_quantized, bool):
        raise TypeError(
            "is_quantized must be boolean."
        )

    if is_quantized:
        return {
            "s_behavior": None,
            "h_strip": None,
            "bypassed_behavior": True,
            "probe_count": 0,
            "successful_probe_count": 0,
            "failed_probe_count": 0,
        }

    if domain != "VISION":
        raise ValueError(
            f"P2 Option 2 supports VISION only. Got: {domain}"
        )

    if model is None:
        raise RuntimeError(
            "Trusted model is required for "
            "non-quantized behavioral probing."
        )

    probes = generate_probes(
        domain=domain,
        n=bound_n,
    )

    outputs = run_bounded_inference(
        model=model,
        probes=probes,
        bound_n=bound_n,
    )

    h_strip = compute_h_strip(outputs)

    s_behavior = normalize_h_strip(
        h_strip=h_strip,
        domain=domain,
        calibration_data=calibration_data,
    )

    return {
        "s_behavior": s_behavior,
        "h_strip": h_strip,
        "bypassed_behavior": False,
        "probe_count": int(len(probes)),
        "successful_probe_count": int(len(outputs)),
        "failed_probe_count": 0,
    }
