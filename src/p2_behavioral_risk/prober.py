# src/p2_behavioral_risk/prober.py
import torch
import numpy as np
from scipy.stats import entropy
from .config import BOUND_N, NLP_VOCAB_SIZE, NLP_SEQ_LEN, ENTROPY_MIN, ENTROPY_MAX


def generate_probes(domain: str, n: int = BOUND_N):
    """Domain-aware probe generator."""
    domain = domain.upper()
    if domain == "VISION":
        return torch.randn(n, 3, 224, 224)
    elif domain == "NLP":
        return torch.randint(0, NLP_VOCAB_SIZE, (n, NLP_SEQ_LEN), dtype=torch.long)
    else:
        raise ValueError(f"Unsupported domain: {domain}")


def run_bounded_inference(model, probes, bound_n=BOUND_N):
    """
    Bounded inference loop.
    Fails if any single pass fails – no silent skipping.
    """
    model.eval()
    outputs = []
    failed_passes = 0
    errors = []

    with torch.no_grad():
        limit = min(bound_n, len(probes))
        for i in range(limit):
            try:
                logits = model(probes[i:i+1])
                probs = torch.softmax(logits, dim=-1)
                outputs.append(probs)
            except Exception as e:
                failed_passes += 1
                errors.append(f"Pass {i}: {e}")

    if not outputs:
        raise RuntimeError("All inference passes failed. No valid outputs.")

    if failed_passes > 0:
        raise RuntimeError(
            f"{failed_passes} out of {limit} inference passes failed. "
            f"Errors: {errors}"
        )

    return torch.cat(outputs, dim=0)


def validate_probability_vector(probs):
    """
    Validate that a probability vector sums to 1, is finite, and within [0,1].
    """
    probs = np.asarray(probs, dtype=np.float64)

    if probs.size == 0:
        raise ValueError("Empty probability vector.")

    if not np.all(np.isfinite(probs)):
        raise ValueError("Probability vector contains NaN or Inf.")

    if np.any(probs < 0.0) or np.any(probs > 1.0):
        raise ValueError("Probability vector contains invalid probabilities.")

    total = float(np.sum(probs))
    if not np.isfinite(total):
        raise ValueError("Probability vector has non-finite sum.")

    if not np.isclose(total, 1.0, atol=1e-5):
        raise ValueError(f"Probability vector does not sum to 1.0: {total}")

    return probs


def compute_h_strip(softmax_outputs):
    """
    Compute STRIP entropy H_STRIP as mean Shannon entropy across probes.
    Raises ValueError on NaN/Inf.
    """
    if softmax_outputs.numel() == 0:
        raise ValueError("Empty softmax outputs – cannot compute entropy.")

    probs = softmax_outputs.detach().cpu().numpy()
    validated_probs = [validate_probability_vector(p) for p in probs]
    per_pass_entropy = [entropy(p) for p in validated_probs]
    h_strip = float(np.mean(per_pass_entropy))

    if np.isnan(h_strip) or np.isinf(h_strip):
        raise ValueError(f"Invalid entropy value: {h_strip}")

    return h_strip


def normalize_h_strip(h_strip, domain, calibration_data, mock_mode=False):
    """
    D4: Convert H_STRIP to S_behavior ∈ [0,1] using baseline-relative deviation.
    """
    if not mock_mode:
        mean = calibration_data[domain]["mean"]
        std = calibration_data[domain]["std"]
        raw = (h_strip - mean) / (3 * std)
        return float(np.clip(raw, 0, 1))
    else:
        clipped = max(ENTROPY_MIN, min(ENTROPY_MAX, h_strip))
        return (clipped - ENTROPY_MIN) / (ENTROPY_MAX - ENTROPY_MIN)


def get_behavioral_result(is_quantized, domain, model, calibration_data,
                          bound_n=BOUND_N, mock_mode=False):
    """
    Main entry point for behavioral probing.
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
    outputs = run_bounded_inference(model, probes, bound_n)
    h_strip = compute_h_strip(outputs)
    s_behavior = normalize_h_strip(h_strip, domain, calibration_data, mock_mode)

    return {
        "s_behavior": s_behavior,
        "h_strip": h_strip,
        "bypassed_behavior": False,
        "probe_count": len(probes),
        "successful_probe_count": len(outputs),
        "failed_probe_count": 0,
    }