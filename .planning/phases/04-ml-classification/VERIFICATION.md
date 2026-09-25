# Phase 4 — ML Classification Verification

## 1. Gate Semantics

PASS requires reproducible current evidence.

A checkbox, historical command output, stale artifact, or old commit reference does not by itself prove CP4.

Required unresolved dependency = **BLOCKED**.

**Current audit date:** 2026-09-25  
**Current integration baseline:** `recovery-mainline`

## 2. Current Verification Classification

The current recovery implementation contains substantial Phase-4 functionality, but the historical CP4 PASS block previously recorded in this file is no longer sufficient as a current certificate.

The historical evidence references older generation identities and predates later P1/P3 reconciliation.

Therefore the current state is:

```
Phase-4 implementation       = SUBSTANTIALLY IMPLEMENTED
Historical CP4 evidence       = PRESERVED / NON-CURRENT
Current CP4 certification     = NOT ESTABLISHED
Current gate                  = BLOCKED PENDING REVERIFICATION
```

## 3. Prerequisite

- [ ] Current CP3 PASS independently evidenced.
- [ ] Current P1 real feature extractor verified.
- [ ] Exact current feature semantics/order locked.
- [ ] Current P1 generation identity recorded.

## 4. Training Path

Required evidence:

- [ ] final training directly invokes current P1 extraction;
- [ ] no copied feature extraction implementation;
- [ ] clean and tampered training models use the same current P1 path;
- [ ] feature order matches inference;
- [ ] training provenance points to the current compatible P1 generation.

## 5. Mock / Placeholder Leakage

Mandatory current-API evidence:

- [ ] mock provenance supplied to final training → reject;
- [ ] placeholder feature source supplied → reject;
- [ ] stale feature artifact supplied → reject;
- [ ] no final model artifact is emitted on rejected training.

Historical tests may document prior behavior but must not be counted as current evidence until reconciled with the recovery API.

## 6. Classifier / SHAP

- [ ] current FP LightGBM artifact generated from current-compatible VERIFIED-REAL P1 data;
- [ ] current quantized LightGBM artifact generated from current-compatible VERIFIED-REAL P1 quantized data;
- [ ] D10 `P_tamper = max_l p_l` verified;
- [ ] TreeSHAP uses exact current feature names/order;
- [ ] TreeSHAP is separate from D6 highest-risk-layer selection;
- [ ] quantized TreeSHAP uses `ks_stat` only.

## 7. D8 / Staleness

Current generation consistency must be proven across:

```
P1 generation
   ↕
classifier provenance
   ↕
ml_results.json
   ↕
feature/schema contract
```

The 2026-09-25 read-only audit found committed FP/ML artifacts with older generation identities than the current recovery lineage. Those artifacts are therefore historical evidence, not automatic current CP4 evidence.

Required:

- [ ] regenerate/reverify only when explicitly authorized;
- [ ] current generation identity recorded;
- [ ] current `ml_results.json` verified against current P1;
- [ ] stale artifact rejection verified.

## 8. Adversarial Regression

Current API must cover:

- [ ] NaN/Inf features;
- [ ] missing feature;
- [ ] extra/unknown feature;
- [ ] wrong feature ordering;
- [ ] stale model;
- [ ] mock provenance;
- [ ] malformed `ml_results.json`;
- [ ] invalid classifier artifact;
- [ ] quantized/FP routing mismatch;
- [ ] invalid quantized `ks_stat`.

Tests targeting removed pre-recovery APIs must be classified as stale and reconciled before being used as CP4 proof.

## 9. Provenance

Required current evidence:

- [ ] training source;
- [ ] P1 producer/version;
- [ ] feature semantic version;
- [ ] contract version;
- [ ] dataset provenance;
- [ ] model artifact identity/hash;
- [ ] generation run;
- [ ] mock/real state.

## 10. D6 Dependency

The current D6 decision document locks authoritative identity to P1 `layer_name` and requires canonical lexical tie ordering.

The current P2 implementation/tests audited on 2026-09-25 still contain input-index tie behavior.

Therefore:

> **D6 implementation reconciliation is a current integration dependency.**

It must not be silently resolved by changing P1 or by importing unrelated P2 WIP.

## 11. End-to-End Evidence

Current `scan_model.py` orchestrates:

```
P1 intake
→ P1 features
→ P3 classifier
→ P2 trusted handoff / behavioral path
→ D5/D6/risk
→ contract validation
```

The orchestration is implemented and fail-closed at artifact-validation boundaries.

However, this read-only audit did not establish a fresh, current-generation end-to-end execution proving all three stages against the present recovery state.

Required:

- [ ] current FP end-to-end run;
- [ ] current quantized end-to-end run;
- [ ] generated artifacts share the expected current generation/provenance;
- [ ] current contracts validate;
- [ ] no stale artifact remains after a failed stage.

## 12. Historical Evidence

The historical Phase-4 evidence recorded:

- real P1 extraction;
- 96-row synthetic training corpus;
- LightGBM artifact;
- D10;
- TreeSHAP;
- regression tests.

That evidence remains useful provenance, but it is not silently promoted to current CP4 PASS.

## 13. Final Current State

**CP4: BLOCKED pending current-generation reverification and cross-owner reconciliation.**

This does **not** mean Phase 4 is missing.

It means the current repository has substantial implementation, while the evidence layer must be brought forward to the current recovery baseline.

Do not restart Phase 4. Reverify and reconcile.
