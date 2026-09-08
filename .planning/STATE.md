# AI Model Scanner — Execution State

**Project Status:** FROZEN FOR EXECUTION
**Architecture Status:** FROZEN
**Current Phase:** Phase 2 — Zero-Trust Intake
**Current Checkpoint:** CP1 — COMPLETE
**Current Gate Status:** PASS — CP1 VERIFIED
**Last Verified Phase:** Phase 1 — Mock Pipeline
**Next Permitted Phase:** Phase 2 — Zero-Trust Intake

---

## Authority

The Final Master Discovery & Dependency Graph is the authoritative architecture source.

This state file records execution status and explicitly locked project decisions only.

It SHALL NOT redefine the architecture or silently resolve design decisions.

---

## Current Objective

Begin Phase 2 Zero-Trust Intake using the completed Phase 1 contracts and verified mock pipeline. D2–D6 remain intentionally unresolved and are not being changed in this transition.

---

## Resolved Master-Graph Decision Records

### D1 — Exact Contract Schemas

**Status: RESOLVED.**

The previous six-feature D1 resolution is superseded because it conflicts with the frozen Master Graph. D1 is now explicitly resolved against the frozen Master Graph; the Master Graph is the sole architectural authority for the static feature set and must be followed exactly for the final P1 feature contract.

The authoritative FP32/FP16 static feature set is **10 features**:

1. `entropy`
2. `pov_chi2`
3. `lsb_kl`
4. `ks_stat`
5. `mean`
6. `std`
7. `skewness`
8. `kurtosis`
9. `sparsity`
10. `outlier_pct`

The current six-feature executable schema was not the final D1 contract. D1 is resolved to the 10-feature Master Graph set, and the executable feature schema is reconciled to that decision. No alternate feature semantics are introduced.

The Master Graph remains the source of truth. Any implementation, downstream contract, feature ordering, feature semantics, or TreeSHAP mapping must follow the explicitly resolved Master Graph feature definitions; unresolved differences are a hard stop.

### D7 — MAD Degenerate Baseline Guard

**Status: RESOLVED.**

Robust intra-model normalization uses leave-one-out comparable layers.

* **Finite nonzero MAD:** Use actual MAD directly. Do not add epsilon or arbitrary near-zero threshold. If calculation is finite, it is valid.
* **Exact MAD = 0:** If target layer feature equals baseline median, record deterministic zero anomaly. If target differs, record deterministic `DEGENERATE_DEVIATION`. Do not invent a finite Z-score or add epsilon.
* **Insufficient baselines (1 or 2 layers):** Do not fabricate a score. Mark static baseline evidence unavailable and block downstream scoring that requires it.
* **Invalid numeric data (missing, NaN, +/-inf):** Invalid. Do not silently impute, replace with zero, or fabricate values.
* **Extremely small nonzero MAD:** Treat as mathematically valid using actual value. Do not replace with epsilon.
* **Quantized models:** Preserve existing format-adaptive rules. Do not invent new semantics. If conflict with schema exists, document it as unresolved follow-up.

Note: D5 (Per-layer risk aggregation) and D6 (Highest-risk-layer aggregation) remain `REQUIRED` and unresolved. TreeSHAP must not be used for highest-risk-layer selection.

### D8 — Artifact Staleness

**Status: RESOLVED.**

Downstream stages must consume outputs generated for the current pipeline execution and must not silently reuse artifacts from a previous execution. Artifact provenance/generation identity (`generation_commit`) is used to distinguish current pipeline outputs from stale outputs. If an artifact does not match the current pipeline execution, the consuming stage must reject/block it rather than reuse it.

---

## Locked Execution Decisions

These decisions were explicitly agreed during execution and are recorded here without changing the frozen architecture.

### Execution Decision 1 — Trusted Architecture Registry

**Status: LOCKED.**

The authoritative trusted architecture registry is exactly:

| Declared architecture | Domain | Trusted implementation |
| --- | --- | --- |
| `resnet18` | VISION | `torchvision.models` |
| `distilbert` | NLP | `transformers` |

Rules:

* The uploader declares one supported architecture.
* Unsupported, unknown, malformed, or incompatible architecture input fails closed.
* There is no automatic architecture detection.
* No uploader-supplied `model.py`, custom executable model code, or arbitrary model import is trusted.
* The registry is intentionally limited to the two explicitly approved architectures above unless separately reopened and extended by an explicit decision.

### Execution Decision 2 — Zero-Trust Intake Resource Limits

**Status: LOCKED.**

Hard fail-closed production intake limits are:

| Resource | Hard limit |
| --- | ---: |
| SafeTensors header | 100 MB |
| Metadata | 1 MB |
| Tensor count | 10,000 |
| Maximum tensor rank | 8 |
| Maximum dimension size | 1,000,000 per dimension |
| Model file size | 2 GB |

Operational targets (not hard walls) are:

* Intake memory target: `<50 MB`
* Intake processing-time target: `<0.5 sec`

If a hard limit is exceeded, intake fails closed and reports the exact exceeded limit.

No per-tensor quota heuristic is introduced. No configuration file is used for these limits. No limit-tuning CLI flag is introduced.

The 100 MB header value is now an explicit project decision; it is no longer treated as merely the illustrative `e.g.` value from the resolved pipeline description.

### Execution Decision 3 — D9.1 Python Baseline

**Status: LOCKED.**

Authoritative Python baseline: **Python 3.11.x**.

### Execution Decision 4 — D9.2 Hardware Policy

**Status: LOCKED.**

The authoritative execution environment is **CPU-only**.

* GPU/CUDA is not a required dependency.
* PASS/REVIEW/FAIL must be reproducible without GPU execution.
* GPU availability may exist on a machine but must not be required by the authoritative pipeline.

### Execution Decision 5 — D9.3 PyTorch Pair

**Status: LOCKED.**

* `torch==2.3.1`
* `torchvision==0.18.1`

This is the pinned PyTorch/torchvision pair for the project. CPU-only execution remains authoritative.

### Execution Decision 6 — D9.4 Transformers

**Status: LOCKED.**

* `transformers==4.41.2`

This is the pinned Transformers version for the trusted `distilbert` architecture.

### D9 — Dependency Pinning

**Overall Status: REQUIRED — PARTIALLY RESOLVED.**

D9 remains `REQUIRED` until the complete dependency policy is explicitly locked. The following D9 sub-decisions are currently locked:

| D9 sub-decision | Status | Locked value |
| --- | --- | --- |
| D9.1 Python | RESOLVED | Python 3.11.x |
| D9.2 Hardware | RESOLVED | CPU-only |
| D9.3 PyTorch | RESOLVED | `torch==2.3.1`, `torchvision==0.18.1` |
| D9.4 Transformers | RESOLVED | `transformers==4.41.2` |
| D9.5 SafeTensors | REQUIRED | Not yet decided |
| Remaining dependency pins | REQUIRED | Not yet decided |

No unapproved dependency version is implied by this partial D9 record.

---

## Phase Status

| Phase                         | Status               | Gate |
| ----------------------------- | -------------------- | ---- |
| Phase 1 — Mock Pipeline       | COMPLETE             | CP1  |
| Phase 2 — Zero-Trust Intake   | IN PROGRESS          | CP2  |
| Phase 3 — Static Steganalysis | NOT STARTED          | CP3  |
| Phase 4 — ML Classification   | NOT STARTED          | CP4  |
| Phase 5 — Behavioral + Risk   | NOT STARTED          | CP5  |
| Phase 6 — Integration + Demo  | NOT STARTED          | CP6  |

---

## Checkpoint Status

| Checkpoint                 | Status               |
| -------------------------- | -------------------- |
| CP1 — Mock Gate            | PASS                 |
| CP2 — Intake Gate          | NOT REACHED          |
| CP3 — Static Gate          | NOT REACHED           |
| CP4 — ML Gate              | NOT REACHED           |
| CP5 — Behavioral/Risk Gate | NOT REACHED           |
| CP6 — Demo Gate            | NOT REACHED           |

Only a `PASS` checkpoint permits advancement.

---

## Decision Status

| Decision                            | Status   |
| ----------------------------------- | -------- |
| D1 — Exact contracts                | RESOLVED |
| D2 — Trusted graph handoff          | REQUIRED |
| D3 — STRIP baseline                 | REQUIRED |
| D4 — Behavioral normalization       | REQUIRED |
| D5 — Risk aggregation               | REQUIRED |
| D6 — Highest-risk-layer aggregation | REQUIRED |
| D7 — MAD guard                      | RESOLVED |
| D8 — Model staleness protection     | RESOLVED |
| D9 — Dependency pinning             | REQUIRED |

A decision may move from `REQUIRED` to `RESOLVED` only through an explicit project/team decision.

An implementation choice does not automatically resolve a decision.

The execution decisions above are recorded separately so they do not collide with the Master Graph's D1–D9 numbering.

---

## Verified Artifacts

### Architecture

* Master Graph: **verified / frozen**
* Project definition: **planning document**
* Roadmap: **planning document**

### Implementation

* Real P1 feature extractor: **not verified**
* Real P3 classifier: **not verified**
* Real P2 risk engine: **not verified**
* Final integration: **not verified**

### Planned Output Artifacts

```text
data/outputs/features.json
data/outputs/ml_results.json
data/outputs/risk_results.json
artifacts/lightgbm_model.txt
```

These remain planned artifacts until actually produced and verified.

---

## Current Dependency Chain

```text
D1 RESOLVED
 ↓
CP1 PASS
 ↓
P1 Zero-Trust Intake
 ↓
CP2 PASS
 ↓
P1 Real Static Features
 ↓
CP3 PASS
 ↓
P3 Final ML Training
 ↓
CP4 PASS
 ↓
P2 Behavioral + Risk
 ↓
CP5 PASS
 ↓
Phase 6 Integration
 ↓
CP6 PASS
```

---

## Hard-Stop Conditions

The agent MUST stop dependent work when any of the following applies:

1. A required `DECISION REQUIRED` item is unresolved.
2. A required upstream checkpoint is not `PASS`.
3. A required contract is undefined.
4. Feature semantics required for downstream work are not verified.
5. A dependency is unavailable or unverified.
6. Verification criteria cannot legitimately be evaluated.
7. The implementation would require inventing a schema, formula, threshold, normalization, baseline, aggregation, fallback, dependency, or feature meaning.
8. A proposed change would redesign the frozen architecture without an explicit decision to reopen it.
9. Ownership of the requested change is unclear.
10. Mock/scaffold behavior would need to be represented as real implementation.

---

## Execution Rules

When not blocked, the agent SHALL:

1. inspect the current repository state;
2. identify the applicable phase;
3. read that phase's `PLAN.md`;
4. read that phase's `VERIFICATION.md`;
5. confirm all upstream gates;
6. implement only within the permitted scope;
7. preserve subsystem ownership;
8. run applicable verification;
9. record the resulting gate status;
10. update this state only with verified facts.

---

## State Update Rules

This file SHALL describe **actual verified state**, not intended state.

Do not mark:

* code as implemented when it is scaffolded;
* outputs as produced when they are mocks;
* a phase as complete before its verification gate passes;
* a decision as resolved because an agent selected an implementation;
* dependencies as verified merely because they appear in a file.

Explicitly agreed execution decisions may be recorded as `LOCKED` even while their corresponding implementation and verification remain incomplete. Such a decision does not by itself advance a checkpoint.

---

## Architecture Integrity

The following remain fixed unless explicitly reopened:

```text
P1 → P3 → P2 → P3
```

with:

```text
P1
  Zero-Trust Intake
       ↓
  Static Steganalysis
       ↓
  features.json
       ↓
P3
  LightGBM + TreeSHAP
       ↓
  ml_results.json
       ↓
P2
  STRIP + Risk Aggregation
       ↓
  risk_results.json
       ↓
P3
  Security Report / Dashboard
```

Quantized models bypass behavioral probing under the finalized format-adaptive design.

TreeSHAP attribution and highest-risk-layer determination remain separate mechanisms.

---

## Next Permitted Action

**Phase 1 is complete: CP1 PASS.**

The six-feature executable schema is no longer authoritative. D1 is resolved to the frozen Master Graph 10-feature set in the listed order. D7 and D8 are also resolved. The trusted architecture registry and zero-trust intake resource limits are explicitly locked execution decisions. D9 is partially resolved through D9.4; remaining dependency decisions are still required.

**Next permitted action: continue Phase 2 — Zero-Trust Intake preparation/implementation once all applicable prerequisites are satisfied.** D2–D6 remain REQUIRED and are intentionally not resolved. D9 remains REQUIRED until all dependency sub-decisions are locked.

No Phase 2 implementation is represented as complete by this state update.

---

## Final Rule

> **When the required information is unavailable, the correct action is BLOCKED — not invention.**
