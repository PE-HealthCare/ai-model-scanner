# AI Model Scanner — Project Definition

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights
**Repository:** `PE-HealthCare/ai-model-scanner`
**Status:** FROZEN FOR EXECUTION

## Problem Being Solved

AI model weight files (e.g. `.safetensors`) can be used as a covert-storage medium: malicious payloads or hidden data can be steganographically embedded within tensor byte patterns, exploiting the fact that weight files are large, numeric, and not commonly inspected the way executable code is. Existing model-sharing workflows generally trust the weight file's contents implicitly. This project builds a scanner that inspects untrusted model weight files for statistical and behavioral evidence of tampering, without relying on the uploader's declared trustworthiness.

## Defensive Security Purpose

The scanner is a **defensive** tool. It does not execute, patch, or neutralize threats — it produces evidence-backed risk signals (PASS / REVIEW / FAIL) so a human or downstream system can decide whether a model is safe to load into production. It is explicitly scoped to detection and explainability, not remediation.

## Frozen Five-Stage Pipeline

1. **Zero-Trust Intake & Trusted Graph Instantiation** — Bounded parsing of the SafeTensors header and declared architecture; instantiation of a trusted, standard-library architecture graph with mapped weights. No uploader-supplied code is trusted at this stage.
2. **Format-Adaptive Static Steganalysis** — Per-layer statistical feature extraction (entropy, PoV chi-square, LSB KL-divergence, KS statistic, moments, sparsity, outlier percentage for FP32/FP16; whole-weight KS only for quantized formats) against an intra-model baseline.
3. **Explainable Anomaly Classification** — A LightGBM classifier trained on P1's verified feature extractor output produces `P_tamper`, with TreeSHAP providing feature-level attribution.
4. **Domain-Aware Sandboxed Behavioral Probing** — STRIP-style probing selected by `input_domain` (VISION vs NLP), bounded inference only, producing `S_behavior`. Quantized models skip behavioral probing under the finalized format-adaptive design.
5. **MAD-Calibrated Risk Aggregation** — Median Absolute Deviation-based normalization of static and tamper evidence, combined into a Model Risk Score (MRS) and PASS/REVIEW/FAIL verdict, feeding the final explainable security report.

## Mapping to PS Evaluation Criteria

| Evaluation Criterion | Pipeline Evidence |
|---|---|
| Cybersecurity Effectiveness | Zero-trust intake, no execution of uploaded code, combined static + behavioral evidence |
| Steganography Awareness | Entropy, PoV chi-square, LSB KL-divergence, KS statistic, statistical moments |
| Technical Soundness | Format-adaptive analysis, intra-model baseline, LightGBM classification, MAD aggregation, synthetic training methodology |
| Explainability | TreeSHAP feature attribution, separately derived highest-risk-layer reporting |
| Practical Feasibility | SafeTensors mmap-based access, bounded inference, no core-model backpropagation |
| Clarity of Demo | PASS/REVIEW/FAIL verdict with supporting evidence and stated assumptions/limitations |

## Supported Input Assumption

The uploader declares a recognizable architecture. The scanner instantiates a trusted, standard-library version of that declared architecture and maps weights into it — it does not attempt to infer or execute an arbitrary, unknown, or self-describing architecture.

## Explicit Security Boundary

**The scanner never executes arbitrary uploaded code.** No uploader-supplied `model.py` is executed. No unrestricted pickle loading is used. Architecture instantiation is restricted to trusted, standard-library definitions; only the declared architecture and the SafeTensors weight bytes are treated as untrusted input.

## Key Limitations (from Master Graph)

- The static baseline is intra-model (layer-vs-layer); no external clean reference model is required or used at runtime.
- Intra-model MAD baselines can be weak when a model has very few layers (degenerate/near-zero MAD case; guard behavior is unresolved — see ROADMAP.md and the Decision-Required Register).
- TreeSHAP explains feature contribution to the classifier's prediction; it does not, by itself, determine the highest-risk neural-network layer. Feature-to-layer aggregation is a separate, distinct mechanism.
- A PASS verdict communicates evidence of manipulation within the tool's detection scope only — it is **not** a guarantee of absolute security.
- Several contract, aggregation, and normalization details remain explicitly unresolved (DECISION REQUIRED) as of this writing and must not be silently invented by future implementation work.
