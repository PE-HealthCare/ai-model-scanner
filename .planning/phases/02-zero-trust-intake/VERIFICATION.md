# Phase 2 — Zero-Trust Intake Verification

## 1. Verification Contract

States are exactly:

- PASS
- FAIL
- BLOCKED

A checkbox without reproducible evidence is NOT a PASS.

Any unresolved required decision/dependency makes the affected gate BLOCKED.

A decision marked resolved/locked is not implementation evidence; pending implementation or verification must remain explicitly pending.

## 2. Prerequisite

- [ ] CP1 is explicitly PASS.
- [ ] Approved Phase-1 state is the base of this work.
- [ ] Required contract is resolved.
- [ ] Required dependency policy is satisfied.

Evidence:
```text
CP1 evidence:
Base commit:
Dependency evidence:
```

## 3. SafeTensors Boundary

- [ ] `safetensors.safe_open` is used.
- [ ] No unauthorized alternative loader exists.
- [ ] No unrestricted pickle loading exists.
- [ ] No uploader-supplied Python/model code executes.
- [ ] No uploader-controlled imports execute.
- [ ] No unauthorized network access is introduced.

Evidence:
```text
Files:
Tests/commands:
Result:
Commit:
```

## 4. Resource Exhaustion Tests

Mandatory adversarial tests:

- [ ] oversized header;
- [ ] excessive metadata;
- [ ] excessive tensor count;
- [ ] pathological tensor dimensions;
- [ ] invalid offsets;
- [ ] integer/size boundary cases;
- [ ] excessive resource/time condition.

For every production limit:
```text
Limit:
Authoritative decision/source:
Test:
Result:
```

If a required production limit is not approved: **BLOCKED**, not PASS.

## 5. Architecture Validation

- [ ] unknown architecture rejected;
- [ ] malformed architecture rejected;
- [ ] architecture/tensor-name mismatch rejected;
- [ ] architecture/shape mismatch rejected;
- [ ] incompatible dtype rejected;
- [ ] no best-effort remapping;
- [ ] trusted graph created only after compatibility validation.

## 6. Domain / Quantization

- [ ] `input_domain` follows approved shape/type semantics.
- [ ] INT8/FP8 produce `is_quantized = TRUE`.
- [ ] other approved non-quantized types produce `FALSE`.
- [ ] domain/quantization tags are traceable to actual inspected model properties.

## 7. D2 Trusted-Model Handoff

D2 is architecturally RESOLVED/LOCKED. CP2 must still verify its implementation.

- [ ] P1 constructs the trusted, weight-loaded model inside the zero-trust intake boundary.
- [ ] `scan_model.py` receives the already-created trusted model/context.
- [ ] `scan_model.py` passes that trusted model/context to P2 by in-process Python object reference during the same pipeline execution.
- [ ] P2 does not independently reload the scanned model.
- [ ] The original untrusted model artifact/path is not used as P2's loading source.
- [ ] No serialized/persisted trusted model is introduced for downstream reloading.
- [ ] P2 does not construct an alternative architecture from the uploader artifact.
- [ ] `input_domain` and `is_quantized` required by P2 are preserved through the handoff.

Evidence:
```text
P1 producer:
Orchestration path:
P2 consumer:
Object/reference evidence:
No-reload evidence:
Metadata evidence:
Tests/commands:
Result:
Commit:
```

A D2 decision lock alone is insufficient for CP2; these criteria require implementation evidence.

## 8. Failure-Closed Tests

Mandatory tests:

- [ ] malformed file;
- [ ] invalid header;
- [ ] invalid tensor metadata;
- [ ] architecture mismatch;
- [ ] unsupported dtype;
- [ ] unknown architecture;
- [ ] intake exception/failure;
- [ ] failed intake prevents downstream handoff.

Expected result:
```text
FAILURE STATUS
NO DOWNSTREAM AUTHORITATIVE OUTPUT
NO FABRICATED TRUSTED GRAPH
NO P2 HANDOFF
```

## 9. Scope

- [ ] only Phase-2-authorized implementation/test files changed during Phase-2 implementation;
- [ ] no P2/P3 implementation changed;
- [ ] no unauthorized `scan_model.py` change;
- [ ] shared utility changes, if any, have authorization and impact evidence.

Governance/documentation synchronization is separately authorized and recorded; it does not by itself constitute CP2 implementation evidence.

## 10. CP2 Evidence Record

```text
Branch: phase-2/zero-trust-intake
Commit:
Reviewer:

CP1:
SafeTensors:
Resource limits:
Architecture compatibility:
Domain:
Quantization:
D2 handoff:
Adversarial tests:
Failure-closed tests:
Scope:
Final state: PASS / FAIL / BLOCKED
Blocker (if any):
```

CP2 may be approved only after all required criteria are PASS and independent approval is recorded.
