# src/p2_behavioral_risk/output_writer.py

import json
import math


REQUIRED_FIELDS = {
    "producer",
    "mock_status",
    "contract_version",
    "generation_commit",
    "mrs_score",
    "verdict",
    "s_static",
    "p_tamper",
    "s_behavior",
}


def _reject_non_finite(value, path="root"):

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                f"Non-finite numeric value at {path}."
            )

    elif isinstance(value, dict):

        for key, child in value.items():
            _reject_non_finite(
                child,
                f"{path}.{key}",
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):
            _reject_non_finite(
                child,
                f"{path}[{index}]",
            )


def write_risk_results(data, filepath):

    missing = REQUIRED_FIELDS - set(data.keys())

    if missing:
        raise ValueError(
            f"risk_results missing required fields: "
            f"{sorted(missing)}"
        )

    _reject_non_finite(data)

    with open(
        filepath,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            allow_nan=False,
        )
