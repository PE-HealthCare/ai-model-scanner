# Phase 6 — Risk Integration + Demo Verification

## 1. Gate Semantics

Exactly:

PASS / FAIL / BLOCKED

Required unresolved prerequisite, decision, dependency, or stale artifact = BLOCKED.

Checkbox alone is NOT verification.

## 2. Prerequisites

- [ ] CP4 APPROVED.
- [ ] CP5 APPROVED.
- [ ] current merged upstream artifacts exist.
- [ ] all required contracts are resolved.

## 3. Artifact Authority

Verify:

- [ ] `features.json` is VERIFIED-REAL;
- [ ] `ml_results.json` is VERIFIED-REAL;
- [ ] `risk_results.json` is VERIFIED-REAL;
- [ ] none are STALE;
- [ ] no MOCK/SCAFFOLD artifact enters final demo;
- [ ] artifacts belong to compatible producer/contract versions.

## 4. Provenance Chain

- [ ] source model/run identified;
- [ ] P1 producer identified;
- [ ] feature semantic/contract version identified;
- [ ] P3 model/version identified;
- [ ] ML artifact provenance identified;
- [ ] P2 producer/version identified;
- [ ] risk artifact provenance identified;
- [ ] report/run identified.

Mixed-generation artifact test MUST fail.

## 5. Architectural Ownership

- [ ] `scan_model.py` orchestrates only;
- [ ] no MRS formula duplicated in integration;
- [ ] no verdict formula duplicated in integration;
- [ ] no behavioral scoring duplicated in integration;
- [ ] no static analysis duplicated in integration;
- [ ] P2 `risk_results.json` is the MRS/verdict authority;
- [ ] TreeSHAP is not used as highest-risk-layer calculation.

## 6. End-to-End Tests

Mandatory:

- [ ] successful non-quantized path;
- [ ] successful quantized path;
- [ ] malformed model;
- [ ] P1 intake failure;
- [ ] P1 static failure;
- [ ] P3 classifier failure;
- [ ] P2 failure;
- [ ] missing artifact;
- [ ] stale artifact;
- [ ] mock artifact;
- [ ] malformed `ml_results.json`;
- [ ] malformed `risk_results.json`.

For any upstream failure, expected:

```text
STOP
NON-ZERO STATUS
NO MRS
NO VERDICT
NO FABRICATED REPORT
```

## 7. Report Verification

- [ ] MRS displayed from verified P2 output;
- [ ] verdict displayed from verified P2 output;
- [ ] highest-risk layer included;
- [ ] TreeSHAP feature evidence included;
- [ ] behavioral note included;
- [ ] assumptions/limitations included;
- [ ] PASS is not described as absolute security.

## 8. Scope

- [ ] only Phase-6 files changed;
- [ ] no P1/P2 algorithm changes;
- [ ] no classifier changes;
- [ ] no governance files changed;
- [ ] shared utility changes, if any, are authorized and reverified.

## 9. CP6 Evidence

```text
Branch: phase-6/risk-integration-demo
Commit:
Reviewer:
CP4:
CP5:
Artifact authority:
Provenance:
E2E non-quantized:
E2E quantized:
Failure tests:
Report:
Ownership:
Final state: PASS / FAIL / BLOCKED
```

CP6 may be APPROVED only after every required criterion is PASS and independent approval is recorded.