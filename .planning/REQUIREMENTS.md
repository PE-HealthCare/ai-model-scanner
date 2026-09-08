# AI Model Scanner — Requirements

**Status:** FROZEN FOR EXECUTION

This document defines implementation requirements derived from the finalized project architecture and Master Graph.

Unresolved decisions listed in this document are **not implementation requirements yet**. They are explicit blockers that require a decision before dependent implementation can be finalized.

---

## 1. Core Functional Requirements

### REQ-001 — Untrusted Model Scanning

The scanner SHALL treat supplied model weight files as untrusted input.

### REQ-002 — Defensive Scope

The scanner SHALL perform detection and explainability only.

It SHALL NOT attempt to patch, neutralize, or remediate detected threats.

### REQ-003 — End-to-End Pipeline

The implemented system SHALL support the finalized detection flow:

```text
Untrusted SafeTensors
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
P2 Behavioral Probing + Risk Aggregation
        ↓
risk_results.json
        ↓
P3 Security Report
```

### REQ-004 — Fixed Orchestration

The root integration flow SHALL follow:

```text
P1 → P3 → P2 → P3
```

`scan_model.py` SHALL orchestrate the pipeline and SHALL NOT duplicate subsystem ownership.

---

## 2. Security Requirements

### REQ-010 — No Uploaded Code Execution

The scanner SHALL NOT execute uploader-supplied Python code.

In particular, uploader-supplied `model.py` SHALL NOT be executed.

### REQ-011 — No Unrestricted Pickle

The scanner SHALL NOT use unrestricted pickle loading for untrusted model content.

### REQ-012 — Trusted Architecture Definitions

Architecture instantiation SHALL use trusted, standard-library definitions.

### REQ-013 — Bounded SafeTensors Handling

SafeTensors header parsing SHALL be bounded.

### REQ-014 — No Arbitrary Architecture Execution

The scanner SHALL NOT execute or dynamically trust an arbitrary architecture supplied by the uploader.

---

## 3. P1 Static Analysis Requirements

### REQ-020 — Architecture and Domain Detection

P1 SHALL establish the recognized declared architecture and the applicable `input_domain`.

Supported domain values are:

* `VISION`
* `NLP`

### REQ-021 — Quantization Detection

P1 SHALL establish whether the model is quantized.

The normalized representation SHALL distinguish:

* `is_quantized = true`
* `is_quantized = false`

### REQ-022 — Format-Adaptive Analysis

For FP32/FP16 models, P1 SHALL support the finalized static feature family:

* entropy
* PoV chi-square
* LSB KL-divergence
* KS statistic
* statistical moments
* sparsity
* outlier percentage

For quantized formats, the finalized static design SHALL use whole-weight KS only.

### REQ-023 — Intra-Model Baseline

Static anomaly analysis SHALL use the finalized intra-model baseline.

An external clean reference model SHALL NOT be required for runtime scanning.

### REQ-024 — Layer Identity

Feature output SHALL preserve sufficient layer identity for downstream attribution and risk reporting.

### REQ-025 — Real Feature Extractor

Final P3 classifier training SHALL consume output from P1's verified real feature extractor.

Mock or synthetic extractor output SHALL NOT be represented as verified real P1 semantics.

---

## 4. P3 Machine-Learning Requirements

### REQ-030 — LightGBM

The final anomaly classifier SHALL use LightGBM as specified by the finalized architecture.

### REQ-031 — Tampering Probability

The classifier SHALL produce `P_tamper`.

### REQ-032 — TreeSHAP

TreeSHAP SHALL provide feature-level attribution for the classifier prediction.

### REQ-033 — Feature Semantic Consistency

The feature semantics used during final classifier training SHALL match the verified P1 inference semantics.

If feature semantics change after training, the classifier SHALL be retrained and TreeSHAP mappings SHALL be reverified.

### REQ-034 — Synthetic Training

Synthetic tampering may be used for training methodology as specified by the finalized design.

Synthetic training data SHALL NOT be represented as real-world malware ground truth.

### REQ-035 — Model Artifact

The final classifier artifact SHALL be represented by:

`artifacts/lightgbm_model.txt`

subject to the unresolved staleness/versioning decision.

---

## 5. P2 Behavioral Requirements

### REQ-040 — Domain-Aware STRIP

Behavioral probing SHALL use the applicable domain-aware STRIP-style strategy.

### REQ-041 — Bounded Inference

Behavioral probing SHALL use bounded inference.

### REQ-042 — Vision Probing

For applicable non-quantized VISION models, behavioral probing SHALL use the finalized image/noise perturbation strategy.

### REQ-043 — NLP Probing

For applicable non-quantized NLP models, behavioral probing SHALL use the finalized integer-token-ID strategy.

### REQ-044 — Quantized Bypass

Quantized models SHALL skip behavioral probing under the finalized format-adaptive design.

### REQ-045 — Behavioral Score

Applicable behavioral probing SHALL produce `S_behavior`.

Exact baseline and normalization remain unresolved where listed in the Decision-Required Register.

---

## 6. Risk Aggregation Requirements

### REQ-050 — Static Anomaly Evidence

The risk pipeline SHALL incorporate static anomaly evidence represented by the finalized MAD-based approach.

### REQ-051 — Tampering Evidence

The risk pipeline SHALL incorporate `P_tamper`.

### REQ-052 — Behavioral Evidence

For non-quantized models where behavioral probing applies, the risk pipeline SHALL incorporate `S_behavior`.

### REQ-053 — Quantized Risk Path

Quantized models SHALL use the finalized quantized risk path without behavioral probing.

### REQ-054 — Model Risk Score

The finalized MRS formulas are:

**Non-quantized:**

```text
MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)
```

**Quantized:**

```text
MRS = min(100, 55*S_static + 45*P_tamper)
```

### REQ-055 — Verdict Thresholds

The finalized verdict thresholds are:

|    MRS | Verdict |
| -----: | ------- |
|   0–34 | PASS    |
|  35–69 | REVIEW  |
| 70–100 | FAIL    |

### REQ-056 — Highest-Risk Layer

Highest-risk-layer reporting SHALL remain separate from TreeSHAP feature attribution.

TreeSHAP SHALL NOT be treated as an automatic highest-risk-layer algorithm.

The exact feature-to-layer aggregation remains `DECISION REQUIRED` unless separately finalized.

---

## 7. Contract Requirements

### REQ-060 — features.json

P1 SHALL produce:

`data/outputs/features.json`

It is consumed by P3 and P2.

### REQ-061 — ml_results.json

P3 SHALL produce:

`data/outputs/ml_results.json`

It is consumed by P2 and the P3 reporting/dashboard layer.

### REQ-062 — risk_results.json

P2 SHALL produce:

`data/outputs/risk_results.json`

It is consumed by P3 reporting/dashboard integration.

### REQ-063 — Schema Authority

The exact contract fields, types, and layout SHALL NOT be invented by implementation.

D1 must be resolved before the contracts are treated as finalized.

### REQ-064 — Empty Schema Semantics

An empty schema SHALL be treated as empty.

Conceptual fields described elsewhere SHALL NOT be treated as implemented schema fields until D1 is resolved.

---

## 8. Reporting Requirements

### REQ-070 — Security Report

The final report SHALL include, where applicable:

* MRS
* PASS/REVIEW/FAIL verdict
* highest-risk layer
* TreeSHAP evidence
* behavioral evidence or explicit quantized-model bypass note
* assumptions
* limitations

### REQ-071 — Explainability

The report SHALL distinguish:

1. classifier feature attribution; and
2. highest-risk-layer determination.

### REQ-072 — PASS Interpretation

The report SHALL NOT describe `PASS` as proof of absolute security.

---

## 9. Integration Requirements

### REQ-080 — One-Command Scan

Phase 6 SHALL provide a one-command end-to-end scanning path.

### REQ-081 — Contract Validation

The integration layer SHALL validate upstream/downstream contracts.

### REQ-082 — Graceful Failure

Invalid or unsupported inputs SHALL fail gracefully rather than causing uncontrolled execution.

### REQ-083 — Reproducibility

Dependency and model-artifact reproducibility SHALL be addressed before final demo completion.

---

## 10. Phase and Verification Requirements

### REQ-090 — Gate-Based Advancement

A phase SHALL advance only when its verification gate is `PASS`.

### REQ-091 — BLOCKED State

A phase SHALL be considered `BLOCKED` when a required dependency, contract, or decision prevents legitimate completion.

`BLOCKED` SHALL NOT be treated as `PASS`.

### REQ-092 — FAIL State

A phase SHALL be considered `FAIL` when verification is attempted and required criteria are not satisfied.

### REQ-093 — No Silent Decisions

Implementation SHALL NOT silently invent:

* schemas;
* field names;
* field types;
* formulas;
* thresholds;
* normalization;
* baselines;
* aggregation methods;
* dependency versions;
* fallback behavior;
* feature semantics;
* architecture behavior.

### REQ-094 — No Mock/Scaffold Misrepresentation

Mock artifacts and scaffolding SHALL NOT be represented as production implementation or verified real outputs.

### REQ-095 — Verification Evidence

Completion claims SHALL be supported by the corresponding phase verification evidence.

---

## 11. Ownership Requirements

### REQ-100 — P1 Ownership

P1 owns:

* zero-trust intake;
* trusted graph;
* SafeTensors handling;
* domain/quantization detection;
* static steganalysis;
* feature extraction.

### REQ-101 — P2 Ownership

P2 owns:

* STRIP probing;
* behavioral scoring;
* MAD risk aggregation;
* MRS;
* verdict.

### REQ-102 — P3 Ownership

P3 owns:

* LightGBM;
* synthetic training;
* TreeSHAP;
* `P_tamper`;
* final security reporting/dashboard.

### REQ-103 — Integration Ownership

`scan_model.py` owns orchestration only.

It SHALL NOT duplicate P1, P2, or P3 algorithms.

---

## 12. Explicit Decision-Required Register

The following remain unresolved and SHALL NOT be silently invented:

* **D1:** Exact contract schemas and fields
* **D2:** Exact trusted-graph handoff mechanism
* **D3:** STRIP entropy baseline
* **D4:** `S_behavior` normalization
* **D5:** Per-layer → model-level risk aggregation
* **D6:** Highest-risk-layer aggregation
* **D8:** Model-artifact staleness protection
* **D9:** Dependency population and pinning

A dependent implementation SHALL be marked `BLOCKED` when one of these decisions is required for completion.

---

## 13. Final Hard Rules

The implementation SHALL:

1. preserve the frozen architecture;
2. respect subsystem ownership;
3. distinguish facts from inference;
4. distinguish scaffolding from implementation;
5. distinguish mocks from real artifacts;
6. preserve phase gates;
7. surface unresolved decisions;
8. stop when a required decision or dependency blocks progress.

**No agent may invent a missing architectural decision merely to continue execution.**
