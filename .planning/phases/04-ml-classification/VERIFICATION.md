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
Branch: recovery-mainline
Commit: e5d1ab5
Reviewer: Human verification in hackathon working session
CP3: PASS - verified-real P1 feature extraction; current generation commit 594c9a91df08a211ee1270de566c70d61205af26
Training command: python -c "import train_lightgbm_classifier as t; r=t.train(); print("TRAINING_COMPLETE"); print("ARTIFACT",r["artifact"]); print("ROWS",r["training_rows"]); print("CLEAN",r["clean_rows"]); print("TAMPERED",r["tampered_rows"]); print("MOCK_STATUS",r["mock_status"])"
Training feature provenance: VERIFIED-REAL P1 extraction; 96 rows total (48 clean, 48 tampered)
Model artifact: artifacts/lightgbm_model.txt; provenance: artifacts/lightgbm_model.provenance.json
P_tamper: 0.9900758624030114; valid [0,1]
TreeSHAP: 10 canonical feature attributions; 27/27 classifier regression tests passed
Staleness evidence: current ml_results.json generation_commit matches verified P1 generation; stale-artifact handling covered by classifier regression tests
Adversarial tests: 27/27 tests passed, including malformed payload, extra/unknown fields, invalid classifier, placeholder-source rejection, and prediction/SHAP validation
Final state: PASS
```
