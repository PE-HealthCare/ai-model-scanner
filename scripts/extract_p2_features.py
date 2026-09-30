"""Resumable P1 B1 extraction for Prompt-2 artifacts.

Each artifact is extracted once with B1; canonical B0 rows are selected from
that same result and checked against standalone B0 on demand by tests.  Cache
entries are keyed by content hash and feature-contract fingerprint, never by
filename alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.common.feature_names import B0_FEATURE_NAMES, B1_FEATURE_NAMES
from src.p1_static_engine.analyzer import extract_features, intake_model

METADATA = ROOT / "data" / "training" / "metadata"
SOURCES = ROOT / "data" / "training" / "sources"
CACHE = ROOT / "data" / "training" / "feature_cache"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_fingerprint() -> str:
    """Fingerprint the complete feature-producing implementation contract.

    Feature names alone are insufficient: numerical changes in P1 can alter
    emitted values without changing the schema.  Hash the extractor wrapper,
    the P1 feature producer, and the ordered feature definitions so a cached
    row is reusable only for the same implementation identity.
    """
    producer_files = (
        ("p2_extractor", Path(__file__)),
        ("p1_analyzer", ROOT / "src" / "p1_static_engine" / "analyzer.py"),
        ("feature_names", ROOT / "src" / "common" / "feature_names.py"),
    )
    digest = hashlib.sha256()
    digest.update(json.dumps({"B0": B0_FEATURE_NAMES, "B1": B1_FEATURE_NAMES}, separators=(",", ":"), sort_keys=True).encode())
    for label, path in producer_files:
        digest.update(label.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _record(path: Path, source: dict, family: str, strength: float | None, seed: int | None, partition: str) -> dict:
    return {"file": str(path.relative_to(ROOT)).replace("\\", "/"), "source_model_id": source["source_model_id"],
            "parent_lineage_id": source["parent_lineage_id"], "partition": partition,
            "attack_family": family, "attack_strength": strength, "seed": seed}


def build_inputs(smoke_manifest: Path | None) -> list[dict]:
    source_manifest = json.loads((METADATA / "source_manifest.json").read_text(encoding="utf-8"))
    split = json.loads((METADATA / "split_manifest.json").read_text(encoding="utf-8"))
    assignments = {x["source_model_id"]: x for x in split["assignments"]}
    sources = {x["source_model_id"]: x for x in source_manifest["records"] if x.get("accepted")}
    rows = []
    for source in sources.values():
        path = ROOT / source["file"]
        rows.append(_record(path, source, "CLEAN", None, None, assignments[source["source_model_id"]]["partition"]))
    manifest_path = smoke_manifest or (METADATA / "attack_manifest.json")
    attack = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in attack["artifacts"]:
        source = sources[item["source_model_id"]]
        rows.append(_record(ROOT / item["file"], source, item["attack_family"], item["attack_strength"], item["seed"], item["partition"]))
    return rows


def extract_all(smoke_manifest: Path | None = None, limit: int | None = None) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    fingerprint = contract_fingerprint()
    source_manifest_sha = sha256(METADATA / "source_manifest.json")
    outputs = []
    inputs = build_inputs(smoke_manifest)
    if limit is not None:
        inputs = inputs[:limit]
    for item in inputs:
        artifact_sha = sha256(ROOT / item["file"])
        key = hashlib.sha256(f"{artifact_sha}|{fingerprint}|B1-v2".encode()).hexdigest()
        cache_path = CACHE / f"{key}.json"
        if cache_path.exists():
            result = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            try:
                context = intake_model(ROOT / item["file"], "resnet18")
                b1 = extract_features(context, "p2-b1", feature_set="b1")
            except Exception:
                # Preserve the original exception and traceback while making
                # the failing corpus record visible to a foreground runner.
                print(
                    "P2 feature extraction failed: "
                    f"artifact_sha256={artifact_sha} "
                    f"source_model_id={item['source_model_id']} "
                    f"parent_lineage_id={item['parent_lineage_id']} "
                    f"attack_family={item['attack_family']} "
                    f"attack_strength={item['attack_strength']} "
                    f"seed={item['seed']} partition={item['partition']} "
                    f"file={item['file']}",
                    file=sys.stderr,
                )
                raise
            b0_rows = [{name: row[name] for name in B0_FEATURE_NAMES} | {"layer_name": row["layer_name"]} for row in b1["static_features"]]
            if not all(row.get(name) is not None for row in b0_rows for name in B0_FEATURE_NAMES):
                raise ValueError(f"Non-finite/missing B0 evidence in {item['file']}")
            result = {"cache_key": key, "artifact_sha256": artifact_sha, "feature_contract_fingerprint": fingerprint,
                      "extractor_implementation_fingerprint": fingerprint,
                      "feature_set": "B1", "b1_rows": b1["static_features"], "b0_rows": b0_rows}
            cache_path.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
        outputs.append({**item, "artifact_sha256": artifact_sha, "cache_key": key,
                        "b1_rows": result["b1_rows"], "b0_rows": result["b0_rows"]})
    payload = {"version": "p2-features-v2", "source_manifest_sha256": source_manifest_sha,
               "feature_contract_fingerprint": fingerprint,
               "extractor_implementation_fingerprint": fingerprint, "feature_rows": outputs}
    out = METADATA / ("feature_smoke_manifest.json" if smoke_manifest else "feature_manifest.json")
    out.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke-manifest", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    result = extract_all(args.smoke_manifest, args.limit)
    print(json.dumps({"artifacts": len(result["feature_rows"]), "feature_manifest": "feature_smoke_manifest.json" if args.smoke_manifest else "feature_manifest.json"}))
