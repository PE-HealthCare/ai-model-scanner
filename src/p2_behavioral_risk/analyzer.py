"""
P2 Behavioral Risk Analyzer
Hackathon Option 2.

Pipeline:

    P1 features.json
            |
            v
    P2 adapter validation
            |
            v
    P3 ml_results.json
            |
            v
    Trusted model handoff
            |
            v
    Vision STRIP probing
            |
            v
    S_behavior
            |
            +------> S_static
            |           |
            |           v
            |     highest-risk layer
            |
            v
          MRS
            |
            v
         verdict
            |
            v
    risk_results.json

P2 does not reload the untrusted SafeTensors model.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime
from typing import Any, Dict

from .adapters import (
    load_features_json,
    load_ml_results_json,
)
from .config import BOUND_N
from .output_writer import write_risk_results
from .prober import get_behavioral_result
from .risk_aggregator import (
    compute_mrs,
    compute_s_static_and_layer,
)


ASSUMPTIONS_LIMITATIONS = (
    "This assessment is based on static steganalysis and "
    "bounded behavioral probing within the tool's detection "
    "scope. PASS does not guarantee absolute security or "
    "absence of all manipulation. Results are probabilistic "
    "and should be used as part of a broader security review."
)


# ---------------------------------------------------------------------
# Provenance helpers
# ---------------------------------------------------------------------

def get_git_commit() -> str:
    """Return current Git commit if available."""

    try:
        return (
            subprocess
            .check_output(
                [
                    "git",
                    "rev-parse",
                    "HEAD",
                ]
            )
            .decode()
            .strip()
        )

    except Exception:
        return "unknown"


def get_file_hash(
    path: str | None,
) -> str | None:
    """Return SHA-256 for a file."""

    if not path or not os.path.exists(path):
        return None

    hasher = hashlib.sha256()

    with open(
        path,
        "rb",
    ) as file:

        for chunk in iter(
            lambda: file.read(65536),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


# ---------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------

def load_calibration_data(
    calibration_path: str | None = None,
) -> Dict[str, Any]:
    """
    Load P2 behavioral calibration data.

    Expected structure:

        {
            "calibration_data": {
                "VISION": {
                    ...
                }
            }
        }
    """

    if calibration_path is None:

        base = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        calibration_path = os.path.join(
            base,
            "data",
            "calibration",
            "calibration_data.json",
        )

    if not os.path.exists(
        calibration_path
    ):
        raise RuntimeError(
            "Calibration data not found at "
            f"{calibration_path}"
        )

    try:

        with open(
            calibration_path,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            f"Invalid calibration JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            "Calibration file must contain a JSON object."
        )

    calibration_data = data.get(
        "calibration_data"
    )

    if not isinstance(
        calibration_data,
        dict,
    ):
        raise RuntimeError(
            "Calibration file is missing "
            "'calibration_data'."
        )

    if "VISION" not in calibration_data:
        raise RuntimeError(
            "Calibration data must contain VISION."
        )

    return calibration_data


# ---------------------------------------------------------------------
# Main P2 assessment
# ---------------------------------------------------------------------

def run_assessment(
    features_path: str,
    ml_results_path: str,
    output_path: str | None = None,
    model: Any = None,
    calibration_path: str | None = None,
) -> Dict[str, Any]:
    """
    Run the authoritative P2 Option 2 assessment.

    Inputs:
        features_path:
            P1-generated features.json

        ml_results_path:
            P3-generated ml_results.json

        output_path:
            destination for risk_results.json

        model:
            trusted in-process ResNet18 model

        calibration_path:
            P2 behavioral calibration artifact

    Returns:
        Final risk result dictionary.
    """

    # ---------------------------------------------------------------
    # Output path
    # ---------------------------------------------------------------

    if output_path is None:

        base = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        output_path = os.path.join(
            base,
            "data",
            "outputs",
            "risk_results.json",
        )

    # ---------------------------------------------------------------
    # Calibration
    # ---------------------------------------------------------------

    calibration_data = (
        load_calibration_data(
            calibration_path
        )
    )

    # ---------------------------------------------------------------
    # Step 1: P1/P3 inputs
    # ---------------------------------------------------------------

    print(
        "P2 Step 1: Loading P1 features "
        "and P3 ML results..."
    )

    features = load_features_json(
        features_path
    )

    ml_results, shap_explanation = (
        load_ml_results_json(
            ml_results_path
        )
    )

    domain = features["domain"]
    is_quantized = features["is_quantized"]
    p_tamper = ml_results["p_tamper"]

    # ---------------------------------------------------------------
    # Step 2: Trusted model
    # ---------------------------------------------------------------

    print(
        "P2 Step 2: Obtaining trusted model..."
    )

    if model is None:

        from .handoff import get_trusted_model

        try:
            model = get_trusted_model()

        except Exception as exc:

            raise RuntimeError(
                "Authoritative P2 execution requires "
                "a trusted model from the handoff layer."
            ) from exc

    if model is None:
        raise RuntimeError(
            "Trusted model is missing."
        )

    # ---------------------------------------------------------------
    # Step 3: Behavioral probing
    # ---------------------------------------------------------------

    print(
        "P2 Step 3: Running Vision behavioral probing..."
    )

    behavioral = get_behavioral_result(
        is_quantized=is_quantized,
        domain=domain,
        model=model,
        calibration_data=calibration_data,
        bound_n=BOUND_N,
    )

    s_behavior = behavioral[
        "s_behavior"
    ]

    if is_quantized:

        behavioral_note = (
            "Behavioral probing bypassed because "
            "the model is quantized."
        )

    else:

        if s_behavior is None:
            raise RuntimeError(
                "Behavioral probing failed for a "
                "non-quantized model. S_behavior is "
                "missing; refusing to fabricate a score."
            )

        behavioral_note = (
            f"H_STRIP={behavioral['h_strip']:.3f}, "
            f"S_behavior={s_behavior:.3f}"
        )

    # ---------------------------------------------------------------
    # Step 4: Static aggregation
    # ---------------------------------------------------------------

    print(
        "P2 Step 4: Computing static risk "
        "and highest-risk layer..."
    )

    s_static, highest_layer = (
        compute_s_static_and_layer(
            features["layer_features"]
        )
    )

    # ---------------------------------------------------------------
    # Step 5: MRS
    # ---------------------------------------------------------------

    print(
        "P2 Step 5: Computing MRS and verdict..."
    )

    mrs_result = compute_mrs(
        s_static=s_static,
        p_tamper=p_tamper,
        s_behavior=s_behavior,
        is_quantized=is_quantized,
    )

    # ---------------------------------------------------------------
    # Step 6: Final result
    # ---------------------------------------------------------------

    final_output = {
        "producer": "P2",

        # Preserve P3 status instead of inventing a new
        # semantic status.
        "mock_status": ml_results.get(
            "mock_status",
            "UNKNOWN",
        ),

        "contract_version": "1.0",

        "generation_commit": ml_results.get(
            "generation_commit",
            get_git_commit(),
        ),

        # Required Option 2 scores.
        "mrs_score": mrs_result["mrs"],
        "verdict": mrs_result["verdict"],
        "s_static": s_static,
        "p_tamper": p_tamper,
        "s_behavior": s_behavior,

        # Evidence.
        "highest_risk_layer": highest_layer,
        "bypassed_behavior": behavioral[
            "bypassed_behavior"
        ],
        "probe_count": behavioral[
            "probe_count"
        ],
        "successful_probe_count": behavioral[
            "successful_probe_count"
        ],
        "failed_probe_count": behavioral[
            "failed_probe_count"
        ],
        "h_strip": behavioral[
            "h_strip"
        ],
        "shap_explanation": shap_explanation,
        "behavioral_note": behavioral_note,

        "assumptions_and_limitations":
            ASSUMPTIONS_LIMITATIONS,

        # Provenance.
        "_provenance": {
            "execution_mode": "authoritative",

            "features_source": {
                "file": features_path,
                "producer": features.get(
                    "source_producer"
                ),
                "mock_status": features.get(
                    "source_mock_status"
                ),
                "contract_version": features.get(
                    "source_contract_version"
                ),
                "generation_commit": features.get(
                    "source_generation_commit"
                ),
                "hash": get_file_hash(
                    features_path
                ),
            },

            "ml_source": {
                "file": ml_results_path,
                "producer": ml_results.get(
                    "producer"
                ),
                "mock_status": ml_results.get(
                    "mock_status"
                ),
                "contract_version": ml_results.get(
                    "contract_version"
                ),
                "generation_commit": ml_results.get(
                    "generation_commit"
                ),
                "hash": get_file_hash(
                    ml_results_path
                ),
            },

            "calibration_hash": get_file_hash(
                calibration_path
            ),

            "run_id": str(
                uuid.uuid4()
            ),

            "timestamp": datetime.now().isoformat(),
        },
    }

    # ---------------------------------------------------------------
    # Step 7: Write output
    # ---------------------------------------------------------------

    print(
        f"P2 Step 6: Writing risk results to "
        f"{output_path}"
    )

    write_risk_results(
        final_output,
        output_path,
    )

    print(
        "P2 complete: "
        f"MRS={mrs_result['mrs']} "
        f"Verdict={mrs_result['verdict']}"
    )

    return final_output
