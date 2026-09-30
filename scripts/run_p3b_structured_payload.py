"""Prompt 3B: deterministic structured-payload corpus and fixed scanner.

This is deliberately separate from the P2 attack corpus.  Its scanner uses
only three byte-stream statistics and never examines payload text or metadata.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import sys

import numpy as np
import torch
from safetensors import safe_open
from safetensors.torch import save_file
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

METADATA = ROOT / "data" / "training" / "metadata"
S5_DIR = ROOT / "data" / "training" / "s5_structured_payload"
MANIFEST = METADATA / "s5_structured_payload_manifest.json"
SCAN_CACHE = METADATA / "s5_structured_payload_development.json"
EVALUATION = METADATA / "s5_structured_payload_evaluation.json"
TARGET = "layer4.1.conv2.weight"
STRENGTHS = (0.005, 0.01, 0.02, 0.05)
PAYLOAD_VERSION = "GE_HEALTHCARE_SAFE_STEG_BENCHMARK_V1"
PAYLOAD_TEMPLATE = (
    b"GE_HEALTHCARE_SAFE_STEG_BENCHMARK_V1|"
    b"NON_EXECUTABLE_PAYLOAD|MODEL_SECURITY_TEST|"
)
WINDOW_SIZE = 4096
STRIDE = 2048
FEATURE_NAMES = ("min_window_entropy", "max_window_printable_fraction", "max_window_byte_chi2")


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _development_sources() -> list[dict]:
    sources = json.loads((METADATA / "source_manifest.json").read_text(encoding="utf-8"))
    split = json.loads((METADATA / "split_manifest.json").read_text(encoding="utf-8"))
    development = set(split["development_parent_lineages"])
    final = set(split["final_test_parent_lineages"])
    if development & final:
        raise AssertionError("Split parent-lineage overlap")
    records = [item for item in sources["records"] if item.get("accepted") and item["parent_lineage_id"] in development]
    if len(records) != 13 or len({item["source_model_id"] for item in records}) != 13:
        raise AssertionError("Prompt 3B requires exactly 13 development clean sources")
    return sorted(records, key=lambda item: item["source_model_id"])


def _load_state(path: Path) -> dict[str, torch.Tensor]:
    with safe_open(path, framework="pt", device="cpu") as handle:
        return {name: handle.get_tensor(name).detach().cpu().contiguous() for name in handle.keys()}


def _payload_bits(bit_count: int) -> tuple[np.ndarray, str]:
    """Repeat harmless UTF-8 payload and unpack least-significant bit first."""
    byte_count = math.ceil(bit_count / 8)
    payload = (PAYLOAD_TEMPLATE * math.ceil(byte_count / len(PAYLOAD_TEMPLATE)))[:byte_count]
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8), bitorder="little")[:bit_count]
    return bits.astype(np.uint32, copy=False), hashlib.sha256(payload).hexdigest()


def _embed(clean_path: Path, strength: float) -> tuple[dict[str, torch.Tensor], dict]:
    state = _load_state(clean_path)
    if TARGET not in state or state[TARGET].dtype != torch.float32:
        raise ValueError(f"Required FP32 target missing: {TARGET}")
    fp32 = {name: tensor for name, tensor in state.items() if tensor.dtype == torch.float32}
    total = sum(tensor.numel() for tensor in fp32.values())
    selected = math.ceil(total * strength)
    if state[TARGET].numel() < selected:
        raise ValueError(f"Target {TARGET} has insufficient elements for {selected} bits")
    bits, payload_sha = _payload_bits(selected)
    array = state[TARGET].numpy().copy(order="C")
    raw = array.view(np.uint32).reshape(-1)
    before = raw[:selected].copy()
    raw[:selected] = (raw[:selected] & np.uint32(0xFFFFFFFE)) | bits
    changed = int(np.count_nonzero(before != raw[:selected]))
    if changed <= 0:
        raise ValueError("Structured payload did not alter any target elements")
    state[TARGET] = torch.from_numpy(array)
    return state, {"attack_family": "S5_STRUCTURED_PAYLOAD", "attack_strength": strength,
                   "target_tensor": TARGET, "total_fp32_elements": int(total),
                   "selected_element_count": int(selected), "actually_changed_element_count": changed,
                   "payload_version": PAYLOAD_VERSION, "payload_sha256": payload_sha,
                   "bit_position": 0, "bit_order": "little_endian_within_byte",
                   "embedding_operation": "u_new=(u&0xFFFFFFFE)|b"}


def _validate_derivative(clean_path: Path, derivative_path: Path, details: dict) -> None:
    clean, derivative = _load_state(clean_path), _load_state(derivative_path)
    if tuple(sorted(clean)) != tuple(sorted(derivative)):
        raise AssertionError("Tensor names changed")
    changed = 0
    for name in sorted(clean):
        left, right = clean[name], derivative[name]
        if left.shape != right.shape or left.dtype != right.dtype:
            raise AssertionError(f"Schema changed for {name}")
        a, b = left.numpy(), right.numpy()
        if name != TARGET:
            if not np.array_equal(a, b):
                raise AssertionError(f"Non-target tensor changed: {name}")
            continue
        if left.dtype != torch.float32:
            raise AssertionError("Target is not FP32")
        delta = np.bitwise_xor(a.view(np.uint32), b.view(np.uint32))
        if np.any(delta & np.uint32(0xFFFFFFFE)):
            raise AssertionError("Target changed outside FP32 mantissa bit 0")
        changed = int(np.count_nonzero(delta))
    if changed != details["actually_changed_element_count"] or changed <= 0:
        raise AssertionError("Changed-element count validation failed")
    if details["selected_element_count"] != math.ceil(details["total_fp32_elements"] * details["attack_strength"]):
        raise AssertionError("Selected-element count validation failed")


def build_corpus() -> dict:
    """Make/reuse only the deterministic S5 artifacts and its separate manifest."""
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"artifacts": []}
    old = {(item["source_model_id"], float(item["attack_strength"])): item for item in previous.get("artifacts", [])}
    artifacts = []
    for source in _development_sources():
        clean_path = ROOT / source["file"]
        if _sha256(clean_path) != source["file_sha256"]:
            raise AssertionError(f"Clean source SHA mismatch: {source['source_model_id']}")
        for strength in STRENGTHS:
            key = (source["source_model_id"], strength)
            identity = hashlib.sha256(_json_bytes({"clean_sha256": source["file_sha256"], "strength": strength,
                                                   "target": TARGET, "payload_version": PAYLOAD_VERSION})).hexdigest()[:24]
            output = S5_DIR / f"{identity}.safetensors"
            existing = old.get(key)
            reusable = existing and output.exists() and existing.get("derivative_sha256") == _sha256(output)
            if reusable:
                details = {name: existing[name] for name in ("attack_family", "attack_strength", "target_tensor", "total_fp32_elements", "selected_element_count", "actually_changed_element_count", "payload_version", "payload_sha256", "bit_position", "bit_order", "embedding_operation")}
                _validate_derivative(clean_path, output, details)
            else:
                state, details = _embed(clean_path, strength)
                output.parent.mkdir(parents=True, exist_ok=True)
                save_file({name: value.contiguous() for name, value in state.items()}, str(output))
                _validate_derivative(clean_path, output, details)
            artifacts.append({"artifact_id": identity, "file": str(output.relative_to(ROOT)).replace("\\", "/"),
                              "derivative_sha256": _sha256(output), "clean_parent_sha256": source["file_sha256"],
                              "source_model_id": source["source_model_id"], "parent_lineage_id": source["parent_lineage_id"],
                              "partition": "DEVELOPMENT", **details})
            _write(MANIFEST, {"version": "p3b-s5-structured-payload-v1", "artifacts": artifacts, "complete": False})
    result = {"version": "p3b-s5-structured-payload-v1", "target_tensor": TARGET, "payload_version": PAYLOAD_VERSION,
              "payload_template_sha256": hashlib.sha256(PAYLOAD_TEMPLATE).hexdigest(), "artifacts": artifacts, "complete": True}
    _write(MANIFEST, result)
    return result


def _byte_features(path: Path) -> dict[str, float]:
    bits = []
    with safe_open(path, framework="pt", device="cpu") as handle:
        for name in sorted(handle.keys()):
            tensor = handle.get_tensor(name).detach().cpu().contiguous()
            if tensor.dtype == torch.float32:
                bits.append((tensor.numpy().view(np.uint32).reshape(-1) & np.uint32(1)).astype(np.uint8))
    if not bits:
        raise ValueError("No FP32 tensors")
    stream = np.packbits(np.concatenate(bits), bitorder="little")
    if stream.size < WINDOW_SIZE:
        raise ValueError("LSB byte stream shorter than frozen window")
    entropy, printable, chi2 = [], [], []
    for start in range(0, stream.size - WINDOW_SIZE + 1, STRIDE):
        window = stream[start:start + WINDOW_SIZE]
        counts = np.bincount(window, minlength=256).astype(np.float64)
        p = counts[counts > 0] / WINDOW_SIZE
        entropy.append(float(-(p * np.log2(p)).sum() / 8.0))
        printable.append(float(np.count_nonzero((window >= 32) & (window <= 126)) / WINDOW_SIZE))
        chi2.append(float(np.square(counts - WINDOW_SIZE / 256.0).sum() / (WINDOW_SIZE / 256.0)))
    return {"min_window_entropy": min(entropy), "max_window_printable_fraction": max(printable),
            "max_window_byte_chi2": max(chi2)}


def _targets(corpus: dict) -> list[dict]:
    clean = [{"file": source["file"], "artifact_sha256": source["file_sha256"], "source_model_id": source["source_model_id"],
              "parent_lineage_id": source["parent_lineage_id"], "partition": "DEVELOPMENT", "attack_family": "CLEAN",
              "attack_strength": None, "label": 0} for source in _development_sources()]
    s5 = [{"file": item["file"], "artifact_sha256": item["derivative_sha256"], "source_model_id": item["source_model_id"],
           "parent_lineage_id": item["parent_lineage_id"], "partition": item["partition"], "attack_family": item["attack_family"],
           "attack_strength": item["attack_strength"], "label": 1} for item in corpus["artifacts"]]
    rows = clean + s5
    if len(rows) != 65 or any(x["partition"] != "DEVELOPMENT" or x["attack_family"] == "S4" for x in rows):
        raise AssertionError("Invalid Prompt 3B target selection")
    return sorted(rows, key=lambda x: (x["source_model_id"], x["attack_strength"] is not None, x["attack_strength"] or 0.0))


def extract(corpus: dict) -> list[dict]:
    prior = json.loads(SCAN_CACHE.read_text(encoding="utf-8")) if SCAN_CACHE.exists() else {"records": []}
    cached = {item["artifact_sha256"]: item for item in prior.get("records", [])}
    records = []
    for target in _targets(corpus):
        path = ROOT / target["file"]
        old = cached.get(target["artifact_sha256"])
        valid = old and _sha256(path) == target["artifact_sha256"] and tuple(old.get("feature_names", [])) == FEATURE_NAMES and all(math.isfinite(float(old["features"][n])) for n in FEATURE_NAMES)
        values = old["features"] if valid else _byte_features(path)
        records.append({**target, "feature_names": list(FEATURE_NAMES), "features": values})
        _write(SCAN_CACHE, {"version": "p3b-structured-byte-scanner-v1", "feature_names": list(FEATURE_NAMES), "records": records, "complete": False})
    _write(SCAN_CACHE, {"version": "p3b-structured-byte-scanner-v1", "feature_names": list(FEATURE_NAMES), "records": records, "complete": True})
    return records


def _roc(rows: list[dict], scores: dict[str, float]) -> float:
    return float(roc_auc_score([r["label"] for r in rows], [scores[r["artifact_sha256"]] for r in rows]))


def evaluate(records: list[dict]) -> dict:
    groups = np.array([r["parent_lineage_id"] for r in records]); scores: dict[str, float] = {}; folds = []
    degenerate = []
    for fold, (tr, va) in enumerate(GroupKFold(n_splits=3).split(np.arange(len(records)), groups=groups)):
        train, valid = [records[i] for i in tr], [records[i] for i in va]
        if {r["parent_lineage_id"] for r in train} & {r["parent_lineage_id"] for r in valid}:
            raise AssertionError("Parent-lineage leakage")
        clean = [r for r in train if r["label"] == 0]; baseline = {}; failed = False
        for name in FEATURE_NAMES:
            values = np.array([r["features"][name] for r in clean], dtype=np.float64); median = float(np.median(values))
            scale = float(1.4826 * np.median(np.abs(values - median)))
            if scale <= 1e-12: scale = float(np.std(values))
            baseline[name] = (median, scale)
            failed |= scale <= 1e-12
        if failed:
            degenerate.append(fold); continue
        for r in valid:
            e, p, c = (r["features"][n] for n in FEATURE_NAMES)
            score = max(0.0, (baseline["min_window_entropy"][0] - e) / baseline["min_window_entropy"][1],
                        (p - baseline["max_window_printable_fraction"][0]) / baseline["max_window_printable_fraction"][1],
                        (c - baseline["max_window_byte_chi2"][0]) / baseline["max_window_byte_chi2"][1])
            scores[r["artifact_sha256"]] = float(score)
        folds.append({"fold": fold, "roc_auc": _roc(valid, scores), "clean_reference": baseline})
    if degenerate:
        return {"records": records, "scores": scores, "folds": folds, "baseline_degenerate_folds": degenerate}
    y = np.array([r["label"] for r in records]); p = np.array([scores[r["artifact_sha256"]] for r in records])
    clean, s5 = [r for r in records if r["label"] == 0], [r for r in records if r["label"] == 1]
    result = {"records": records, "scores": scores, "folds": folds, "baseline_degenerate_folds": [],
              "pooled_ROC_AUC": float(roc_auc_score(y, p)), "pooled_PR_AUC": float(average_precision_score(y, p)), "PR_baseline": float(y.mean())}
    for strength, label in zip(STRENGTHS, ("0.5", "1", "2", "5")):
        result[f"S5_{label}_ROC"] = _roc(clean + [r for r in s5 if r["attack_strength"] == strength], scores)
    return result


def run() -> dict:
    corpus = build_corpus(); records = extract(corpus); result = evaluate(records)
    if result["baseline_degenerate_folds"]:
        raise RuntimeError(f"BASELINE_DEGENERATE folds: {result['baseline_degenerate_folds']}")
    result["corpus"] = corpus
    _write(EVALUATION, result)
    return result


def _median(records: list[dict], name: str) -> float:
    return float(np.median([r["features"][name] for r in records]))


def report(result: dict) -> None:
    rows = result["records"]; clean = [r for r in rows if not r["label"]]; s5 = [r for r in rows if r["label"]]
    counts = Counter(str(r["attack_strength"]) for r in s5); corpus = result["corpus"]
    pooled = result["pooled_ROC_AUC"]; fold_rocs = [x["roc_auc"] for x in result["folds"]]
    decision = "KEEP_STRUCTURED_STEGO_DETECTOR" if pooled >= .80 and all(x >= .70 for x in fold_rocs) else ("STRUCTURED_SIGNAL_PRESENT_BUT_INSUFFICIENT" if pooled >= .65 or any(x < .70 for x in fold_rocs) else "STOP_STRUCTURED_STEGO_DETECTOR")
    values = {"PROMPT3B": "COMPLETE", "clean_artifacts": len(clean), "s5_artifacts": len(s5), "lineage_count": len({r["parent_lineage_id"] for r in rows}),
              "S5_0.5_count": counts["0.005"], "S5_1_count": counts["0.01"], "S5_2_count": counts["0.02"], "S5_5_count": counts["0.05"],
              "target_tensor": TARGET, "payload_version": PAYLOAD_VERSION, "bit_position": 0, "embedding_operation": "LSB substitution: u_new=(u&0xFFFFFFFE)|b",
              "detector_features": 3, "window_size_bytes": WINDOW_SIZE, "stride_bytes": STRIDE, "pooled_ROC_AUC": pooled,
              "pooled_PR_AUC": result["pooled_PR_AUC"], "PR_baseline": result["PR_baseline"],
              "fold_0_ROC_AUC": fold_rocs[0], "fold_1_ROC_AUC": fold_rocs[1], "fold_2_ROC_AUC": fold_rocs[2],
              **{name: result[name] for name in ("S5_0.5_ROC", "S5_1_ROC", "S5_2_ROC", "S5_5_ROC")},
              "clean_entropy_median": _median(clean, "min_window_entropy"), "s5_entropy_median": _median(s5, "min_window_entropy"),
              "clean_printable_median": _median(clean, "max_window_printable_fraction"), "s5_printable_median": _median(s5, "max_window_printable_fraction"),
              "clean_chi2_median": _median(clean, "max_window_byte_chi2"), "s5_chi2_median": _median(s5, "max_window_byte_chi2"),
              "clean_score_median": float(np.median([result["scores"][r["artifact_sha256"]] for r in clean])), "s5_score_median": float(np.median([result["scores"][r["artifact_sha256"]] for r in s5])),
              "baseline_degenerate_folds": result["baseline_degenerate_folds"], "lineage_leakage": False, "final_test_records": 0, "s4_records": 0, "DECISION": decision}
    for key, value in values.items(): print(f"{key}={value}")
    print("RAW_FEATURE_MEDIANS_BY_STRENGTH:")
    for strength, label in zip(STRENGTHS, ("0.5", "1", "2", "5")):
        subset = [r for r in s5 if r["attack_strength"] == strength]
        print(f"S5_{label}_entropy_median={_median(subset, 'min_window_entropy')}")
        print(f"S5_{label}_printable_median={_median(subset, 'max_window_printable_fraction')}")
        print(f"S5_{label}_chi2_median={_median(subset, 'max_window_byte_chi2')}")
        print(f"S5_{label}_score_median={float(np.median([result['scores'][r['artifact_sha256']] for r in subset]))}")
    print("FILES_CREATED_OR_MODIFIED:")
    print("scripts/run_p3b_structured_payload.py")
    print("data/training/s5_structured_payload/")
    print("data/training/metadata/s5_structured_payload_manifest.json")
    print("data/training/metadata/s5_structured_payload_development.json")
    print("data/training/metadata/s5_structured_payload_evaluation.json")


if __name__ == "__main__":
    report(run())
