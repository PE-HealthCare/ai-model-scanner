# Phase 4 — ML Classification Verification

## 1. Gate Rules

PASS requires reproducible evidence.

Required unresolved decision/dependency = BLOCKED.

Code execution success alone does not prove CP4.

## 2. Prerequisite

- [ ] CP3 PASS.
- [ ] P1 real feature extractor is verified.
- [ ] Exact feature semantics/order are locked.

## 3. Training Path

- [ ] final training directly invokes P1 extraction;
- [ ] no copied feature extraction implementation exists;
- [ ] clean and tampered training models both use the same P1 extraction path;
- [ ] feature order matches inference.

## 4. Mock Leakage Tests

Mandatory:

- [ ] mock provenance supplied to final training;
- [ ] placeholder feature source supplied to final training;
- [ ] stale feature artifact supplied to final training.

Expected result:
```text
REJECT / BLOCK
NO FINAL MODEL ARTIFACT
```

## 5. Classifier / SHAP

- [ ] LightGBM artifact generated from verified-real features;
- [ ] P_tamper output is valid;
- [ ] TreeSHAP uses exact feature names;
- [ ] TreeSHAP ordering matches P1;
- [ ] TreeSHAP feature attribution is not incorrectly presented as highest-risk-layer calculation.

## 6. Staleness Tests

- [ ] change feature name;
- [ ] change feature meaning;
- [ ] change representation;
- [ ] change feature ordering.

Expected:
```text
classifier = STALE
CP4 = BLOCKED
retraining required
TreeSHAP remap/reverification required
```

## 7. Adversarial Regression

- [ ] NaN/Inf features;
- [ ] missing feature;
- [ ] extra feature;
- [ ] wrong feature ordering;
- [ ] stale model;
- [ ] mock feature provenance;
- [ ] malformed `ml_results.json`;
- [ ] invalid classifier artifact.

## 8. Provenance

- [ ] training source;
- [ ] P1 producer version;
- [ ] semantic version;
- [ ] contract version;
- [ ] dataset provenance;
- [ ] model artifact identity;
- [ ] generation run;
- [ ] mock/real state.

## 9. Scope

- [ ] only Phase-4 files changed;
- [ ] no P1/P2 implementation changes;
- [ ] no governance changes;
- [ ] shared utility changes authorized and reverification recorded.

## 10. CP4 Evidence

```text
Branch: phase-4/ml-classification
Commit:
Reviewer:
CP3:
Training command:
Training feature provenance:
Model artifact:
P_tamper:
TreeSHAP:
Staleness tests:
Adversarial tests:
Final state: PASS / FAIL / BLOCKED
```
