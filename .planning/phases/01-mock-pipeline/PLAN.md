# FILE: .planning/phases/01-mock-pipeline/PLAN.md

# Phase 01 — Mock Pipeline — PLAN

**Status:** Current execution target
**Gate:** CP1 — Phase 1 Mock Gate
**Owners:** P1, P2, P3, with `scan_model.py` as integration surface
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

## 1. Objective

Establish the end-to-end interface between P1, P3, P2, and the final P3 report surface using controlled mock outputs.

This phase validates:

* contract shape;
* stage ordering;
* handoff behavior;
* schema validation;
* failure propagation.

This phase does **not** validate detection quality.

No real SafeTensors analysis, real static feature extraction, real LightGBM training, real TreeSHAP, or real behavioral probing is permitted.

## 2. Hard Prerequisite

Before implementation begins:

* D1 — exact contract schemas — MUST be explicitly resolved by the team.
* The three schemas must contain the agreed fields/types/layout.
* The decision must be recorded outside this phase as the authoritative D1 decision.

If D1 is unresolved:

**STATUS = BLOCKED.**

The agent MUST stop implementation of authoritative mock contracts.

The agent MUST NOT invent fields, dimensions, names, defaults, or types.

## 3. Frozen Mock Data Flow

```text
P1 mock
   ↓
features.json
   ↓
P3 mock
   ↓
ml_results.json
   ↓
P2 mock
   ↓
risk_results.json
   ↓
P3 report surface
```

`scan_model.py` MUST orchestrate:

```text
P1 → P3 → P2 → P3
```

It MUST NOT implement subsystem logic.

## 4. Authorized Files

### P1

Primary implementation:

```text
src/p1_static_engine/analyzer.py
```

### P2

Primary implementation:

```text
src/p2_behavioral_risk/prober.py
```

### P3

Primary implementation:

```text
src/p3_ml_dashboard/classifier.py
src/p3_ml_dashboard/dashboard.py
```

### Integration

```text
scan_model.py
```

### Contract files

```text
features.schema.json
ml_results.schema.json
risk_results.schema.json
```

These may only be changed to reflect the explicitly approved D1 decision.

### Outputs

```text
data/outputs/features.json
data/outputs/ml_results.json
data/outputs/risk_results.json
```

### Tests

Only tests required for Phase 1 verification may be added or changed.

## 5. Forbidden Scope

The Phase 1 agent MUST NOT:

* modify the frozen Master Graph;
* redesign the architecture;
* implement real P1/P2/P3 logic;
* modify another owner's implementation;
* modify `src/common/utils.py` unless explicitly authorized;
* add arbitrary dependencies;
* install unapproved production dependencies;
* introduce network access;
* execute uploaded model code;
* introduce pickle loading;
* treat mocks as real artifacts.

## 6. Mock Data Rules

Every Phase 1 output is:

```text
MOCK
NON-AUTHORITATIVE
DEVELOPMENT/INTERFACE ONLY
```

Mock data MUST be distinguishable from real data.

A mock artifact MUST NOT be:

* used to train the final LightGBM model;
* used to claim real classifier performance;
* used to claim real behavioral results;
* used as evidence for a final security verdict;
* silently copied into a later authoritative artifact.

If provenance cannot distinguish mock from real:

**BLOCKED.**

## 7. Branch

Each owner works on:

```text
phase/01-mock-pipeline
```

If multiple agents require simultaneous independent work, use an explicitly owner-qualified child branch:

```text
phase/01-mock-pipeline-p1
phase/01-mock-pipeline-p2
phase/01-mock-pipeline-p3
phase/01-mock-pipeline-integration
```

The branch MUST start from the current approved base.

An agent MUST NOT assume another agent's unmerged working tree is available.

## 8. Parallel Work

After D1 is resolved:

```text
P1 mock ─┐
P2 mock ─┼─→ integration
P3 mock ─┘
```

All three mock implementations may proceed in parallel.

Integration MUST wait until the agreed mock interfaces exist.

## 9. Handoff Rule

Before consuming an upstream output:

1. verify the file exists;
2. validate it against its schema;
3. verify provenance says `MOCK`;
4. reject missing/malformed data;
5. never substitute an empty/default value.

## 10. Failure Rule

Any stage failure MUST propagate.

Forbidden:

```text
stage fails
↓
agent inserts empty/default value
↓
pipeline continues
```

Required:

```text
stage fails
↓
visible failure
↓
non-zero execution status
↓
stop
```

## 11. Commit / Merge Rule

An agent MUST:

1. implement only authorized scope;
2. run verification;
3. record evidence;
4. commit its work;
5. open/update the appropriate PR.

Passing tests do **not** authorize merge.

The agent MUST NOT self-approve or self-merge its own phase work.

Phase 1 becomes complete only after the CP1 gate is independently accepted.

## 12. Phase Exit

CP1 is the only authorization to leave Phase 1.

```text
CP1 PASS → Phase 2 may begin
CP1 FAIL → remain in Phase 1
CP1 BLOCKED → STOP and wait
```

No downstream phase may treat a branch containing unmerged Phase 1 work as equivalent to CP1 PASS.

---

# FILE: .planning/phases/01-mock-pipeline/VERIFICATION.md

# Phase 01 — Mock Pipeline — VERIFICATION

**Gate:** CP1 — Phase 1 Mock Gate
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

## 1. Gate Semantics

Only three outcomes exist:

```text
PASS
FAIL
BLOCKED
```

Definitions:

* **PASS:** every required criterion passes with recorded evidence.
* **FAIL:** a required criterion was executed and failed.
* **BLOCKED:** a required dependency/decision/authorization is unresolved or required evidence cannot be obtained.

An unresolved required decision MUST NOT be treated as PASS.

A checkbox without evidence is NOT verification.

## 2. Required Evidence

Every verification item marked PASS MUST record:

```text
Command/test:
Result:
Artifact/path:
Relevant code location:
Commit:
```

Where a test cannot reasonably provide a command, a reproducible inspection method MUST be recorded.

## 3. D1 Gate

* [ ] D1 is explicitly resolved and recorded.
* [ ] All three schemas contain the approved fields/types/layout.
* [ ] No field was invented by an implementation agent.

**If D1 is unresolved: CP1 = BLOCKED.**

## 4. Contract Verification

* [ ] `features.json` validates against `features.schema.json`.
* [ ] `ml_results.json` validates against `ml_results.schema.json`.
* [ ] `risk_results.json` validates against `risk_results.schema.json`.
* [ ] Validation is programmatic.
* [ ] Validation evidence is recorded.

## 5. Mock Provenance

* [ ] All Phase 1 outputs are explicitly identified as MOCK.
* [ ] Mock artifacts cannot be mistaken for authoritative real artifacts.
* [ ] No mock output is used to create a final classifier.
* [ ] No mock output is used to claim a real security verdict.

## 6. Orchestration

* [ ] `scan_model.py` executes P1 → P3 → P2 → P3.
* [ ] `scan_model.py` contains orchestration only.
* [ ] No subsystem implementation logic has been moved into `scan_model.py`.
* [ ] Each stage consumes the expected upstream artifact.
* [ ] A single invocation completes the mock chain.

## 7. Failure Tests

The following adversarial cases are mandatory:

* [ ] missing `features.json`;
* [ ] malformed `features.json`;
* [ ] missing `ml_results.json`;
* [ ] malformed `ml_results.json`;
* [ ] missing `risk_results.json`;
* [ ] schema mismatch;
* [ ] wrong field type;
* [ ] unexpected required field;
* [ ] mock artifact presented as real.

Each must result in a visible failure rather than silent substitution.

## 8. Scope Verification

* [ ] No unauthorized owner files were modified.
* [ ] No Master Graph modification occurred.
* [ ] No unauthorized dependency was introduced.
* [ ] No unauthorized network access was introduced.
* [ ] No pickle/unrestricted deserialization was introduced.

## 9. Gate Result

```text
IF all required checks PASS + evidence exists:
    CP1 = PASS

ELSE IF any required check was executed and failed:
    CP1 = FAIL

ELSE IF any required dependency/decision/evidence is unavailable:
    CP1 = BLOCKED
```

Only:

```text
CP1 = PASS
```

authorizes Phase 2.

---

# FILE: .planning/phases/02-zero-trust-intake/PLAN.md

# Phase 02 — Zero-Trust Intake — PLAN

**Owner:** P1 — Eyes
**Primary file:** `src/p1_static_engine/analyzer.py`
**Gate prerequisite:** CP1 = PASS
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

## 1. Objective

Implement real bounded zero-trust intake of an untrusted `.safetensors` file and its declared architecture.

Produce:

* trusted graph;
* tensor metadata;
* `input_domain`;
* `is_quantized`.

No static steganalysis occurs in this phase.

## 2. Start Condition

Phase 2 MAY begin only when:

```text
CP1 = PASS
```

If CP1 is:

```text
FAIL → STOP
BLOCKED → WAIT
```

The agent MUST NOT bypass CP1 using mock completion.

## 3. Authorized Files

Primary:

```text
src/p1_static_engine/analyzer.py
```

Phase-specific tests may be added/modified.

No P2/P3 implementation changes are permitted.

`scan_model.py` may be touched only if a previously authorized integration change is strictly required for the Phase 2 handoff and does not implement P1 logic.

## 4. Frozen Security Boundary

The implementation SHALL use:

```text
safetensors.safe_open
```

for SafeTensors weight access.

The agent MUST NOT replace this with an agent-defined "equivalent" loader.

No uploader-supplied `model.py` or other uploader code may execute.

No unrestricted pickle loading is permitted.

## 5. Bounded Intake

Header handling MUST be bounded.

The implementation MUST explicitly enforce approved limits for:

* header size;
* tensor count;
* metadata size;
* tensor dimensions;
* model/resource size;
* memory usage where applicable.

If required limits have not been approved:

**DO NOT INVENT VALUES.**

The relevant operation is BLOCKED until the required limit is explicitly resolved.

## 6. Architecture Trust

The uploader-declared architecture selects a trusted standard-library architecture definition.

The implementation MUST NOT infer an arbitrary architecture.

The following MUST all agree:

```text
declared architecture
+
actual SafeTensors tensor names
+
actual shapes
+
actual dtypes
↓
compatibility validation
↓
trusted graph
```

Mismatch MUST fail closed.

No best-effort remapping is permitted.

## 7. Tensor Metadata

P1 must extract:

* tensor name;
* tensor shape;
* tensor dtype.

This information must remain available for downstream processing.

## 8. Quantization

Exactly:

```text
INT8 / FP8 → is_quantized = TRUE
otherwise  → is_quantized = FALSE
```

No additional quantization categories may be invented.

## 9. Domain

`input_domain` is determined from input shape/type characteristics.

Frozen supported paths:

```text
VISION → 4D float tensors
NLP    → 2D/3D integer token tensors
```

Unknown/unsupported characteristics MUST be surfaced.

The agent MUST NOT silently guess a domain from architecture name, filename, metadata, or convenience.

## 10. Handoff

Phase 3 receives the trusted graph and P1 metadata.

D2 remains unresolved for the exact P1 → P2 trusted-graph handoff.

The agent MUST NOT invent D2.

If P2 integration requires D2 before the phase's authorized work can proceed:

**BLOCKED.**

## 11. Branch

```text
phase/02-zero-trust-intake
```

Optional owner-qualified branch:

```text
phase/02-zero-trust-intake-p1
```

Branch MUST start from the approved CP1 state.

## 12. Waiting Rule

The Phase 2 agent waits when:

* CP1 is not PASS;
* required dependency installation is not approved/pinned;
* a required security/resource limit is unresolved;
* required architecture compatibility information is unavailable.

It MUST NOT work around these by inventing assumptions.

## 13. Commit / Merge

Implementation → verification evidence → commit → PR.

No self-merge.

Phase 3 starts from the merged/approved Phase 2 state after CP2 PASS.

---

# FILE: .planning/phases/02-zero-trust-intake/VERIFICATION.md

# Phase 02 — Zero-Trust Intake — VERIFICATION

**Gate:** CP2 — Intake Gate
**Owner:** P1
**Primary file:** `src/p1_static_engine/analyzer.py`

## 1. Gate Semantics

Only:

```text
PASS / FAIL / BLOCKED
```

A required unresolved dependency or decision means:

```text
BLOCKED
```

A checkbox without reproducible evidence cannot be PASS.

## 2. Evidence Requirement

Every PASS item records:

```text
test/command
result
artifact/path
code location
commit
```

## 3. SafeTensors Security

* [ ] `safetensors.safe_open` is used.
* [ ] No alternate loader was introduced.
* [ ] Header parsing is bounded.
* [ ] No pickle loading exists.
* [ ] No uploader-supplied code executes.
* [ ] No generic deserialization path exists.

## 4. Resource Exhaustion

Mandatory adversarial tests:

* [ ] oversized header;
* [ ] malformed header;
* [ ] excessive tensor count;
* [ ] pathological tensor dimensions;
* [ ] malformed metadata;
* [ ] invalid tensor offsets;
* [ ] invalid shape;
* [ ] invalid dtype;
* [ ] resource-limit violation.

Each must fail safely rather than trigger uncontrolled resource use.

## 5. Architecture Trust

* [ ] Declared architecture is required.
* [ ] Unknown architecture fails closed.
* [ ] Arbitrary architecture inference is absent.
* [ ] Trusted architecture comes only from approved definitions.
* [ ] Tensor names/shapes/dtypes are checked for compatibility.
* [ ] Architecture/weight mismatch fails closed.
* [ ] No best-effort mapping silently occurs.

## 6. Metadata

* [ ] Tensor names are extracted correctly.
* [ ] Shapes are extracted correctly.
* [ ] Dtypes are extracted correctly.
* [ ] `is_quantized` follows the frozen rule.
* [ ] `input_domain` follows the frozen shape/type rule.
* [ ] Missing/malformed metadata produces an explicit failure.

## 7. Downstream Handoff

* [ ] Phase 3 receives the actual trusted graph.
* [ ] Actual `input_domain` is handed off.
* [ ] Actual `is_quantized` is handed off.
* [ ] No mock/default metadata leaks into a real run.
* [ ] D2 is not silently resolved.

If D2 is required for the current acceptance criteria and unresolved:

**CP2 = BLOCKED.**

## 8. Security Regression

Mandatory:

* [ ] executable-content smuggling test;
* [ ] pickle-path absence test;
* [ ] unknown-architecture test;
* [ ] architecture/tensor mismatch test;
* [ ] malformed SafeTensors test.

## 9. Scope

* [ ] Only authorized files changed.
* [ ] Master Graph unchanged.
* [ ] No P2/P3 ownership crossed.
* [ ] No unauthorized dependency/network change.

## 10. Gate

```text
all required checks + evidence → PASS
executed failure → FAIL
required unresolved decision/dependency/evidence → BLOCKED
```

Only CP2 PASS authorizes Phase 3.
