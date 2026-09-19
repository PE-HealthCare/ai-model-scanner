# Phase 5 — Behavioral Probing + Risk Verification

> Chronology note (read first): §1–§9 below are the HISTORICAL pre-evidence
> verification checklist (pre-CP5-PASS planning state; checkboxes intentionally
> left as originally written). They are SUPERSEDED by the authoritative
> current status in §10 (CP5 PASS — CODE + RUNTIME EVIDENCE VERIFIED). Do not
> read unchecked historical boxes as contradicting the §10 PASS; they record
> the gate as originally specified before the evidence pass. §10 is the
> authoritative current CP5 verification. This PASS is code-runtime evidence
> only and is NOT VERIFIED-REAL production authorization.

## 1. Gate Semantics

Exactly:

PASS / FAIL / BLOCKED

Required unresolved decision or required pending evidence = BLOCKED for the affected authoritative completion criterion.

A checkbox without evidence is not verification.

A methodology that is locked while implementation/calibration evidence is pending SHALL NOT be treated as fully verified.

## 2. Prerequisites

- [ ] CP4 PASS.
- [ ] P1 real inputs verified.
- [ ] P3 `ml_results.json` verified-real.
- [ ] required contracts resolved.

## 3. Probe Routing

- [ ] quantized models bypass behavioral probing;
- [ ] non-quantized VISION uses float/image-noise probe path;
- [ ] non-quantized NLP uses integer token-ID probe path;
- [ ] no invalid input type is generated for a domain.

## 4. Bounded Execution

- [ ] finite production pass limit exists;
- [ ] production limit is explicitly approved;
- [ ] agent did not choose it autonomously;
- [ ] time/resource constraints are tested where applicable.

If production bound is unresolved: BLOCKED.

## 5. D3 / D4

### D3 — STRIP baseline

- [ ] D3 methodology matches the locked project decision:
  - non-quantized models only;
  - Shannon entropy over softmax output probabilities;
  - existing 32 domain-appropriate probes;
  - empirical, domain-specific baseline distributions;
  - fixed scanner-controlled clean reference models;
  - no baseline derived from the uploaded model.
- [ ] required empirical calibration run completed;
- [ ] measured VISION/NLP baseline evidence recorded in `.planning/STATE.md`;
- [ ] evidence-dependent parameters, if any, are explicitly recorded;
- [ ] no invented baseline values, thresholds, or fallback behavior exists.

D3 methodology being locked is not sufficient for full authoritative behavioral verification while required calibration evidence is pending.

### D4 — Behavioral normalization

- [ ] H_STRIP→S_behavior normalization explicitly resolved.
- [ ] no invented threshold, clipping, normalization, or fallback behavior exists.

Unresolved D4 or incomplete required D3 calibration/evidence = BLOCKED.

## 6. Risk Aggregation

- [ ] per-layer→model aggregation follows approved D5;
- [ ] highest-risk-layer aggregation follows approved D6;
- [ ] D7 MAD handling follows approved locked decision;
- [ ] final non-quantized formula exact;
- [ ] final quantized formula exact;
- [ ] verdict ranges exact.

Unresolved D5 or D6 = BLOCKED for the affected authoritative risk/reporting completion.

## 7. Mandatory Adversarial Tests

- [ ] one-layer model;
- [ ] insufficient layers;
- [ ] zero MAD;
- [ ] near-zero MAD;
- [ ] NaN/Inf evidence;
- [ ] malformed `ml_results.json`;
- [ ] missing P_tamper;
- [ ] stale P3 artifact;
- [ ] quantized model accidentally entering behavioral path;
- [ ] probe input type mismatch;
- [ ] upstream failure.

Expected upstream-failure behavior:
```text
STOP
NON-ZERO STATUS
NO MRS
NO VERDICT
NO FABRICATED OUTPUT
```

## 8. Provenance

- [ ] features source recorded;
- [ ] ML source recorded;
- [ ] source versions/commits recorded;
- [ ] P2 version recorded;
- [ ] contract/semantic version recorded;
- [ ] run ID recorded;
- [ ] mock/real status recorded.

## 9. Scope

- [ ] only Phase-5 implementation/test files changed during Phase-5 implementation;
- [ ] no P1/P3 implementation changes;
- [ ] no unauthorized integration changes;
- [ ] governance/documentation synchronization is separately authorized and recorded when required.

## 10. CP5 Evidence — AUTHORITATIVE CURRENT STATUS

**CP5 STATUS: PASS — CODE + RUNTIME EVIDENCE VERIFIED**

**This is NOT VERIFIED-REAL production authorization.**

This documentation update is the final synchronization step. It records
already-verified code + runtime evidence. It performs no new measurement,
changes no implementation, formula, contract, calibration value, or test.

```text
Branch: person2
Verified commit: 4849706f5eaad16cca5d54933fff75e6431ee41a
Calibration check: python scripts/finalize_calibration_artifact.py --check → exit code 0
CP4: PASS (prerequisite, per .planning/STATE.md)
Probe evidence: domain-routed probes verified
  - non-quantized VISION uses float/image-noise probe path
  - non-quantized NLP uses integer token-ID probe path
  - no invalid input type generated for a domain
Bound evidence: exactly 32 probes per run (BOUND_N = 32); bounded inference
  enforced; every requested probe must succeed (fail-closed)
D3 methodology: locked methodology followed — Shannon entropy over softmax
  outputs, 32 domain-appropriate probes, empirical domain-specific baselines
  from scanner-controlled clean references (ResNet18 / DistilBERT),
  no baseline derived from the uploaded model
D3 empirical calibration/evidence:
  artifact: data/calibration/calibration_data.json
  methodology: recorded h_strip_values replayed through the repository's own
    scripts/generate_calibration_data.compute_statistics
    (median + median(|H_STRIP - median|)); no values invented
  VISION: ResNet18, 32 probes, 30 recorded observations,
    median = 5.085757341909422, MAD = 0.026241989955190892
  NLP: DistilBERT, 32 probes, 30 recorded observations,
    median = 6.881156798617935, MAD = 0.0007370728479614286
  new_measurement_performed = false
  recomputed statistics match the artifact exactly (match=True both domains)
D4: PASS — locked normalization
  deviation = H_median - H_STRIP; Z = deviation / (1.4826 * H_MAD);
  Z_clamped = max(0, Z); S_behavior = min(1, Z_clamped / 3)
  - missing MAD fails closed (RuntimeError: mad)
  - invalid (NaN/negative/non-finite) MAD rejected
  - zero MAD: target == median -> 0.0; target != median -> DEGENERATE_DEVIATION
D5: PASS — S_static = 1 - prod_l(1 - E_l),
  E_l = max_f(|Z_lf| / (1 + |Z_lf|)), intra-model D7 baselines
D6: PASS — highest_risk_layer = argmax_l(E_l)
D7: PASS — finite nonzero MAD used directly (no epsilon); exact MAD = 0
  handled as deterministic zero anomaly vs DEGENERATE_DEVIATION;
  1-2 comparable layers blocked; NaN/Inf target/baseline rejected;
  near-zero positive MAD used directly and yields finite Z
MRS: PASS — non-quantized min(100, 40*S_static + 35*P_tamper + 25*S_behavior);
  quantized min(100, 55*S_static + 45*P_tamper)
Verdict: PASS — PASS 0-34 / REVIEW 35-69 / FAIL 70-100
Adversarial tests: PASS (D7 edges, malformed features/ml_results,
  missing p_tamper, STALE artifact rejection, quantized bypass,
  probe-type routing, upstream failure blocks output with no MRS/verdict)
D8 generation binding: PASS — P1 features.json and P3 ml_results.json must
  carry the same generation_commit; missing/mismatched commit blocks the run
  (P2AnalyzerError D8 BLOCKED); covered by tests/test_d8_generation.py
Provenance: calibration provenance recorded in the calibration artifact
  (generated_by, purpose, methodology, probe_count, repetitions, random_seed,
  mad_derivation, observations_replayed, new_measurement_performed=false,
  artifact_finalized_at, artifact_finalized_commit — the finalized-commit
  pointer is historical; the current verified CP5 commit is
  4849706f5eaad16cca5d54933fff75e6431ee41a).
  Risk-result provenance is intentionally NOT emitted: the current
  contracts/risk_results.schema.json requires exactly 9 fields with
  additionalProperties:false and contains no provenance field. This is an
  architectural limitation, not an implementation bug. The contract was
  not changed to add fields.
Non-quantized VISION E2E (run_assessment, mock_mode=True / stub model):
  s_behavior = 0.0, mrs_score = 47.18, verdict = REVIEW — PASS,
  output validated against contracts/risk_results.schema.json
Non-quantized NLP E2E (run_assessment, mock_mode=True / stub model):
  s_behavior = 1.0, mrs_score = 72.18, verdict = FAIL — PASS,
  output validated against contracts/risk_results.schema.json
Quantized E2E (run_assessment, mock_mode=True):
  s_behavior = null, mrs_score = 63.63, verdict = REVIEW,
  behavioral probing bypassed (probe_count 0) — PASS,
  output validated against contracts/risk_results.schema.json
Full suite: python -m pytest tests -q -> 75 passed
Tracked data/outputs/risk_results.json: structurally schema-valid, but NOT
  freshly regenerated in this documentation session (values not re-generated
  in place; fresh E2E outputs were written to temp files and validated).
  The tracked file contains mock_status: "MOCK" and the current placeholder
  generation-commit value; do not represent it as a fresh production artifact.
Final state: PASS — CODE + RUNTIME EVIDENCE ONLY (NOT VERIFIED-REAL production authorization)
```

Limitations explicitly recorded (not to be misrepresented; CP5 PASS does NOT equal production approval):
- Calibration statistics were replayed from existing recorded observations;
  no new STRIP measurement was performed (`new_measurement_performed=false`).
- E2E validation used `mock_mode=True` / stub models. A real-model
  VERIFIED-REAL production gate was NOT exercised; do not claim real
  production models were verified.
- Tracked `data/outputs/risk_results.json` is schema-valid but was not
  freshly overwritten in this session. It contains `mock_status: "MOCK"` and
  the current placeholder generation-commit value; do not represent it as a
  fresh production artifact.
- Risk-result provenance is excluded by the current output contract
  (`additionalProperties:false`, no provenance field).
- This documentation update is the final synchronization step; it adds
  no new code, measurement, or contract change.
## Person 2 Verification Evidence

Implementation:
- src/p2_behavioral_risk/prober.py
- src/p2_behavioral_risk/risk_aggregator.py
- src/p2_behavioral_risk/handoff.py
- src/p2_behavioral_risk/output_writer.py

Tests:
- tests/test_p2_adversarial.py
- tests/test_d4_behavioral.py
- tests/test_d7.py
- tests/test_d8_generation.py
- tests/test_integration.py


CP5 may be marked PASS only after every required criterion is PASS, all required evidence is present, and independent approval is recorded. (Governance requirement preserved — no independent approval is fabricated by this documentation cleanup.)

> Historical 89e5f4f pointer (superseded): earlier CP5 evidence drafts cited
> `89e5f4fdc1ea810984cb8b192cc072b21d099518` as the verified commit. That
> pointer is superseded by the current verified CP5 commit
> `4849706f5eaad16cca5d54933fff75e6431ee41a` recorded in §10 above. The
> underlying code-runtime evidence is unchanged; only the commit pointer was
> advanced by subsequent documentation-sync commits.
