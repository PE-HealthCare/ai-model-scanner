"""Project-wide utilities only."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def get_generation_commit() -> str:
    value = os.getenv("AI_MODEL_SCANNER_GENERATION_COMMIT")
    if value:
        return value
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "PHASE1-MOCK"


def validate_artifact(artifact_path: Path, schema_path: Path) -> None:
    with artifact_path.open(encoding="utf-8") as fh:
        instance = json.load(fh)
    with schema_path.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)
