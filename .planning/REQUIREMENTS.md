# AI Model Scanner — Requirements

**Status:** FROZEN FOR EXECUTION

This document defines implementation requirements derived from the finalized project architecture and Master Graph.

Decision status is maintained separately from implementation verification: a decision may be locked while its implementation, empirical calibration, or checkpoint evidence remains pending. Such pending evidence SHALL NOT be inferred.

## 1. Core Functional Requirements

### REQ-001 — Untrusted Model Scanning

The scanner SHALL treat supplied model weight files as untrusted input.

### REQ-002 — Defensive Scope

The scanner SHALL perform detection and explainability only. It SHALL NOT attempt to patch, neutralize, or remediate detected threats.

### REQ-003 — End-to-End Pipeline

The implemented system SHALL support:

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

The root integration flow SHALL follow `P1 → P3 → P2 → P3`. `scan_model.py` SHALL orchestrate the pipeline and SHALL NOT duplicate subsystem ownership.

## 2. Security Requirements

### REQ-010 — No Uploaded Code Execution

The scanner SHALL NOT execute uploader-supplied Python code, including uploader-supplied `model.py`.

### REQ-011 — No Unrestricted Pickle

The scanner SHALL NOT use unrestricted pickle loading for untrusted model content.

### REQ-012 — Trusted Architecture Definitions

Architecture instantiation SHALL use trusted scanner-controlled definitions.

### REQ-013 — Bounded SafeTensors Handling

SafeTensors handling SHALL obey the current locked resource limits.

### REQ-014 — No Arbitrary Architecture Execution

The scanner SHALL NOT execute or dynamically trust an arbitrary architecture supplied by the uploader.

## 3. P1 Static Analysis Requirements

### REQ-020 — Architecture and Domain Detection

P1 SHALL establish the recognized declared architecture and applicable `input_domain` (`VISION` or `NLP`).

### REQ-021 — Quantization Detection

P1 SHALL establish whether the model is quantized using `is_quantized = true/false`.

### REQ-022 — Format-Adaptive Analysis

For FP32/FP16 models, P1 SHALL support the frozen feature family: entropy, PoV chi-square, LSB KL-divergence, KS statistic, statistical moments, sparsity, and outlier percentage.

For quantized formats, the finalized static design SHALL use whole-weight KS only.

### REQ-023 — Intra-Model Baseline

Static anomaly analysis SHALL use the finalized intra-model baseline. An external clean reference model SHALL NOT be required for runtime scanning.

### REQ-024 — Layer Identity

Feature output SHALL preserve authoritative layer identity sufficient for downstream risk reporting and attribution.

### REQ-025 — Real Feature Extractor

Final P3 classifier training SHALL consume output from P1's verified real feature extractor. Mock/synthetic extractor output SHALL NOT be represented as verified-real P1 semantics.

## 4. P3 Machine-Learning Requirements

### REQ-030 — LightGBM

The final anomaly classifier SHALL use LightGBM as specified by the finalized architecture.

### REQ-031 — Tampering Probability

The classifier SHALL produce `P_tamper`.

### REQ-032 — TreeSHAP

TreeSHAP SHALL provide feature-level attribution for classifier predictions.

TreeSHAP SHALL remain separate from highest-risk-layer determination.

### REQ-033 — Feature Semantic Consistency

The feature semantics used during final classifier training SHALL match verified P1 inference semantics. If feature semantics change after training, the classifier SHALL be retrained and TreeSHAP mappings SHALL be reverified.

### REQ-034 — Synthetic Training

Synthetic tampering may be used for training methodology. Synthetic training data SHALL NOT be represented as real-world malware ground truth.

### REQ-035 — Model Artifact

The final classifier artifact SHALL be represented by `artifacts/lightgbm_model.txt` with applicable provenance/staleness validation under D8.

## 5. P2 Behavioral Requirements

### REQ-040 — Domain-Aware STRIP

Behavioral probing SHALL use the applicable domain-aware STRIP strategy.

### REQ-041 — Bounded Inference

Behavioral probing SHALL use bounded inference.

### REQ-042 — Vision Probing

Applicable non-quantized VISION models SHALL use the finalized image/noise perturbation strategy.

### REQ-043 — NLP Probing

Applicable non-quantized NLP models SHALL use the finalized integer-token-ID strategy.

### REQ-044 — Quantized Bypass

Quantized models SHALL skip behavioral probing under the finalized format-adaptive design.

### REQ-045 — Behavioral Score

Applicable behavioral probing SHALL produce `S_behavior` only under the approved D3/D4 methodology. D3 empirical calibration remains pending and D4 normalization remains unresolved; implementations SHALL NOT invent baseline values, thresholds, normalization, or fallback behavior.

## 6. Risk Aggregation Requirements

### REQ-050 — Static Anomaly Evidence

The risk pipeline SHALL incorporate valid static anomaly evidence under the approved D5 boundary.

### REQ-051 — Tampering Evidence

The risk pipeline SHALL incorporate `P_tamper`.

### REQ-052 — Behavioral Evidence

Applicable non-quantized models SHALL incorporate `S_behavior` after D4 is resolved.

### REQ-053 — Quantized Risk Path

Quantized models SHALL use the finalized quantized risk path without behavioral probing.

### REQ-054 — Model Risk Score

**Non-quantized:**

```text
MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)
```

**Quantized:**

```text
MRS = min(100, 55*S_static + 45*P_tamper)
```

### REQ-055 — Verdict Thresholds

| MRS | Verdict |
|---:|---|
| 0–34 | PASS |
| 35–69 | REVIEW |
| 70–100 | FAIL |

### REQ-056 — Highest-Risk Layer

Highest-risk-layer reporting SHALL remain separate from TreeSHAP feature attribution.

D6 owns **selection/reporting from authoritative per-layer evidence**. D6 is not a second model-level aggregation stage and SHALL NOT manufacture layer-level `P_tamper`/`S_behavior`, recalculate MRS, or use TreeSHAP as the selection algorithm.

The exact deterministic D6 selection rule, final ownership wording, input contract, layer-identity semantics, and tie behavior remain `DECISION REQUIRED`.

## 7. Contract Requirements

### REQ-060 — features.json

P1 SHALL produce `data/outputs/features.json`, consumed by P3 and P2.

### REQ-061 — ml_results.json

P3 SHALL produce `data/outputs/ml_results.json`, consumed by P2 and P3 reporting/dashboard.

### REQ-062 — risk_results.json

P2 SHALL produce `data/outputs/risk_results.json`, consumed by P3 reporting/dashboard integration.

### REQ-063 — Schema Authority

Exact contract fields, types, and layout SHALL NOT be invented by implementation. **D1 is already RESOLVED / LOCKED**, so current contracts follow the approved contract definitions.

### REQ-064 — Empty Schema Semantics

An empty schema SHALL be treated as empty. Conceptual fields SHALL NOT be treated as implemented schema fields merely because they are mentioned in prose.

## 8. Reporting Requirements

### REQ-070 — Security Report

The final report SHALL include, where applicable: MRS, PASS/REVIEW/FAIL verdict, highest-risk layer, TreeSHAP evidence, behavioral evidence or explicit quantized-model bypass note, assumptions, and limitations.

### REQ-071 — Explainability

The report SHALL distinguish classifier feature attribution from highest-risk-layer determination.

### REQ-072 — PASS Interpretation

The report SHALL NOT describe PASS as proof of absolute security.

## 9. Integration Requirements

### REQ-080 — One-Command Scan

Phase 6 SHALL provide a one-command end-to-end scanning path.

### REQ-081 — Contract Validation

The integration layer SHALL validate upstream/downstream contracts.

### REQ-082 — Graceful Failure

Invalid or unsupported inputs SHALL fail safely rather than causing uncontrolled execution.

### REQ-083 — Reproducibility

Dependency and model-artifact reproducibility SHALL be addressed before final demo completion.

## 10. Phase and Verification Requirements

### REQ-090 — Gate-Based Advancement

A phase SHALL advance only when its verification gate is `PASS`.

### REQ-091 — BLOCKED State

A phase SHALL be `BLOCKED` when a required dependency, contract, decision, calibration item, or evidence item prevents legitimate completion. BLOCKED SHALL NOT be treated as PASS.

### REQ-092 — FAIL State

A phase SHALL be `FAIL` when verification is attempted and required criteria are not satisfied.

### REQ-093 — No Silent Decisions

Implementation SHALL NOT silently invent schemas, field names/types, formulas, thresholds, normalization, baselines, aggregation methods, dependency versions, fallback behavior, feature semantics, or architecture behavior.

### REQ-094 — No Mock/Scaffold Misrepresentation

Mock artifacts and scaffolding SHALL NOT be represented as production implementation or verified-real outputs.

### REQ-095 — Verification Evidence

Completion claims SHALL be supported by corresponding phase verification evidence.

## 11. Ownership Requirements

### REQ-100 — P1 Ownership

P1 owns zero-trust intake, trusted graph, SafeTensors handling, domain/quantization detection, static steganalysis, and feature extraction.

### REQ-101 — P2 Ownership

P2 owns STRIP probing, behavioral scoring, MAD risk aggregation, MRS, and verdict.

### REQ-102 — P3 Ownership

P3 owns LightGBM, synthetic training, TreeSHAP, `P_tamper`, and final security reporting/dashboard.

### REQ-103 — Integration Ownership

`scan_model.py` owns orchestration only and SHALL NOT duplicate P1/P2/P3 algorithms.

## 12. Current Decision Status

* **D1:** RESOLVED / LOCKED — exact 10-feature static contract.
* **D2:** RESOLVED / LOCKED — in-process trusted-model handoff; implementation/verification COMPLETE — CP2 PASS.
* **D3:** RESOLVED / LOCKED methodology; empirical calibration/evidence pending.
* **D4:** REQUIRED — exact `S_behavior` normalization.
* **D5:** RESOLVED / LOCKED methodology boundary; exact aggregation operator/evidence pending.
* **D6:** REQUIRED — boundary revised to highest-risk-layer selection/reporting; exact rule/input/tie semantics pending.
* **D7:** RESOLVED / LOCKED — MAD guard.
* **D8:** RESOLVED / LOCKED — artifact staleness protection.
* **D9:** PARTIALLY RESOLVED — D9.1–D9.20 locked; D9.21+ remains required.

A dependent implementation SHALL be `BLOCKED` when an unresolved decision or pending prerequisite is required for legitimate completion.

## 13. Final Hard Rules

1. Preserve the frozen architecture.
2. Respect subsystem ownership.
3. Distinguish facts from inference.
4. Distinguish scaffolding from implementation.
5. Distinguish mocks from real artifacts.
6. Preserve phase gates.
7. Surface unresolved decisions and pending evidence.
8. Return to the relevant decision record when pending implementation or empirical evidence becomes available.
9. Stop when a required decision or dependency blocks progress.

**No agent may invent a missing architectural decision merely to continue execution.**
