"""Focused P2 tests: MRS routing, frozen weights, and the BLOCKED guard.

Self-contained: imports ONLY P2 modules (src.p2_behavioral_risk.*), the
standard library and jsonschema. It does not import the orchestrator
(scan_model), P1 static analysis, or the P3 classifier, so this module runs
and stays meaningful without any other subsystem being importable.

Locked contracts exercised here (unchanged by this file):

  - D5  S_static = 1 - prod(1 - E_l); unavailable evidence is never
       zero-imputed, and a run with no eligible evidence fails closed.
  - D6  identity is `layer_name`; exact ties are resolved by canonical
       lexical `layer_name` ordering. There is no `layer_id` and no
       positional identity.
  - D7  Z = (x - median) / (1.4826 * MAD); baseline <= 2 is unavailable;
       zero MAD with target == median is a deterministic 0, otherwise
       DEGENERATE_DEVIATION. No epsilon substitution.
  - MRS non-quantized: min(100, 40*S_static + 35*P_tamper + 25*S_behavior)
    quantized:     min(100, 55*S_static + 45*P_tamper)

Governance intent of the BLOCKED guard: when behavioral evidence is missing
for a non-quantized model, P2 must stop. It must NOT emit an MRS, must NOT
renormalize the remaining weights, and must NOT redistribute the behavioral
weight across the other components. The `test_frozen_*_weights_*` tests pin
each weight exactly so that any such renormalization or redistribution
fails.

The quantized branch carries no behavioral component, so a supplied
`s_behavior` cannot influence the quantized score; see
`test_compute_mrs_quantized_is_invariant_to_s_behavior`.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from src.p2_behavioral_risk.analyzer import run_assessment
from src.p2_behavioral_risk.risk_aggregator import (
    compute_mrs,
    compute_s_static_and_layer,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "contracts"

FEATURE_NAMES = (
    "entropy", "pov_chi2", "lsb_kl", "ks_stat", "mean",
    "std", "skewness", "kurtosis", "sparsity", "outlier_pct",
)

GENERATION_COMMIT = "TEST-GEN"


def _load_schema(name: str) -> dict:
    with (CONTRACT_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def _synthetic_features(is_quantized: bool) -> dict:
    """Contract-valid P1-shaped features payload, built locally for P2 tests.

    Three layers are required: D7 needs more than two comparable baseline
    observations, so a two-layer payload is rejected as insufficient
    evidence. For quantized input the nine FP-only measurements are JSON
    null (D11); only `ks_stat` carries evidence.
    """
    layer_seeds = (
        ("synthetic.layer1", 0.12),
        ("synthetic.layer2", 0.10),
        ("synthetic.layer3", 0.14),
    )
    static_features: list[dict[str, str | float | None]] = []
    for index, (layer_name, ks_stat) in enumerate(layer_seeds):
        # Value domain is mixed and matches contracts/features.schema.json:
        # "layer_name" is a string, while the ten statistical feature keys hold
        # a finite number in [0, 1] or JSON null (D11) when evidence is
        # unavailable for a quantized model. null is preserved verbatim and is
        # never substituted with 0 or any other fabricated value.
        layer: dict[str, str | float | None] = {"layer_name": layer_name}
        for position, name in enumerate(FEATURE_NAMES):
            # Every non-quantized static feature must be a finite number in
            # [0, 1] per contracts/features.schema.json. Values are kept
            # distinct per layer/stat so the D7 intra-model baseline has a
            # non-degenerate spread.
            layer[name] = (
                None if is_quantized
                else round(0.1 * (index + 1) + 0.01 * position, 4)
            )
        layer["ks_stat"] = ks_stat
        static_features.append(layer)

    return {
        "producer": "P1",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": GENERATION_COMMIT,
        "input_domain": "VISION",
        "is_quantized": is_quantized,
        "layer_count": len(static_features),
        "static_features": static_features,
    }


def _synthetic_ml_results() -> dict:
    """Contract-valid P3-shaped ml_results payload, built locally for P2 tests."""
    return {
        "producer": "P3",
        "mock_status": "VERIFIED-REAL",
        "contract_version": "1.0",
        "generation_commit": GENERATION_COMMIT,
        "p_tamper": 0.08,
        "shap_attributions": {name: 0.0 for name in FEATURE_NAMES},
        "model_version": "synthetic-test",
    }


class _AssessmentBase(unittest.TestCase):
    """Runs run_assessment against temporary inputs so nothing is persisted."""

    output_existed = False
    output_path = None

    def _assess(self, features: dict, ml_results: dict, mock_mode: bool):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            features_path = root / "features.json"
            ml_results_path = root / "ml_results.json"
            output_path = root / "risk_results.json"
            features_path.write_text(json.dumps(features), encoding="utf-8")
            ml_results_path.write_text(json.dumps(ml_results), encoding="utf-8")
            try:
                result = run_assessment(
                    features_path=features_path,
                    ml_results_path=ml_results_path,
                    output_path=output_path,
                    mock_mode=mock_mode,
                )
            finally:
                self.output_existed = output_path.exists()
                self.output_path = output_path
        return result


class TestBehavioralEvidenceMRSRouting(_AssessmentBase):
    """Frozen-formula routing and the incomplete-evidence BLOCKED guard."""

    def setUp(self):
        # The synthetic upstream payloads must be contract-valid so the
        # pipeline-level tests below exercise the real provenance checks.
        for is_quantized in (False, True):
            Draft202012Validator(_load_schema("features.schema.json")).validate(
                _synthetic_features(is_quantized)
            )
        Draft202012Validator(_load_schema("ml_results.schema.json")).validate(
            _synthetic_ml_results()
        )

    # --- frozen formula: quantized branch (55/45) --------------------------

    def test_compute_mrs_quantized_bypass_exact_scores(self):
        # 55*0.25 + 45*0.5 = 13.75 + 22.5
        self.assertEqual(compute_mrs(0.25, 0.5, None, True)["mrs_score"], 36.25)
        self.assertEqual(compute_mrs(0.0, 0.0, None, True)["mrs_score"], 0.0)
        # min(100, ...) clamp is part of the frozen formula.
        self.assertEqual(compute_mrs(1.0, 1.0, None, True)["mrs_score"], 100.0)

    def test_compute_mrs_quantized_is_invariant_to_s_behavior(self):
        # 55*0.25 + 45*0.5 = 36.25
        expected = min(100.0, 55 * 0.25 + 45 * 0.5)
        self.assertEqual(expected, 36.25)

        scores = [
            compute_mrs(0.25, 0.5, s_behavior, True)["mrs_score"]
            for s_behavior in (None, 0.0, 0.75)
        ]
        # The documented absence state (None) and supplied evidence agree.
        self.assertEqual(scores[0], scores[1])
        self.assertEqual(scores[1], scores[2])
        # ...and that score is the frozen 55/45 formula, with no behavioral term.
        for score in scores:
            self.assertEqual(score, expected)

    def test_run_assessment_quantized_uses_frozen_55_45(self):
        features = _synthetic_features(is_quantized=True)
        ml_results = _synthetic_ml_results()
        risk = self._assess(features, ml_results, mock_mode=False)

        expected_s_static, _ = compute_s_static_and_layer(features["static_features"])
        # s_static is not rounded, so it is compared at full precision;
        # mrs_score is rounded to 2dp by the frozen contract.
        self.assertAlmostEqual(risk["s_static"], expected_s_static, places=12)
        self.assertAlmostEqual(
            risk["mrs_score"],
            min(100.0, 55.0 * expected_s_static + 45.0 * float(ml_results["p_tamper"])),
            places=2,
        )
        # Contract: s_behavior is null iff the quantized bypass was taken.
        self.assertIsNone(risk["s_behavior"])
        self.assertEqual(
            risk["verdict"],
            "PASS" if risk["mrs_score"] <= 34
            else "REVIEW" if risk["mrs_score"] <= 69
            else "FAIL",
        )
        Draft202012Validator(_load_schema("risk_results.schema.json")).validate(risk)

    # --- frozen formula: non-quantized with real evidence (40/35/25) -------

    def test_compute_mrs_non_quantized_with_evidence_exact_scores(self):
        # 40*0.25 + 35*0.5 + 25*0.75 = 10 + 17.5 + 18.75
        self.assertEqual(compute_mrs(0.25, 0.5, 0.75, False)["mrs_score"], 46.25)
        self.assertEqual(compute_mrs(0.0, 0.0, 0.0, False)["mrs_score"], 0.0)
        self.assertEqual(compute_mrs(1.0, 1.0, 1.0, False)["mrs_score"], 100.0)

    def test_frozen_mrs_weights_are_exactly_40_35_25(self):
        # Each weight is pinned in isolation. Any renormalization of the
        # weights (e.g. rescaling to sum to 100) or redistribution of the
        # behavioral weight across the other components changes these
        # values and fails this test.
        self.assertEqual(compute_mrs(1.0, 0.0, 0.0, False)["mrs_score"], 40.0)
        self.assertEqual(compute_mrs(0.0, 1.0, 0.0, False)["mrs_score"], 35.0)
        self.assertEqual(compute_mrs(0.0, 0.0, 1.0, False)["mrs_score"], 25.0)

    def test_frozen_quantized_weights_are_exactly_55_45(self):
        self.assertEqual(compute_mrs(1.0, 0.0, None, True)["mrs_score"], 55.0)
        self.assertEqual(compute_mrs(0.0, 1.0, None, True)["mrs_score"], 45.0)

    # --- BLOCKED guard: non-quantized without behavioral evidence ----------

    def test_compute_mrs_blocked_on_missing_non_quantized_evidence(self):
        # BLOCKED: no MRS is produced at all for a non-quantized model with
        # no behavioral evidence.
        with self.assertRaises(RuntimeError) as caught:
            compute_mrs(0.25, 0.5, None, False)
        message = str(caught.exception)
        self.assertIn("missing S_behavior", message)
        # No fabricated score: the call aborts rather than substituting one.
        self.assertIn("refusing to fabricate a score", message)

    def test_blocked_non_quantized_does_not_renormalize_or_redistribute(self):
        # If P2 ever fell back to renormalizing 40/35 (or redistributing the
        # 25% behavioral weight) it would have to return a number. It must
        # raise instead, for every evidence-scarce input shape.
        for s_static, p_tamper in ((0.25, 0.5), (0.0, 0.0), (1.0, 1.0)):
            with self.subTest(s_static=s_static, p_tamper=p_tamper):
                with self.assertRaises(RuntimeError):
                    compute_mrs(s_static, p_tamper, None, False)

    def test_run_assessment_blocked_emits_no_risk_artifact(self):
        # A non-quantized assessment without a trusted P1 model context must
        # stop: no MRS, no verdict, and no risk_results artifact on disk.
        with self.assertRaises(RuntimeError) as caught:
            self._assess(
                _synthetic_features(is_quantized=False),
                _synthetic_ml_results(),
                mock_mode=False,
            )
        self.assertIn("trusted", str(caught.exception).lower())
        self.assertFalse(
            self.output_existed,
            "BLOCKED run must not persist a risk_results artifact",
        )

    # --- input-contract rejection ------------------------------------------

    def test_run_assessment_rejects_missing_is_quantized_tag(self):
        features = _synthetic_features(is_quantized=False)
        del features["is_quantized"]
        with self.assertRaises(KeyError) as caught:
            self._assess(features, _synthetic_ml_results(), mock_mode=False)
        self.assertIn("is_quantized", str(caught.exception))

    # --- rejection: invalid / non-finite / out-of-range evidence ----------

    def test_compute_mrs_rejects_invalid_behavioral_evidence(self):
        for bad in (float("nan"), float("inf"), float("-inf"), -0.5, 1.5):
            with self.subTest(s_behavior=bad):
                with self.assertRaisesRegex(
                    ValueError, r"s_behavior must be in \[0,1\]"
                ):
                    compute_mrs(0.25, 0.5, bad, False)

    # --- mock path (P2-owned stub models, no P1/P3 dependency) -------------

    def test_mock_path_produces_contract_valid_non_quantized_result(self):
        # Mock mode uses P2's own stub_models and D4 calibration, so this
        # exercises the full non-quantized 40/35/25 path without P1 or P3.
        risk = self._assess(
            _synthetic_features(is_quantized=False),
            _synthetic_ml_results(),
            mock_mode=True,
        )
        self.assertEqual(risk["mock_status"], "MOCK")
        # Mock mode still supplies behavioral evidence, so the non-quantized
        # formula applies with no renormalization or weight redistribution.
        self.assertIsNotNone(risk["s_behavior"])
        self.assertAlmostEqual(
            risk["mrs_score"],
            min(
                100.0,
                40.0 * risk["s_static"]
                + 35.0 * float(_synthetic_ml_results()["p_tamper"])
                + 25.0 * risk["s_behavior"],
            ),
            places=2,
        )
        self.assertEqual(
            risk["verdict"],
            "PASS" if risk["mrs_score"] <= 34
            else "REVIEW" if risk["mrs_score"] <= 69
            else "FAIL",
        )
        Draft202012Validator(_load_schema("risk_results.schema.json")).validate(risk)


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
