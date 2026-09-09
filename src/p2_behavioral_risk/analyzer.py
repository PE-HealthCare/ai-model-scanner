def run_assessment(
    features_path,
    ml_results_path,
    output_path=None,
    model=None,
    mock_mode=False,
    calibration_path=None,
):

    if output_path is None:
        base = os.path.dirname(
            os.path.dirname(
                os.path.dirname(__file__)
            )
        )

        output_path = os.path.join(
            base,
            "data",
            "outputs",
            "risk_results.json",
        )

    if calibration_path is None:

        base = os.path.dirname(
            os.path.dirname(
                os.path.dirname(__file__)
            )
        )

        calibration_path = os.path.join(
            base,
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

    feature_commit = features[
        "source_generation_commit"
    ]

    ml_commit = ml_results[
        "generation_commit"
    ]

    if feature_commit != ml_commit:
        raise RuntimeError(
            "D8 REJECT: P1 features and P3 ML results "
            "have different generation_commit values."
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

        "ml_generation_commit": ml_commit,

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
                    StubVisionModel
                )

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
