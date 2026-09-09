# Phase 5 — Behavioral Probing + Risk Verification

## 1. Gate Semantics

Exactly: PASS / FAIL / BLOCKED.

Required unresolved decision or required pending evidence = BLOCKED for the affected authoritative completion criterion. A checkbox without evidence is not verification. A methodology/boundary that is locked while implementation/calibration/verification evidence is pending SHALL NOT be treated as fully verified.

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

- [ ] locked D3 methodology matches the current project decision;
- [ ] required empirical calibration run completed;
- [ ] measured VISION/NLP baseline evidence recorded;
- [ ] evidence-dependent parameters, if any, explicitly recorded;
- [ ] no invented baseline values, thresholds, or fallback behavior exists.

D3 methodology being locked is not sufficient for full authoritative behavioral verification while required calibration evidence is pending.

### D4 — Behavioral normalization

- [ ] H_STRIP→S_behavior normalization explicitly resolved.
- [ ] no invented threshold, clipping, normalization, or fallback behavior exists.

Unresolved D4 or incomplete required D3 calibration/evidence = BLOCKED.

## 6. Risk Aggregation and Highest-Risk-Layer Boundary

- [ ] per-layer→model aggregation follows the approved D5 methodology boundary and the explicitly authorized exact operator;
- [ ] D5 preserves authoritative per-layer evidence and layer identity for D6;
- [ ] highest-risk-layer selection/reporting follows the approved D6 selection rule;
- [ ] D6 does not perform a second model-level aggregation;
- [ ] D6 does not manufacture layer-level P_tamper/S_behavior;
- [ ] TreeSHAP is not used for D6 layer selection;
- [ ] D7 MAD handling follows the approved locked decision;
- [ ] final non-quantized formula exact;
- [ ] final quantized formula exact;
- [ ] verdict ranges exact.

Unresolved D5 exact aggregation or D6 exact selection rule = BLOCKED for the affected authoritative risk/reporting completion.

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

## 10. CP5 Evidence

```text
Branch: phase-5/behavioral-probing
Commit:
Reviewer:
CP4:
Probe evidence:
Bound evidence:
D3 methodology:
D3 empirical calibration/evidence:
D4:
D5 methodology boundary / exact operator:
D6 boundary / exact selection rule:
D7:
MRS:
Verdict:
Adversarial tests:
Provenance:
Final state: PASS / FAIL / BLOCKED
```

CP5 may be marked PASS only after every required criterion is PASS, all required evidence is present, and independent approval is recorded.