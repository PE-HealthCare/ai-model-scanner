# src/p2_behavioral_risk/prober.py

import torch
import numpy as np
from scipy.stats import entropy

from .config import BOUND_N, NLP_VOCAB_SIZE, NLP_SEQ_LEN


def generate_probes(domain: str, n: int = BOUND_N):
    """Generate exactly n domain-appropriate STRIP probes."""
    domain = domain.upper()

    if n <= 0:
        raise ValueError("Probe count must be positive.")

    if domain == "VISION":
        return torch.randn(n, 3, 224, 224)

    if domain == "NLP":
        return torch.randint(
            0,
            NLP_VOCAB_SIZE,
            (n, NLP_SEQ_LEN),
            dtype=torch.long,
        )

    raise ValueError(f"Unsupported domain: {domain}")


def run_bounded_inference(model, probes, bound_n=BOUND_N):
    """
    Run bounded inference.

    Fail closed:
    - every requested probe must succeed
    - no failed probe is silently skipped
    - no empty result is converted to a score
    """
    if model is None:
        raise RuntimeError("Trusted model is required for behavioral probing.")

    if len(probes) < bound_n:
        raise RuntimeError(
            f"Insufficient probes: required {bound_n}, got {len(probes)}."
        )

    model.eval()
    outputs = []

    with torch.no_grad():
        for i in range(bound_n):
            try:
                logits = model(probes[i:i + 1])

                if not isinstance(logits, torch.Tensor):
                    raise TypeError("Model output must be a torch.Tensor.")

                if logits.numel() == 0:
                    raise ValueError("Model returned empty output.")

                if not torch.all(torch.isfinite(logits)):
                    raise ValueError(
                        f"Model returned NaN/Inf logits on probe {i}."
                    )

                probs = torch.softmax(logits, dim=-1)

                if not torch.all(torch.isfinite(probs)):
                    raise ValueError(
                        f"Softmax produced NaN/Inf on probe {i}."
                    )

                outputs.append(probs)

            except Exception as exc:
                raise RuntimeError(
                    f"Behavioral probing failed on probe {i}: {exc}"
                ) from exc

    if len(outputs) != bound_n:
        raise RuntimeError(
            f"Probe count mismatch: expected {bound_n}, got {len(outputs)}."
        )

    return torch.cat(outputs, dim=0)


def validate_probability_vector(probs):
    """Validate one probability distribution."""
    probs = np.asarray(probs, dtype=np.float64)

    if probs.size == 0:
        raise ValueError("Empty probability vector.")

    if not np.all(np.isfinite(probs)):
        raise ValueError("Probability vector contains NaN or Inf.")

    if np.any(probs < 0.0) or np.any(probs > 1.0):
        raise ValueError(
            "Probability vector contains values outside [0,1]."
        )

    total = float(np.sum(probs))

    if not np.isfinite(total):
        raise ValueError("Probability vector sum is non-finite.")

    if not np.isclose(total, 1.0, atol=1e-5):
        raise ValueError(
            f"Probability vector does not sum to 1.0: {total}"
        )

    return probs


def compute_h_strip(softmax_outputs):
    """
    D3/D4:
    H_STRIP = mean Shannon entropy over all probe distributions.
    """
    if softmax_outputs is None:
        raise ValueError("Softmax outputs cannot be None.")

    if softmax_outputs.numel() == 0:
        raise ValueError(
            "Empty softmax outputs – cannot compute H_STRIP."
        )

    probs = softmax_outputs.detach().cpu().numpy()

    if probs.ndim != 2:
        raise ValueError(
            f"Expected 2-D probability matrix, got shape {probs.shape}."
        )

    per_probe_entropy = []

    for i, probability_vector in enumerate(probs):
        validated = validate_probability_vector(probability_vector)
        h = float(entropy(validated))

        if not np.isfinite(h):
            raise ValueError(
                f"Invalid entropy on probe {i}: {h}"
            )

        per_probe_entropy.append(h)

    if len(per_probe_entropy) != len(probs):
        raise RuntimeError("Not all probes produced entropy values.")

    h_strip = float(np.mean(per_probe_entropy))

    if not np.isfinite(h_strip):
        raise ValueError(
            f"H_STRIP is non-finite: {h_strip}"
        )

    return h_strip


def normalize_h_strip(h_strip, domain, calibration_data, mock_mode=False):
    """
    D4 LOCKED behavioral normalization.

    deviation = H_median - H_STRIP
    Z = deviation / (1.4826 * H_MAD)
    Z_clamped = max(0, Z)
    S_behavior = min(1, Z_clamped / 3)

    Zero-MAD handling:
      MAD == 0 and target == median -> 0
      MAD == 0 and target != median -> unavailable/blocked
    """

    if not np.isfinite(h_strip):
        raise ValueError("H_STRIP must be finite.")

    domain = domain.upper()

    if domain not in calibration_data:
        raise RuntimeError(
            f"No calibration data available for domain {domain}."
        )

    calibration = calibration_data[domain]

    required = ["median", "mad"]

    for key in required:
        if key not in calibration:
            raise RuntimeError(
                f"Calibration data missing required D4 field: {key}"
            )

    h_median = float(calibration["median"])
    h_mad = float(calibration["mad"])

    if not np.isfinite(h_median):
        raise ValueError("Calibration median is non-finite.")

    if not np.isfinite(h_mad) or h_mad < 0:
        raise ValueError("Calibration MAD is invalid.")

    # D7 zero-MAD handling.
    if h_mad == 0.0:
        if h_strip == h_median:
            return 0.0

        raise RuntimeError(
            "DEGENERATE_DEVIATION: H_MAD is zero and "
            "H_STRIP differs from calibration median."
        )

    deviation = h_median - h_strip
    z = deviation / (1.4826 * h_mad)

    if not np.isfinite(z):
        raise ValueError("Behavioral Z-score is non-finite.")

    z_clamped = max(0.0, z)

    s_behavior = min(1.0, z_clamped / 3.0)

    return float(s_behavior)


def get_behavioral_result(
    is_quantized,
    domain,
    model,
    calibration_data,
    bound_n=BOUND_N,
    mock_mode=False,
):
    """
    Main P2 behavioral assessment.

    Quantized models bypass behavioral probing.
    Non-quantized models require exactly bound_n successful probes.
    """

    if is_quantized:
        return {
            "s_behavior": None,
            "h_strip": None,
            "bypassed_behavior": True,
            "probe_count": 0,
            "successful_probe_count": 0,
            "failed_probe_count": 0,
        }

    probes = generate_probes(domain, n=bound_n)

    outputs = run_bounded_inference(
        model,
        probes,
        bound_n=bound_n,
    )

    h_strip = compute_h_strip(outputs)

    s_behavior = normalize_h_strip(
        h_strip,
        domain,
        calibration_data,
        mock_mode=mock_mode,
    )

    return {
        "s_behavior": s_behavior,
        "h_strip": h_strip,
        "bypassed_behavior": False,
        "probe_count": bound_n,
        "successful_probe_count": bound_n,
        "failed_probe_count": 0,
    }
