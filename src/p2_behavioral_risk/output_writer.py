# src/p2_behavioral_risk/output_writer.py

"""
P2 Option 2 output writer.

Writes the final risk assessment to JSON.

Security rule:
    Invalid floating-point values must never silently become a
    seemingly valid result.
"""

import json
import math
import os


def _validate_value(value, path="root"):
    """
    Recursively validate JSON-compatible values.

    Reject NaN/Inf instead of silently converting them to null.
    """

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(
                f"Invalid non-finite numeric value at {path}: {value}"
            )
        return value

    if isinstance(value, dict):
        return {
            str(key): _validate_value(item, f"{path}.{key}")
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _validate_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]

    return value


def write_risk_results(data, filepath):
    """
    Write the final P2 risk assessment.

    Args:
        data: Dictionary containing the final assessment.
        filepath: Destination JSON path.

    Raises:
        ValueError: If data contains NaN/Inf.
        TypeError: If data is not a dictionary.
    """

    if not isinstance(data, dict):
        raise TypeError("risk_results must be a dictionary")

    cleaned = _validate_value(data)

    directory = os.path.dirname(filepath)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            cleaned,
            f,
            indent=2,
            allow_nan=False,
        )
