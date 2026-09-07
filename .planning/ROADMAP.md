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

This is **D1 — DECISION REQUIRED**.

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
* bounded/mmap-safe weight access.

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
* no unrestricted pickle loading.

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

Verified upstream outputs, including P3's real `P_tamper`.

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
* risk contract satisfaction.

If D3, D4, D5, or D7 remains required for completion:

**CP5 = BLOCKED**

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

# Decision-Required Register

* **D1:** Exact contract schemas and fields/types/layout
* **D2:** Exact in-process trusted-graph handoff mechanism
* **D3:** STRIP entropy baseline definition
* **D4:** Exact `S_behavior` normalization
* **D5:** Per-layer → model-level risk aggregation
* **D6:** Highest-risk-layer aggregation
* **D7:** MAD zero/near-zero and low-layer-count guard
* **D8:** Model staleness protection
* **D9:** Dependency population and pinning

These decisions remain unresolved until explicitly resolved.

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
11. Unresolved items are `DECISION REQUIRED`.
12. Future agents must not silently invent unresolved behavior.
