# Phase 02 — Zero-Trust Intake — VERIFICATION

**Gate:** CP2 — Intake Gate (per Master Graph Section 13)

No phase advances until its VERIFICATION.md gate passes. This is CP2; Phase 03 (Static Steganalysis) real implementation may only proceed after all checks below pass.

## Pass/Fail Checklist

### Bounded Header Handling

- [ ] SafeTensors header parsing is bounded (does not read beyond the declared header region)
- [ ] Header parsing does not execute any code embedded in or referenced by the file

### SafeTensors-Only Intake

- [ ] Weight access uses `safetensors.safe_open` (or equivalent bounded SafeTensors API), not a generic/unbounded deserializer
- [ ] No other untrusted serialization format is accepted as a substitute for SafeTensors in this phase

### No Pickle Execution

- [ ] No Pickle-based loading path exists anywhere in the intake code
- [ ] A file crafted to trigger Pickle deserialization (if such a path existed) does not execute code — verified by absence of any Pickle usage in the intake implementation

### Declared Architecture Validation

- [ ] Intake requires an uploader-declared architecture and validates it against the trusted, standard-library set before proceeding
- [ ] An unrecognized/undeclared architecture causes intake to fail closed, not proceed with a guessed architecture
- [ ] No automatic architecture inference/detection is implemented for arbitrary unlabeled models

### Trusted Graph Creation

- [ ] The instantiated graph is built exclusively from trusted, standard-library architecture definitions
- [ ] No uploader-supplied `model.py` (or equivalent uploader-supplied code) is executed at any point during graph instantiation
- [ ] Weights from the SafeTensors file are correctly mapped onto the trusted graph structure

### Shape/Dtype Extraction

- [ ] Tensor shape is correctly extracted for each tensor in the file
- [ ] Tensor dtype is correctly extracted for each tensor in the file
- [ ] Extracted shape/dtype data is available to downstream quantization and domain tagging logic

### Quantization Tagging

- [ ] `is_quantized = TRUE` is correctly set when dtype is INT8 or FP8
- [ ] `is_quantized = FALSE` is correctly set for all other observed dtypes (e.g. FP32/FP16)
- [ ] Quantization tag is included in the metadata handed off downstream

### Domain Tagging

- [ ] `input_domain = VISION` is correctly set for 4D float tensor input characteristics
- [ ] `input_domain = NLP` is correctly set for 2D/3D integer token tensor input characteristics
- [ ] Domain tagging is derived only from input shape/type characteristics, per the canonical wording — not from architecture name, filename, or other unspecified signals
- [ ] Domain tag is included in the metadata handed off downstream

### Downstream Handoff

- [ ] Trusted graph, `input_domain`, and `is_quantized` are all available to the Phase 3 (Static Steganalysis) stage
- [ ] The mechanism used for handoff is documented; if it relies on resolving D2 (P1→P2 trusted-graph handoff), this is explicitly noted as pending rather than assumed complete
- [ ] Handoff data matches the values actually computed during intake (no default/placeholder values leaking through in a real run)

### Malformed/Untrusted Input Handling

- [ ] A malformed SafeTensors file (corrupt header) causes a visible, handled failure — not a crash with no diagnostic, and not silent continuation
- [ ] A file with an undeclared or unrecognized architecture causes a visible, handled failure
- [ ] A file attempting to smuggle executable content (e.g. disguised as a valid tensor) does not result in code execution during intake
- [ ] Failure modes are distinguishable from success (e.g. explicit error/status, not an empty or partially-populated success result)

## Gate Result

- [ ] **PASS** — all checks above are satisfied; Phase 03 real implementation may proceed
- [ ] **FAIL** — one or more checks unsatisfied; remain in Phase 02 until resolved

## Preserved Unresolved Decision

- **D2 — Trusted graph handoff mechanism** between P1 and P2 through `scan_model.py` is DECISION REQUIRED. If any downstream-handoff check above depends on this mechanism being finalized, record it as blocked on D2 rather than marking it PASS by assumption.
