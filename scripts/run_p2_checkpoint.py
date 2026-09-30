"""Prompt-2 Gate 2B corpus, extraction, and development learning-curve runner.

This runner is deliberately local and SafeTensors-only.  It seals a source
manifest fingerprint before splitting parent lineages, generates deterministic
defensive bit-level perturbations, validates each derivative through P1, and
uses P1 B1 once to derive B0 rows.  Final-test and S4 rows are persisted but
are never read by the learning-curve evaluator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from safetensors import safe_open
from safetensors.torch import save_file
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.feature_names import B0_FEATURE_NAMES, B1_FEATURE_NAMES
from src.p1_static_engine.analyzer import extract_features, intake_model


MANIFEST_PATH = ROOT / "data/training/metadata/source_manifest.json"
METADATA = ROOT / "data/training/metadata"
DERIVATIVES = ROOT / "data/training/derivatives"
FEATURES = ROOT / "data/training/features"
SEED = 20260929
STRENGTHS = (0.005, 0.01, 0.02, 0.05)
PRIMARY_FAMILIES = ("S1", "S2", "S3")
OOD_FAMILY = "S4"
LOW_STRENGTHS = {0.005, 0.01}
FEATURE_CONTRACT = hashlib.sha256(
    ("P1-B1-v1\0" + "\0".join(B1_FEATURE_NAMES)).encode("utf-8")
).hexdigest()
LGB_PARAMS = {
    "objective": "binary", "learning_rate": 0.05, "num_leaves": 15,
    "max_depth": 5, "min_child_samples": 40, "feature_fraction": 0.9,
    "bagging_fraction": 0.9, "bagging_freq": 1, "lambda_l1": 0.0,
    "lambda_l2": 1.0, "verbosity": -1, "seed": SEED,
    "feature_fraction_seed": SEED, "bagging_seed": SEED,
    "data_random_seed": SEED, "deterministic": True, "num_threads": 1,
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seed(*parts: object) -> int:
    return int.from_bytes(hashlib.sha256("\0".join(map(str, parts)).encode()).digest()[:8], "little")


def _load_manifest() -> tuple[dict, str, list[dict]]:
    raw = MANIFEST_PATH.read_bytes()
    payload = json.loads(raw)
    accepted = [record for record in payload["records"] if record["accepted"]]
    if payload["distinct_clean_weight_population_count"] != len(accepted):
        raise ValueError("Source manifest accepted-count mismatch")
    if len({record["source_model_id"] for record in accepted}) != len(accepted):
        raise ValueError("Source manifest contains duplicate accepted source_model_id")
    for record in accepted:
        if not record.get("parent_lineage_id"):
            raise ValueError(f"Missing parent_lineage_id for {record['source_model_id']}")
    return payload, hashlib.sha256(raw).hexdigest(), accepted


def create_split() -> dict:
    """Freeze an ~80/20 parent-lineage split selected by stable hash."""
    manifest, manifest_hash, accepted = _load_manifest()
    lineages = sorted({record["parent_lineage_id"] for record in accepted})
    final_count = max(1, round(len(lineages) * 0.2))
    ranked = sorted(lineages, key=lambda value: hashlib.sha256(
        f"{manifest_hash}\0{SEED}\0{value}".encode()).hexdigest())
    final_lineages = sorted(ranked[:final_count])
    development_lineages = sorted(set(lineages) - set(final_lineages))
    if set(final_lineages) & set(development_lineages):
        raise AssertionError("Parent-lineage split overlap")
    assignments = []
    for record in accepted:
        partition = "FINAL_TEST" if record["parent_lineage_id"] in final_lineages else "DEVELOPMENT"
        assignments.append({
            "source_model_id": record["source_model_id"],
            "parent_lineage_id": record["parent_lineage_id"], "partition": partition,
        })
    if len({row["source_model_id"] for row in assignments}) != len(assignments):
        raise AssertionError("A source_model_id crosses partitions")
    result = {
        "version": "p2-gate2b-split-v1", "seed": SEED,
        "source_manifest_sha256": manifest_hash,
        "development_parent_lineages": development_lineages,
        "final_test_parent_lineages": final_lineages,
        "zero_parent_lineage_overlap": True, "assignments": assignments,
    }
    METADATA.mkdir(parents=True, exist_ok=True)
    (METADATA / "split_manifest.json").write_bytes(_canonical_json(result) + b"\n")
    return result


def _floating_tensors(path: Path) -> dict[str, np.ndarray]:
    tensors: dict[str, np.ndarray] = {}
    with safe_open(path, framework="pt", device="cpu") as handle:
        for name in handle.keys():
            tensor = handle.get_tensor(name).detach().cpu()
            if tensor.is_floating_point():
                arr = tensor.numpy().copy()
                if arr.dtype != np.float32 or not np.isfinite(arr).all():
                    raise ValueError(f"Invalid FP32 source tensor {name}")
                tensors[name] = arr
    if not tensors:
        raise ValueError("No floating-point tensors available for tampering")
    return tensors


def _flat_locations(tensors: dict[str, np.ndarray], count: int, rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    names = sorted(tensors)
    sizes = np.array([tensors[name].size for name in names], dtype=np.int64)
    total = int(sizes.sum())
    if count <= 0 or count > total:
        raise ValueError("Invalid requested modification count")
    chosen = np.sort(rng.choice(total, size=count, replace=False))
    edges = np.cumsum(sizes)
    out = []
    for position, name in enumerate(names):
        indices = chosen[(chosen >= (edges[position - 1] if position else 0)) & (chosen < edges[position])]
        if indices.size:
            out.append((name, indices - (edges[position - 1] if position else 0)))
    return out


def _flip_bits(flat: np.ndarray, indices: np.ndarray, bits: np.ndarray) -> None:
    view = flat.view(np.uint32)
    view[indices] ^= (np.uint32(1) << bits.astype(np.uint32))


def apply_attack(clean_path: Path, family: str, strength: float, seed: int) -> tuple[dict[str, np.ndarray], dict]:
    """Apply a finite, deterministic bit-level defensive perturbation."""
    tensors = _floating_tensors(clean_path)
    total = sum(array.size for array in tensors.values())
    requested = math.ceil(total * strength)
    rng = np.random.default_rng(seed)
    touched: dict[str, int] = {}
    if family in {"S1", "S2"}:
        locations = _flat_locations(tensors, requested, rng)
        for name, indices in locations:
            flat = tensors[name].reshape(-1)
            bits = np.zeros(indices.size, dtype=np.uint32) if family == "S1" else rng.integers(1, 23, indices.size, dtype=np.uint32)
            _flip_bits(flat, indices, bits)
            touched[name] = int(indices.size)
    elif family == "S3":
        eligible = [(name, array) for name, array in sorted(tensors.items()) if array.size >= requested]
        if not eligible:
            raise ValueError("No tensor large enough for requested localized attack")
        name, array = eligible[rng.integers(0, len(eligible))]
        start = int(rng.integers(0, array.size - requested + 1))
        indices = np.arange(start, start + requested, dtype=np.int64)
        _flip_bits(array.reshape(-1), indices, np.full(requested, 7, dtype=np.uint32))
        touched[name] = int(requested)
    elif family == "S4":
        # Spread deterministically through every eligible tensor rather than
        # concentrating in one layer; reserved exclusively for OOD evaluation.
        names = sorted(tensors)
        raw_counts = [requested * tensors[name].size / total for name in names]
        counts = [math.floor(value) for value in raw_counts]
        for index in np.argsort(np.asarray(raw_counts) - counts)[::-1][:requested - sum(counts)]:
            counts[int(index)] += 1
        for name, count in zip(names, counts):
            array = tensors[name]
            if count:
                indices = np.linspace(0, array.size - 1, num=count, dtype=np.int64)
                _flip_bits(array.reshape(-1), indices, np.full(count, 11, dtype=np.uint32))
                touched[name] = int(count)
    else:
        raise ValueError(f"Unknown attack family {family}")
    if sum(touched.values()) != requested or not all(np.isfinite(array).all() for array in tensors.values()):
        raise ValueError("Attack failed exact-count or finite-value validation")
    return tensors, {
        "attack_family": family, "attack_strength": strength, "seed": seed,
        "affected_element_count": requested, "eligible_element_count": total,
        "modified_tensors": sorted(touched), "modified_tensor_element_counts": touched,
    }


def generate_artifact(record: dict, partition: str, family: str, strength: float, seed_slot: int) -> dict:
    clean_path = ROOT / record["file"]
    seed = _seed(record["tensor_content_fingerprint"], family, strength, seed_slot)
    tensors, attack = apply_attack(clean_path, family, strength, seed)
    artifact_id = hashlib.sha256(_canonical_json({
        "source": record["source_model_id"], "family": family, "strength": strength, "seed": seed,
    })).hexdigest()[:24]
    destination = DERIVATIVES / f"{artifact_id}.safetensors"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        # Preserve control tensors exactly; only validated FP tensors may change.
        with safe_open(clean_path, framework="pt", device="cpu") as handle:
            state = {name: (tensors[name] if name in tensors else handle.get_tensor(name)) for name in handle.keys()}
        import torch
        save_file({name: torch.from_numpy(value) if isinstance(value, np.ndarray) else value for name, value in state.items()}, str(destination))
    context = intake_model(destination, "resnet18")
    if context.is_quantized:
        raise ValueError("Unexpected quantized derivative")
    derivative_hash = _sha256_file(destination)
    if derivative_hash == record["file_sha256"]:
        raise ValueError("Derivative hash unexpectedly equals clean parent hash")
    return {
        "artifact_id": artifact_id, "file": str(destination.relative_to(ROOT)).replace("\\", "/"),
        "source_model_id": record["source_model_id"], "parent_lineage_id": record["parent_lineage_id"],
        "partition": partition, "clean_parent_sha256": record["file_sha256"],
        "derivative_sha256": derivative_hash, **attack,
    }


def build_attack_corpus(smoke_only: bool = False) -> dict:
    manifest, manifest_hash, accepted = _load_manifest()
    split = create_split()
    partitions = {row["source_model_id"]: row["partition"] for row in split["assignments"]}
    records = accepted[:1] if smoke_only else accepted
    artifacts: list[dict] = []
    for record in records:
        partition = partitions[record["source_model_id"]]
        for family in PRIMARY_FAMILIES + (OOD_FAMILY,):
            for strength in ((STRENGTHS[0],) if smoke_only else STRENGTHS):
                artifacts.append(generate_artifact(record, partition, family, strength, 0))
                if partition == "DEVELOPMENT" and family in PRIMARY_FAMILIES and strength in LOW_STRENGTHS and not smoke_only:
                    artifacts.append(generate_artifact(record, partition, family, strength, 1))
    output = {
        "version": "p2-attacks-v1", "source_manifest_sha256": manifest_hash,
        "attack_config_sha256": hashlib.sha256(_canonical_json({"strengths": STRENGTHS, "seed": SEED})).hexdigest(),
        "artifacts": artifacts,
    }
    name = "attack_smoke_manifest.json" if smoke_only else "attack_manifest.json"
    (METADATA / name).write_bytes(_canonical_json(output) + b"\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="generate and validate one source only")
    args = parser.parse_args()
    started = time.monotonic()
    output = build_attack_corpus(smoke_only=args.smoke)
    print(json.dumps({"artifacts": len(output["artifacts"]), "runtime_seconds": round(time.monotonic() - started, 3)}))


if __name__ == "__main__":
    main()
