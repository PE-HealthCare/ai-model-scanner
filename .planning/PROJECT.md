# AI Model Scanner — Project Definition

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights
**Repository:** `PE-HealthCare/ai-model-scanner`
**Status:** FROZEN FOR EXECUTION

## Problem Being Solved

AI model weight files (e.g. `.safetensors`) can be used as a covert-storage medium: malicious payloads or hidden data can be steganographically embedded within tensor byte patterns, exploiting the fact that weight files are large, numeric, and not commonly inspected the way executable code is.

This project builds a scanner that inspects untrusted model weight files for statistical and behavioral evidence of tampering, without relying on the uploader's declared trustworthiness.

## Defensive Security Purpose

The scanner is a **defensive** tool.

It does not execute, patch, or neutralize threats. It produces evidence-backed risk signals (`PASS / REVIEW / FAIL`) so a human or downstream system can decide whether a model is safe to load into production.

The project is scoped to **detection and explainability**, not remediation.

## Frozen Five-Stage Detection Pipeline + Phase 6 Integration/Demo

The finalized detection architecture contains **five detection stages**.

The repository uses **six implementation phases** because Phase 6 performs final integration and demonstration of the five-stage pipeline. Phase 6 is **not a sixth detection stage**.

### Stage 1 — Zero-Trust Intake & Trusted Graph Instantiation

Bounded parsing of the SafeTensors header and declared architecture.

A trusted, standard-library architecture graph is instantiated and mapped to the supplied weights.

No uploader-supplied code is trusted or executed.

### Stage 2 — Format-Adaptive Static Steganalysis

Per-layer statistical feature extraction is performed against an intra-model baseline.

For FP32/FP16 formats, the planned feature family includes:

* entropy
* PoV chi-square
* LSB KL-divergence
* KS statistic
* statistical moments
* sparsity
* outlier percentage

For quantized formats, the finalized design uses **whole-weight KS only**.

### Stage 3 — Explainable Anomaly Classification

A LightGBM classifier trained from P1's verified feature-extractor output produces `P_tamper`.

TreeSHAP provides feature-level attribution.

TreeSHAP feature attribution is not itself the mechanism for determining the highest-risk neural-network layer.

### Stage 4 — Domain-Aware Sandboxed Behavioral Probing

STRIP-style probing is selected according to `input_domain`:

* `VISION`
* `NLP`

Inference is bounded and performed without executing uploader-supplied code.

Quantized models skip behavioral probing under the finalized format-adaptive design.

The stage produces `S_behavior` where applicable.

### Stage 5 — MAD-Calibrated Risk Aggregation

Static anomaly evidence, classifier tampering probability, and applicable behavioral evidence are combined into a Model Risk Score (`MRS`).

The final verdict is:

* `PASS`
* `REVIEW`
* `FAIL`

The stage feeds the final explainable security report.

## Implementation Phase Mapping

| Implementation Phase | Purpose                              |
| -------------------- | ------------------------------------ |
| Phase 1              | Mock pipeline and contract agreement |
| Phase 2              | Zero-trust intake                    |
| Phase 3              | Real static steganalysis             |
| Phase 4              | ML classification                    |
| Phase 5              | Behavioral probing and risk          |
| Phase 6              | Final integration and demo           |

Phase 6 integrates the five detection stages. It does not introduce a new detection subsystem.

## Ownership

| Subsystem                 | Owner                                               |
| ------------------------- | --------------------------------------------------- |
| P1 Static Engine          | `src/p1_static_engine/analyzer.py`                  |
| P2 Behavioral/Risk Engine | `src/p2_behavioral_risk/prober.py`                  |
| P3 ML/Dashboard           | `src/p3_ml_dashboard/classifier.py`, `dashboard.py` |
| Shared utilities          | `src/common/utils.py`                               |
| Root orchestration        | `scan_model.py`                                     |

`scan_model.py` is the integration/orchestration surface and is **not a fourth subsystem owner**.

P2 owns risk aggregation, MRS, and verdict logic.

## Mapping to PS Evaluation Criteria

| Evaluation Criterion        | Pipeline Evidence                                                                             |
| --------------------------- | --------------------------------------------------------------------------------------------- |
| Cybersecurity Effectiveness | Zero-trust intake, no uploaded-code execution, combined evidence                              |
| Steganography Awareness     | Entropy, PoV chi-square, LSB KL-divergence, KS statistic, statistical moments                 |
| Technical Soundness         | Format-adaptive analysis, intra-model baseline, LightGBM, MAD aggregation, synthetic training |
| Explainability              | TreeSHAP feature attribution and separately derived highest-risk-layer reporting              |
| Practical Feasibility       | SafeTensors mmap-based access, bounded inference, no core-model backpropagation               |
| Clarity of Demo             | PASS/REVIEW/FAIL verdict with evidence and assumptions/limitations                            |

## Supported Input Assumption

The uploader declares a recognizable architecture.

The scanner instantiates a trusted, standard-library version of that declared architecture and maps the supplied weights into it.

The scanner does **not** attempt to infer or execute an arbitrary, unknown, or self-describing architecture.

## Explicit Security Boundary

**The scanner never executes arbitrary uploaded code.**

Specifically:

* No uploader-supplied `model.py` is executed.
* No unrestricted pickle loading is used.
* Architecture instantiation is restricted to trusted, standard-library definitions.
* SafeTensors header parsing is bounded.
* Uploaded weight bytes are treated as untrusted input.

## Decision Status / Current Limitations

The project distinguishes **locked decision methodology**, **implementation/verification status**, and **empirical evidence**. A locked decision does not by itself prove implementation or checkpoint completion.

* The static baseline is intra-model (layer-vs-layer); no external clean reference model is required or used at runtime.
* D2 (trusted graph handoff) is resolved and locked; its real implementation and CP2 verification remain pending.
* D3 (STRIP entropy baseline) is methodologically resolved and locked, but its empirical calibration/evidence is pending. Baseline values must not be invented; the approved calibration run must populate the evidence before D3 is considered fully evidenced for authoritative behavioral scoring.
* D4 (behavioral normalization), D5 (per-layer to model-level risk aggregation), and D6 (highest-risk-layer aggregation) remain explicitly unresolved and must not be silently invented.
* D7 (MAD degenerate/insufficient-baseline guard) is resolved and locked.
* D8 (artifact staleness protection) is resolved and locked.
* D9 remains partially resolved: D9.1–D9.20 are locked, while D9.21+ remain required.
* TreeSHAP explains feature contribution to the classifier prediction; it does not by itself determine the highest-risk neural-network layer.
* A `PASS` verdict is evidence only within the scanner's detection scope; it is **not** a guarantee of absolute security.
* Future implementation must not silently invent unresolved behavior or treat pending implementation/evidence as already verified.

## Source of Truth

The **Final Master Discovery & Dependency Graph** is the authoritative architecture source.

Project and planning documents must remain consistent with that frozen architecture.

If an unresolved item conflicts with an implementation assumption, the unresolved item remains unresolved until explicitly decided.

Future agents must:

1. inspect the repository before changing it;
2. preserve the frozen architecture;
3. respect subsystem ownership;
4. distinguish repository facts from inference;
5. never treat scaffolding as implementation;
6. never treat mock artifacts as real outputs;
7. never silently invent unresolved decisions;
8. distinguish a locked methodology from pending implementation or empirical evidence;
9. when pending evidence becomes available, return to the corresponding decision record, update only the evidence-dependent portion, and re-verify downstream consistency;
10. stop when a required dependency or decision is blocking progress.
