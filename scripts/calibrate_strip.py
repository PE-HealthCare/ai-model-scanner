"""
Empirical Calibration Experiment for D3 STRIP Baseline.
Owner: Person 2 (Muscle)
Target: Verified Clean Reference ResNet18 (VISION)
Constraint: Strict D-drive containment (TORCH_HOME on D: drive, zero C: writes)
"""

import os
import sys
from pathlib import Path

# STRICT D-DRIVE CONTAINMENT: Set cache directories BEFORE any torch/torchvision imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
CACHE_DIR = WORKSPACE_ROOT / ".cache"
TORCH_CACHE = CACHE_DIR / "torch"
TORCH_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["TORCH_HOME"] = str(TORCH_CACHE)
os.environ["HF_HOME"] = str(CACHE_DIR / "huggingface")

import json
import hashlib
from datetime import datetime
import subprocess

import torch
import numpy as np
from scipy.stats import entropy

import torchvision.models as models
from torchvision.models import ResNet18_Weights


def get_git_commit() -> str:
    """Retrieve current git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN"


def compute_model_hash(model: torch.nn.Module) -> str:
    """Compute SHA-256 hash across all model parameters."""
    hasher = hashlib.sha256()
    for name, param in sorted(model.named_parameters()):
        hasher.update(name.encode("utf-8"))
        hasher.update(param.detach().cpu().numpy().tobytes())
    return hasher.hexdigest()


def validate_probability_vector(probs: np.ndarray) -> np.ndarray:
    """Validate one softmax probability vector according to prober.py contract."""
    probs = np.asarray(probs, dtype=np.float64)
    if probs.size == 0:
        raise ValueError("Empty probability vector.")
    if not np.all(np.isfinite(probs)):
        raise ValueError("Probability vector contains NaN or Inf.")
    if np.any(probs < 0.0) or np.any(probs > 1.0):
        raise ValueError("Probability vector contains values outside [0, 1].")
    total = float(np.sum(probs))
    if not np.isclose(total, 1.0, atol=1e-5):
        raise ValueError(f"Probability vector does not sum to 1.0: {total}")
    return probs


def run_vision_calibration(repetitions: int = 30, probe_count: int = 32, seed: int = 42) -> dict:
    """Run empirical STRIP calibration on verified clean ResNet18."""
    print("=" * 70)
    print("D3 STRIP CALIBRATION EXPERIMENT — VISION (ResNet18)")
    print("=" * 70)
    print(f"TORCH_HOME Cache: {os.environ.get('TORCH_HOME')}")
    print("Loading official torchvision ResNet18 with default clean ImageNet weights...")
    
    weights = ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights)
    model.eval()

    model_sha256 = compute_model_hash(model)
    print(f"Architecture: resnet18")
    print(f"Weights version: {weights}")
    print(f"Weights SHA-256: {model_sha256}")
    print(f"Total parameters: {sum(p.numel() for p in model.parameters()):,}")

    torch.manual_seed(seed)
    np.random.seed(seed)

    raw_probe_entropies = []  # 30 runs x 32 probes = 960 raw measurements
    run_mean_entropies = []   # 30 run averages

    print(f"\nExecuting {repetitions} calibration passes of {probe_count} probes each on CPU...")
    start_time = datetime.now()

    with torch.no_grad():
        for run_idx in range(repetitions):
            # 32 domain-appropriate Gaussian float image probes
            probes = torch.randn(probe_count, 3, 224, 224)
            run_entropies = []

            for probe_idx in range(probe_count):
                single_probe = probes[probe_idx:probe_idx + 1]
                logits = model(single_probe)
                probs = torch.softmax(logits, dim=-1).detach().cpu().numpy()[0]
                valid_p = validate_probability_vector(probs)
                h = float(entropy(valid_p))
                if np.isnan(h) or np.isinf(h):
                    raise ValueError(f"Invalid entropy value: {h}")
                run_entropies.append(h)

            run_mean = float(np.mean(run_entropies))
            raw_probe_entropies.append(run_entropies)
            run_mean_entropies.append(run_mean)

            print(f"  Pass {run_idx+1:02d}/{repetitions}: Mean H_STRIP = {run_mean:.4f} "
                  f"(Min: {min(run_entropies):.4f}, Max: {max(run_entropies):.4f}, Std: {np.std(run_entropies):.4f})")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nCompleted {repetitions * probe_count} forward passes in {elapsed:.2f} seconds ({elapsed / (repetitions * probe_count):.3f}s/pass).")

    # Aggregate analysis across all 960 raw probe entropy measurements
    all_probes_flat = [h for r in raw_probe_entropies for h in r]

    # Robust statistics (MAD)
    med_runs = float(np.median(run_mean_entropies))
    mad_runs = float(np.median(np.abs(run_mean_entropies - med_runs)))

    med_probes = float(np.median(all_probes_flat))
    mad_probes = float(np.median(np.abs(all_probes_flat - med_probes)))

    return {
        "model_identity": {
            "declared_architecture": "resnet18",
            "source_library": "torchvision.models",
            "weights_version": str(weights),
            "weights_sha256": model_sha256,
            "num_classes": 1000,
            "max_theoretical_entropy": float(np.log(1000))
        },
        "domain": "VISION",
        "probe_configuration": {
            "probe_count_per_run": probe_count,
            "repetitions": repetitions,
            "total_probes_measured": len(all_probes_flat),
            "tensor_shape": [probe_count, 3, 224, 224],
            "probe_dtype": "torch.float32",
            "probe_distribution": "torch.randn standard Gaussian N(0, 1)",
            "initial_seed": seed
        },
        "statistics_run_means": {
            "description": "Statistics across the 30 repeated 32-probe run averages (H_STRIP)",
            "sample_count": len(run_mean_entropies),
            "mean": float(np.mean(run_mean_entropies)),
            "median": med_runs,
            "mad": mad_runs,
            "std": float(np.std(run_mean_entropies)),
            "min": float(np.min(run_mean_entropies)),
            "max": float(np.max(run_mean_entropies)),
            "percentiles": {
                "p5": float(np.percentile(run_mean_entropies, 5)),
                "p10": float(np.percentile(run_mean_entropies, 10)),
                "p25": float(np.percentile(run_mean_entropies, 25)),
                "p50": float(np.percentile(run_mean_entropies, 50)),
                "p75": float(np.percentile(run_mean_entropies, 75)),
                "p90": float(np.percentile(run_mean_entropies, 90)),
                "p95": float(np.percentile(run_mean_entropies, 95))
            },
            "values": run_mean_entropies
        },
        "statistics_all_probes": {
            "description": "Statistics across all 960 individual probe entropy measurements",
            "sample_count": len(all_probes_flat),
            "mean": float(np.mean(all_probes_flat)),
            "median": med_probes,
            "mad": mad_probes,
            "std": float(np.std(all_probes_flat)),
            "min": float(np.min(all_probes_flat)),
            "max": float(np.max(all_probes_flat)),
            "percentiles": {
                "p5": float(np.percentile(all_probes_flat, 5)),
                "p10": float(np.percentile(all_probes_flat, 10)),
                "p25": float(np.percentile(all_probes_flat, 25)),
                "p50": float(np.percentile(all_probes_flat, 50)),
                "p75": float(np.percentile(all_probes_flat, 75)),
                "p90": float(np.percentile(all_probes_flat, 90)),
                "p95": float(np.percentile(all_probes_flat, 95))
            }
        },
        "raw_measurements": {
            "per_probe_entropies_by_run": raw_probe_entropies
        }
    }


def main():
    output_dir = PROJECT_ROOT / "data" / "calibration"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "strip_calibration.json"

    vision_calibration = run_vision_calibration(repetitions=30, probe_count=32, seed=42)

    payload = {
        "calibration_metadata": {
            "producer": "P2",
            "purpose": "D3 empirical baseline measurement for D4 normalization",
            "generated_at": datetime.now().isoformat(),
            "generation_commit": get_git_commit(),
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "torchvision_version": models.__version__ if hasattr(models, "__version__") else "installed",
            "execution_device": "cpu",
            "torch_home": os.environ.get("TORCH_HOME"),
            "governance_note": "Authoritative empirical clean-reference measurements. No values invented."
        },
        "domains": {
            "VISION": vision_calibration,
            "NLP": {
                "status": "BLOCKED_ON_ARCHITECTURE_CONTRACT",
                "note": (
                    "DistilBertModel lacks a classification head and does not output class probabilities. "
                    "Awaiting formal task-head contract resolution before calibrating."
                )
            }
        }
    }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"SUCCESS: Authoritative calibration artifact written to:")
    print(f"  {output_path}")
    print("=" * 70)
    stats = vision_calibration["statistics_run_means"]
    print(f"VISION ResNet18 Clean Baseline Summary (30 runs of 32 probes):")
    print(f"  Mean H_STRIP   : {stats['mean']:.4f} nats")
    print(f"  Median H_STRIP : {stats['median']:.4f} nats")
    print(f"  MAD H_STRIP    : {stats['mad']:.4f} nats")
    print(f"  Std Dev        : {stats['std']:.4f} nats")
    print(f"  [P5, P95]      : [{stats['percentiles']['p5']:.4f}, {stats['percentiles']['p95']:.4f}] nats")
    print(f"  Min / Max      : [{stats['min']:.4f}, {stats['max']:.4f}] nats")
    print("=" * 70)


if __name__ == "__main__":
    main()
