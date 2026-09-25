# Phase 5 — Behavioral Probing + Risk Verification

## 1. Gate Semantics

Exactly:

```
PASS / FAIL / BLOCKED
```

A checkbox without current evidence is not verification.

**Current audit date:** 2026-09-25  
**Current integration baseline:** `recovery-mainline`

## 2. Current State

The current recovery branch contains substantial Phase-5 production implementation, including behavioral probing, quantized bypass, D4 normalization, D5/D7 aggregation, MRS, generation checks, and risk-contract validation.

The historical verification checklist was not synchronized with that implementation.

Therefore:

```
Phase-5 implementation = SUBSTANTIALLY IMPLEMENTED
Historical verification = NON-CURRENT
Current CP5 certification = NOT ESTABLISHED
Current gate = BLOCKED
```

## 3. Prerequisites

- [ ] current CP4 PASS;
- [ ] current P1 real inputs verified;
- [ ] current P3 `ml_results.json` verified-real;
- [ ] current generation identities match;
- [ ] required contracts resolved.

## 4. Probe Routing

- [ ] quantized models bypass behavioral probing;
- [ ] non-quantized VISION uses the bounded float/image-noise path;
- [ ] non-quantized NLP uses the bounded integer token-ID path;
- [ ] invalid domain/input combinations are rejected;
- [ ] current production probe bound is explicitly evidenced/approved.

## 5. D3 / D4

### D3

- [ ] scanner-controlled STRIP calibration artifact is current;
- [ ] D3 baseline decision is explicitly recorded;
- [ ] baseline provenance and replay evidence are current.

The implementation currently consumes calibration data, but the audit did not establish a synchronized standalone D3 decision record. Do not mark D3 PASS from implementation presence alone.

### D4

- [x] locked normalization formula implemented;
- [x] zero-MAD equal branch returns 0;
- [x] zero-MAD unequal branch fails closed;
- [x] non-finite/missing invalid calibration inputs are rejected;
- [x] current D4 tests cover the formula.

Locked formula:

```
deviation = H_median - H_STRIP
Z = deviation / (1.4826 * H_MAD)
Z_clamped = max(0.0, Z)
S_behavior = min(1.0, Z_clamped / 3.0)
```

## 6. D5 / D7

Current implementation evidence:

- [x] D5 per-layer evidence reduction implemented;
- [x] model-level static aggregation implemented;
- [x] finite/missing evidence is not zero-imputed;
- [x] D7 MAD/degeneracy handling implemented;
- [x] non-quantized MRS formula implemented;
- [x] quantized MRS formula implemented;
- [x] verdict ranges implemented.

Still required for CP5:

- [ ] current decision/evidence records synchronized with implementation;
- [ ] current-generation adversarial tests verified;
- [ ] current end-to-end risk artifact verified.

## 7. D6 Integration Dependency

The locked D6 decision requires:

```
authoritative identity = P1 layer_name
exact tie = lexical layer_name
```

Current audited P2 implementation/tests still contain input-index tie behavior.

Therefore:

**D6 = implementation reconciliation required.**

This is not a P1 rework request. P1 identity is already defined by the current contract. P2/D6 must reconcile its implementation/tests with that identity contract.

## 8. Mandatory Adversarial Evidence

Current API evidence is required for:

- [ ] one-layer model;
- [ ] insufficient layers;
- [ ] zero MAD;
- [ ] near-zero MAD;
- [ ] NaN/Inf evidence;
- [ ] malformed `ml_results.json`;
- [ ] missing `P_tamper`;
- [ ] stale P3 artifact;
- [ ] quantized model accidentally entering behavioral path;
- [ ] probe input type mismatch;
- [ ] upstream failure.

Expected upstream-failure behavior:

```
STOP
NON-ZERO STATUS
NO MRS
NO VERDICT
NO FABRICATED OUTPUT
```

## 9. Provenance

Current evidence must show:

- [ ] features source;
- [ ] ML source;
- [ ] source versions/commits;
- [ ] P2 producer/version;
- [ ] contract/semantic version;
- [ ] run ID;
- [ ] mock/real status;
- [ ] current generation identity;
- [ ] artifact identity/hash where applicable.

## 10. End-to-End Verification

Current `scan_model.py` provides the intended orchestration:

```
P1 → P3 → P2 → risk_results
```

with contract validation and fail-closed cleanup.

Current audit did **not** execute a new end-to-end run, so no current-generation PASS is claimed.

Required:

- [ ] fresh FP end-to-end evidence;
- [ ] fresh quantized end-to-end evidence;
- [ ] features/ml/risk generation identities reconciled;
- [ ] current contracts validate;
- [ ] no stale output survives a failed stage.

## 11. Stale Test Classification

Some repository tests still target pre-recovery APIs (for example old P1 intake helpers or old P2 risk functions).

Those tests must be classified/reconciled before being counted as current CP5 evidence.

Do not silently import unrelated WIP to make stale tests pass.

## 12. Controlled Publication

Phase-5 changes must follow the project-wide controlled Git integration protocol:

1. verify actual `origin/recovery-mainline` SHA;
2. audit current remote read-only;
3. isolate the exact P2 payload;
4. use a disposable integration worktree;
5. check Git and logical/contract/provenance/ownership conflicts;
6. run relevant tests;
7. obtain explicit owner authorization;
8. publish only the authorized payload;
9. independently verify the actual remote SHA;
10. require the next owner to refresh from the new baseline.

## 13. Final Current State

**CP5: BLOCKED pending current-generation evidence, D3 decision synchronization, D6 reconciliation, and current end-to-end verification.**

This does not mean Phase 5 implementation is absent.

It means the verification record must be brought forward to the current recovery implementation.
