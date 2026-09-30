from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from safetensors import safe_open


ROOT = Path("data/training")
MANIFEST = ROOT / "metadata" / "attack_manifest.json"
SOURCE_DIR = ROOT / "sources"

FAMILIES = {"S1", "S2", "S3"}
TIERS = {0.005, 0.01, 0.02, 0.05}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        return obj
    for key in ("records", "artifacts", "entries"):
        if isinstance(obj.get(key), list):
            return obj[key]
    raise RuntimeError("Cannot locate attack records")


def bit_stats(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns z_mono[23], z_serial[23] for FP32 mantissa bits 0..22.

    z_mono:
        (ones - n/2) / (sqrt(n)/2)

    z_serial:
        adjacent transition count under iid Bernoulli(0.5)
        E[T]   = (n-1)/2
        SD[T]  = sqrt(n-1)/2
    """
    flat = np.ascontiguousarray(arr.reshape(-1))

    if flat.dtype != np.float32:
        raise ValueError(f"Expected FP32, got {flat.dtype}")

    raw = flat.view(np.uint32)
    n = raw.size

    mono = np.zeros(23, dtype=np.float64)
    serial = np.zeros(23, dtype=np.float64)

    if n == 0:
        return mono, serial

    for bit in range(23):
        b = ((raw >> np.uint32(bit)) & np.uint32(1)).astype(np.uint8)

        ones = int(b.sum())
        mono[bit] = (
            (ones - n / 2.0)
            / (math.sqrt(n) / 2.0)
        )

        if n >= 2:
            transitions = int(np.count_nonzero(b[1:] != b[:-1]))
            m = n - 1

            serial[bit] = (
                (transitions - m / 2.0)
                / (math.sqrt(m) / 2.0)
            )

    return mono, serial


def load_tensor(path: Path, name: str) -> np.ndarray:
    with safe_open(str(path), framework="np") as f:
        return np.asarray(f.get_tensor(name))


# ------------------------------------------------------------
# Resolve canonical clean parent from SHA256.
# ------------------------------------------------------------

print("=== STEP 1A: RESOLVE CLEAN SOURCES ===")

source_sha = {}

for path in sorted(SOURCE_DIR.glob("*.safetensors")):
    digest = sha256(path)
    source_sha[digest] = path

print(f"indexed_clean_files={len(source_sha)}")


records = [
    r for r in load_manifest()
    if r.get("partition") == "DEVELOPMENT"
    and r.get("attack_family") in FAMILIES
    and float(r.get("attack_strength")) in TIERS
]

# Only primary seed per source/family/tier.
primary = {}

for r in records:
    key = (
        r["source_model_id"],
        r["attack_family"],
        float(r["attack_strength"]),
    )
    primary.setdefault(key, r)

records = list(primary.values())

print(f"development_primary_attacks={len(records)}")


# ------------------------------------------------------------
# Cache CLEAN tensor statistics once.
# ------------------------------------------------------------

clean_cache = {}
results = []


for idx, r in enumerate(
    sorted(
        records,
        key=lambda x: (
            x["source_model_id"],
            x["attack_family"],
            float(x["attack_strength"]),
        )
    ),
    start=1,
):

    family = r["attack_family"]
    tier = float(r["attack_strength"])
    source = r["source_model_id"]

    clean_sha = r["clean_parent_sha256"]

    if clean_sha not in source_sha:
        raise RuntimeError(
            f"Cannot resolve clean parent for {source}: {clean_sha}"
        )

    clean_path = source_sha[clean_sha]
    attack_path = Path(r["file"])

    modified_counts = r["modified_tensor_element_counts"]
    modified_names = set(r["modified_tensors"])

    print(
        f"[{idx}/{len(records)}] "
        f"{source} {family} tier={tier:.3%} "
        f"modified_tensors={len(modified_names)}"
    )

    # --------------------------------------------------------
    # Modified tensor paired comparison
    # --------------------------------------------------------

    modified_abs_shifts = defaultdict(list)
    modified_signed_shifts = defaultdict(list)

    for name in sorted(modified_names):

        cache_key = (str(clean_path), name)

        if cache_key not in clean_cache:
            clean_arr = load_tensor(clean_path, name)

            if clean_arr.dtype != np.float32:
                continue

            clean_cache[cache_key] = bit_stats(clean_arr)

        clean_mono, clean_serial = clean_cache[cache_key]

        tampered_arr = load_tensor(attack_path, name)

        if tampered_arr.dtype != np.float32:
            continue

        attack_mono, attack_serial = bit_stats(tampered_arr)

        mono_shift = attack_mono - clean_mono
        serial_shift = attack_serial - clean_serial

        n_modified = int(modified_counts[name])

        for bit in range(23):
            modified_signed_shifts[
                ("mono", bit)
            ].append(float(mono_shift[bit]))

            modified_signed_shifts[
                ("serial", bit)
            ].append(float(serial_shift[bit]))

            modified_abs_shifts[
                ("mono", bit)
            ].append(abs(float(mono_shift[bit])))

            modified_abs_shifts[
                ("serial", bit)
            ].append(abs(float(serial_shift[bit])))

        results.append(
            {
                "source_model_id": source,
                "family": family,
                "tier": tier,
                "tensor": name,
                "n_modified": n_modified,
                "tensor_numel": int(tampered_arr.size),
                "mono_shift": mono_shift.tolist(),
                "serial_shift": serial_shift.tolist(),
            }
        )


OUT = ROOT / "metadata" / "step1_oracle_tensor_results.json"

OUT.write_text(
    json.dumps(
        {
            "version": "step1-oracle-v1",
            "records": results,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print("\n=== STEP 1A COMPLETE ===")
print(f"tensor_records={len(results)}")
print(f"saved={OUT}")
