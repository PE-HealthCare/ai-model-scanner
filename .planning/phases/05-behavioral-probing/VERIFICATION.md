# Phase 5 — Behavioral Probing + Risk Verification

## 1. Gate Semantics

Exactly:

PASS / FAIL / BLOCKED

Required unresolved decision = BLOCKED.

A checkbox without evidence is not verification.

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

- [ ] STRIP baseline explicitly resolved.
- [x] H_STRIP→S_behavior normalization explicitly resolved.
  Resolved by the explicit project decision recorded in `.planning/STATE.md`
  ("D4 — Behavioral Normalization — RESOLVED"). Locked formula:

  ```text
  deviation = H_median - H_STRIP
  Z = deviation / (1.4826 * H_MAD)
  Z_clamped = max(0.0, Z)
  S_behavior = min(1.0, Z_clamped / 3.0)
  ```

  Implemented in `src/p2_behavioral_risk/prober.py::normalize_h_strip`.
  Evidence: `tests/test_d4_behavioral.py` (formula, bounding, zero-MAD both
  branches, non-finite/missing/invalid MAD rejection) and
  `tests/test_p2_calibration_artifact.py` (calibration artifact replay,
  including `test_non_quantized_s_behavior_matches_locked_d4_formula`).
- [ ] no invented baseline/threshold/fallback exists.

Unresolved D3 or D4 = BLOCKED.

## 6. Risk Aggregation

- [ ] per-layer→model aggregation follows approved D5;
- [ ] D7 MAD handling follows approved decision;
- [ ] final non-quantized formula exact;
- [ ] final quantized formula exact;
- [ ] verdict ranges exact.

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

- [ ] only Phase-5 files changed;
- [ ] no P1/P3 implementation changes;
- [ ] no unauthorized integration changes;
- [ ] no governance changes.

## 10. CP5 Evidence

```text
Branch: phase-5/behavioral-probing
Commit:
Reviewer:
CP4:
Probe evidence:
Bound evidence:
D3:
D4: Resolved — explicit project decision recorded in `.planning/STATE.md`
    ("D4 — Behavioral Normalization — RESOLVED"). Locked formula:
    deviation = H_median - H_STRIP; Z = deviation / (1.4826 * H_MAD);
    Z_clamped = max(0.0, Z); S_behavior = min(1.0, Z_clamped / 3.0).
    Implementation: src/p2_behavioral_risk/prober.py::normalize_h_strip
    (fail-closed zero-MAD handling; invalid/non-finite inputs rejected).
    Evidence: tests/test_d4_behavioral.py;
    tests/test_p2_calibration_artifact.py (artifact replay incl.
    test_non_quantized_s_behavior_matches_locked_d4_formula);
    calibration artifact data/calibration/calibration_data.json.
    Independent review: PENDING.
D5:
D7:
MRS:
Verdict:
Adversarial tests:
Provenance:
Final state: PASS / FAIL / BLOCKED
```

CP5 may be marked PASS only after every required criterion is PASS and independent approval is recorded.
