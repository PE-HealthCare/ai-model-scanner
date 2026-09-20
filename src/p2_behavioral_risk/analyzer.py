# src/p2_behavioral_risk/analyzer.py
"""
P2 risk analysis entry point.

Orchestrates the D2 trusted handoff, D3/D4 behavioral probing, D5/D6 static
aggregation, D7 MAD handling, MRS/verdict computation and risk_results
emission.

Fail-closed: any upstream failure stops the run with no MRS, no verdict and
no fabricated risk_results.json.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import uuid
from datetime import datetime

from .adapters import (
    load_calibration_data,
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


class P2AnalyzerError(RuntimeError):
    """Fail-closed P2 error. No MRS and no verdict may be produced."""


def _project_root():
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )


def get_file_hash(path):
    """SHA-256 of an artifact file (P2 provenance)."""
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def get_git_commit():
    """Current P2 code commit (P2 provenance)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_project_root(),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "UNKNOWN"


def _require_generation_commit(features, ml_results):
    """
    D8 – model staleness protection (LOCKED).

    P1 features.json and P3 ml_results.json MUST carry the same
    generation_commit. A missing or mismatched commit blocks the run.
    """
    feature_commit = features.get("generation_commit")
    ml_commit = ml_results.get("generation_commit")

    if not feature_commit or not ml_commit:
        raise P2AnalyzerError(
            "D8 BLOCKED: generation_commit is missing from the "
            "P1 features.json / P3 ml_results.json pair."
        )

    if feature_commit != ml_commit:
        raise P2AnalyzerError(
            "D8 BLOCKED: P1 features and P3 ML results "
            "have different generation_commit values."
        )

    return feature_commit


def run_assessment(
    features_path,
    ml_results_path,
    output_path=None,
    model=None,
    mock_mode=False,
    calibration_path=None,
):

    if output_path is None:
        output_path = os.path.join(
            _project_root(),
            "data",
            "outputs",
            "risk_results.json",
        )

    if calibration_path is None:
        calibration_path = os.path.join(
            _project_root(),
            "data",
            "calibration",
            "calibration_data.json",
        )

    calibration_data = load_calibration_data(
        calibration_path
    )

    # --------------------------------------------------------
    # STEP 1: Load upstream artifacts
    # --------------------------------------------------------

    features = load_features_json(
        features_path
    )

    ml_results, shap_explanation = (
        load_ml_results_json(
            ml_results_path
        )
    )

    # --------------------------------------------------------
    # D8 – generation commit consistency
    # --------------------------------------------------------

    feature_commit = _require_generation_commit(
        features,
        ml_results,
    )

    # --------------------------------------------------------
    # Authoritative input gate
    # --------------------------------------------------------

    if not mock_mode:

        if features["source_mock_status"] != "VERIFIED-REAL":
            raise RuntimeError(
                "P1 features.json is not VERIFIED-REAL."
            )

        if ml_results["mock_status"] != "VERIFIED-REAL":
            raise RuntimeError(
                "P3 ml_results.json is not VERIFIED-REAL."
            )

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    provenance = {
        "execution_mode": (
            "mock" if mock_mode else "authoritative"
        ),

        "features_generation_commit": feature_commit,

        "ml_generation_commit": ml_results["generation_commit"],

        "calibration_hash": (
            get_file_hash(calibration_path)
        ),

        "p2_commit": get_git_commit(),

        "run_id": str(uuid.uuid4()),

        "timestamp": datetime.now().isoformat(),
    }

    domain = features["domain"]
    is_quantized = features["is_quantized"]

    # --------------------------------------------------------
    # STEP 2 – D2 trusted handoff
    # --------------------------------------------------------

    if not is_quantized:

        if model is None:

            if mock_mode:

                from .stub_models import (
                    StubNLPModel,
                    StubVisionModel,
                )

                # Domain routing: VISION probes are float image noise,
                # NLP probes are integer token IDs. The mock model must
                # accept the routed probe input type.
                if domain == "NLP":
                    model = StubNLPModel()
                else:
                    model = StubVisionModel()

            else:

                from .handoff import (
                    get_trusted_model
                )

                model = get_trusted_model()

    # --------------------------------------------------------
    # STEP 3 – D3/D4 behavioral probing
    # --------------------------------------------------------

    behavioral = get_behavioral_result(
        is_quantized=is_quantized,
        domain=domain,
        model=model,
        calibration_data=calibration_data,
        bound_n=BOUND_N,
        mock_mode=mock_mode,
    )

    s_behavior = behavioral[
        "s_behavior"
    ]

    # --------------------------------------------------------
    # STEP 4 – D5/D6
    # --------------------------------------------------------

    s_static, highest_layer = (
        compute_s_static_and_layer(
            features["layer_features"]
        )
    )

    # --------------------------------------------------------
    # STEP 5 – MRS
    # --------------------------------------------------------

    p_tamper = float(
        ml_results["p_tamper"]
    )

    mrs_result = compute_mrs(
        s_static=s_static,
        p_tamper=p_tamper,
        s_behavior=s_behavior,
        is_quantized=is_quantized,
    )

    # --------------------------------------------------------
    # STEP 6 – risk_results contract
    # --------------------------------------------------------

    final_output = {

        "producer": "P2",

        "mock_status": (
            "MOCK"
            if mock_mode
            else "VERIFIED-REAL"
        ),

        "contract_version": "1.0",

        "generation_commit": feature_commit,

        "mrs_score": mrs_result[
            "mrs_score"
        ],

        "verdict": mrs_result[
            "verdict"
        ],

        "s_static": s_static,

        "p_tamper": p_tamper,

        "s_behavior": s_behavior,

    }

    # --------------------------------------------------------
    # STEP 7 – write
    # --------------------------------------------------------

    write_risk_results(
        final_output,
        output_path,
    )

    return final_output
