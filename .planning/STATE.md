# AI Model Scanner — Execution State

**Project Status:** FROZEN FOR EXECUTION  
**Architecture Status:** FROZEN  
**Current Phase:** Phase 2 — Zero-Trust Intake  
**Current Checkpoint:** CP1 — COMPLETE  
**Current Gate Status:** PASS — CP1 VERIFIED  
**Last Verified Phase:** Phase 1 — Mock Pipeline  
**Next Permitted Phase:** Phase 2 — Zero-Trust Intake

---

## Authority

The Final Master Discovery & Dependency Graph is the authoritative architecture source.

This state file records execution status only. It SHALL NOT redefine the architecture or silently resolve design decisions.

The explicit project decisions recorded below are persistent execution decisions already agreed by the project team. They do not by themselves constitute implementation verification or checkpoint PASS.

---

## Persistent Locked Decisions

### D1 — Exact Static Feature Contract

**Status: RESOLVED.**

The authoritative FP32/FP16 static feature set and order are:

1. `entropy`
2. `pov_chi2`
3. `lsb_kl`
4. `ks_stat`
5. `mean`
6. `std`
7. `skewness`
8. `kurtosis`
9. `sparsity`
10. `outlier_pct`

The previous six-feature executable schema is not authoritative. Implementations, downstream contracts, feature ordering, feature semantics, and TreeSHAP mapping must follow the frozen Master Graph definitions exactly.

### Decision 1 — Trusted Architecture Registry

**Status: RESOLVED / LOCKED.**

The trusted architecture registry is intentionally limited to:

| Declared architecture | Domain | Trusted implementation |
|---|---|---|
| `resnet18` | VISION | `torchvision.models` |
| `distilbert` | NLP | `transformers` |

Rules:

- The uploader declares the architecture.
- No automatic architecture detection.
- No uploader-supplied `model.py` or custom executable architecture.
- Unsupported architecture fails closed.
- Malformed or incompatible tensor names/shapes/dtypes fail closed.
- No best-effort graph construction, silent omission, shape correction, or fallback.

### Decision 2 — Zero-Trust Intake Resource Limits

**Status: RESOLVED / LOCKED.**

Hard fail-closed production limits:

| Resource | Hard limit |
|---|---:|
| SafeTensors header | 100 MB |
| Metadata | 1 MB |
| Tensor count | 10,000 |
| Maximum tensor rank | 8 |
| Maximum dimension | 1,000,000 |
| Model file size | 2 GB |

Operational targets (not hard security walls):

- Intake memory target: `<50 MB`
- Intake processing-time target: `<0.5 sec`

When a hard limit is exceeded, intake fails closed and reports the exact exceeded limit. No per-tensor quota heuristics, no configuration-file override, and no limit-tuning CLI flag are part of this decision.

The 100 MB header value is the locked project limit; it is not merely the illustrative `e.g. 100MB` wording in the original pipeline document.

### D7 — MAD Degenerate Baseline Guard

**Status: RESOLVED.**

- Finite nonzero MAD: use actual MAD directly; no epsilon.
- Exact MAD = 0 and target equals median: deterministic zero anomaly.
- Exact MAD = 0 and target differs from median: `DEGENERATE_DEVIATION`.
- 1–2 comparable layers: baseline evidence unavailable; block downstream scoring requiring it.
- Missing/NaN/+/-inf numeric data: invalid; no imputation.
- Very small nonzero MAD: use actual value.
- Quantized behavior retains the finalized format-adaptive rules; no new semantics are invented here.

### D8 — Artifact Staleness Protection

**Status: RESOLVED.**

Downstream stages consume outputs from the current pipeline execution only. `generation_commit` provides artifact provenance/generation identity. A stale/mismatched artifact must be rejected or blocked rather than silently reused.

### D9 — Dependency Pinning

**Status: REQUIRED — PARTIALLY RESOLVED.**

D9 is being resolved as explicit sub-decisions. Only the sub-decisions listed as LOCKED below are settled. Remaining D9 sub-decisions remain REQUIRED and must not be inferred from this file.

#### D9.1 — Python baseline
**Status: LOCKED.** Python **3.11.x**.

#### D9.2 — Execution hardware
**Status: LOCKED.** **CPU-only** is the authoritative execution environment; GPU/CUDA is not required for the authoritative pipeline or PASS/REVIEW/FAIL result.

#### D9.3 — PyTorch stack
**Status: LOCKED.** `torch==2.3.1`, `torchvision==0.18.1`.

#### D9.4 — Transformers
**Status: LOCKED.** `transformers==4.41.2`.

#### D9.5 — SafeTensors
**Status: LOCKED.** `safetensors==0.4.3`.

This is the pinned SafeTensors dependency for the security-critical P1 zero-trust intake boundary.

#### D9.6 — NumPy
**Status: LOCKED.** `numpy==1.26.4`.

This is the pinned NumPy dependency for the Python 3.11 / PyTorch 2.3.1 compatibility baseline.

#### D9.7 — SciPy
**Status: LOCKED.** `scipy==1.13.1`.

This is the pinned SciPy dependency for the Python 3.11 / NumPy 1.26.4 numerical baseline.

#### D9.8 — LightGBM
**Status: LOCKED.** `lightgbm==4.3.0`.

This is the pinned LightGBM dependency for the P3 classifier.

#### D9.9 — SHAP
**Status: LOCKED.** `shap==0.45.1`.

This is the pinned SHAP dependency for TreeSHAP attribution. SHAP 0.45.1 is a production/stable release and provides CPython 3.11 wheels. citeturn0search0

#### D9.10 — jsonschema
**Status: LOCKED.** `jsonschema==4.22.0`.

This is the pinned JSON Schema validation dependency for the project contracts.

#### D9.11 — Installation Source Policy
**Status: LOCKED.**

The authoritative installation sources are:

- Standard Python runtime dependencies: **PyPI**.
- `torch` / `torchvision` CPU wheels: **official PyTorch CPU wheel index** (`https://download.pytorch.org/whl/cpu`). The official PyTorch installation documentation publishes the exact `torch==2.3.1` / `torchvision==0.18.1` CPU installation path, and the CPU index contains Python 3.11 wheels. citeturn0search0turn0search8turn0search1
- No Git/VCS URLs, arbitrary package repositories, local unpublished package sources, or unpinned `latest` installation choices are authoritative.

The installation-source policy is a reproducibility/security requirement. It does not by itself pin transitive dependencies; those require the later lockfile/hash policy decision.

#### D9.12 — Exact Direct Runtime Dependency Pins
**Status: LOCKED.**

Every **direct runtime dependency** selected for the authoritative environment must use an exact `==` version pin. The currently locked direct runtime set is:

```text
torch==2.3.1
torchvision==0.18.1
transformers==4.41.2
safetensors==0.4.3
numpy==1.26.4
scipy==1.13.1
lightgbm==4.3.0
shap==0.45.1
jsonschema==4.22.0
```

No `>=`, `~=`, caret/wildcard, or unpinned version specification is authoritative for these direct runtime dependencies. pip documents `==` as the exact-version pinning form and notes that fully pinned requirements can be used for repeatable installs. citeturn0search9turn0search11

D9.12 does **not** silently resolve transitive dependency versions. Transitive reproducibility remains a separate D9 decision and must be explicitly locked before claiming a fully reproducible environment.

#### D9.13 and later — NOT YET RESOLVED

Dependency hashes/lockfile policy, transitive dependency pinning, and any other remaining dependency-policy details remain **REQUIRED** until explicitly agreed.

No implementation choice may silently resolve a remaining D9 sub-decision.

---

## Intentionally Unresolved Decisions

| Decision | Status |
|---|---|
| D2 — Trusted graph handoff | REQUIRED |
| D3 — STRIP baseline | REQUIRED |
| D4 — Behavioral normalization | REQUIRED |
| D5 — Risk aggregation | REQUIRED |
| D6 — Highest-risk-layer aggregation | REQUIRED |

D2–D6 are not resolved by any implementation branch, placeholder, or prior agent choice.

---

## Phase Status

| Phase | Status | Gate |
|---|---|---|
| Phase 1 — Mock Pipeline | COMPLETE | CP1 |
| Phase 2 — Zero-Trust Intake | IN PROGRESS | CP2 |
| Phase 3 — Static Steganalysis | NOT STARTED | CP3 |
| Phase 4 — ML Classification | NOT STARTED | CP4 |
| Phase 5 — Behavioral + Risk | NOT STARTED | CP5 |
| Phase 6 — Integration + Demo | NOT STARTED | CP6 |

## Checkpoint Status

| Checkpoint | Status |
|---|---|
| CP1 — Mock Gate | PASS |
| CP2 — Intake Gate | NOT REACHED |
| CP3 — Static Gate | NOT REACHED |
| CP4 — ML Gate | NOT REACHED |
| CP5 — Behavioral/Risk Gate | NOT REACHED |
| CP6 — Demo Gate | NOT REACHED |

Only a `PASS` checkpoint permits advancement.

## Verified Implementation Status

- Real P1 zero-trust intake: **not verified**
- Real P1 static feature extractor: **not verified**
- Real P3 classifier: **not verified**
- Real P2 risk engine: **not verified**
- Final integration: **not verified**

Locked decisions are requirements for implementation; they are not evidence that implementation exists.

## Current Dependency Chain

```text
D1 RESOLVED
 ↓
CP1 PASS
 ↓
P1 Zero-Trust Intake
 ↓
CP2 PASS
 ↓
P1 Real Static Features
 ↓
CP3 PASS
 ↓
P3 Final ML Training
 ↓
CP4 PASS
 ↓
P2 Behavioral + Risk
 ↓
CP5 PASS
 ↓
Phase 6 Integration
 ↓
CP6 PASS
```

## Hard-Stop Conditions

The agent MUST stop dependent work when any of the following applies:

1. A required decision remains unresolved.
2. A required upstream checkpoint is not `PASS`.
3. A required contract is undefined.
4. Feature semantics required for downstream work are not verified.
5. A dependency is unavailable or unverified.
6. Verification criteria cannot legitimately be evaluated.
7. Implementation would require inventing a schema, formula, threshold, normalization, baseline, aggregation, dependency, or feature meaning.
8. A proposed change would redesign the frozen architecture without an explicit reopening decision.
9. Ownership is unclear.
10. Mock/scaffold behavior would be represented as real implementation.

## Execution Rules

When not blocked, the agent SHALL:

1. inspect current repository state;
2. identify applicable phase;
3. read that phase's `PLAN.md`;
4. read that phase's `VERIFICATION.md`;
5. confirm upstream gates;
6. implement only within permitted scope;
7. preserve subsystem ownership;
8. run applicable verification;
9. record resulting gate status;
10. update this state only with verified facts.

## State Update Rules

This file SHALL describe actual verified state, not intended state.

Do not mark code implemented when scaffolded, outputs produced when mocks, phases complete before verification, decisions resolved because an agent selected an implementation, or dependencies verified merely because they appear in a file.

## Architecture Integrity

The architecture remains frozen:

```text
P1 → P3 → P2 → P3
```

with P1 zero-trust intake → static steganalysis → `features.json` → P3 LightGBM + TreeSHAP → `ml_results.json` → P2 STRIP + risk aggregation → `risk_results.json` → P3 security report/dashboard.

Quantized models bypass behavioral probing under the finalized format-adaptive design. TreeSHAP attribution and highest-risk-layer determination remain separate mechanisms.

## Next Permitted Action

Phase 1 is complete with CP1 PASS. Phase 2 is the current permitted implementation phase. D2–D6 remain REQUIRED. D9 is partially resolved; continue only with the next explicitly proposed D9 sub-decisions and obtain explicit agreement before recording them as LOCKED.

**Current D9 frontier: D9.13 — dependency hashes/lockfile policy and transitive dependency pinning.**

## Final Rule

> **When the required information is unavailable, the correct action is BLOCKED — not invention.**
