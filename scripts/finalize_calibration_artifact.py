"""
Finalize the P2 D3/D4 calibration artifact.

Artifact: data/calibration/calibration_data.json

Why this exists
---------------
`scripts/generate_calibration_data.py` owns the authoritative calibration
statistics calculation (`compute_statistics`) and the artifact writer
(`save_calibration`), but its `main()` intentionally refuses to construct or
load a model: real measurement must be driven by an authorized calibration
workflow.

The already-measured calibration observations for this repository are recorded
in the calibration artifact itself (`h_strip_values`, 30 run-level H_STRIP
observations per domain, probe_count 32, seed 42). That artifact predates the
`mad` field that `compute_statistics` now emits, so the P2 runtime could not
satisfy D4 and failed closed with:

    RuntimeError: Calibration data missing required D4 field: mad

What this script does
---------------------
It performs NO new measurement and invents NO values. It replays the recorded
observations through the repository's own `compute_statistics` calculation and
persists the result with the repository's own `save_calibration`.

Fail-closed integrity rules:
  * a domain block without usable recorded observations aborts the run;
  * any already-recorded statistic that disagrees with the replay aborts the
    run instead of being silently overwritten;
  * probe_count / repetitions declared by the block must satisfy the
    repository's own validators;
  * blocks without replayable numerical observations are never emptied.

Usage
-----
    python scripts/finalize_calibration_artifact.py --check
    python scripts/finalize_calibration_artifact.py
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_calibration_data import (  # noqa: E402
    compute_statistics,
    save_calibration,
    validate_probe_count,
    validate_repetitions,
)

DEFAULT_ARTIFACT = (
    PROJECT_ROOT / "data" / "calibration" / "calibration_data.json"
)

CALIBRATION_KEY = "calibration_data"

# Fields owned by compute_statistics. Everything here is recomputed from the
# recorded observations; nothing is authored by hand.
REPLAY_FIELDS = (
    "h_strip_values",
    "mean",
    "median",
    "mad",
    "std",
    "min",
    "max",
    "percentiles",
)

# Block metadata preserved exactly as recorded (never recomputed).
METADATA_FIELDS = (
    "model_name",
    "domain",
    "probe_count",
    "repetitions",
    "seed",
    "timestamp",
)


def get_generation_commit() -> str:
    """Current repository commit, for regeneration provenance."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def replay_domain(domain: str, block: dict) -> dict:
    """
    Recompute the authoritative statistics for one domain block.

    Returns the rebuilt block in the key order produced by
    `calibrate_model` (metadata first, then statistics).
    """
    if not isinstance(block, dict):
        raise RuntimeError(
            f"Calibration block for {domain} is not an object."
        )

    observations = block.get("h_strip_values")

    if not isinstance(observations, list):
        raise RuntimeError(
            f"Calibration block for {domain} has no recorded "
            "h_strip_values observations to replay."
        )

    repetitions = block.get("repetitions")

    if isinstance(repetitions, int) and len(observations) != repetitions:
        raise RuntimeError(
            f"Calibration block for {domain} declares "
            f"repetitions={repetitions} but records "
            f"{len(observations)} observations."
        )

    probe_count = block.get("probe_count")

    if isinstance(probe_count, int):
        # Repository's own D3/D4 probe-count validator.
        validate_probe_count(probe_count)

    if isinstance(repetitions, int):
        # Repository's own repetition validator.
        validate_repetitions(repetitions)

    # Repository's own authoritative statistics calculation.
    # Requires >= 3 finite observations and computes median + MAD.
    statistics = compute_statistics(observations)

    # Integrity: never overwrite disagreeing recorded evidence.
    for field in REPLAY_FIELDS:
        if field not in block:
            continue

        if block[field] != statistics[field]:
            raise RuntimeError(
                f"Integrity violation for {domain}/{field}: recorded value "
                "disagrees with the replay of the recorded observations. "
                "Refusing to overwrite recorded calibration evidence."
            )

    rebuilt = {
        field: block[field]
        for field in METADATA_FIELDS
        if field in block
    }

    for field in REPLAY_FIELDS:
        rebuilt[field] = statistics[field]

    return rebuilt


def build_payload(artifact: dict) -> tuple[dict, dict]:
    """Replay every domain block and rebuild the artifact payload."""
    if CALIBRATION_KEY not in artifact:
        raise RuntimeError(
            f"Calibration artifact is missing '{CALIBRATION_KEY}'."
        )

    calibration_data = artifact[CALIBRATION_KEY]

    if not isinstance(calibration_data, dict) or not calibration_data:
        raise RuntimeError(
            "Calibration artifact contains no domain calibration data."
        )

    replayed_blocks = {}
    observed_counts = {}

    # Preserve the recorded domain order so the artifact diff stays additive.
    for domain in calibration_data:
        replayed_blocks[domain] = replay_domain(
            domain,
            calibration_data[domain],
        )
        observed_counts[domain] = len(
            replayed_blocks[domain]["h_strip_values"]
        )

    provenance = dict(artifact.get("provenance") or {})

    provenance.update(
        {
            "mad_derivation": (
                "median(|H_STRIP - median(H_STRIP)|) computed by "
                "scripts/generate_calibration_data.compute_statistics"
            ),
            "observations_replayed": observed_counts,
            "new_measurement_performed": False,
            "artifact_finalized_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "artifact_finalized_commit": get_generation_commit(),
        }
    )

    return (
        {
            CALIBRATION_KEY: replayed_blocks,
            "provenance": provenance,
        },
        observed_counts,
    )


def report(payload: dict, observed_counts: dict) -> None:
    print("=" * 70)
    print("P2 D3/D4 CALIBRATION ARTIFACT - REPLAYED STATISTICS")
    print("=" * 70)

    for domain, block in payload[CALIBRATION_KEY].items():
        print(f"{domain}")
        print(f"  reference model   : {block.get('model_name')}")
        print(f"  probe_count       : {block.get('probe_count')}")
        print(f"  repetitions       : {block.get('repetitions')}")
        print(
            f"  observations      : {observed_counts[domain]} "
            "(replayed, none synthesized)"
        )
        print(f"  median            : {block['median']!r}")
        print(f"  mad               : {block['mad']!r}")
        print(f"  mean              : {block['mean']!r}")
        print(f"  std               : {block['std']!r}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the recorded P2 calibration observations through the "
            "repository's own compute_statistics and finalize the artifact."
        )
    )
    parser.add_argument(
        "--artifact",
        default=str(DEFAULT_ARTIFACT),
        help="Calibration artifact path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify only; do not write the artifact.",
    )

    args = parser.parse_args()
    artifact_path = Path(args.artifact)

    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Calibration artifact not found: {artifact_path}"
        )

    with artifact_path.open(encoding="utf-8") as handle:
        artifact = json.load(handle)

    payload, observed_counts = build_payload(artifact)
    report(payload, observed_counts)

    if args.check:
        print()
        print("CHECK ONLY: artifact not written.")
        return 0

    # Repository's own writer: validates that every numeric value is finite
    # and writes JSON with allow_nan=False.
    save_calibration(payload, artifact_path)

    # The repository writer opens in text mode, so on Windows it would emit
    # CRLF while the committed artifact is LF. The artifact is content-addressed
    # by provenance, so line endings are normalised to LF to keep its hash
    # identical across platforms. No content is altered.
    raw = artifact_path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")

    if normalized != raw:
        artifact_path.write_bytes(normalized)
        print("Normalised artifact line endings to LF.")

    print()
    print(f"Artifact finalized: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())