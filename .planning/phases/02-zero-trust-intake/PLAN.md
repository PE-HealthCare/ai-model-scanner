# Phase 2 — Zero-Trust Intake

## Status

**Owner:** P1 — Eyes  
**Checkpoint:** CP2  
**Prerequisite:** CP1 = PASS  
**Branch:** `phase-2/zero-trust-intake`

Phase 2 implements the real zero-trust model intake boundary. It must consume only the approved Phase 1 contract state and must fail closed on untrusted or structurally inconsistent input.

## 1. Agent Execution Control

Before changing code, the agent MUST:

1. Verify CP1 is explicitly PASS.
2. Inspect the current merged Phase-1 state.
3. Confirm no required Phase-2 decision/dependency is unresolved.
4. Create/use `phase-2/zero-trust-intake`.
5. Modify only authorized Phase-2 files.
6. Record evidence for every verification criterion.

If CP1 is not PASS, Phase 2 is **BLOCKED**. The agent may inspect code and prepare non-authoritative design notes, but must not implement real intake against an unapproved contract.

## 2. Ownership and File Scope

### Allowed

- `src/p1_static_engine/analyzer.py`
- Phase-2-specific tests under `tests/...`
- Phase-2-approved configuration/test fixtures only

### Forbidden

- `src/p2_behavioral_risk/...`
- `src/p3_ml_dashboard/...`
- `scan_model.py`
- `.planning/...`
- `PROJECT.md`
- `ROADMAP.md`
- `REQUIREMENTS.md`
- `STATE.md`
- `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

Shared `src/common/utils.py` is cross-boundary. Changes require explicit authorization, impact analysis, affected-owner notification, and reverification.

## 3. Dependency / Wait Rules

Phase 2 requires:

- CP1 PASS;
- approved contract fields;
- required dependencies available under approved/pinned policy.

The agent MUST WAIT/BLOCK if any required prerequisite is missing.

D1 is RESOLVED/LOCKED. D2 is RESOLVED/LOCKED at the architectural level, but its real implementation and verification evidence are COMPLETE and were demonstrated and accepted at CP2. D9.1–D9.20 are locked; remaining D9.21+ details remain required. The agent MUST NOT silently resolve any remaining D9 item.

## 4. Security Boundary

The implementation SHALL use `safetensors.safe_open` for SafeTensors access unless the team explicitly reopens the architecture.

No agent may introduce an alternative loader under the label "equivalent."

The intake boundary MUST NOT:

- execute uploader-supplied `model.py`;
- execute arbitrary model code;
- use unrestricted pickle loading;
- import uploader-controlled modules;
- deserialize untrusted executable objects;
- make unauthorized external network requests.

## 5. Resource-Boundary Rule

SafeTensors processing MUST enforce approved finite resource limits covering, as applicable:

- maximum header bytes;
- maximum tensor count;
- maximum metadata size;
- maximum tensor dimensions;
- maximum model/file size;
- maximum memory/resource use;
- maximum processing time.

The authoritative hard production limits are:

| Resource | Hard limit |
|---|---:|
| SafeTensors header | **5 MB** |
| Metadata | 1 MB |
| Tensor count | 10,000 |
| Maximum tensor rank | 8 |
| Maximum dimension | 1,000,000 |
| Model file size | 2 GB |

Operational targets remain:

- Intake memory target: `<50 MB`
- Intake processing-time target: `<0.5 sec`

The 5 MB SafeTensors header limit is the explicitly locked resolution to the previously identified conflict between the 100 MB header boundary, the `<50 MB` operational memory target, and the mandatory native `safetensors.safe_open()` parser. It is a hard production security limit, not an illustrative test value.

When a hard limit is exceeded, intake fails closed and reports the exact exceeded limit. No per-tensor quota heuristics, no configuration-file override, and no limit-tuning CLI flag are part of this decision.

A test may use a fixture-specific bound only when that bound is explicitly identified as a test fixture limit and not represented as the production policy.

## 6. Architecture Trust

The uploader's declared architecture is only an input claim.

The implementation MUST validate:

```text
declared architecture
+
actual SafeTensors tensor names/shapes/dtypes
+
trusted architecture definition
        ↓
compatibility validation
        ↓
trusted graph
```

Unknown architecture, malformed structure, or architecture/tensor mismatch MUST fail closed.

Best-effort mapping, silent tensor omission, silent shape correction, or fallback architecture selection is forbidden.

## 7. Domain and Quantization

The implementation must preserve the Master Graph semantics:

- `input_domain` is determined from model input shape/type characteristics;
- VISION uses 4D float input characteristics;
- NLP uses 2D/3D integer token input characteristics;
- `is_quantized = TRUE` for INT8/FP8;
- otherwise `is_quantized = FALSE`.

Do not silently redefine these semantics.

## 8. Mock / Real Lifecycle

Phase 2 may use fixtures for security tests, but test fixtures are not authoritative model artifacts.

Required lifecycle:

```text
fixture/mock
→ security test only
→ real SafeTensors intake
→ verification
→ VERIFIED-REAL intake
```

Production execution MUST NOT identify a test fixture as a verified real model.

## 9. Required Outputs / Handoff

A successful intake must make available the trusted graph and approved metadata required by Phase 3 and downstream consumers.

The trusted graph MUST NOT be independently reloaded unsafely by downstream phases.

D2 is now the locked architectural handoff: P1 constructs the trusted, weight-loaded model; `scan_model.py` passes the already-created trusted model/context to P2 by in-process Python object reference during the same pipeline execution. No downstream serialization/reload or alternative model construction is permitted. The exact Python representation remains an implementation detail. Real implementation and verification evidence are COMPLETE; CP2 PASS was independently reviewed and accepted.

## 10. Failure Behavior

Any intake failure MUST:

- identify the failure;
- stop dependent processing;
- return a failure/non-success status;
- produce no authoritative downstream artifact.

No best-effort architecture mapping or fabricated metadata is permitted.

## 11. Commit / PR / Merge

Commit only authorized Phase-2 changes.

Before commit:

- inspect `git status`;
- inspect `git diff`;
- run required tests;
- record evidence.

Open a PR only after Phase-2 verification evidence is complete.

The implementing agent MUST NOT merge its own PR.

Merge requires:

- Phase 2 verification = PASS;
- required evidence recorded;
- no unresolved required blocker;
- required independent/human review;
- CP2 approval.

## 12. Exact CP2 Gate

CP2 = PASS only when all required intake/security criteria are evidenced and PASS.

CP2 = BLOCKED when a required decision, dependency, approved resource limit, contract, or security prerequisite is unresolved.

CP2 = FAIL when implemented behavior violates the approved requirement.

Only **CP2 = PASS** permits Phase 3 real static implementation.
