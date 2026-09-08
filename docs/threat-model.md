# AI Model Scanner — Threat Model

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights
**Status:** **FROZEN FOR EXECUTION**
**Primary Source of Truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

---

# 1. Purpose

This document defines the defensive threat model for the AI Model Scanner.

It describes:

* what is considered untrusted;
* what an attacker may attempt;
* what the scanner is designed to defend against;
* what controls are required;
* what verification evidence is required;
* what remains outside the detection scope.

This document does not authorize new capabilities.

It does not override the Master Graph.

It does not convert limitations into future implementation requirements.

---

# 2. Security Objective

The scanner is designed to provide defensive evidence about potentially tampered AI model weight artifacts before downstream deployment.

The primary security objectives are:

1. prevent the model artifact from gaining arbitrary code execution inside the scanner;
2. safely inspect untrusted `.safetensors` metadata and weights;
3. detect statistical evidence associated with weight-level steganographic manipulation;
4. detect selected behavioral anomalies through bounded probing;
5. combine independent evidence into a risk score;
6. produce explainable evidence rather than an unexplained binary label;
7. fail closed when safe scanning cannot be completed.

---

# 3. Security Boundary

The uploaded model is untrusted.

The security boundary is:

```text
                UNTRUSTED
┌────────────────────────────────────┐
│ Declared architecture              │
│ SafeTensors file                   │
│ Tensor names/shapes/dtypes         │
│ Weight bytes                       │
└─────────────────┬──────────────────┘
                  │
                  ▼
         VALIDATION / BOUNDARY
                  │
                  ▼
┌────────────────────────────────────┐
│ Trusted architecture definitions   │
│ Bounded parser                     │
│ Scanner-controlled execution      │
│ Bounded inference                  │
└────────────────────────────────────┘
                TRUSTED
```

No uploaded file is trusted merely because its extension is `.safetensors`.

---

# 4. Threat Actor Model

The threat actor is assumed to control or influence the untrusted model artifact.

The actor may attempt to:

* modify model weights;
* embed hidden information in weight representations;
* manipulate LSB/mantissa patterns;
* create localized statistical anomalies;
* construct malformed tensor metadata;
* provide inconsistent architecture declarations;
* create resource-exhaustion inputs;
* attempt to exploit unsafe deserialization;
* attempt to trigger unsupported execution paths;
* exploit scanner implementation weaknesses.

The attacker is NOT assumed to control:

* the trusted scanner source at runtime;
* approved standard-library architecture definitions;
* the scanner's verification infrastructure;
* protected credentials;
* the scanner's policy configuration.

If those assumptions change, the threat model must be revisited.

---

# 5. Primary Threat: Weight-Level Steganography

### Threat

An attacker embeds hidden data or malicious content inside numeric weight representations while preserving enough model functionality to avoid obvious detection.

### Relevant representations

For FP32/FP16:

* mantissa bits;
* least-significant bits;
* byte distributions.

### Potential effects

* altered LSB entropy;
* artificial bit equalization;
* abnormal divergence;
* distributional anomalies;
* localized layer anomalies.

### Controls

P1 performs:

* byte-position Shannon entropy;
* PoV Chi-Square;
* LSB KL-Divergence;
* KS statistics;
* distributional moments;
* intra-model comparison.

### Verification

Security tests must confirm that controlled synthetic tampering produces expected feature changes where the frozen detection methods are designed to respond.

---

# 6. Quantized Representation Threat

### Threat

An attacker targets quantized weights where floating-point mantissa assumptions no longer apply.

### Control

The scanner uses a format-adaptive branch:

```text
FP32 / FP16
    ↓
mantissa + LSB analysis

INT8 / FP8
    ↓
whole-weight KS path
```

Mantissa/LSB-specific tests MUST NOT be applied indiscriminately to quantized representations.

### Verification

Tests must confirm:

* quantized models enter the quantized path;
* mantissa/LSB tests are skipped;
* whole-weight KS is used;
* behavioral probing is bypassed;
* quantized MRS formula is used.

---

# 7. Malformed Header Threat

### Threat

An attacker provides a malformed or hostile SafeTensors header intended to cause:

* parser failure;
* excessive allocation;
* memory exhaustion;
* CPU exhaustion;
* invalid offset handling;
* denial of service.

### Controls

* bounded parsing;
* explicit resource limits;
* validation before use;
* no unsafe fallback parser;
* fail-closed behavior.

### Verification

Regression tests MUST include:

* malformed JSON/header;
* truncated header;
* oversized header;
* invalid offsets;
* overlapping/invalid tensor regions;
* invalid tensor metadata.

---

# 8. Resource Exhaustion Threat

A malicious artifact may be syntactically valid but intentionally expensive.

Threats include:

* enormous header;
* excessive tensor count;
* excessive metadata;
* pathological tensor dimensions;
* enormous total weight size;
* excessive memory use;
* excessive inference time;
* excessive probe count.

### Controls

The scanner requires explicit bounded resource policies.

Relevant ceilings include:

* header bytes;
* metadata size;
* tensor count;
* tensor dimensions;
* total input size;
* memory;
* parsing time;
* inference time;
* probe count.

### Important rule

A phrase such as "bounded" does not permit an autonomous agent to choose an unlimited or arbitrarily large value.

Unresolved production security limits MUST be treated as unresolved decisions.

### Failure behavior

```text
resource limit exceeded
        ↓
STOP
        ↓
NO MRS
NO VERDICT
```

---

# 9. Architecture Confusion Threat

### Threat

An attacker supplies a declared architecture that does not correspond to the actual tensor structure.

Potential results:

* incorrect graph loading;
* malformed state loading;
* misleading analysis;
* crashes;
* accidental fallback behavior.

### Controls

P1 MUST validate:

* architecture identity;
* expected tensor names;
* shapes;
* dtypes;
* required parameters;
* unexpected parameters;
* missing parameters.

Mismatch MUST fail closed.

---

# 10. Arbitrary Code Execution Threat

### Threat

An attacker attempts to cause the scanner to execute malicious code through model loading.

Examples include:

* uploader-supplied `model.py`;
* unrestricted pickle;
* executable plugins;
* arbitrary deserialization hooks.

### Controls

The scanner MUST NOT:

* execute uploaded Python;
* import uploaded model code;
* load unrestricted pickle;
* execute arbitrary model-defined functions.

Architecture classes must originate from trusted scanner-controlled libraries.

---

# 11. Unknown Architecture Threat

### Threat

An attacker provides a model requiring custom executable architecture code.

### Control

Unknown/custom architecture is outside the prototype scope.

The scanner does NOT:

```text
unknown architecture
        ↓
execute uploader code
```

Instead:

```text
unknown architecture
        ↓
unsupported / FAIL CLOSED
```

---

# 12. Behavioral Probing Threat

### Threat

A tampered model may behave normally on ordinary inputs while responding abnormally to trigger-like probes.

### Control

P2 performs domain-aware bounded STRIP-style probing.

For VISION:

* float/image-compatible probes.

For NLP:

* integer token-ID-compatible probes.

The scanner computes:

```text
H_STRIP
      ↓
S_behavior
```

through the approved D3/D4 mechanisms.

---

# 13. Behavioral Input-Type Threat

### Threat

Incorrect probe types may cause:

* model crashes;
* invalid inference;
* misleading behavioral results.

### Control

Probe generation is gated by:

```text
input_domain
is_quantized
```

NLP integer-only models MUST NOT receive incompatible floating-point image noise.

### Verification

Tests must exercise both:

* VISION path;
* NLP path.

---

# 14. Quantized Behavioral Bypass

The finalized architecture skips behavioral probing for quantized models.

Threat-model implication:

> Quantized models receive reduced behavioral coverage by design.

This is a known architectural limitation, not an implementation bug.

The quantized risk formula therefore excludes `S_behavior`.

---

# 15. Statistical Baseline Threat

### Threat

A naturally unusual model layer may be falsely identified as anomalous.

The intra-model baseline can become weak when:

* the model has very few layers;
* layer distributions are unusually homogeneous;
* the baseline has near-zero dispersion.

### Control

MAD-based robust statistics are used.

### D7 Guard

D7 is RESOLVED. The exact behavior for degenerate baselines is:
*   **Finite nonzero MAD:** Use actual MAD. Do not add epsilon.
*   **Exact MAD = 0:** Record zero anomaly (if target equals median) or `DEGENERATE_DEVIATION` (if target differs).
*   **Insufficient baselines (1-2 layers):** Block downstream scoring.
*   **Invalid data:** Fail closed. Do not impute.

---

# 16. Classifier Integrity Threat

### Threat

The classifier may produce apparently valid predictions despite receiving features whose semantics differ from those used during training.

This is particularly dangerous because the classifier may execute without an obvious software error.

### Control

Final training MUST use the authoritative P1 feature extractor.

Feature semantic changes invalidate the classifier.

```text
P1 semantic change
        ↓
LightGBM = STALE
        ↓
retrain + TreeSHAP reverification
```

---

# 17. TreeSHAP Interpretation Threat

### Threat

An operator or agent may incorrectly interpret TreeSHAP attribution as the highest-risk neural-network layer.

### Control

The architecture explicitly separates:

```text
TreeSHAP
→ classifier feature contribution

Highest-risk layer
→ layer aggregation
```

D5/D6 govern unresolved aggregation behavior.

---

# 18. Output Artifact Poisoning

### Threat

An attacker, stale process, or faulty pipeline may cause downstream artifacts to be consumed without proving their provenance.

Examples:

* stale `features.json`;
* stale `ml_results.json`;
* stale `risk_results.json`;
* classifier trained against different feature semantics;
* mock data accidentally used as real data.

### Controls

Artifacts must have identifiable provenance where practical.

Required status vocabulary:

```text
MOCK
SCAFFOLD
VERIFIED-REAL
STALE
FAILED
```

Artifact existence alone does not establish trust.

---

# 19. Mock Data Leakage Threat

### Threat

Development scaffolding is accidentally used in the production/demo path.

### Controls

The pipeline must distinguish:

```text
MOCK ≠ VERIFIED-REAL
SCAFFOLD ≠ IMPLEMENTED
```

Final gates must reject mock-only upstream evidence.

---

# 20. Contract Poisoning / Schema Drift

### Threat

A field remains syntactically valid but its meaning changes.

Examples:

* reordered features;
* changed units;
* changed normalization;
* renamed semantics;
* changed layer association.

A classifier may continue executing while producing invalid results.

### Control

Contract changes require:

* affected-owner notification;
* downstream revalidation;
* classifier retraining where necessary;
* TreeSHAP remapping;
* updated evidence.

---

# 21. Risk Aggregation Threat

### Threat

Different components calculate inconsistent risk scores or verdicts.

### Control

P2 is the sole owner of:

* risk aggregation;
* MRS;
* verdict.

`scan_model.py` MUST NOT calculate an alternative MRS.

P3 MUST NOT override P2's verdict.

---

# 22. Risk Formula Integrity

For non-quantized models:

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

Verdicts:

```text
PASS    = 0–34
REVIEW  = 35–69
FAIL    = 70–100
```

Any change to these formulas is an architectural/contract change and requires explicit approval.

---

# 23. Detection Failure vs. Scanner Safety Failure

These are different events.

### Detection failure

The scanner completes but does not detect a threat within its scope.

### Scanner safety failure

The scanner cannot safely process the input.

Examples:

* malformed artifact;
* resource exhaustion;
* architecture mismatch;
* unsupported input;
* internal security-boundary violation.

A scanner safety failure MUST NOT be converted into:

```text
PASS
```

The appropriate result is failure/blocking.

---

# 24. Network Egress Threat

### Threat

Model artifacts or sensitive scanner data could be transmitted externally.

### Control

Runtime scanning does not require arbitrary external network access.

Agents MUST NOT upload:

* model weights;
* proprietary artifacts;
* credentials;
* scan results containing sensitive data

to external services without explicit authorization.

Unexpected network requirements must be surfaced rather than silently introduced.

---

# 25. Secret Exposure Threat

The model artifact and scanner inputs are untrusted data.

The scanner MUST NOT treat strings found in:

* tensor metadata;
* model filenames;
* configuration fields;
* arbitrary input fields

as credentials or commands.

Agents MUST NOT commit credentials or secrets discovered during development.

---

# 26. Dependency Supply-Chain Threat

### Threat

A malicious or incompatible dependency could compromise the scanner or invalidate reproducibility.

### Controls

Production dependencies must eventually be pinned according to D9.

Dependency changes require:

* explicit version;
* justification;
* compatibility testing;
* regression testing;
* security consideration.

Until D9 is resolved, agents must not silently finalize dependency versions.

---

# 27. Scanner Host Isolation

The threat model assumes the scanner is defensive infrastructure.

The runtime environment should provide appropriate isolation so that a compromise of the scanner process does not automatically compromise unrelated host resources.

At minimum, the design must avoid granting the uploaded model:

* arbitrary shell access;
* arbitrary filesystem writes;
* unrestricted network access;
* access to secrets.

Where deployment controls exist, sandboxing/containerization should reinforce these boundaries.

This does not authorize introducing a new runtime architecture into the frozen prototype without approval.

---

# 28. Integrity / Model Identity

Where practical, model artifacts should be associated with an integrity identifier such as a cryptographic hash.

The purpose is to prevent:

```text
model A scanned
      ↓
model B reported
```

through accidental or malicious artifact substitution.

The same artifact identity should remain associated with downstream results.

---

# 29. Threat → Control → Verification Matrix

| Threat                   | Primary Control                | Owner           | Verification                |
| ------------------------ | ------------------------------ | --------------- | --------------------------- |
| Malformed header         | bounded SafeTensors parsing    | P1              | malformed-header tests      |
| Oversized input          | resource limits                | P1              | limit regression tests      |
| Invalid offsets          | metadata validation            | P1              | hostile-header tests        |
| Architecture mismatch    | tensor/architecture validation | P1              | mismatch tests              |
| Arbitrary code execution | trusted architecture only      | P1              | no-uploaded-code regression |
| FP steganography         | entropy/PoV/KL/KS/moments      | P1              | synthetic tamper tests      |
| Quantized evasion        | quantized static path          | P1              | INT8/FP8 tests              |
| Behavioral anomaly       | STRIP probing                  | P2              | VISION/NLP probe tests      |
| Wrong NLP input          | domain-aware probes            | P2              | integer-input tests         |
| Weak MAD baseline        | D7-controlled guard            | P2              | degenerate-baseline tests   |
| Classifier drift         | provenance/staleness control   | P3              | stale-model tests           |
| Feature semantic drift   | retraining gate                | P1/P3           | contract regression         |
| Layer misinterpretation  | TreeSHAP/layer separation      | P3/P2           | attribution tests           |
| Risk inconsistency       | P2 sole MRS owner              | P2              | integration tests           |
| Mock leakage             | artifact status/provenance     | all             | mock-to-real tests          |
| Output poisoning         | provenance                     | all             | artifact identity tests     |
| Dependency compromise    | D9/pinning                     | project         | dependency verification     |
| Network exfiltration     | restricted egress              | project/runtime | network policy test         |
| Scanner crash            | fail-closed behavior           | all             | stage-failure tests         |

---

# 30. Mandatory Adversarial Regression Set

The implementation must maintain regression coverage for applicable cases including:

### Intake

* malformed header;
* truncated file;
* oversized header;
* excessive tensor count;
* excessive metadata;
* invalid offsets;
* invalid shape;
* invalid dtype;
* architecture mismatch;
* unknown architecture.

### Feature extraction

* NaN/Inf;
* zero MAD;
* near-zero MAD;
* one-layer model;
* empty/invalid feature output;
* incorrect feature ordering.

### ML

* missing feature;
* unexpected feature;
* stale classifier;
* incompatible feature semantics;
* mock feature input.

### Behavioral

* VISION input path;
* NLP integer input path;
* quantized bypass;
* bounded pass limit;
* timeout;
* malformed behavioral result.

### Risk

* malformed P3 output;
* missing `P_tamper`;
* invalid score range;
* invalid aggregation;
* invalid verdict;
* upstream failure.

### Integration

* P1 failure;
* P3 failure;
* P2 failure;
* partial output;
* stale output;
* mock output;
* artifact identity mismatch.

---

# 31. Security Failure Policy

When a security control fails:

```text
STOP
 ↓
record failure
 ↓
prevent downstream scoring
 ↓
mark affected artifacts invalid/stale
 ↓
surface issue
```

The system MUST NOT:

* continue silently;
* downgrade the security control;
* substitute arbitrary defaults;
* suppress the failure;
* report PASS.

---

# 32. Known Detection Limitations

The scanner does not claim universal detection.

Known limitations include:

* intra-model baseline weakness for very small models;
* missing dependency pinning;
* unresolved D3/D4 behavioral semantics;
* unresolved D5/D6 aggregation;
* declared-architecture limitation;
* quantized behavioral bypass;
* stale classifier risk if provenance is not enforced;
* limited detection coverage for sophisticated statistical evasion.

---

# 33. Explicit Non-Claims

The scanner does NOT claim to:

* detect every backdoor;
* detect every steganographic technique;
* identify malicious payloads;
* recover hidden data;
* guarantee a model is safe;
* detect data/label poisoning;
* reliably detect spread-spectrum/LDPC-style schemes specifically engineered below statistical detection thresholds;
* support arbitrary uploader-defined architectures.

These limitations are part of the security model.

They are not silently converted into implementation promises.

---

# 34. Detection Scope

The core detection scope is:

```text
post-training weight-level manipulation
+
selected statistical evidence
+
selected bounded behavioral evidence
```

The scanner is evidence-producing.

It is not a remediation engine.

---

# 35. No Automatic Remediation

The scanner does not automatically:

* delete models;
* modify weights;
* repair backdoors;
* shuffle weights;
* patch model architecture;
* quarantine external systems.

A FAIL verdict is a security signal.

Any operational remediation belongs outside the frozen detection pipeline unless explicitly added through an approved architecture decision.

---

# 36. PASS Semantics

A PASS means:

> No evidence of manipulation was found within the scanner's tested detection scope.

It does NOT mean:

> The model is mathematically proven clean.

Every final report must preserve this distinction.

---

# 37. Threat Model Acceptance Conditions

The implementation is security-model compliant only when:

* untrusted model artifacts cannot execute arbitrary uploaded code;
* SafeTensors intake is bounded;
* architecture/tensor mismatches fail closed;
* unsupported architectures fail closed;
* static analysis follows the correct format branch;
* behavioral probing is domain-aware;
* quantized models bypass behavioral probing as specified;
* unresolved D3/D4/D5/D6 decisions are not silently invented;
* classifier staleness is handled;
* mock artifacts cannot masquerade as real;
* downstream failures cannot become PASS;
* MRS is calculated only by P2;
* output provenance is maintained;
* dependency/network/secret boundaries are respected;
* adversarial regression tests exist.

---

# 38. Final Security Principle

> **The scanner must be safer than the model it is scanning.**

The untrusted model is data, not executable authority.

The scanner may inspect it, measure it, probe it within explicit bounds, and produce evidence.

It must never surrender control of its execution boundary to the artifact being analyzed.
