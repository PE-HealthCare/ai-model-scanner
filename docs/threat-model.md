# AI Model Scanner — Threat Model

**Status:** FROZEN FOR EXECUTION
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

## Scope

This document describes the defensive threat model the scanner is designed against, as established in the Master Graph. It does not introduce new capabilities, claims, or guarantees beyond what the frozen pipeline defines.

## Threat Class: AI Model Supply-Chain Threats

The scanner addresses the risk that an AI model weight file, obtained from an external or otherwise untrusted source, has been tampered with to covertly carry malicious content or hidden data before being loaded into a production or downstream system. The weight file is treated as an untrusted artifact from the moment it enters the pipeline.

## Untrusted `.safetensors` Input

The `.safetensors` file and its declared architecture are the untrusted inputs to the system. Intake is bounded: the SafeTensors header is parsed in a bounded manner, and a trusted, standard-library architecture is instantiated from the declared architecture rather than trusting or executing anything embedded in the uploaded artifact itself.

## Static Steganographic Payloads Hidden in Model Weights

The primary threat modeled is steganographic hiding of payloads within the numeric byte patterns of model weight tensors — exploiting the fact that weight data is large, high-entropy-tolerant, and not routinely inspected the way executable code is.

### Mantissa/LSB-Based Hiding

For FP32/FP16 weights, the scanner specifically targets least-significant-bit and mantissa-level hiding techniques, using byte-position Shannon entropy, PoV chi-square, LSB KL-divergence, KS statistic, and statistical moments (mean, standard deviation, skewness, kurtosis, sparsity, outlier percentage) computed against an intra-model, layer-vs-layer baseline (no external clean reference required at runtime).

### Format Differences: FP32/FP16 vs. Quantized

The static analysis is format-adaptive:

- **FP32/FP16:** full feature set above, including mantissa/LSB-specific tests.
- **Quantized (INT8/FP8):** mantissa/LSB-specific tests are skipped; only whole-weight KS statistic is used, reflecting that quantized representations do not carry the same mantissa structure.

## Static Anomaly Detection vs. Behavioral Evidence

The threat model separates two distinct evidence types, which are combined only at the risk-aggregation stage:

- **Static anomaly evidence:** derived from per-layer statistical analysis of weight bytes (P1 → P3 classification), producing `P_tamper` with TreeSHAP feature attribution.
- **Behavioral evidence:** derived from observing the model's inference-time output behavior under bounded probing (P2), producing `S_behavior`.

Neither is treated as sufficient alone; both feed into MAD-calibrated risk aggregation with `S_static`, `P_tamper`, and `S_behavior` combined into the MRS.

## Domain-Aware Behavioral Probing

Behavioral probing is gated by `input_domain` and `is_quantized`:

- **VISION** models are probed with float/image-noise inputs.
- **NLP** models are probed with integer token-ID inputs.
- Probing is a bounded number of inference-only passes (e.g. 32), producing softmax entropy `H_STRIP`, compared against a baseline and normalized to `S_behavior ∈ [0,1]`.
- **Quantized models skip behavioral probing entirely** under the finalized format-adaptive design, and use a quantized-specific MRS formula (`S_static` and `P_tamper` only) instead.

The exact STRIP entropy baseline and the exact `H_STRIP → S_behavior` normalization are **DECISION REQUIRED** and are not yet finalized.

## Defensive Security Boundary

The scanner's own execution boundary is a core part of its threat model:

- **No arbitrary uploaded-code execution.** No uploader-supplied `model.py` is executed, and no unrestricted pickle loading is used.
- Only a **trusted, standard-library** architecture definition is instantiated; the declared architecture and SafeTensors weight bytes are the only untrusted inputs consumed, and are handled through bounded parsing rather than execution.
- Behavioral probing itself is bounded inference-only (no core-model backpropagation), limiting the scanner's own attack surface when interacting with a potentially tampered model.

## Recognizable Declared Architecture Assumption

The threat model assumes the uploader declares a recognizable architecture that the scanner can instantiate using trusted, standard-library definitions. The scanner does not attempt to detect or defend against threats that would require executing or interpreting an unknown, self-describing, or uploader-supplied architecture implementation.

## Known Limitations

The following limitations are carried over from the Master Graph and are preserved as-is, not resolved or expanded:

- The static baseline is intra-model (layer-vs-layer) and can be **weak when a model has very few layers** — the exact degenerate/near-zero MAD guard behavior is DECISION REQUIRED (D7).
- TreeSHAP explains feature contribution to the classifier's prediction; it does **not**, by itself, determine the highest-risk neural-network layer — feature-to-layer and per-layer-to-model-level aggregation mechanisms are separate and are DECISION REQUIRED (D5, D6).
- The exact STRIP baseline and behavioral normalization are DECISION REQUIRED (D3, D4).
- The exact P1→P2 trusted-graph handoff mechanism is DECISION REQUIRED (D2).
- `lightgbm_model.txt` can become stale if P1 feature semantics change after training, and this can fail silently since LightGBM may still run; whether a staleness check is added is DECISION REQUIRED (D8).
- **A PASS verdict communicates evidence of manipulation within the tool's detection scope only. It is not a guarantee of absolute security.**

## Explicit Non-Claims

Consistent with the frozen scope of this pipeline, this scanner does **not** claim to universally detect all forms of backdoors or steganographic hiding. In particular, the frozen detection methods are statistical/entropy-based static analysis plus bounded behavioral probing; they are not designed around, and no claim is made regarding detection of, spread-spectrum or LDPC-style encoding schemes engineered to evade byte-level statistical tests, nor data/label poisoning attacks that manipulate model behavior through training data rather than through post-hoc weight-level tampering. These remain outside the detection scope established by the Master Graph and are noted here as a limitation, not as a roadmap item to be silently resolved.
