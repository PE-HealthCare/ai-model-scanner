# AI Model Scanner — Solution Architecture

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights
**Status:** **FROZEN FOR EXECUTION**
**Architecture Authority:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

---

# 1. Architecture Status

This document describes the finalized defensive scanner architecture.

It is an architectural specification.

It is NOT permission to:

* redesign the pipeline;
* invent unresolved implementation decisions;
* expand detection scope;
* introduce arbitrary-code execution;
* replace one subsystem with another;
* treat examples as finalized numerical requirements.

Where this document conflicts with the Master Graph, the Master Graph wins.

Where an implementation detail is marked **DECISION REQUIRED**, agents MUST stop and surface the decision.

---

# 2. Core Objective

Build a defensive pre-deployment scanner that analyzes an untrusted `.safetensors` AI model artifact for evidence consistent with:

* weight-level steganographic manipulation;
* localized statistical anomalies;
* potential backdoor-related behavioral anomalies.

The scanner produces:

* statistical evidence;
* classifier probability;
* TreeSHAP explanations;
* behavioral evidence where applicable;
* an aggregated Model Risk Score;
* PASS / REVIEW / FAIL.

The scanner detects **evidence of manipulation within its defined scope**.

It does NOT claim to identify or extract malicious payloads.

It does NOT provide absolute security assurance.

---

# 3. Frozen End-to-End Architecture

```text
Declared Architecture
        +
Untrusted .safetensors
        │
        ▼
┌──────────────────────────────┐
│ P1 — Zero-Trust Intake       │
│ Trusted Graph + Validation   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ P1 — Static Steganalysis     │
│ Per-layer statistical feats │
└──────────────┬───────────────┘
               │
               ▼
        features.json
               │
               ▼
┌──────────────────────────────┐
│ P3 — LightGBM + TreeSHAP     │
│ P_tamper + explanations     │
└──────────────┬───────────────┘
               │
               ▼
        ml_results.json
               │
               ▼
┌──────────────────────────────┐
│ P2 — Behavioral + Risk       │
│ STRIP + MAD + MRS + Verdict │
└──────────────┬───────────────┘
               │
               ▼
        risk_results.json
               │
               ▼
┌──────────────────────────────┐
│ P3 — Security Report         │
│ / Dashboard                  │
└──────────────────────────────┘
```

`scan_model.py` orchestrates this sequence.

It does not become a fourth implementation stage.

---

# 4. Trust Boundary

The uploaded model artifact is untrusted.

The scanner MUST NOT execute code supplied by the uploader.

The trusted boundary is:

```text
UNTRUSTED
──────────────────────────────
Declared architecture input
SafeTensors weight file
Tensor metadata / bytes
──────────────────────────────
             │
             ▼
VALIDATED / TRUSTED
──────────────────────────────
Approved architecture definition
Scanner-controlled execution
Bounded parsing
Bounded inference
──────────────────────────────
```

Explicitly prohibited:

* uploader-supplied `model.py`;
* arbitrary Python execution;
* unrestricted pickle deserialization;
* arbitrary plugin loading from the model artifact;
* executing code embedded in model files.

---

# 5. Supported Architecture Model

The prototype assumes that the uploader declares a recognizable architecture.

Examples may include approved architectures such as:

* ResNet18;
* DistilBERT.

The examples above illustrate the supported architecture class; they do not authorize arbitrary architecture execution.

The architecture MUST be instantiated from a trusted library implementation.

Unknown/custom architecture handling is outside the finalized prototype scope.

If the declared architecture cannot be safely instantiated:

> **FAIL CLOSED.**

Do not fall back to executing uploader-supplied architecture code.

---

# 6. Stage 1 — Zero-Trust Intake

## Owner

P1.

## Input

* declared architecture;
* untrusted `.safetensors` artifact.

## Required behavior

P1 must:

1. parse the SafeTensors header through the approved SafeTensors mechanism;
2. enforce approved resource limits;
3. extract tensor names, shapes, offsets, and dtypes;
4. validate tensor metadata;
5. instantiate only the declared trusted architecture;
6. validate the declared architecture against the actual tensor structure;
7. determine `input_domain`;
8. determine `is_quantized`;
9. create the trusted graph handoff.

---

# 7. Bounded Intake

The phrase "bounded parsing" is a security requirement.

It is NOT a license for an agent to invent arbitrary limits.

Resource ceilings MUST be established through the approved project decision process before they are treated as final implementation constants.

Potential limits include:

* maximum header bytes;
* maximum metadata size;
* maximum tensor count;
* maximum tensor dimensions;
* maximum total model/resource size;
* maximum memory consumption;
* maximum parsing time.

If a required security limit is unresolved:

> **The implementation MUST fail closed rather than silently inventing a production limit.**

Illustrative examples in historical design material, such as a particular header size, MUST NOT be interpreted as approved requirements unless explicitly promoted through the project decision process.

---

# 8. Architecture/Tensor Consistency

The declared architecture MUST agree with the actual SafeTensors tensor structure.

Validation includes, as applicable:

* tensor names;
* tensor shapes;
* expected layers;
* expected dtypes;
* required parameters;
* unexpected parameters;
* missing parameters.

Mismatch MUST NOT trigger best-effort loading.

The safe result is:

```text
architecture mismatch
        ↓
FAIL / BLOCKED
        ↓
no downstream scoring
```

---

# 9. Domain and Quantization

The scanner uses:

```text
input_domain ∈ {VISION, NLP}
```

and:

```text
is_quantized ∈ {true, false}
```

Domain classification MUST be based on validated architecture/input characteristics, not arbitrary assumptions.

The semantics of these fields are shared contract semantics.

Changing them requires downstream impact analysis.

---

# 10. Stage 2 — Format-Adaptive Static Steganalysis

## Owner

P1.

## Non-quantized models

For FP32/FP16 weights, the frozen design includes:

* Byte-position Shannon Entropy;
* PoV Chi-Square;
* LSB KL-Divergence;
* KS statistic;
* mean;
* standard deviation;
* skewness;
* kurtosis;
* sparsity;
* outlier percentage.

The features are computed per layer against an intra-model baseline.

No external clean model is required at runtime.

---

# 11. Quantized Models

For quantized representations:

```text
is_quantized = true
```

the finalized design skips mantissa/LSB-specific analysis.

The quantized static path uses the whole-weight KS statistic as specified by the Master Graph.

The implementation MUST NOT apply floating-point mantissa analysis merely because such features exist elsewhere in the code.

---

# 12. Feature Semantics

The feature vector is not defined by an arbitrary dimension count.

The authoritative feature contract must define:

* exact field names;
* order;
* data type;
* units;
* normalization;
* missing-value behavior;
* layer association;
* semantic meaning.

Until D1 is resolved, agents MUST NOT invent a final schema.

A feature name that sounds correct but has different semantics is a breaking change.

---

# 13. Intra-Model Baseline

The baseline is self-referential:

```text
layer ↔ other layers in the same model
```

No external clean reference model is required at runtime.

This is an intentional design choice.

Limitation:

* models with very few layers can produce weak baselines.

Degenerate baseline handling is governed by D7.

---

# 14. Stage 3 — Explainable Anomaly Classification

## Owner

P3.

## Input

Verified P1 feature output.

## Method

The classifier uses:

* LightGBM;
* TreeSHAP.

The classifier produces:

```text
P_tamper ∈ [0,1]
```

TreeSHAP provides feature-level attribution for the classifier prediction.

---

# 15. Final Classifier Training Integrity

The final classifier MUST be trained using the same authoritative P1 feature extraction semantics used at runtime.

The training pipeline may use:

* clean pretrained models;
* controlled synthetic tampering;
* LSB manipulation;
* mantissa-bit manipulation;
* other approved synthetic perturbations.

However:

> Synthetic training data does not make the P1 feature extractor optional.

The authoritative relationship is:

```text
P1 real extractor
        ↓
features
        ↓
synthetic training dataset
        ↓
LightGBM
```

A copied feature extractor is not equivalent to the authoritative P1 implementation.

---

# 16. Classifier Staleness

The classifier artifact is tied to the feature semantics used during training.

If any material P1 feature semantic changes:

```text
feature semantics changed
        ↓
classifier = STALE
        ↓
P3 retraining
        ↓
TreeSHAP re-verification
        ↓
downstream re-verification
```

A classifier that executes successfully but was trained against incompatible feature semantics is NOT valid.

---

# 17. TreeSHAP ≠ Highest-Risk Layer

TreeSHAP answers:

> Which classifier features contributed to the prediction?

Highest-risk-layer determination answers:

> Which neural-network layer has the greatest aggregated risk?

They are separate mechanisms.

TreeSHAP MUST NOT be used as a shortcut for D5 or D6.

Until the approved layer aggregation decisions exist, final highest-risk-layer reporting remains constrained by those decisions.

---

# 18. Stage 4 — Domain-Aware Behavioral Probing

## Owner

P2.

Behavioral probing operates on the trusted, weight-loaded graph.

It is:

* inference-only;
* bounded;
* domain-aware.

### VISION

Use appropriate floating-point/image-style synthetic probes.

### NLP

Use integer token-ID-compatible probes.

Gaussian image-style inputs MUST NOT be blindly fed into integer-only NLP embedding inputs.

---

# 19. Quantized Behavioral Bypass

For quantized models:

```text
is_quantized = true
        ↓
behavioral probing skipped
```

The quantized model follows the quantized-specific risk path.

This is a finalized architecture rule.

---

# 20. Behavioral Resource Limits

"Bounded inference" means production execution MUST have explicit finite resource constraints.

These include, as applicable:

* maximum inference passes;
* maximum wall-clock time;
* maximum memory;
* maximum generated probe size.

A historical value such as "32 passes" is illustrative unless explicitly approved as the final limit.

Agents MUST NOT silently select a large or unbounded value.

If a mandatory limit remains unresolved:

> **BLOCKED / FAIL CLOSED.**

---

# 21. STRIP

Behavioral probing computes:

```text
H_STRIP
```

and derives:

```text
S_behavior ∈ [0,1]
```

through the approved baseline and normalization mechanism.

The exact:

* STRIP baseline;
* `H_STRIP → S_behavior` normalization

remain governed by:

* D3;
* D4.

Agents MUST NOT silently resolve them.

---

# 22. Stage 5 — Risk Aggregation

## Owner

P2.

P2 is the sole owner of:

* per-layer risk aggregation;
* model-level aggregation;
* MRS;
* verdict.

The conceptual static anomaly calculation uses:

```text
Z = (X - median(X_base)) /
    (1.4826 × MAD(X_base))
```

with normalization to:

```text
S_static ∈ [0,1]
```

where approved implementation semantics are applied.

---

# 23. MAD Degenerate Cases

The approved D7 guard for zero/near-zero MAD and degenerate baselines is:

*   **Finite nonzero MAD:** Use the actual MAD directly (even if extremely small). Do not add epsilon or near-zero thresholds.
*   **Exact MAD = 0:** If the target equals the median, anomaly is 0. If it differs, record `DEGENERATE_DEVIATION`. Do not invent a finite Z-score or add epsilon.
*   **Insufficient baselines (1-2 layers):** Mark static baseline evidence unavailable; block downstream scoring requiring it. Do not fabricate scores.
*   **Invalid data (NaN, inf, missing):** Invalid. Do not impute.

Note: D5 (Model-level risk aggregation) and D6 (Highest-risk-layer aggregation) remain unresolved and must not be bypassed using TreeSHAP.

---

# 24. Model Risk Score

For non-quantized models, the finalized formula is:

```text
MRS = min(
    100,
    40*S_static +
    35*P_tamper +
    25*S_behavior
)
```

For quantized models:

```text
MRS = min(
    100,
    55*S_static +
    45*P_tamper
)
```

Verdict thresholds:

```text
0–34   → PASS
35–69  → REVIEW
70–100 → FAIL
```

These formulas MUST NOT be recalculated independently by `scan_model.py` or P3.

P2 is authoritative.

---

# 25. Highest-Risk-Layer Aggregation

The mechanism that converts per-layer evidence into:

```text
highest-risk-layer
```

is separate from TreeSHAP.

D6 governs this behavior.

If the aggregation method is unresolved, the implementation MUST NOT invent one and present it as final.

---

# 26. Output Contracts

Planned artifacts:

```text
data/outputs/features.json
data/outputs/ml_results.json
data/outputs/risk_results.json
artifacts/lightgbm_model.txt
```

File existence does not prove validity.

Each artifact must be classified as:

```text
MOCK
SCAFFOLD
VERIFIED-REAL
STALE
FAILED
```

as applicable.

---

# 27. Output Failure Semantics

If an upstream stage fails:

```text
P1 failure
    ↓
STOP
```

```text
P3 failure
    ↓
STOP final scoring
```

```text
P2 failure
    ↓
NO MRS
NO VERDICT
```

The system MUST NOT:

* fabricate missing values;
* use arbitrary defaults;
* silently substitute mock output;
* report PASS because a detector failed.

Technical inability to scan is not equivalent to evidence of safety.

---

# 28. Security Report

A complete verified report includes:

* MRS;
* PASS / REVIEW / FAIL;
* highest-risk layer where valid;
* primary TreeSHAP evidence;
* behavioral result/note;
* assumptions;
* limitations;
* scan status;
* provenance where required.

A PASS means:

> No evidence of manipulation was found within the scanner's defined detection scope.

It does NOT mean:

> The model is guaranteed clean or secure.

---

# 29. Scope

## Core

The frozen prototype includes:

* declared trusted architecture;
* safe SafeTensors intake;
* zero-copy/memory-mapped weight access where approved;
* format-adaptive static analysis;
* intra-model baseline;
* LightGBM;
* TreeSHAP;
* domain-aware bounded STRIP;
* MAD-calibrated risk aggregation;
* explainable report.

---

# 30. Explicitly Out of Scope

The prototype does not include:

* uploader-supplied architecture code;
* arbitrary `model.py` execution;
* unrestricted pickle loading;
* universal backdoor detection;
* payload extraction;
* payload decryption;
* automatic architecture inference from arbitrary files;
* remediation/modification of uploaded weights;
* data/label poisoning detection;
* claims of detection against all advanced steganographic encodings.

Optional/future concepts MUST NOT silently enter the core pipeline.

---

# 31. Unsupported Input Handling

If an input is:

* unsupported;
* malformed;
* ambiguous;
* architecturally inconsistent;
* outside resource limits;
* unsafe to instantiate;

the scanner MUST fail closed.

Unsupported input MUST NOT be silently coerced into a supported format.

---

# 32. Provenance

The final pipeline must preserve the relationship:

```text
model artifact
      ↓
P1 verified extraction
      ↓
features
      ↓
P3 classifier
      ↓
ml_results
      ↓
P2 behavioral/risk
      ↓
risk_results
      ↓
report
```

Where practical, artifacts should carry or be associated with:

* model identity/hash;
* code revision;
* schema version;
* feature semantic version;
* classifier version;
* run identifier.

This prevents a valid artifact from being accidentally paired with incompatible upstream data.

---

# 33. Architecture Integrity Rules

Agents MUST NOT:

* add an alternative risk engine;
* add a second classifier path;
* bypass P1;
* bypass P2 for final risk;
* move P1 detection into `scan_model.py`;
* move P2 risk logic into P3;
* use TreeSHAP as highest-layer aggregation;
* introduce arbitrary uploaded-code execution;
* silently expand supported architectures.

Any such change requires explicit architecture reopening.

---

# 34. Phase Dependency Model

```text
Phase 1
  ↓
Phase 2
  ↓
Phase 3
  ↓
P1 real feature semantics verified
  ↓
Phase 4 final classifier
  ↓
Phase 5 behavioral + risk
  ↓
Phase 6 integration/demo
```

Parallel preparation is permitted where explicitly allowed, but final dependency gates remain mandatory.

---

# 35. Architecture Decision Register

The following remain unresolved until explicitly decided:

| ID | Decision                             |
| -- | ------------------------------------ |
| D1 | Exact contract schemas               |
| D2 | P1 → P2 trusted graph handoff        |
| D3 | STRIP baseline                       |
| D4 | `H_STRIP → S_behavior` normalization |
| D5 | Per-layer → model-level aggregation  |
| D6 | Highest-risk-layer aggregation       |
| D7 | MAD zero/near-zero guard             |
| D8 | Classifier staleness protection      |
| D9 | Dependency pinning                   |

No implementation convenience overrides this register.

---

# 36. Architecture Acceptance Rule

An implementation is architecturally compliant only if it satisfies all of the following:

* follows the frozen P1/P3/P2/P3 ownership chain;
* preserves the zero-trust boundary;
* does not execute arbitrary uploaded code;
* respects quantized/non-quantized behavior;
* preserves feature semantics;
* uses verified real P1 features for final classifier training;
* keeps TreeSHAP distinct from highest-risk-layer aggregation;
* keeps MRS/verdict under P2;
* fails closed on required upstream failures;
* does not silently resolve D1–D9;
* preserves provenance;
* passes the applicable phase verification gate.

---

# 37. Final Architectural Principle

> **The scanner is an evidence-producing defensive pipeline, not an autonomous architecture-discovery or malware-execution system.**

Implementation agents are authorized to implement the frozen architecture.

They are not authorized to redefine it.
