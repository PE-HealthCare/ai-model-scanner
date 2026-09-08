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

### D2 — Trusted Graph Handoff

**Status: RESOLVED / LOCKED.**

P1 SHALL construct the trusted, weight-loaded model as part of the zero-trust intake boundary and make that trusted model and the required trusted metadata available to `scan_model.py`.

`scan_model.py` SHALL hand the already-created trusted model/context to P2 by in-process Python object reference during the same pipeline execution.

The D2 handoff SHALL NOT:

- serialize or persist the trusted model for downstream loading;
- independently reload the model in P2;
- provide the original untrusted model artifact as P2's loading source;
- create an alternative architecture in P2.

P2 SHALL consume the received trusted model for bounded, inference-only behavioral analysis. P2's inference-only contract prohibits training, gradient/backward execution, optimizer use, weight modification, or independent model loading.

The handoff SHALL carry the trusted metadata required by P2, including:

- `input_domain` (`VISION` or `NLP`);
- `is_quantized` (`true` or `false`).

The exact Python class, function names, type annotations, and module location used to represent this handoff are implementation details and are NOT fixed by D2.

D2 does not change the artifact contracts (`features.json`, `ml_results.json`, or `risk_results.json`) because the trusted-model handoff is an in-process runtime mechanism rather than a JSON artifact.

D2 does not resolve D3, D4, D5, or D6.

**Implementation / verification status:** The D2 architectural decision is locked, but its implementation and verification evidence remain pending. `RESOLVED / LOCKED` here does not mean the real P1→P2 handoff has been implemented, tested, or accepted at CP2.

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

This is the pinned SHAP dependency for TreeSHAP attribution.

#### D9.10 — jsonschema
**Status: LOCKED.** `jsonschema==4.22.0`.

This is the pinned JSON Schema validation dependency for the project contracts.

#### D9.11 — Installation Source Policy
**Status: LOCKED.**

The authoritative installation sources are:

- Standard Python runtime dependencies: **PyPI**.
- `torch` / `torchvision` CPU wheels: **official PyTorch CPU wheel index** (`https://download.pytorch.org/whl/cpu`).
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

No `>=`, `~=`, caret/wildcard, or unpinned version specification is authoritative for these direct runtime dependencies.

D9.12 does **not** silently resolve transitive dependency versions. Transitive reproducibility remains a separate D9 decision and must be explicitly locked before claiming a fully reproducible environment.

#### D9.13 — Transitive Dependency Lockfile
**Status: LOCKED.**

The authoritative environment must capture **all direct and transitive runtime dependencies** in a fully pinned reproducibility artifact. The lock artifact must not rely on resolver-selected floating transitive versions at authoritative verification time.

The lock artifact may be generated from a successfully resolved authoritative Python 3.11 CPU environment; it must record the exact versions required for that environment rather than manually inventing transitive versions. pip documents that a fully pinned requirements file can capture top-level and transitive dependencies for repeatable installs.

The lock artifact is a reproducibility record, not permission to change any already locked direct dependency version.

#### D9.14 — Package Hash Integrity
**Status: LOCKED.**

The authoritative reproducibility artifact must include cryptographic hashes for installable package artifacts and authoritative installation must enforce hash checking.

The artifact must account for platform-specific package artifacts where applicable; one hash must not be falsely represented as universal when different wheels are authoritative for different supported environments.

D9.14 does not permit unpinned requirements, arbitrary package sources, or silent package substitution.

#### D9.15 — Authoritative Lock Artifact Format
**Status: LOCKED.**

The authoritative dependency reproducibility artifact shall be a **generated, fully pinned requirements lock artifact** (requirements-file format), rather than relying on experimental `pylock.toml` support.

Rules:

- Generate it from a successfully resolved authoritative Python 3.11 CPU environment.
- Include exact versions for all direct and transitive runtime dependencies.
- Include the required cryptographic hashes for installable artifacts.
- Preserve the already locked direct dependency versions; generation must not silently alter them.
- Do not manually invent transitive versions or hashes.
- The artifact is authoritative for reproducible installation/verification; ordinary unpinned `requirements.txt` content is not sufficient by itself.
- Because package artifacts can vary by platform, the lock artifact must represent each authoritative supported platform/artifact set explicitly rather than falsely treating a platform-specific hash as universal.

#### D9.16 — Authoritative Environment Verification
**Status: LOCKED.**

Before CP2 and before any authoritative PASS/REVIEW/FAIL result, the environment must be verified against the dependency contract.

Verification must confirm:

- Python is **3.11.x**.
- All D9.3–D9.10 direct dependency pins are installed exactly as locked.
- Every transitive dependency required by the authoritative lock artifact is present at its locked version.
- Required package hashes are enforced by the authoritative installation procedure.
- Execution is CPU-only for the authoritative pipeline; GPU/CUDA availability must not be treated as a requirement or substituted into the authoritative result.

Any mismatch, missing package, version drift, unresolved lock entry, hash-integrity failure, or unsupported environment condition results in **BLOCKED** verification. The verifier must not auto-upgrade, auto-downgrade, or silently repair the environment and then claim the original environment was verified.

#### D9.17 — Authoritative Platform Scope
**Status: LOCKED.**

The authoritative reproducibility scope is:

- **Windows x86-64**
- **Linux x86-64**
- **Python 3.11.x**
- **CPU-only** execution

Platform-specific wheels and hashes must be represented explicitly for each supported platform/artifact set. A platform-specific hash must not be treated as universal. Any unsupported platform, architecture, Python major/minor version, or non-CPU execution target is **BLOCKED** for authoritative verification.

#### D9.18 — Authoritative Dependency Installation Procedure
**Status: LOCKED.**

The authoritative installation procedure is a clean-environment, verification-first process:

1. Create a clean Python **3.11.x** environment.
2. Install from the generated authoritative hashed requirements lock artifact.
3. Use PyPI for standard runtime dependencies and the official PyTorch CPU wheel index for `torch` / `torchvision`, consistent with D9.11.
4. Enforce pip hash checking with `--require-hashes`; installation must not proceed with missing or mismatched hashes.
5. Do not silently resolve, upgrade, downgrade, or substitute dependencies outside the authoritative lock artifact.
6. Complete D9.16 environment verification after installation.
7. Any installation or verification mismatch results in **BLOCKED**; the environment must be corrected and re-verified rather than treating an altered environment as the originally verified environment.

#### D9.19 — Dependency Change Control
**Status: LOCKED.**

Locked dependency policy is immutable by implementation convenience. Any change to a direct or transitive dependency version, installation source, hash, or authoritative supported-platform artifact set requires an explicit new dependency decision.

A dependency-contract change invalidates the affected reproducibility artifact until the artifact is regenerated from a successfully resolved authoritative environment and the environment verification procedure passes again. No dependency change may be introduced silently through resolver drift, opportunistic upgrades/downgrades, or source substitution.

#### D9.20 — Dependency Completion Criterion
**Status: LOCKED.**

D9 may be marked fully **RESOLVED** only after both policy and implementation evidence exist:

1. all required D9 sub-decisions are explicitly locked;
2. authoritative platform lock artifacts actually exist;
3. direct and transitive versions are fully pinned;
4. required artifact hashes are populated and enforced;
5. the authoritative installation procedure is implemented/documented;
6. D9.16 environment verification passes on the authoritative environment(s).

Until these implementation and verification conditions are satisfied, D9 remains **REQUIRED / PARTIALLY RESOLVED** and must not be represented as fully complete merely because the policy decisions are locked.

#### D9.21 and later — NOT YET RESOLVED

Any remaining dependency-policy details remain **REQUIRED** until explicitly agreed. No implementation choice may silently resolve a remaining D9 sub-decision.

## Intentionally Unresolved Decisions

| Decision | Status |
|---|---|
| D3 — STRIP baseline | REQUIRED |
| D4 — Behavioral normalization | REQUIRED |
| D5 — Risk aggregation | REQUIRED |
| D6 — Highest-risk-layer aggregation | REQUIRED |

D3–D6 are not resolved by any implementation branch, placeholder, or prior agent choice. D2 is resolved as a persistent project decision above; its implementation remains subject to Phase 2/CP2 verification.

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

with P1 zero-trust intake → static steganalysis → `features.json` → P3 LightGBM + TreeSHAP → `ml_results.json` → P2 STRIP + risk aggregation → `risk_results.json` → P3 security report.

Quantized models bypass behavioral probing under the finalized format-adaptive design. TreeSHAP attribution and highest-risk-layer determination remain separate mechanisms.

## Next Permitted Action

Phase 1 is complete with CP1 PASS. Phase 2 is the current permitted implementation phase. D2 is RESOLVED as a project decision, while D3–D6 remain REQUIRED. D9 remains partially resolved; D9.1–D9.20 are LOCKED, while D9.21+ remain REQUIRED. Continue Phase 2 only within the approved D2 handoff boundary and existing Phase 2 plan/verification; do not implement D3–D6 or silently resolve remaining D9 details.

**Current D9 frontier: D9.21 — remaining dependency-policy details.**

## Final Rule

> **When the required information is unavailable, the correct action is BLOCKED — not invention.**
