"""P1-owned deterministic utility: real quantized (INT8) ResNet18 corpus.

Generates a clean + tampered INT8 ResNet18 pair plus real P1 feature
outputs to unblock P3 D11 training. Fixture/utility only: never alters
P1 semantics, contracts, or P2/P3 code. Drives the real P1 path
``intake_model() -> extract_features()`` and never fabricates features.

INT8 pattern mirrors tests/test_intake.py
``test_quantized_int8_is_accepted_and_preserved``: every FP tensor of
``resnet18(weights=None)`` is converted with ``tensor.to(torch.int8)``;
integer control tensors (e.g. BatchNorm num_batches_tracked) untouched.
Names/shapes preserved exactly for the P1 trust boundary.

Determinism contract:
* SEED = 42 (torch/numpy/random) before resnet18(weights=None) build.
* MUTATION_TENSOR = "layer4.1.conv2.weight" ([512, 512, 3, 3]).
* MUTATION_COUNT = 1024 first row-major elements.
* MUTATION_DELTA = 7: v' = wrap_int8(v + 7) = ((v+7+128) % 256) - 128
  on the INT8 representation itself (int16 intermediate, back to int8).
  7 mod 256 != 0 so exactly 1024 INT8 elements change; wraps, never
  saturates, so no element stays unchanged.

Outputs (isolated; never touches data/outputs/features.json):
* data/outputs/quantized_corpus/resnet18_int8_clean.safetensors
* data/outputs/quantized_corpus/resnet18_int8_tampered.safetensors
* data/outputs/quantized_corpus/p1_features_clean.json
* data/outputs/quantized_corpus/p1_features_tampered.json

Usage: python tests/fixtures/generate_quantized_corpus.py
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import torch
from safetensors import safe_open
from safetensors.torch import save_file

from src.p1_static_engine.analyzer import extract_features, intake_model

SEED = 42
ARCHITECTURE = "resnet18"
GENERATION_COMMIT = "quantized-corpus-seed42-v1"

MUTATION_TENSOR = "layer4.1.conv2.weight"
MUTATION_COUNT = 1024
MUTATION_DELTA = 7

FP_ONLY_FIELDS = (
    "entropy", "pov_chi2", "lsb_kl", "mean", "std",
    "skewness", "kurtosis", "sparsity", "outlier_pct",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "outputs" / "quantized_corpus"
CLEAN_PATH = OUT_DIR / "resnet18_int8_clean.safetensors"
TAMPERED_PATH = OUT_DIR / "resnet18_int8_tampered.safetensors"
CLEAN_FEATURES_PATH = OUT_DIR / "p1_features_clean.json"
TAMPERED_FEATURES_PATH = OUT_DIR / "p1_features_tampered.json"


def build_quantized_state_dict(seed: int = SEED) -> dict:
    """Build architecture-valid resnet18 state dict with all FP -> INT8."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    from torchvision.models import resnet18

    model = resnet18(weights=None)
    state_dict = model.state_dict()
    quantized = {}
    for name, tensor in state_dict.items():
        if tensor.is_floating_point():
            quantized[name] = tensor.to(torch.int8)
        else:
            quantized[name] = tensor.clone()
    return quantized

def apply_int8_mutation(state_dict: dict) -> dict:
    """Deterministically mutate ACTUAL INT8 values; return mutated copy."""
    if MUTATION_TENSOR not in state_dict:
        raise KeyError(f"Mutation tensor {MUTATION_TENSOR!r} missing")
    target = state_dict[MUTATION_TENSOR]
    if target.dtype != torch.int8:
        raise TypeError(f"Mutation target must be INT8, got {target.dtype}")
    if target.numel() < MUTATION_COUNT:
        raise ValueError("Mutation target smaller than MUTATION_COUNT")
    mutated = {k: v.clone() for k, v in state_dict.items()}
    flat = mutated[MUTATION_TENSOR].reshape(-1)
    idx = torch.arange(MUTATION_COUNT)
    before = flat[idx].to(torch.int16)
    after = ((before + MUTATION_DELTA + 128) % 256 - 128).to(torch.int8)
    flat[idx] = after
    changed = int((flat[idx].to(torch.int16) != before).sum().item())
    if changed != MUTATION_COUNT:
        raise AssertionError(f"Mutation changed {changed}, expected {MUTATION_COUNT}")
    return mutated


def count_tensor_differences(path_a: Path, path_b: Path) -> tuple:
    """Count element-wise differences between two SafeTensors artifacts."""
    total = 0
    per_tensor = {}
    with safe_open(path_a, framework="pt") as a, safe_open(path_b, framework="pt") as b:
        if set(a.keys()) != set(b.keys()):
            raise AssertionError("Tensor key sets differ between artifacts")
        for key in a.keys():
            ta, tb = a.get_tensor(key), b.get_tensor(key)
            if ta.shape != tb.shape or ta.dtype != tb.dtype:
                raise AssertionError(f"Shape/dtype mismatch for {key}")
            diff = int((ta.reshape(-1) != tb.reshape(-1)).sum().item())
            per_tensor[key] = diff
            total += diff
    return total, per_tensor


def run_p1(path: Path) -> dict:
    """Run the real P1 path: intake_model() -> extract_features()."""
    ctx = intake_model(path, declared_architecture=ARCHITECTURE)
    return extract_features(ctx, GENERATION_COMMIT)


def verify_p1_output(output: dict, artifact_path: Path, label: str) -> None:
    """Verify every required P1 property for one artifact output."""
    assert output["producer"] == "P1", f"{label}: bad producer"
    assert output["mock_status"] == "VERIFIED-REAL", f"{label}: bad mock_status"
    assert output["is_quantized"] is True, f"{label}: not quantized"
    assert output["layer_count"] == len(output["static_features"]), (
        f"{label}: layer_count mismatch")
    assert output["layer_count"] >= 3, f"{label}: invalid layer_count"
    with safe_open(artifact_path, framework="pt") as st:
        int8_names = {k for k in st.keys() if st.get_slice(k).get_dtype() == "I8"}
    produced = [f["layer_name"] for f in output["static_features"]]
    # layer_name must be the real P1-produced identity: exactly the INT8
    # tensor names carried through intake (control tensors excluded by P1).
    assert set(produced) == int8_names, f"{label}: layer identity mismatch"
    assert len(set(produced)) == len(produced), f"{label}: dup layers"
    for feat in output["static_features"]:
        ks = feat["ks_stat"]
        assert isinstance(ks, float), f"{label}: ks_stat not float"
        assert math.isfinite(ks) and 0.0 <= ks <= 1.0, (
            f"{label}: ks_stat out of range: {ks}")
        for field in FP_ONLY_FIELDS:
            assert feat[field] is None, f"{label}: {field} not null"
        assert not any(
            isinstance(v, float) and math.isnan(v) for v in feat.values()
        ), f"{label}: NaN in features"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clean = build_quantized_state_dict()
    tampered = apply_int8_mutation(clean)
    save_file(clean, CLEAN_PATH)
    save_file(tampered, TAMPERED_PATH)
    total_diff, per_tensor = count_tensor_differences(CLEAN_PATH, TAMPERED_PATH)
    assert total_diff == MUTATION_COUNT, (
        f"Artifacts differ in {total_diff}, expected {MUTATION_COUNT}")
    assert per_tensor[MUTATION_TENSOR] == MUTATION_COUNT
    assert all(v == 0 for k, v in per_tensor.items() if k != MUTATION_TENSOR)
    clean_out = run_p1(CLEAN_PATH)
    tampered_out = run_p1(TAMPERED_PATH)
    verify_p1_output(clean_out, CLEAN_PATH, "clean")
    verify_p1_output(tampered_out, TAMPERED_PATH, "tampered")
    for output, path in ((clean_out, CLEAN_FEATURES_PATH),
                         (tampered_out, TAMPERED_FEATURES_PATH)):
        with path.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            f.write("\n")
    print(f"seed: {SEED}")
    print(f"generation_commit: {GENERATION_COMMIT}")
    print(f"clean artifact: {CLEAN_PATH}")
    print(f"tampered artifact: {TAMPERED_PATH}")
    print(f"clean P1 output: {CLEAN_FEATURES_PATH}")
    print(f"tampered P1 output: {TAMPERED_FEATURES_PATH}")
    print(f"mutation: tensor={MUTATION_TENSOR} count={MUTATION_COUNT} "
          f"op=wrap_int8(v + {MUTATION_DELTA}) changed={MUTATION_COUNT}")
    print(f"tensor-level difference: total={total_diff} (all in {MUTATION_TENSOR})")
    for label, output in (("clean", clean_out), ("tampered", tampered_out)):
        ks_vals = [f["ks_stat"] for f in output["static_features"]]
        print(f"{label}: producer=P1 mock_status=VERIFIED-REAL "
              f"is_quantized=True layer_count={output['layer_count']} "
              f"ks_min={min(ks_vals):.6f} ks_max={max(ks_vals):.6f} "
              f"fp_fields_all_null=True")
    print("OK: both artifacts verified through real P1 intake + extraction")


if __name__ == "__main__":
    main()
