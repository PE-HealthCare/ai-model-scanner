# Phase 3 — Static Steganalysis Verification

## 1. Gate Semantics

Only PASS / FAIL / BLOCKED exist.

Required unresolved decision = BLOCKED.

Checkbox alone = NOT verification.

## 2. Prerequisite

- [ ] CP2 PASS.
- [ ] Real P1 intake is used.
- [ ] No unapproved contract change exists.

## 3. Feature Coverage

- [ ] all approved FP32/FP16 feature families implemented;
- [ ] quantized models use whole-weight KS only;
- [ ] mantissa/LSB-specific tests are skipped for quantized models;
- [ ] intra-model baseline is used;
- [ ] layer identity is preserved.

## 4. Semantic Tests

Evidence must identify definitions for:

- [ ] entropy;
- [ ] PoV chi-square;
- [ ] LSB KL;
- [ ] KS;
- [ ] moments;
- [ ] sparsity;
- [ ] outlier percentage;
- [ ] estimator choice;
- [ ] binning;
- [ ] normalization;
- [ ] edge cases;
- [ ] feature ordering.

If a material semantic choice is unresolved, mark BLOCKED.

## 5. Mandatory Adversarial Regression

- [ ] empty tensor;
- [ ] one-element tensor;
- [ ] constant tensor;
- [ ] NaN/Inf input;
- [ ] insufficient comparable layers;
- [ ] zero MAD;
- [ ] near-zero MAD;
- [ ] quantized model incorrectly invoking mantissa/LSB tests;
- [ ] malformed upstream intake output;
- [ ] missing required contract field;
- [ ] wrong feature ordering.

For D7:
```text
Condition detected:
Approved handling:
Evidence:
```
No arbitrary epsilon is acceptable without approval.

## 6. Provenance

- [ ] `features.json` is marked/recorded as VERIFIED-REAL only after real extraction.
- [ ] source model/run is known.
- [ ] producer commit is known.
- [ ] feature semantic version is known.
- [ ] contract version is known.
- [ ] artifact generation evidence exists.

## 7. Scope

- [ ] only Phase-3 scope changed;
- [ ] no P2/P3 ownership changes;
- [ ] no governance files changed;
- [ ] no unauthorized shared utility change.

## 8. CP3 Evidence

```text
Branch: phase-3/static-stegananalysis
Commit:
Reviewer:
Real input:
Feature artifact:
Schema:
Semantic evidence:
Adversarial tests:
D7 status:
Provenance:
Final state: PASS / FAIL / BLOCKED
```

CP3 APPROVAL is required before P3 final classifier training.
