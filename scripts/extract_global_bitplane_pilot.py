from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from src.p3_ml_dashboard.global_bitplane_features import (
    extract_global_bitplane_from_safetensors,
)

ROOT = Path("data/training")
ATTACK_MANIFEST = ROOT / "metadata" / "attack_manifest.json"
SOURCE_MANIFEST = ROOT / "metadata" / "source_manifest.json"
OUT = ROOT / "metadata" / "global_bitplane_pilot.json"

TARGET_STRENGTH = 0.005
TARGET_FAMILIES = {"S1", "S2", "S3"}


def load_records(path):
    obj = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(obj, list):
        return obj

    for key in ("artifacts", "records", "entries", "sources"):
        value = obj.get(key)
        if isinstance(value, list):
            return value

    raise RuntimeError(f"Cannot locate record list in {path}")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


attack_records = load_records(ATTACK_MANIFEST)

# Only DEVELOPMENT, primary attacks, 0.5%, S1/S2/S3.
selected_attacks = {}

for r in attack_records:
    if r.get("partition") != "DEVELOPMENT":
        continue

    family = r.get("attack_family")
    strength = r.get("attack_strength")

    if family not in TARGET_FAMILIES:
        continue

    if abs(float(strength) - TARGET_STRENGTH) > 1e-12:
        continue

    source_id = r["source_model_id"]

    # Keep the first manifest entry for each source/family.
    # Do not pull second-seed augmentation into validation.
    selected_attacks.setdefault((source_id, family), r)


source_ids = sorted(
    {
        source_id
        for source_id, family in selected_attacks
    }
)

print("=== PILOT SOURCES ===")
print(f"development_sources_with_attacks={len(source_ids)}")

rows = []

for source_id in source_ids:
    family_records = {
        family: selected_attacks.get((source_id, family))
        for family in sorted(TARGET_FAMILIES)
    }

    if any(v is None for v in family_records.values()):
        print(f"SKIP {source_id}: incomplete S1/S2/S3 set")
        continue

    expected_clean_sha = next(iter(family_records.values()))[
        "clean_parent_sha256"
    ]

    candidates = list(
        (ROOT / "sources").glob(
            source_id.replace("-", "_") + "*.safetensors"
        )
    )

    clean_path = None

    for candidate in candidates:
        if sha256(candidate) == expected_clean_sha:
            clean_path = candidate
            break

    if clean_path is None:
        print(
            f"SKIP {source_id}: "
            f"could not resolve canonical clean parent"
        )
        continue

    artifacts = [
        {
            "label": 0,
            "family": "CLEAN",
            "source_model_id": source_id,
            "parent_lineage_id":
                next(iter(family_records.values()))[
                    "parent_lineage_id"
                ],
            "path": clean_path,
        }
    ]

    for family, r in family_records.items():
        artifacts.append(
            {
                "label": 1,
                "family": family,
                "source_model_id": source_id,
                "parent_lineage_id": r["parent_lineage_id"],
                "path": Path(r["file"]),
            }
        )

    for item in artifacts:
        print(
            f"\nEXTRACT {item['source_model_id']} "
            f"{item['family']}"
        )

        t0 = time.perf_counter()

        result = extract_global_bitplane_from_safetensors(
            item["path"]
        )

        runtime = time.perf_counter() - t0

        rows.append(
            {
                "label": item["label"],
                "family": item["family"],
                "strength":
                    None
                    if item["family"] == "CLEAN"
                    else TARGET_STRENGTH,
                "source_model_id": item["source_model_id"],
                "parent_lineage_id":
                    item["parent_lineage_id"],
                "artifact_path": str(item["path"]),
                "runtime_seconds": runtime,
                "feature_names": result["feature_names"],
                "features": result["features"],
            }
        )

        print(
            f"  done: {runtime:.2f}s, "
            f"{result['feature_count']} features"
        )


if not rows:
    raise RuntimeError("Pilot extracted zero artifacts")

contracts = {
    tuple(r["feature_names"])
    for r in rows
}

assert len(contracts) == 1
assert len(next(iter(contracts))) == 92

OUT.write_text(
    json.dumps(
        {
            "representation": "GLOBAL_BITPLANE_92_V1",
            "strength": TARGET_STRENGTH,
            "artifact_count": len(rows),
            "records": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print("\n=== PILOT COMPLETE ===")
print(f"artifacts={len(rows)}")
print(
    "clean="
    f"{sum(r['family']=='CLEAN' for r in rows)}"
)
print(f"S1={sum(r['family']=='S1' for r in rows)}")
print(f"S2={sum(r['family']=='S2' for r in rows)}")
print(f"S3={sum(r['family']=='S3' for r in rows)}")
print(
    "total_runtime_seconds="
    f"{sum(r['runtime_seconds'] for r in rows):.2f}"
)
print(f"saved={OUT}")
