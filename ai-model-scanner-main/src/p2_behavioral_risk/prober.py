# src/p2_behavioral_risk/prober.py
import torch
import numpy as np
from scipy.stats import entropy
from .config import BOUND_N, NLP_VOCAB_SIZE, NLP_SEQ_LEN, ENTROPY_MIN, ENTROPY_MAX

def generate_probes(domain: str, n: int = BOUND_N):
    """Step 2: Domain-aware probe generator."""
    domain = domain.upper()
    if domain == "VISION":
        return torch.randn(n, 3, 224, 224)
    elif domain == "NLP":
        return torch.randint(0, NLP_VOCAB_SIZE, (n, NLP_SEQ_LEN), dtype=torch.long)
    else:
        raise ValueError(f"Unsupported domain: {domain}")  # Fail loud.

def run_bounded_inference(model, probes, bound_n=BOUND_N):
    """Step 4: Bounded inference loop."""
    model.eval()
    outputs = []
    with torch.no_grad():  # Inference-only requirement
        for i in range(min(bound_n, len(probes))):
            try:
                logits = model(probes[i:i+1])
                probs = torch.softmax(logits, dim=-1)
                outputs.append(probs)
            except Exception as e:
                # Step 4b: Single bad pass doesn't crash the whole loop
                print(f"Warning: Pass {i} failed: {e}. Skipping.")
                continue
    if not outputs:
        return torch.tensor([])  # Graceful fallback
    return torch.cat(outputs, dim=0)

def compute_h_strip(softmax_outputs):
    """Step 5: Entropy calculator."""
    if softmax_outputs.numel() == 0:
        return 0.0
    probs = softmax_outputs.numpy()
    per_pass_entropy = [entropy(p) for p in probs]
    h_strip = float(np.mean(per_pass_entropy))
    # Guard against NaN/Inf
    if np.isnan(h_strip) or np.isinf(h_strip):
        return 0.0  # Degenerate guard
    return h_strip

def normalize_h_strip(h_strip):
    """Step 5b (D4 Placeholder). Mark clearly for team."""
    # DECISION REQUIRED (D4): Exact normalization formula pending.
    # Placeholder: Min-Max scaling to [0,1] using guessed bounds.
    clipped = max(ENTROPY_MIN, min(ENTROPY_MAX, h_strip))
    return (clipped - ENTROPY_MIN) / (ENTROPY_MAX - ENTROPY_MIN)

def get_behavioral_result(is_quantized, domain, model, bound_n=BOUND_N):
    """Step 6: Quantized Bypass Branch."""
    if is_quantized:
        return {"s_behavior": None, "bypassed_behavior": True}
    
    probes = generate_probes(domain, n=bound_n)
    outputs = run_bounded_inference(model, probes, bound_n)
    h_strip = compute_h_strip(outputs)
    s_behavior = normalize_h_strip(h_strip)
    return {"s_behavior": s_behavior, "bypassed_behavior": False}