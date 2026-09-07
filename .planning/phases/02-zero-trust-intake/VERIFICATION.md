# Phase 2 — Zero-Trust Intake Verification

## 1. Verification Contract

States are exactly:

- PASS
- FAIL
- BLOCKED

A checkbox without reproducible evidence is NOT a PASS.

Any unresolved required decision/dependency makes the affected gate BLOCKED.

## 2. Prerequisite

- [ ] CP1 is explicitly APPROVED.
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

## 7. Failure-Closed Tests

Mandatory tests:

- [ ] malformed file;
- [ ] invalid header;
- [ ] invalid tensor metadata;
- [ ] architecture mismatch;
- [ ] unsupported dtype;
- [ ] unknown architecture;
- [ ] intake exception/failure.

Expected result:
```text
FAILURE STATUS
NO DOWNSTREAM AUTHORITATIVE OUTPUT
NO FABRICATED TRUSTED GRAPH
```

## 8. Scope

- [ ] only Phase-2-authorized files changed;
- [ ] no planning governance files changed;
- [ ] no P2/P3 implementation changed;
- [ ] no unauthorized `scan_model.py` change;
- [ ] shared utility changes, if any, have authorization and impact evidence.

## 9. CP2 Evidence Record

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
Adversarial tests:
Failure-closed tests:
Scope:
Final state: PASS / FAIL / BLOCKED
Blocker (if any):
```

CP2 may be approved only after all required criteria are PASS and independent approval is recorded.
