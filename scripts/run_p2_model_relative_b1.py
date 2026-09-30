"""Step-8 development-only model-relative B1 evaluation."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_p2_static_model_level import (
    GLOBAL_OUT,
    METADATA,
    decision,
    evaluate_artifact_features,
    model_relative_b1_records,
)

OUTPUT = METADATA / "model_relative_b1_development_results.json"


def run() -> dict:
    global_data = json.loads(GLOBAL_OUT.read_text(encoding="utf-8"))
    targets = global_data["records"]
    if not global_data.get("complete") or len(targets) != 169:
        raise AssertionError("Complete Step-4 development artifact set required")
    records, names = model_relative_b1_records(targets)
    if len(names) != 168 or any("layer" in name.lower() or "tensor" in name.lower() for name in names):
        raise AssertionError("Model-relative feature contract is not the 168 B1 summaries")
    evaluation = evaluate_artifact_features(records, names)
    result = {"version": "p2-model-relative-b1-v1", "representation": "MODEL_RELATIVE_B1_168_V1",
              "artifact_count": len(records), "feature_count": len(names),
              "lineage_count": len({x["parent_lineage_id"] for x in records}), "feature_names": names,
              "evaluation": evaluation,
              "decision": decision(evaluation, "KEEP_MODEL_RELATIVE_B1", "MODEL_RELATIVE_SIGNAL_PRESENT_BUT_INSUFFICIENT", "STOP_STATIC_MODEL_LEVEL_ML")}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
