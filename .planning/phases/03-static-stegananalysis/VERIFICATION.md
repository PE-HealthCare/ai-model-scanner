# Phase 3 — Static Steganalysis Verification

## 1. Gate Semantics

Only PASS / FAIL / BLOCKED exist.

Required unresolved decision = BLOCKED.

Checkbox alone = NOT verification.

## 2. Prerequisite

- [x] CP2 PASS — Phase 2 intake and D2 handoff were independently reviewed and merged into `main`.
- [x] Real P1 intake is used — a real ResNet-18 SafeTensors artifact was accepted through the trusted intake path.
- [x] No unapproved contract change exists — the frozen 10-feature order was preserved.

## 3. Feature Coverage

- [x] all approved FP32/FP16 feature families implemented;
- [x] quantized models use whole-weight KS only;
- [x] mantissa/LSB-specific tests are skipped for quantized models;
- [x] intra-model baseline is used;
- [x] layer identity is preserved.

## 4. Semantic Tests

The implementation uses the following recorded semantics:

- [x] entropy — Shannon entropy over the byte-value distribution of each FP32/FP16 layer;
- [x] PoV chi-square — chi-square statistic for the two raw LSB states against a 50/50 expectation;
- [x] LSB KL — KL divergence of the two-state LSB distribution against `[0.5, 0.5]`;
- [x] KS — two-sample KS statistic comparing the current layer with the pooled other floating-point layers in the same model;
- [x] moments — population mean/std (`ddof=0`), biased skewness, and Pearson kurtosis (`fisher=False`);
- [x] sparsity — zero-valued element fraction;
- [x] outlier percentage — fraction outside Tukey 1.5×IQR fences, reported as a percentage;
- [x] estimator choice — explicit SciPy/NumPy estimators as documented above;
- [x] binning — byte histogram uses the 256 possible byte values; LSB features use two states;
- [x] normalization — no arbitrary epsilon or fallback normalization is introduced; values are computed directly from the specified distributions/statistics;
- [x] edge cases — empty tensors, non-finite values, and insufficient comparable layers fail closed; constant tensors are handled deterministically by the locked numerical path;
- [x] feature ordering — `entropy`, `pov_chi2`, `lsb_kl`, `ks_stat`, `mean`, `std`, `skewness`, `kurtosis`, `sparsity`, `outlier_pct`.

## 5. Mandatory Adversarial Regression

- [x] empty tensor;
- [x] one-element tensor;
- [x] constant tensor;
- [x] NaN/Inf input;
- [x] insufficient comparable layers;
- [x] zero MAD;
- [x] near-zero MAD;
- [x] quantized model incorrectly invoking mantissa/LSB tests;
- [x] malformed upstream intake output;
- [x] missing required contract field;
- [x] wrong feature ordering.

Evidence: full project test suite passed with **48 tests passed** after Phase 3 implementation and merge. The Phase 3 extractor test suite explicitly covers the listed extractor edge cases; intake and D2 tests cover malformed/failed upstream paths and trusted handoff behavior.

For D7:
```text
Decision status: RESOLVED / LOCKED
Condition detected: zero/near-zero MAD, insufficient comparable layers, and invalid numeric data
Approved handling: actual finite nonzero MAD; deterministic zero when MAD=0 and target=median; DEGENERATE_DEVIATION when MAD=0 and target!=median; block scoring for 1–2 comparable layers; reject invalid numeric data; no epsilon
Evidence: implemented/covered by the Phase 3 regression suite and locked decision record
```

No arbitrary epsilon or fallback is acceptable.

## 6. Provenance

- [x] `features.json` is recorded as `VERIFIED-REAL` only after real extraction.
- [x] source model/run is known — real ResNet-18 SafeTensors artifact used for the verification run.
- [x] producer commit is known — `d154eb98ec6b66611408dfa6692fdf3c7112c17`.
- [x] feature semantic version is known — `contract_version: 1.0` in the verified artifact.
- [x] contract version is known — `1.0`.
- [x] artifact generation evidence exists — 102 extracted layers and successful schema validation.

Verified artifact checks:

```text
mock_status: VERIFIED-REAL
producer: P1
input_domain: VISION
is_quantized: false
layer_count: 102
schema validation: PASS
feature order: exact frozen 10-feature order
```

## 7. Scope

- [x] only Phase-3 implementation/test scope was changed on the Phase 3 branch;
- [x] no P2/P3 ownership changes were introduced by the Phase 3 implementation;
- [x] no unauthorized governance change was introduced;
- [x] no unauthorized shared utility change was introduced.

## 8. CP3 Evidence

```text
Branch: phase-3/static-stegananalysis
Commit: 9fd3a51bba4cbe383ba0da47efa28fe5d69f674f (PR head before merge)
Merge commit: b19a26cef97c3980d80f3784679ec314e35a4492
Reviewer: tamannaragit — APPROVED; "checked & approved the changes."
Real input: real ResNet-18 SafeTensors artifact
Feature artifact: data/outputs/features.json — VERIFIED-REAL
Schema: PASS
Semantic evidence: recorded above and exercised by tests
Adversarial tests: full suite 48 passed
D7 status: RESOLVED / LOCKED; implementation evidence recorded above
Provenance: generation_commit d154eb98ec6b66611408dfa6692fdf3c7112c17; producer P1; contract 1.0; 102 layers
Final state: PASS — independently reviewed and merged
```

CP3 approval is evidenced by the independent GitHub review and merge. This document records that evidence; it does not resolve D4–D6 or D9's remaining artifact/verification requirements.
