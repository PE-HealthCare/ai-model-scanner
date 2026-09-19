"""Train the authoritative CP4 LightGBM classifier (artifacts/lightgbm_model.txt).

Training-data rule (D10 decision doc #4 + Phase 4 plan):
- Clean and tampered tensors come ONLY from the repository's existing
  approved generators:
    * clean tensors: the seeded Gaussian weight-tensor generator
      train_classifier._clean_example and its approved scale families
      (reused verbatim from the interim trainer);
    * tampered tensors: the three approved P3 methods in
      src/p3_ml_dashboard/synthetic_tamper.py (controlled_perturbation,
      lsb_manipulation, mantissa_bit_modification) with the approved
      parameter grids from train_classifier.py.
- Features for every training row are extracted through the REAL P1 path
  (zero-trust intake + build_features) via
  src.p3_ml_dashboard.classifier.extract_training_example.
- Corpus tensors are written to a temporary directory and are fully
  reproducible from the recorded seeds/parameters; per-file SHA-256 hashes
  feed the dataset_source_sha256 provenance value.
- Deterministic: fixed seeds; LightGBM trained with deterministic=True.
- Provenance is persisted to artifacts/lightgbm_model.provenance.json
  (artifacts/AGENT_RULES.md section 4).

Usage:
    python train_lightgbm_classifier.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

import train_classifier as tc  # approved clean generator + parameter grids
from src.common.utils import ROOT, get_generation_commit
from src.p1_static_engine.intake import write_safetensors
from src.p3_ml_dashboard.classifier import (
    DEFAULT_MODEL_PATH,
    DEFAULT_PROVENANCE_PATH,
    train_final_classifier,
)
from src.p3_ml_dashboard.synthetic_tamper import (
    controlled_perturbation,
    lsb_manipulation,
    mantissa_bit_modification,
)

LAYERS_PER_MODEL = 8
CLEAN_MODELS = 6
TAMPERED_MODELS_PER_METHOD = 2
CORPUS_SEED = tc.SEED  # same approved seed base as the interim trainer

_TAMPER_METHODS = (
    "controlled_perturbation",
    "lsb_manipulation",
    "mantissa_bit_modification",
)


def _layer_tensor(rng: np.random.Generator) -> np.ndarray:
    """One clean layer tensor from the approved clean generator."""
    return tc._clean_example(rng)


def _tamper_layer(method: str, arr: np.ndarray, rng: np.random.Generator):
    """Apply one APPROVED P3 tampering method with its approved grid."""
    if method == "controlled_perturbation":
        return controlled_perturbation(
            arr,
            epsilon=float(rng.choice(tc._EPSILON_GRID)),
            seed=int(rng.integers(0, 2**31 - 1)),
        )
    if method == "lsb_manipulation":
        return lsb_manipulation(arr, bits=int(rng.choice(tc._LSB_BITS_GRID)))
    if method == "mantissa_bit_modification":
        return mantissa_bit_modification(
            arr,
            bits=int(rng.choice(tc._MANTISSA_BITS_GRID)),
            seed=int(rng.integers(0, 2**31 - 1)),
        )
    raise ValueError(f"Unsupported tamper method: {method}")


def _write_model_file(path: Path, layer_arrays) -> Path:
    tensors = {f"model.layer_{i:02d}": arr for i, arr in enumerate(layer_arrays)}
    return write_safetensors(path, tensors)


def build_corpus(corpus_dir: Path):
    """Build the reproducible clean/tampered training corpus (real files)."""
    rng = np.random.default_rng(CORPUS_SEED)
    records = []
    clean_paths = []
    for i in range(CLEAN_MODELS):
        layers = [_layer_tensor(rng) for _ in range(LAYERS_PER_MODEL)]
        path = _write_model_file(corpus_dir / f"clean_model_{i:02d}.safetensors", layers)
        clean_paths.append(path)
        records.append({"file": path.name, "label": "clean", "layers": LAYERS_PER_MODEL})

    tampered_paths = []
    for method in _TAMPER_METHODS:
        for i in range(TAMPERED_MODELS_PER_METHOD):
            clean_layers = [_layer_tensor(rng) for _ in range(LAYERS_PER_MODEL)]
            tampered_layers = []
            parameters = []
            for arr in clean_layers:
                tampered, prov = _tamper_layer(method, arr, rng)
                tampered_layers.append(tampered)
                parameters.append(prov["parameters"])
            path = _write_model_file(
                corpus_dir / f"tampered_{method}_{i:02d}.safetensors", tampered_layers
            )
            tampered_paths.append(path)
            records.append(
                {
                    "file": path.name,
                    "label": "tampered",
                    "method": method,
                    "parameters": parameters,
                }
            )
    return clean_paths, tampered_paths, records


def train() -> dict:
    generation_commit = get_generation_commit()
    with tempfile.TemporaryDirectory(prefix="cp4_corpus_") as td:
        clean_paths, tampered_paths, records = build_corpus(Path(td))
        provenance = train_final_classifier(
            clean_paths,
            tampered_paths,
            generation_commit=generation_commit,
            dataset_id="synthetic-clean-vs-approved-tamper-cp4-v1",
            output_path=DEFAULT_MODEL_PATH,
        )

    payload = {
        "artifact": str(DEFAULT_MODEL_PATH.relative_to(ROOT)),
        **provenance,
        "corpus": {
            "seed": CORPUS_SEED,
            "layers_per_model": LAYERS_PER_MODEL,
            "clean_models": CLEAN_MODELS,
            "tampered_models_per_method": TAMPERED_MODELS_PER_METHOD,
            "tamper_methods": list(_TAMPER_METHODS),
            "clean_generator": (
                "train_classifier._clean_example (approved methodology, reused verbatim)"
            ),
            "tamper_generator": "src/p3_ml_dashboard/synthetic_tamper.py (approved methods)",
            "note": (
                "Training data is SYNTHETIC; model-level clean/tampered labels are "
                "applied to layer-level feature rows (D10 decision doc #4)."
            ),
            "files": records,
        },
    }
    DEFAULT_PROVENANCE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    info = train()
    print(f"model artifact: {DEFAULT_MODEL_PATH}")
    print(f"provenance sidecar: {DEFAULT_PROVENANCE_PATH}")
    print(f"model_sha256: {info['model_sha256']}")
    print(f"rows: clean={info['clean_rows']} tampered={info['tampered_rows']}")
    print(f"generation_commit: {info['generation_commit']}")