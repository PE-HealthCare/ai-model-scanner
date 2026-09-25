# tests/test_quantized_reconciliation.py
"""
P2 quantized-representation reconciliation tests (D5/D6/D7 + bypass + MRS).

Authoritative P1 quantized contract (origin/recovery-mainline @ e3de268,
contracts/features.schema.json, docs/D11_QUANTIZED_P3_CLASSIFIER_DECISION.md):

    is_quantized = true
    ks_stat      = finite numeric value
    entropy, pov_chi2, lsb_kl, mean, std, skewness, kurtosis,
    sparsity, outlier_pct = null

null means unavailable. It is never converted to 0, NaN, a fabricated value,
or an FP-derived substitute.

Covers the P2-owned reconciliation checklist:

  7.  quantized input parses with ks_stat finite and the other nine null
  8.  quantized input never executes FP behavioral probing
  9.  quantized D5 uses ks_stat only, without treating None as zero
  10. quantized MRS uses the frozen 55/45 weighting
  11. non-quantized MRS retains the frozen 40/35/25 weighting
  12. no fake layer_id is introduced in active P2 code
  13. D6 documents the locked layer-identity contract (authoritative
      layer_name identity, canonical lexical tie ordering)
  14. output schema remains valid (risk_results + features contracts)
  2.  legacy feature names are not consumed by active D5 code

Scope discipline: no layer_id fixtures. Exact-tie behavior follows the
locked P1/D6 contract (authoritative ``layer_name``, canonical lexical
ordering); tie-winner coverage lives in tests/test_d6_tie_break.py.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import statistics
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from jsonschema import Draft202012Validator

import src.p2_behavioral_risk.prober as prober
import src.p2_behavioral_risk.risk_aggregator as risk_aggregator
from src.p2_behavioral_risk.adapters import load_features_json
from src.p2_behavioral_risk.analyzer import run_assessment
from src.p2_behavioral_risk.risk_aggregator import (
    compute_mrs,
    compute_s_static_and_layer,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = REPO_ROOT / "contracts"

FP_ONLY_NINE = (
    "entropy", "pov_chi2", "lsb_kl", "mean", "std",
    "skewness", "kurtosis", "sparsity", "outlier_pct",
)
CANONICAL_TEN = (
    "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean",
    "std", "skewness", "kurtosis", "sparsity", "outlier_pct",
)

P2_ACTIVE_MODULES = (
    "src/p2_behavioral_risk/adapters.py",
    "src/p2_behavioral_risk/risk_aggregator.py",
    "src/p2_behavioral_risk/prober.py",
    "src/p2_behavioral_risk/output_writer.py",
)


# ------------------------------------------------------------------ helpers
def _load_schema(name: str) -> dict:
    with (CONTRACT_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(data) -> str:
    fd, path = tempfile.mkstemp(suffix=".json", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def quantized_layer(name, ks_stat):
    """Authoritative P1 quantized layer record: finite ks_stat, nine nulls."""
    layer = {"layer_name": name, "ks_stat": ks_stat}
    for stat in FP_ONLY_NINE:
        layer[stat] = None
    return layer


def quantized_payload(ks_values) -> dict:
    layers = [
        quantized_layer(f"q.layer{i}", ks)
        for i, ks in enumerate(ks_values)
    ]
    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "TEST-Q-GEN",
        "input_domain": "VISION",
        "is_quantized": True,
        "layer_count": len(layers),
        "static_features": layers,
    }


def ml_payload() -> dict:
    return {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": "TEST-Q-GEN",
        "p_tamper": 0.3,
        "shap_attributions": {name: 0.0 for name in CANONICAL_TEN},
        "model_version": "quantized-reconciliation-test",
    }


def fp_layer(name, **overrides):
    """Canonical ten-feature non-quantized layer dict (no legacy names)."""
    layer = {
        "layer_name": name,
        "entropy": 1.5, "pov_chi2": 2.0, "lsb_kl": 0.1, "ks_stat": 0.5,
        "mean": 0.0, "std": 1.0, "skewness": 0.0, "kurtosis": 3.0,
        "sparsity": 0.0, "outlier_pct": 5.0,
    }
    layer.update(overrides)
    return layer


def _ks_only_reference(ks_values):
    """
    Independent, pure-python restatement of the locked D5 operator using ONLY
    the supplied ks_stat evidence (single eligible feature per layer).
    Returns None when no layer is eligible.
    """
    med = statistics.median(ks_values)
    mad = statistics.median([abs(v - med) for v in ks_values])
    factors = []
    for x in ks_values:
        if mad == 0.0:
            if x != med:
                continue  # DEGENERATE -> layer non-eligible, never E=0
            e = 0.0       # deterministic zero anomaly (eligible)
        else:
            z = (x - med) / (1.4826 * mad)
            e = abs(z) / (1.0 + abs(z))
        factors.append(e)
    if not factors:
        return None
    product = 1.0
    for e in factors:
        product *= (1.0 - e)
    return 1.0 - product


# ------------------------------------------------- 7. quantized parse / schema
def test_quantized_payload_is_contract_valid_and_parses_ks_only():
    payload = quantized_payload([0.10, 0.35, 0.75])
    Draft202012Validator(_load_schema("features.schema.json")).validate(payload)

    path = _write_json(payload)
    try:
        parsed = load_features_json(path)
    finally:
        os.unlink(path)

    assert parsed["is_quantized"] is True
    assert len(parsed["layer_features"]) == 3
    for layer in parsed["layer_features"]:
        assert isinstance(layer["ks_stat"], float)
        assert np.isfinite(layer["ks_stat"])
        for stat in FP_ONLY_NINE:
            # unavailable — never 0, never NaN
            assert layer[stat] is None


def test_quantized_adapter_rejects_fabricated_fp_field():
    """D11: on quantized input the nine FP-only fields must be null."""
    payload = quantized_payload([0.2, 0.4, 0.6])
    payload["static_features"][0]["entropy"] = 0.5  # fabricated FP evidence

    path = _write_json(payload)
    try:
        with pytest.raises(ValueError, match="must be null for quantized"):
            load_features_json(path)
    finally:
        os.unlink(path)


def test_quantized_adapter_rejects_missing_ks_stat():
    """Missing ks_stat fails closed — never zero-filled."""
    payload = quantized_payload([0.2, 0.4, 0.6])
    payload["static_features"][1]["ks_stat"] = None

    path = _write_json(payload)
    try:
        with pytest.raises(ValueError, match="invalid value"):
            load_features_json(path)
    finally:
        os.unlink(path)


# --------------------------------------- 9. quantized D5 uses ks_stat only
def test_quantized_d5_uses_ks_stat_without_none_zero_imputation():
    ks_values = [0.10, 0.35, 0.75]
    layers = [
        quantized_layer(f"q.layer{i}", ks) for i, ks in enumerate(ks_values)
    ]

    seen_targets = []
    real_mad_zscore = risk_aggregator.mad_zscore

    def spy(x, x_base):
        seen_targets.append(float(x))
        return real_mad_zscore(x, x_base)

    with mock.patch.object(risk_aggregator, "mad_zscore", side_effect=spy):
        s_static, highest = compute_s_static_and_layer(layers)

    # Exactly one D7 evaluation per layer, and its target is ks_stat.
    # (A None reaching mad_zscore would raise; a zero-imputed FP field would
    # add extra targets.) Neither happens.
    assert len(seen_targets) == 3
    assert sorted(seen_targets) == sorted(ks_values)

    expected = _ks_only_reference(ks_values)
    assert expected is not None
    assert s_static == pytest.approx(expected, abs=1e-12)
    assert 0.0 < s_static <= 1.0
    assert isinstance(highest, str)
    assert highest in {layer["layer_name"] for layer in layers}


def test_quantized_mixed_valid_invalid_layers_exclude_only_invalid():
    layers = [
        quantized_layer("q.no_ks", None),  # unavailable evidence -> excluded
        quantized_layer("q1", 0.10),
        quantized_layer("q2", 0.35),
        quantized_layer("q3", 0.75),
    ]

    s_static, _ = compute_s_static_and_layer(layers)

    expected = _ks_only_reference([0.10, 0.35, 0.75])
    assert expected is not None
    assert s_static == pytest.approx(expected, abs=1e-12)


def test_quantized_no_eligible_evidence_fails_closed():
    # Every layer's only statistical evidence is unavailable -> explicit
    # fail-closed, never S_static = 0.0 fabricated from nothing.
    layers = [quantized_layer(f"q{i}", None) for i in range(4)]
    with pytest.raises(RuntimeError, match="No D7-valid layer evidence"):
        compute_s_static_and_layer(layers)


def test_quantized_insufficient_layers_fail_closed_for_d7_baseline():
    layers = [quantized_layer("a", 0.3), quantized_layer("b", 0.7)]
    with pytest.raises(RuntimeError, match="Insufficient baseline"):
        compute_s_static_and_layer(layers)


# ------------------------------------- 8. quantized bypasses FP probing path
def test_quantized_input_never_executes_fp_behavioral_probing():
    features_path = _write_json(quantized_payload([0.2, 0.4, 0.6]))
    ml_path = _write_json(ml_payload())
    fd, out_path = tempfile.mkstemp(suffix=".json", text=True)
    os.close(fd)
    os.unlink(out_path)  # the writer must create it, not a leftover

    try:
        with mock.patch.object(
            prober, "generate_probes",
            side_effect=AssertionError(
                "FP probe generation must not run for quantized input"
            ),
        ), mock.patch.object(
            prober, "run_bounded_inference",
            side_effect=AssertionError(
                "FP inference must not run for quantized input"
            ),
        ):
            result = run_assessment(
                features_path=features_path,
                ml_results_path=ml_path,
                output_path=out_path,
                model=None,
                mock_mode=False,
            )

        behavioral = prober.get_behavioral_result(
            is_quantized=True,
            domain="VISION",
            model=None,
            calibration_data={"VISION": {"median": 1.0, "mad": 0.5}},
            mock_mode=False,
        )
    finally:
        os.unlink(features_path)
        os.unlink(ml_path)

    # Bypass contract: no probing, no behavioral evidence.
    assert behavioral["bypassed_behavior"] is True
    assert behavioral["s_behavior"] is None
    assert behavioral["probe_count"] == 0

    # Output contract: s_behavior null iff quantized bypass (risk schema).
    assert result["s_behavior"] is None

    # S_static is computed from the supplied ks_stat evidence alone.
    expected_s = _ks_only_reference([0.2, 0.4, 0.6])
    assert expected_s is not None
    assert float(result["s_static"]) == pytest.approx(expected_s, abs=1e-12)

    # Quantized MRS uses the frozen 55/45 weighting end to end.
    expected_mrs = round(
        min(100.0, 55.0 * float(result["s_static"]) + 45.0 * 0.3), 2
    )
    assert result["mrs_score"] == pytest.approx(expected_mrs)

    # 14. the emitted artifact remains schema-valid.
    written = json.loads(Path(out_path).read_text(encoding="utf-8"))
    Draft202012Validator(_load_schema("risk_results.schema.json")).validate(
        written
    )
    os.unlink(out_path)


# ------------------------------------------------ 10 / 11. frozen MRS weights
def test_quantized_mrs_uses_frozen_55_45_weighting():
    result = compute_mrs(0.25, 0.5, None, True)
    assert result["mrs_score"] == pytest.approx(36.25)  # 55*.25 + 45*.5

    result = compute_mrs(0.4, 0.2, None, True)
    assert result["mrs_score"] == pytest.approx(round(55 * 0.4 + 45 * 0.2, 2))

    # min(100, ...) clamp is part of the frozen formula.
    assert compute_mrs(1.0, 1.0, None, True)["mrs_score"] == 100.0
    # S_behavior is not required — and never introduced — for quantized.
    assert compute_mrs(0.0, 0.0, None, True)["mrs_score"] == 0.0
    assert compute_mrs(0.5, 0.5, None, True)["verdict"] in {
        "PASS", "REVIEW", "FAIL",
    }


def test_non_quantized_mrs_retains_frozen_40_35_25_weighting():
    result = compute_mrs(0.25, 0.5, 0.75, False)
    assert result["mrs_score"] == pytest.approx(46.25)  # 40*.25+35*.5+25*.75

    # Fail-closed: non-quantized without S_behavior never fabricates a score.
    with pytest.raises(RuntimeError, match="missing S_behavior"):
        compute_mrs(0.25, 0.5, None, False)


# -------------------------------------------- 12 / 13. no invented identity
def _executable_layer_id_refs(source: str) -> list:
    """Collect executable (non-comment) ``layer_id`` references from source.

    ``ast`` drops comments, so explanatory prose such as "no production
    ``layer_id`` field" is invisible here; only real code — variable names,
    attribute access, and string keys like ``layer["layer_id"]`` — is found.
    """
    refs = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "layer_id":
            refs.append("Name:layer_id")
        elif isinstance(node, ast.Attribute) and node.attr == "layer_id":
            refs.append("Attribute:layer_id")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value == "layer_id"
        ):
            refs.append("Constant:'layer_id'")
    return refs


def test_no_fake_layer_id_in_active_p2_code():
    for rel in P2_ACTIVE_MODULES:
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        # AST excludes comments: the check covers ACTIVE code only, where a
        # commented-out legacy block is not executable semantics.
        assert _executable_layer_id_refs(source) == [], (
            f"executable layer_id identity usage in {rel}"
        )

    # The active D5/D6 entry point must not use layer_id as executable
    # production identity. Explanatory comments documenting that there is NO
    # production layer_id field are permitted and invisible to this check.
    assert _executable_layer_id_refs(
        inspect.getsource(compute_s_static_and_layer)
    ) == []

    # Layer dicts without any layer_id key remain fully accepted.
    s_static, _ = compute_s_static_and_layer(
        [
            fp_layer("L1", entropy=3.0),
            fp_layer("L2", entropy=1.0),
            fp_layer("L3", entropy=2.0),
        ]
    )
    assert 0.0 <= s_static <= 1.0


def test_d6_documents_locked_layer_identity_contract():
    src = inspect.getsource(compute_s_static_and_layer)
    lowered = src.lower()

    # Locked contract is documented: authoritative layer_name identity and
    # canonical lexical tie ordering (D6 decision Sections 3, 5.7, 13).
    assert "layer_name" in lowered
    assert "canonical lexical" in lowered
    # The stale "unresolved upstream interface" marker must be gone.
    assert "unresolved" not in lowered
    # No executable layer_id identity usage (comments excluded via AST).
    assert _executable_layer_id_refs(src) == []


# ------------------------------------------- 2. legacy names are not consumed
def test_legacy_feature_names_are_not_consumed_by_d5():
    legacy_layers = [
        {"layer_name": f"legacy{i}", "chi_square": 1.0 + i, "kl_div": 0.5 + i}
        for i in range(4)
    ]
    # chi_square / kl_div are not canonical D5 evidence: they contribute
    # nothing, and with no eligible evidence D5 fails closed.
    with pytest.raises(RuntimeError, match="No D7-valid layer evidence"):
        compute_s_static_and_layer(legacy_layers)


def test_legacy_keys_do_not_alter_canonical_computation():
    base = [
        fp_layer("L1", entropy=3.0, pov_chi2=3.0),
        fp_layer("L2", entropy=1.0, pov_chi2=1.0),
        fp_layer("L3", entropy=2.0, pov_chi2=2.0),
    ]
    s_plain, h_plain = compute_s_static_and_layer(base)

    polluted = [
        dict(layer, chi_square=999.0, kl_div=999.0) for layer in base
    ]
    s_dirty, h_dirty = compute_s_static_and_layer(polluted)

    assert s_dirty == s_plain
    assert h_dirty == h_plain
