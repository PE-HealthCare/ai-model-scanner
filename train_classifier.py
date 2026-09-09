"""Train the P3 tampering classifier and write models/classifier.json.

SCIENTIFIC INTEGRITY (important):
All training data is SYNTHETIC. Clean examples are seeded Gaussian-ish
weight tensors; tampered examples are produced with the three approved P3
methods from src.p3_ml_dashboard.synthetic_tamper. The committed model
records training_data_status="SYNTHETIC", authoritative=false, per-method
counts and seeds, plus holdout metrics. This model demonstrates the
pipeline end-to-end; it is NOT evidence of production-grade detection.

Features per example are computed with the production P1 extractor
(src.p1_static_engine.analyzer.extract_layer_features) and the canonical
shared vector construction (src.common.feature_names.feature_vector), so
training and inference see identical feature semantics and ordering. The
committed models/classifier.json is reproduced exactly by this script
(verified by tests); inference never retrains or rewrites the artifact.

Deterministic: fixed seeds; the only randomness is NumPy PCG64 with
explicit seeds. Re-running this script reproduces the same model bytes.

Usage:
    python train_classifier.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.common.feature_names import FEATURE_NAMES, feature_vector
from src.p1_static_engine.analyzer import extract_layer_features
from src.p3_ml_dashboard.synthetic_tamper import (
    controlled_perturbation,
    lsb_manipulation,
    mantissa_bit_modification,
)

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "classifier.json"

SEED = 20260909  # fixed training seed (date-pinned for provenance)
N_CLEAN_PER_FAMILY = 24
N_TAMPERED_PER_METHOD = 24
TENSOR_ROWS, TENSOR_COLS = 32, 64  # 2048 elements per example tensor
HOLDOUT_FRACTION = 0.25
EPOCHS = 4000
LEARNING_RATE = 0.35
L2 = 1e-4

# Scale families mimic common weight distributions (kaiming-ish, small std).
_SCALES = (0.05, 0.1, 0.25, 0.5)
_EPSILON_GRID = (0.005, 0.01, 0.02, 0.05)
_LSB_BITS_GRID = (1, 2, 3)
_MANTISSA_BITS_GRID = (1, 2, 4, 8)


def _clean_example(rng: np.random.Generator) -> np.ndarray:
    """A seeded synthetic 'natural' weight tensor (float32, Gaussian-ish)."""
    scale = float(rng.choice(_SCALES))
    base = rng.normal(loc=0.0, scale=scale, size=(TENSOR_ROWS, TENSOR_COLS)).astype(np.float32)
    # Sparse zero structure (like ReLU-pruned weights) for some families.
    if rng.random() < 0.5:
        mask = rng.random(base.shape) < 0.15
        base[mask] = 0.0
    return base


def _features_of(arr: np.ndarray) -> list[float]:
    """Canonical 10-feature vector for one tensor (shared with inference)."""
    return feature_vector(extract_layer_features(arr))


def _dataset() -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(SEED)
    xs: list[list[float]] = []
    ys: list[int] = []
    method_labels: list[str] = []

    for _ in range(N_CLEAN_PER_FAMILY):
        arr = _clean_example(rng)
        xs.append(_features_of(arr))
        ys.append(0)
        method_labels.append("clean")

    tamper_factories = (
        ("controlled_perturbation", lambda a, r: controlled_perturbation(a, epsilon=float(rng.choice(_EPSILON_GRID)), seed=int(r.integers(0, 2**31 - 1)))),
        ("lsb_manipulation", lambda a, r: lsb_manipulation(a, bits=int(rng.choice(_LSB_BITS_GRID)))),
        ("mantissa_bit_modification", lambda a, r: mantissa_bit_modification(a, bits=int(rng.choice(_MANTISSA_BITS_GRID)), seed=int(r.integers(0, 2**31 - 1)))),
    )
    for method, _ in tamper_factories:
        for _ in range(N_TAMPERED_PER_METHOD):
            arr = _clean_example(rng)
            idx = [i for i, (name, _) in enumerate(tamper_factories) if name == method][0]
            tampered, _prov = tamper_factories[idx][1](arr, rng)
            xs.append(_features_of(tampered))
            ys.append(1)
            method_labels.append(method)

    return np.array(xs, dtype=np.float64), np.array(ys, dtype=np.float64), method_labels


def _standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    return (x - mean) / np.maximum(std, 1e-12), mean, std


def _fit_logistic(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    n, d = x.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(EPOCHS):
        z = x @ w + b
        p = 1.0 / (1.0 + np.exp(-z))
        gw = x.T @ (p - y) / n + L2 * w
        gb = float((p - y).mean())
        w -= LEARNING_RATE * gw
        b -= LEARNING_RATE * gb
    return w, b


def _metrics(x: np.ndarray, y: np.ndarray, w: np.ndarray, b: float) -> dict:
    p = 1.0 / (1.0 + np.exp(-(x @ w + b)))
    pred = (p >= 0.5).astype(np.float64)
    tp = float(((pred == 1) & (y == 1)).sum())
    tn = float(((pred == 0) & (y == 0)).sum())
    fp = float(((pred == 1) & (y == 0)).sum())
    fn = float(((pred == 0) & (y == 1)).sum())
    return {
        "accuracy": (tp + tn) / max(tp + tn + fp + fn, 1.0),
        "precision": tp / max(tp + fp, 1.0),
        "recall": tp / max(tp + fn, 1.0),
        "n_holdout": int(len(y)),
    }


def train() -> dict:
    x, y, method_labels = _dataset()
    idx = np.random.default_rng(SEED).permutation(len(y))
    x, y, method_labels = x[idx], y[idx], [method_labels[i] for i in idx]
    n_holdout = max(int(len(y) * HOLDOUT_FRACTION), 4)
    x_tr, y_tr = x[:-n_holdout], y[:-n_holdout]
    x_te, y_te = x[-n_holdout:], y[-n_holdout:]

    x_tr_s, mean, std = _standardize(x_tr)
    w, b = _fit_logistic(x_tr_s, y_tr)
    holdout = _metrics((x_te - mean) / np.maximum(std, 1e-12), y_te, w, b)

    from src.p3_ml_dashboard.classifier import MODELS_DIR

    model = {
        "model_version": "sigtensor-logreg-synthetic-v1",
        "feature_names": list(FEATURE_NAMES),
        "means": mean.tolist(),
        "stds": std.tolist(),
        "weights": w.tolist(),
        "bias": float(b),
        "training_data_status": "SYNTHETIC",
        "authoritative": False,
        "provenance": {
            "seed": SEED,
            "clean_examples": N_CLEAN_PER_FAMILY,
            "tampered_per_method": N_TAMPERED_PER_METHOD,
            "tamper_methods": ["controlled_perturbation", "lsb_manipulation", "mantissa_bit_modification"],
            "tensor_shape": [TENSOR_ROWS, TENSOR_COLS],
            "epochs": EPOCHS,
            "learning_rate": LEARNING_RATE,
            "l2": L2,
            "holdout_metrics": holdout,
        },
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    return model


if __name__ == "__main__":
    trained = train()
    metrics = trained["provenance"]["holdout_metrics"]
    print(f"model written: {MODEL_PATH}")
    print(
        "holdout (SYNTHETIC data): "
        f"acc={metrics['accuracy']:.3f} prec={metrics['precision']:.3f} rec={metrics['recall']:.3f}"
    )
    print("note: metrics describe synthetic-data separation, not production detection.")