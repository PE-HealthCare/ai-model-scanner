# Phase 1 — Mock Pipeline

## Status

**Execution state:** BLOCKED until the required contract decision is resolved.

**Checkpoint:** CP1

**Purpose:** Build the end-to-end pipeline shape using explicit mock artifacts so that integration contracts can be validated before real model analysis begins.

This phase is a **mock/scaffold phase**. It must not be represented as real detection capability.

---

## 1. Source of Truth

The following are authoritative:

1. `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`
2. `PROJECT.md`
3. `ROADMAP.md`
4. `REQUIREMENTS.md`
5. `STATE.md`

Agents MUST NOT redesign the finalized architecture.

Agents MUST NOT modify the Master Graph or other planning governance files unless explicitly authorized.

If this plan conflicts with the Master Graph, the Master Graph wins.

---

## 2. Final Pipeline Being Prepared

The implementation flow is:

```text
Untrusted .safetensors
        ↓
P1 Zero-Trust Intake
        ↓
P1 Static Steganalysis
        ↓
features.json
        ↓
P3 LightGBM + TreeSHAP
        ↓
ml_results.json
        ↓
P2 STRIP + Risk Aggregation
        ↓
risk_results.json
        ↓
P3 Security Report
```

`scan_model.py` is orchestration only.

It is NOT an additional implementation owner.

---

## 3. Phase Objective

Phase 1 establishes:

* exact cross-phase artifact locations;
* agreed contract fields;
* mock `features.json`;
* mock `ml_results.json`;
* mock `risk_results.json`;
* basic orchestration wiring;
* producer/consumer ownership;
* explicit mock artifact provenance;
* verification that later phases can consume the contracts without inventing fields.

Phase 1 does **not** establish:

* real SafeTensors security;
* real static steganalysis;
* real LightGBM performance;
* real STRIP behavior;
* real MRS validity;
* production security guarantees.

---

## 4. Blocking Rule

### Required decision: D1 — Exact Contract Schemas

D1 covers the exact fields and semantics of:

* `features.schema.json`;
* `ml_results.schema.json`;
* `risk_results.schema.json`.

If D1 is unresolved, Phase 1 is **BLOCKED**.

An unresolved decision can NEVER be interpreted as approval.

The agent MUST NOT:

* invent fields;
* invent field names;
* invent types;
* invent feature ordering;
* invent normalization;
* invent thresholds;
* invent formulas;
* invent fallback behavior;
* silently choose a schema.

The correct action is:

```text
BLOCKED → report missing decision → stop affected implementation
```

---

## 5. Parallel Work

After D1 is explicitly resolved, the three implementation owners may work in parallel:

| Owner       | Responsibility                         |
| ----------- | -------------------------------------- |
| P1          | Mock feature producer                  |
| P3          | Mock ML consumer/producer              |
| P2          | Mock behavioral/risk consumer/producer |
| Integration | `scan_model.py` orchestration only     |

All mock artifacts MUST conform to the approved contracts.

---

## 6. Mock Artifact Rules

Mock artifacts MUST be visibly distinguishable from real artifacts.

Every mock artifact must have provenance recorded in verification evidence stating:

* artifact path;
* producer;
* source/input;
* mock status;
* contract/schema version;
* generation run or commit;
* verification result.

A mock artifact MUST NOT be presented as evidence of real detection.

Mock data MUST NOT silently become the training or production source for later phases.

---

## 7. Mock → Real Transition

The transition is explicit.

### Mock state

```text
MOCK
```

means the artifact was generated from synthetic or placeholder data.

### Real state

```text
VERIFIED-REAL
```

means the artifact was produced by the actual upstream implementation and independently verified against the approved contract and semantics.

### Stale state

```text
STALE
```

means the artifact was produced using an upstream implementation or contract whose relevant semantics have subsequently changed.

### Required transition

```text
MOCK
  ↓
real producer implemented
  ↓
real producer verified
  ↓
real artifact generated
  ↓
contract + semantics verified
  ↓
VERIFIED-REAL
```

No agent may simply relabel a mock artifact as real.

---

## 8. Required File Scope

### Allowed

Phase 1 may modify only:

```text
src/p1_static_engine/analyzer.py
src/p2_behavioral_risk/prober.py
src/p3_ml_dashboard/classifier.py
src/p3_ml_dashboard/dashboard.py
scan_model.py
contracts/features.schema.json
contracts/ml_results.schema.json
contracts/risk_results.schema.json
tests/...
data/outputs/...
```

Only files actually required by Phase 1 may be changed. Contract schemas under `contracts/` are read-only to autonomous Phase-1 implementation; approved schema changes require the contract governance process.

### Forbidden

The agent MUST NOT modify contract schemas or governance/planning files during ordinary Phase-1 implementation.

```text
.planning/...
AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md
PROJECT.md
ROADMAP.md
REQUIREMENTS.md
STATE.md
```

unless explicit authorization is given.

The agent MUST NOT modify another phase's implementation merely to make Phase 1 pass.

`src/common/utils.py` is not a general-purpose escape hatch. Changes there require explicit justification and downstream impact analysis.

---

## 9. Ownership Rules

### P1 owns

```text
src/p1_static_engine/analyzer.py
```

P1 owns:

* safe intake;
* trusted architecture graph;
* SafeTensors handling;
* domain/quantization detection;
* static steganalysis;
* feature extraction.

### P3 owns

```text
src/p3_ml_dashboard/classifier.py
src/p3_ml_dashboard/dashboard.py
```

P3 owns:

* LightGBM;
* synthetic training;
* TreeSHAP;
* `P_tamper`;
* reporting/dashboard functionality assigned to P3.

### P2 owns

```text
src/p2_behavioral_risk/prober.py
```

P2 owns:

* STRIP probing;
* behavioral scoring;
* MAD risk aggregation;
* MRS;
* verdict.

### Integration owns

```text
scan_model.py
```

Integration may:

* call verified stage implementations;
* pass approved artifacts;
* enforce execution order;
* stop on failure;
* coordinate outputs.

Integration MUST NOT duplicate:

* static analysis;
* classifier logic;
* behavioral scoring;
* MRS formulas;
* verdict calculation.

---

## 10. Branch

Phase 1 branch:

```text
phase/01-mock-pipeline
```

All Phase 1 implementation changes MUST be made on this branch.

---

## 11. Dependency Rule

Agents MUST NOT autonomously select production dependency versions when dependency pinning is unresolved.

If a dependency/version is required and no approved version exists:

```text
BLOCKED
```

Do not guess.

Temporary local execution using an already approved environment does not constitute dependency pinning.

Final reproducibility requires the dependency decision defined by D9.

---

## 12. Security and Network Rules

The agent MUST:

* treat model files as untrusted;
* avoid executing uploaded model code;
* avoid unrestricted pickle loading;
* avoid uploader-controlled imports;
* avoid arbitrary network access;
* never upload model data, credentials, secrets, or repository contents to external services;
* never use secrets as model inputs;
* fail closed when a security boundary cannot be established.

Network access is allowed only when explicitly authorized for a project operation.

---

## 13. Failure Behavior

Any implementation failure MUST be explicit.

The agent MUST NOT:

* fabricate an output;
* silently substitute a fallback;
* silently skip a failed stage;
* mark a failed artifact as verified;
* continue to the next dependent stage.

Required behavior:

```text
failure
  ↓
record evidence
  ↓
mark affected work BLOCKED/FAIL
  ↓
stop dependent work
```

---

## 14. Completion Conditions

Phase 1 is complete only when:

* D1 is resolved;
* approved schemas exist;
* mock producer/consumer contracts match exactly;
* mock artifacts are generated;
* mock provenance is recorded;
* orchestration follows the approved graph;
* ownership boundaries are preserved;
* adversarial contract tests pass;
* verification evidence is complete;
* CP1 is explicitly approved.

Code compiling is NOT sufficient.

Tests passing are NOT automatically sufficient.

A phase is complete only when its checkpoint is approved.

---

## 15. Commit Rules

The agent may commit only Phase 1 changes.

Commit messages must clearly identify Phase 1 work.

The agent MUST NOT:

* commit unrelated fixes;
* include generated secrets;
* include unrelated formatting changes;
* commit stale artifacts as authoritative real outputs.

Before commit, the agent must verify:

```text
git status
git diff
tests
artifact provenance
scope
```

---

## 16. PR and Merge Rules

The agent may open a PR.

The agent MUST NOT merge its own PR.

Merge requires:

1. Phase 1 implementation complete;
2. Phase 1 verification PASS;
3. CP1 approval;
4. required human/independent review;
5. no unresolved blocking decision;
6. no failing required checks.

If any condition is missing:

```text
DO NOT MERGE
```

---

## 17. Downstream Gate

Phase 2 may begin only after:

```text
CP1 = PASS
```

Phase 2 MUST NOT treat:

* an unapproved mock;
* a failed verification;
* an unresolved D1;
* an unreviewed commit

as permission to proceed.

---

## 18. Hard Stop

STOP immediately if:

* D1 is unresolved;
* a required schema field is ambiguous;
* ownership is ambiguous;
* an implementation requires inventing semantics;
* an upstream contract changes unexpectedly;
* mock and real artifact provenance cannot be distinguished;
* a required security boundary cannot be established;
* a required dependency version is unknown;
* a verification requirement cannot be evidenced.

Do not work around the blocker silently.

Report the blocker and wait for resolution.
