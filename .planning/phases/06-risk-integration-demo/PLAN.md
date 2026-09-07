# Phase 6 — Risk Integration + Demo

## Status

**Owner:** Integration surface + P3 reporting  
**Checkpoint:** CP6  
**Prerequisites:** CP4 = APPROVED and CP5 = APPROVED  
**Branch:** `phase-6/risk-integration-demo`

Phase 6 integrates already-verified outputs into the final end-to-end runner and security report.

## 1. Architectural Boundary

Phase 6 MUST NOT independently implement or recalculate:

- static steganalysis;
- LightGBM;
- TreeSHAP;
- behavioral scoring;
- MAD aggregation;
- MRS;
- verdict.

Those responsibilities remain with P1/P2/P3 as defined by the Master Graph.

`scan_model.py` is orchestration only.

P2's verified `risk_results.json` is the authoritative source for MRS and verdict.

## 2. Agent Execution Control

Before starting final integration:

1. verify CP4 APPROVED;
2. verify CP5 APPROVED;
3. inspect the merged states;
4. verify all required upstream artifacts are VERIFIED-REAL and current;
5. create/use `phase-6/risk-integration-demo`;
6. modify only authorized files.

If either prerequisite is not approved, Phase 6 is BLOCKED.

## 3. Allowed Files

Allowed:

- `scan_model.py`
- `src/p3_ml_dashboard/dashboard.py` for final report integration
- Phase-6 tests under `tests/...`
- approved demo/report assets

Forbidden:

- P1 implementation;
- P2 risk algorithm implementation;
- classifier implementation;
- planning governance files;
- Master Graph.

Shared utility changes require explicit authorization and downstream reverification.

## 4. Artifact Lifecycle

Final integration consumes:

```text
features.json      = VERIFIED-REAL
ml_results.json    = VERIFIED-REAL
risk_results.json  = VERIFIED-REAL
```

Any artifact may be:

- MOCK;
- SCAFFOLD;
- VERIFIED-REAL;
- STALE.

MOCK/SCAFFOLD artifacts are permitted only in development tests and MUST NOT support a final authoritative demo.

An artifact becomes STALE when its producer, contract, feature semantics, upstream source, or other relevant dependency has changed such that prior verification no longer establishes correctness.

## 5. Provenance Chain

The final report must be traceable through:

```text
model
→ P1 intake/version
→ features version
→ P3 classifier/version
→ ml_results version
→ P2 risk engine/version
→ risk_results version
→ report/run
```

Where practical, record hashes or immutable identifiers.

Mixed-generation artifacts are forbidden.

## 6. Upstream Change Rule

If an upstream contract or semantic implementation changes after verification:

```text
affected artifact = STALE
→ affected checkpoint loses validity
→ required phase re-verification/rebuild
→ CP6 BLOCKED
```

Do not patch around a stale artifact.

## 7. Failure Policy

The safe default is fixed:

```text
ANY UPSTREAM FAILURE
→ STOP
→ non-zero failure status
→ NO MRS
→ NO VERDICT
→ NO FABRICATED REPORT
```

Do not invent "graceful" fallback behavior.

## 8. Final Report

The report must present verified:

- MRS;
- verdict;
- highest-risk layer;
- TreeSHAP feature evidence;
- behavioral note;
- assumptions/limitations.

TreeSHAP attribution must not be presented as the method that calculated highest-risk layer.

PASS is not a guarantee of absolute security.

## 9. End-to-End Execution

The final runner must execute the approved architecture:

```text
P1 intake
→ P1 static
→ P3 classifier
→ P2 behavioral/risk
→ P3 report
```

No duplicated risk formula may exist in `scan_model.py`.

## 10. Commit / PR / Merge

Branch: `phase-6/risk-integration-demo`.

Commit only Phase-6 scope.

PR only after full verification evidence.

The agent MUST NOT self-merge.

Merge requires CP6 PASS, evidence, and independent/human review.

## 11. Exact CP6 Gate

CP6 PASS requires:

- CP4 approved;
- CP5 approved;
- all final artifacts VERIFIED-REAL and current;
- E2E runner works;
- P2 risk result is consumed rather than recalculated;
- report contains required evidence;
- provenance chain is complete;
- adversarial failure tests pass;
- no unresolved required decision;
- evidence recorded.

Required unresolved decision or stale artifact = BLOCKED.

CP6 APPROVAL is the final execution gate.
