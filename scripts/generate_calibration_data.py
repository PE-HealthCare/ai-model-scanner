"""
Generate empirical STRIP calibration data for P2.

D3 / D4:
- Generate exactly probe_count probes per repetition.
- Compute H_STRIP for each repetition.
- Store the empirical distribution.
- Calculate median and MAD.
- Median + MAD are authoritative for D4 normalization.

Important:
- mean/std are retained for reporting only.
- They must NOT be used by P2 for D4 scoring.
- NLP calibration must not be treated as authoritative unless the
  scanner-controlled probability-output contract has been verified.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.p2_behavioral_risk.prober import (
    compute_h_strip,
    generate_probes,
    run_bounded_inference,
)


DEFAULT_PROBE_COUNT = 32
DEFAULT_REPETITIONS = 30


def set_seed(seed: int) -> None:
    """
    Make calibration runs reproducible where supported.
    """

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def validate_domain(domain: str) -> str:
    domain = domain.upper()

    if domain not in {"VISION", "NLP"}:
        raise ValueError(
            f"Unsupported domain: {domain}. "
            "Expected VISION or NLP."
        )

    return domain


def validate_probe_count(probe_count: int) -> None:
    if probe_count != DEFAULT_PROBE_COUNT:
        raise ValueError(
            f"D3/D4 requires exactly {DEFAULT_PROBE_COUNT} probes; "
            f"received {probe_count}"
        )


def validate_repetitions(repetitions: int) -> None:
    if repetitions < 3:
        raise ValueError(
            "Calibration requires at least 3 repetitions"
        )


def compute_statistics(results: list[float]) -> dict[str, Any]:
    """
    Calculate empirical calibration statistics.

    D4-authoritative values:
        median
        mad

    mean/std/percentiles are reporting metadata only.
    """

    if len(results) < 3:
        raise ValueError(
            "At least 3 calibration observations are required"
        )

    arr = np.asarray(results, dtype=np.float64)

    if not np.all(np.isfinite(arr)):
        raise ValueError(
            "Calibration contains NaN or Inf"
        )

    median = float(np.median(arr))

    # Median Absolute Deviation.
    mad = float(
        np.median(
            np.abs(arr - median)
        )
    )

    return {
        "h_strip_values": [
            float(value)
            for value in results
        ],
        "mean": float(np.mean(arr)),
        "median": median,
        "mad": mad,
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "percentiles": {
            "p5": float(np.percentile(arr, 5)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p95": float(np.percentile(arr, 95)),
        },
    }


def calibrate_model(
    model: torch.nn.Module,
    *,
    model_name: str,
    domain: str,
    probe_count: int = DEFAULT_PROBE_COUNT,
    repetitions: int = DEFAULT_REPETITIONS,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Generate calibration observations for one trusted model.

    The model passed here must already be trusted/authorized by the
    caller. This function does not load an untrusted artifact.
    """

    domain = validate_domain(domain)

    validate_probe_count(probe_count)
    validate_repetitions(repetitions)

    set_seed(seed)

    model.eval()

    results: list[float] = []

    for repetition in range(repetitions):
        probes = generate_probes(
            domain=domain,
            n=probe_count,
        )

        if len(probes) != probe_count:
            raise RuntimeError(
                f"Probe generation returned {len(probes)} probes; "
                f"expected {probe_count}"
            )

        inference_result = run_bounded_inference(
            model=model,
            probes=probes,
            domain=domain,
        )

        if not inference_result.get("success", False):
            raise RuntimeError(
                "Calibration inference failed closed: "
                f"{inference_result}"
            )

        probabilities = inference_result.get(
            "probabilities"
        )

        if not isinstance(probabilities, list):
            raise RuntimeError(
                "Calibration inference returned invalid probabilities"
            )

        if len(probabilities) != probe_count:
            raise RuntimeError(
                f"Expected {probe_count} probability vectors; "
                f"got {len(probabilities)}"
            )

        h_strip = compute_h_strip(
            probabilities
        )

        if not np.isfinite(h_strip):
            raise ValueError(
                f"Non-finite H_STRIP at repetition {repetition}"
            )

        results.append(float(h_strip))

    statistics = compute_statistics(results)

    return {
        "model_name": model_name,
        "domain": domain,
        "probe_count": probe_count,
        "repetitions": repetitions,
        "seed": seed,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),

        **statistics,
    }


def save_calibration(
    calibration: dict[str, Any],
    output_path: str | Path,
) -> None:
    """
    Save calibration JSON after validating that all numeric values
    are finite.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    def validate_finite(value: Any, path: str = "root") -> None:
        if isinstance(value, float):
            if not np.isfinite(value):
                raise ValueError(
                    f"Non-finite value at {path}"
                )

        elif isinstance(value, dict):
            for key, child in value.items():
                validate_finite(
                    child,
                    f"{path}.{key}",
                )

        elif isinstance(value, list):
            for index, child in enumerate(value):
                validate_finite(
                    child,
                    f"{path}[{index}]",
                )

    validate_finite(calibration)

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            calibration,
            handle,
            indent=2,
            allow_nan=False,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate P2 STRIP calibration data"
    )

    parser.add_argument(
        "--domain",
        required=True,
        choices=["VISION", "NLP"],
    )

    parser.add_argument(
        "--model-name",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "--probe-count",
        type=int,
        default=DEFAULT_PROBE_COUNT,
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=DEFAULT_REPETITIONS,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    raise RuntimeError(
        "Calibration model construction/loading is intentionally "
        "not performed by this script. Pass a trusted scanner-approved "
        "model into calibrate_model() from the authorized calibration "
        "workflow."
    )


if __name__ == "__main__":
    main()
