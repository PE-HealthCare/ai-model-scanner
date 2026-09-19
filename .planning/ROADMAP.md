# AI Model Scanner — Execution Roadmap

**Status:** DISCOVERY → EXECUTION

The roadmap implements the frozen five-stage detection architecture through six implementation phases.

**Phase 6 is final integration and demonstration, not a sixth detection stage.**

No phase advances until its verification gate passes.

---

## Gate Outcomes

Every phase verification has exactly one of three outcomes:

### PASS

The applicable verification criteria are objectively satisfied, and no required unresolved decision or dependency prevents completion.

### BLOCKED

Verification cannot legitimately complete because a required dependency, contract, or `DECISION REQUIRED` item is unresolved or unavailable.

`BLOCKED` is **not** a pass and the phase cannot advance.

### FAIL

Verification was attempted, but one or more required criteria were not satisfied.

An unresolved decision must never be guessed or silently implemented merely to obtain `PASS`.

---

# Phase 1 — Mock Pipeline

**Owners:** P1 + P2 + P3 in parallel

### Purpose

Establish the initial contracts and validate the intended end-to-end flow using clearly identified mock artifacts.

### Deliverables

* exact contract field agreement;
* mock `features.json`;
* mock `ml_results.json`;
* mock `risk_results.json`;
* dependency plan;
* mock end-to-end `scan_model.py` execution.

### Dependency

Exact contract fields must be agreed.

This was **D1 — now RESOLVED / LOCKED**.

### Verification Gate

**CP1 — Phase 1 Mock Gate**

CP1 may be `PASS` only when:

* contract fields are agreed;
* mock artifacts conform to those agreed contracts;
* schema validation succeeds;
* mock runner execution succeeds;
* mocks are explicitly identified as mocks.

If D1 remains required for completion:

**CP1 = BLOCKED**

---

# Phase 2 — Zero-Trust Intake

**Owner:** P1

P3 may prepare ML/training scaffolding in parallel, but such preparation is provisional and cannot be treated as final training.

### Deliverables

* bounded SafeTensors header parsing;
* declared-architecture validation;
* trusted standard-library architecture instantiation;
* `input_domain` tagging;
* `is_quantized` tagging;
* bounded/mmap-safe weight access;
* trusted-model handoff consistent with locked D2.

### Dependency

`CP1 = PASS`

Required dependencies must also be available.

### Verification Gate

**CP2 — Intake Gate**

CP2 requires verification of:

* declared architecture handling;
* bounded SafeTensors handling;
* trusted graph instantiation;
* domain identification;
* quantization identification;
* no uploader-supplied code execution;
* no unrestricted pickle loading;
* D2 handoff behavior where exercised.

D2 is architecturally resolved, but its real implementation and verification are COMPLETE, independently approved, and integrated into main.

---

# Phase 3 — Static Steganalysis

**Owner:** P1

This phase is the critical handoff to P3.

### Deliverables

Real per-layer static feature extraction using the finalized format-adaptive design.

For FP32/FP16:

* entropy;
* PoV chi-square;
* LSB KL-divergence;
* KS statistic;
* moments;
* sparsity;
* outlier percentage.

For quantized formats:

* whole-weight KS only.

Also required:

* intra-model baseline evidence;
* preserved layer identity;
* `features.json` production.

### Dependency

`CP2 = PASS`

Exact feature semantics required for downstream training must be available.

### Verification Gate

**CP3 — Static Gate**

CP3 requires:

* real feature extraction;
* correct format-adaptive behavior;
* intra-model baseline;
* preserved layer identity;
* contract-compliant output;
* verified feature semantics.

If required feature semantics remain undecided:

**CP3 = BLOCKED**

### Critical Handoff

P1's verified real feature extractor becomes the source consumed by final P3 classifier training.

---

# Phase 4 — ML Classification

**Owner:** P3

### Deliverables

* synthetic tampering methodology;
* LightGBM classifier;
* `P_tamper`;
* TreeSHAP feature attribution;
* `ml_results.json`;
* `artifacts/lightgbm_model.txt`.

### Dependency

`CP3 = PASS`

Final training cannot proceed using Phase 2 scaffolding alone.

### Verification Gate

**CP4 — ML Gate**

CP4 requires:

* the same verified P1 feature semantics used for training and inference;
* LightGBM classifier produced;
* `P_tamper` produced;
* TreeSHAP feature names verified;
* ML contract satisfied.

If P1 feature semantics change after training:

1. retrain P3;
2. remap/reverify TreeSHAP;
3. rerun applicable verification.

---

# Phase 5 — Behavioral + Risk

**Owner:** P2

### Deliverables

* domain-aware STRIP probing;
* bounded inference;
* `H_STRIP`;
* `S_behavior`;
* quantized-model bypass;
* MAD-based risk aggregation;
* MRS;
* verdict;
* `risk_results.json`.

### Dependency

> Historical dependency statement (superseded for the CP5 code-runtime PASS
> scope; preserved for history): verified upstream outputs, including P3's
> real `P_tamper`, were specified as the dependency for an authoritative
> production risk artifact. The CP5 code-runtime PASS scope used mock/stub E2E
> runtime checks and claims no VERIFIED-REAL production gate (see VERIFICATION.md §10).

Verified upstream outputs, including P3's real `P_tamper` (historical authoritative-production dependency; see scope note above).

### Decision dependencies

> Historical planning state (superseded for CP5 code-runtime scope; preserved
> for history): before the CP5 evidence pass, D3 empirical calibration was
> recorded as pending and D4/D5/D6 were recorded as REQUIRED. Current status:
> for the CP5 code-runtime PASS scope, D3 is represented by the committed
> calibration artifact plus verified replay (`new_measurement_performed=false`,
> `python scripts/finalize_calibration_artifact.py --check` → exit code 0),
> and D4/D5/D6 are implemented (see
> `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10 and
> `.planning/STATE.md` `## Checkpoint Status`). This PASS is code-runtime
> evidence only and is NOT VERIFIED-REAL production authorization.

* **D3 (historical):** methodology RESOLVED / LOCKED; empirical calibration/evidence then pending. Baseline values were not to be invented and were to be populated from the approved calibration process before authoritative behavioral scoring was considered fully evidenced.
* **D4 (historical):** REQUIRED — exact `S_behavior` normalization then unresolved.
* **D5 (historical):** REQUIRED — exact per-layer → model-level risk aggregation then unresolved.
* **D6 (historical):** REQUIRED — exact highest-risk-layer aggregation then unresolved.
* **D7:** RESOLVED / LOCKED.

### Verification Gate

**CP5 — Behavioral/Risk Gate**

CP5 requires:

* correct domain probes;
* bounded inference;
* quantized bypass;
* applicable `S_behavior`;
* applicable MAD guard behavior;
* MRS computation;
* verdict computation;
* risk contract satisfaction;
* all evidence-dependent decisions completed and verified.

If D4, D5, or D6 remained required, or D3's required empirical calibration/evidence remained incomplete, CP5 was specified as `BLOCKED` in the historical plan. D3's locked methodology alone was not to constitute full D3 evidence. (Historical gate language; superseded for the CP5 code-runtime PASS scope defined in `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10 and `.planning/STATE.md` `## Checkpoint Status`. That PASS is code-runtime evidence only — repository implementation verification, replayed calibration statistics, calibration-artifact verification, automated tests [`75 passed`], and mock/stub E2E runtime checks — and is NOT VERIFIED-REAL production authorization.)

No silent substitute behavior is permitted.

---

# Phase 6 — Integration + Demo

**Owners:**

* P2 — risk aggregation/MRS/verdict;
* P3 — final security report/dashboard;
* `scan_model.py` — orchestration only.

### Deliverables

* one-command end-to-end scan;
* contract validation;
* fixed orchestration;
* final `risk_results.json`;
* final security report/dashboard;
* reproducibility;
* graceful failure behavior.

### Dependency

`CP1` through `CP5` must all be `PASS`.

### Ownership Rule

P2 owns:

* risk aggregation;
* MRS;
* verdict logic.

`scan_model.py` invokes the owner implementation.

It must **not** become a second implementation of P2 risk logic.

### Verification Gate

**CP6 — Demo Gate**

CP6 requires:

* complete end-to-end run;
* valid contracts;
* MRS;
* verdict;
* highest-risk layer;
* TreeSHAP evidence;
* behavioral evidence or explicit quantized bypass;
* assumptions;
* limitations;
* reproducible execution;
* graceful failure.

Any applicable unresolved decision remains a blocker.

---

# Critical Dependency Chain

```text
P3 Preparation
      ↓
P1 Phase 3 — Verified Real Feature Extractor
      ↓
P3 Phase 4 — Final Classifier Training
      ↓
P2 Phase 5 — Final Risk Aggregation
      ↓
Phase 6 — End-to-End Integration + Demo
```

---

# Phase Advancement Rule

Only `PASS` advances a phase.

The following are insufficient:

* partial implementation;
* scaffolding presented as implementation;
* mocks presented as real outputs;
* informal confidence without verification;
* unresolved required decisions;
* unverified dependencies;
* unfulfilled verification criteria;
* invented schemas;
* invented values;
* invented formulas;
* invented thresholds;
* invented dependencies;
* invented fallback behavior;
* invented feature semantics.

When blocked:

1. record the blocker;
2. identify the required decision/dependency;
3. stop dependent work;
4. do not silently choose a value.

For a staged decision, the agent MUST distinguish the locked methodology from pending implementation, calibration, or verification evidence and MUST return to that decision record when the pending evidence becomes available.

---

# Execution Sequence

```text
Phase 1
   ↓
CP1 PASS
   ↓
Phase 2
   ↓
CP2 PASS
   ↓
Phase 3
   ↓
CP3 PASS
   ↓
Phase 4
   ↓
CP4 PASS
   ↓
Phase 5
   ↓
CP5 PASS
   ↓
Phase 6
   ↓
CP6 PASS
```

---

# Decision Status Register

> Note: decision-state records below preserve historical planning language.
> For current CP5 code-runtime status, see
> `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10 and
> `.planning/STATE.md` `## Checkpoint Status` (CP5 PASS — CODE + RUNTIME
> EVIDENCE VERIFIED; NOT VERIFIED-REAL production authorization). D4/D5/D6
> entries marked REQUIRED below are historical planning states superseded for
> the CP5 code-runtime scope, where D4/D5/D6 are implemented.

* **D1:** RESOLVED / LOCKED — exact contract schemas and fields/types/layout.
* **D2:** RESOLVED / LOCKED — exact in-process trusted-graph handoff mechanism; implementation/verification COMPLETE — CP2 PASS.
* **D3:** RESOLVED / LOCKED — STRIP entropy baseline methodology; empirical calibration represented for the CP5 code-runtime scope by the committed calibration artifact plus verified replay (`new_measurement_performed=false`, check exit code 0); values MUST NOT have been invented (none were); VERIFIED-REAL production validation remains out of scope.
* **D4:** REQUIRED (historical planning state; superseded for CP5 code-runtime scope — D4 normalization/behavior score implemented and tested) — exact `S_behavior` normalization.
* **D5:** REQUIRED (historical planning state; superseded for CP5 code-runtime scope — D5 static risk aggregation implemented) — per-layer → model-level risk aggregation.
* **D6:** REQUIRED (historical planning state; superseded for CP5 code-runtime scope — D6 highest-risk-layer selection implemented) — highest-risk-layer aggregation.
* **D7:** RESOLVED / LOCKED — MAD zero/near-zero and low-layer-count guard.
* **D8:** RESOLVED / LOCKED — model staleness protection.
* **D9:** REQUIRED / PARTIALLY RESOLVED — D9.1–D9.20 locked; D9.21+ remains required.

These statuses preserve historical decision-state language, not implementation or checkpoint evidence (for current checkpoint evidence see `.planning/STATE.md` `## Checkpoint Status` and Phase 5 VERIFICATION.md §10).

---

# Non-Negotiable Architecture Rules

1. Do not redesign the finalized pipeline unless the team explicitly reopens a decision.
2. Distinguish repository facts from design/inference.
3. Empty schemas are empty.
4. Conceptual fields are not implemented fields.
5. Scaffolding is not implementation.
6. Mock artifacts are not real outputs.
7. `scan_model.py` is root orchestration, not a fourth owner.
8. Final P3 training depends on P1's verified real feature extractor.
9. TreeSHAP attribution and highest-risk-layer determination are separate mechanisms.
10. Quantized models skip behavioral probing under the finalized design.
11. Unresolved items remain `DECISION REQUIRED`.
12. A locked methodology with pending evidence MUST be represented as pending evidence, not as verified completion.
13. Future agents must not silently invent unresolved behavior or pending empirical values.
