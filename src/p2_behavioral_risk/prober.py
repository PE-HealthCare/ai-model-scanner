"""Phase 2 behavioral handoff boundary plus Phase 1 mock producer."""

from __future__ import annotations

from src.p1_static_engine.analyzer import TrustedModelContext


def receive_trusted_model(context: TrustedModelContext) -> TrustedModelContext:
    """Accept the already-created trusted context without reloading the artifact."""
    if not isinstance(context, TrustedModelContext):
        raise ValueError("D2 handoff requires a TrustedModelContext")
    return context


<<<<<<< Updated upstream
def build_mock_risk_results(ml_results: dict, generation_commit: str) -> dict:
    if ml_results.get("producer") != "P3" or ml_results.get("mock_status") != "MOCK":
        raise ValueError("Phase 1 mock P2 requires a P3 MOCK ML artifact")
    if ml_results.get("generation_commit") != generation_commit:
        raise ValueError("Phase 1 P2 rejects stale P3 artifact generation")
    s_static, s_behavior = 0.10, 0.05
    p_tamper = float(ml_results["p_tamper"])
    mrs_score = min(100.0, 40 * s_static + 35 * p_tamper + 25 * s_behavior)
    verdict = "PASS" if mrs_score < 35 else "REVIEW" if mrs_score < 70 else "FAIL"
=======
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


def get_behavioral_result(is_quantized, domain, model, calibration_data, bound_n=BOUND_N):
    """
    Option 2: VISION-only STRIP probing.
    Fails closed on any error.
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

    if domain != "VISION":
        raise ValueError(f"P2 Option 2 supports VISION only. Got: {domain}")

    probes = generate_probes(domain, n=bound_n)
    outputs = run_bounded_inference(model, probes, bound_n)
    h_strip = compute_h_strip(outputs)
    s_behavior = normalize_h_strip(h_strip, domain, calibration_data)

>>>>>>> Stashed changes
    return {
        "producer": "P2", "mock_status": "MOCK", "contract_version": "1.0", "generation_commit": generation_commit,
        "mrs_score": mrs_score, "verdict": verdict, "s_static": s_static, "p_tamper": p_tamper, "s_behavior": s_behavior,
    }
