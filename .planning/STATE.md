# AI Model Scanner — Execution State

**Project Status:** FROZEN FOR EXECUTION
**Architecture Status:** FROZEN  
**Current Phase:** Phase 6 — Integration + Demo   
**Current Checkpoint:** CP6 — VERIFICATION IN PROGRESS   
**Current Gate Status:** CP5 PASS; CP6 NOT YET VERIFIED   
**Last Verified Phase:** Phase 5 — Behavioral + Risk   
**Next Permitted Phase:** Phase 6 — Integration + Demo  


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

D2 defines the handoff scope; it does not by itself determine D3, D4, D5, or D6 status (for current D3–D6 status see `## Checkpoint Status` and VERIFICATION.md §10).

**Implementation / verification status:** D2 implementation and verification evidence are COMPLETE.
D2 was implemented, tested, independently reviewed, accepted at CP2, and integrated into main.

**Status: RESOLVED / LOCKED — METHODOLOGY LOCKED; CP5 CODE-RUNTIME EVIDENCE COMPLETE (replayed calibration, verified). VERIFIED-REAL production validation remains out of scope.**

> Historical note (superseded): this decision was previously recorded as
> "METHODOLOGY ONLY; EMPIRICAL CALIBRATION PENDING" before the CP5 code-runtime
> evidence pass. That pending status is retained below for history and is
> superseded by the CP5 evidence status recorded in `## Checkpoint Status` and
> `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10.

For non-quantized models, behavioral probing SHALL compute Shannon entropy over the model's softmax output probability distribution for the existing 32 domain-appropriate probes.

The STRIP baseline SHALL be empirical and domain-specific. Separate `VISION` and `NLP` baseline distributions SHALL be established from a fixed, scanner-controlled set of clean reference models for the corresponding domain.

The reference models and resulting calibration evidence SHALL be explicitly recorded before D3 is considered fully evidenced for authoritative behavioral scoring.

The baseline SHALL NOT be derived from the uploaded model itself, and no arbitrary universal numeric entropy threshold may be introduced without corresponding calibration evidence.

D3 defines the entropy measurement and baseline methodology only (scope definition, not a status claim). The conversion of baseline deviation into `S_behavior ∈ [0,1]` is governed by D4 (for current D4 status see `## Checkpoint Status` and VERIFICATION.md §10).

Quantized models do not use the behavioral baseline because behavioral probing is skipped under the finalized quantized path.

**Implementation / empirical-evidence status (historical planning text, superseded for CP5 code-runtime scope):** The D3 methodology was locked, but calibration execution, measured baseline distributions, and supporting evidence were recorded as pending. Agents were told they MUST NOT invent baseline values. After the approved calibration run completes, the agent was told it MUST return to this D3 section, record the measured evidence and any evidence-dependent parameters, and re-verify downstream consistency before treating D3 as fully evidenced.

**CP5 code-runtime evidence status (current, authoritative):** For the CP5 code-runtime PASS scope, D3 is represented by the committed calibration artifact `data/calibration/calibration_data.json` and verified replay: VISION ResNet18 30 recorded observations (median `5.085757341909422`, MAD `0.026241989955190892`); NLP DistilBERT 30 recorded observations (median `6.881156798617935`, MAD `0.0007370728479614286`); replayed via `compute_statistics` with `new_measurement_performed=false`; `python scripts/finalize_calibration_artifact.py --check` → exit code 0. No values were invented. No fresh STRIP measurement was performed, no VERIFIED-REAL production validation was exercised, and no production authorization is claimed; see `## Checkpoint Status` and `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10.

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
| SafeTensors header | **5 MB** |
| Metadata | 1 MB |
| Tensor count | 10,000 |
| Maximum tensor rank | 8 |
| Maximum dimension | 1,000,000 |
| Model file size | 2 GB |

Operational targets (not hard security walls):

- Intake memory target: `<50 MB`
- Intake processing-time target: `<0.5 sec`

The SafeTensors header limit is **5 MB** and is the locked project boundary. This explicitly supersedes the previous 100 MB header value and resolves the identified conflict between the header boundary, the `<50 MB` operational memory target, and mandatory native `safetensors.safe_open()` parsing. The 5 MB value is a hard production security limit, not an illustrative value.

When a hard limit is exceeded, intake fails closed and reports the exact exceeded limit. No per-tensor quota heuristics, no configuration-file override, and no limit-tuning CLI flag are part of this decision.

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

## Historical Planning State — Intentionally Unresolved Decisions (SUPERSEDED for CP5 code-runtime scope)

> Historical record: before the CP5 code-runtime evidence pass, the project
> recorded the following decision states. This table is preserved for history.
> It is SUPERSEDED by the current CP5 status in `## Checkpoint Status` and
> `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10. Do not read
> this historical table as the current status.

| Decision | Historical status (superseded) | Current CP5 code-runtime status |
|---|---|---|
| D4 — Behavioral normalization | REQUIRED (historical) | Implemented and tested — CP5 code-runtime PASS |
| D5 — Risk aggregation | REQUIRED (historical) | Implemented — CP5 code-runtime PASS |
| D6 — Highest-risk-layer aggregation | REQUIRED (historical) | Implemented — CP5 code-runtime PASS |

D4–D6 were recorded as not resolved by any implementation branch, placeholder, or prior agent choice. D2 is resolved as a persistent project decision above; its implementation and verification are COMPLETE with CP2 PASS. D3 was recorded as methodologically resolved with empirical calibration/evidence pending and subject to a must-not-invent rule; for the CP5 code-runtime PASS scope, D3 is now represented by the committed calibration artifact plus verified replay (`new_measurement_performed=false`, check exit code 0), with no values invented and no VERIFIED-REAL production validation claimed.

## Phase Status

| Phase | Status | Gate |
|---|---|---|
| Phase 1 — Mock Pipeline | COMPLETE | CP1 |
| Phase 2 — Zero-Trust Intake | COMPLETE | CP2 |
| Phase 3 — Static Steganalysis | COMPLETE | CP3 |
| Phase 4 — ML Classification | COMPLETE | CP4 |
| Phase 5 — Behavioral + Risk | COMPLETE | CP5 |
| Phase 6 — Integration + Demo | NOT STARTED | CP6 |

## Checkpoint Status

| Checkpoint | Status |
|---|---|
| CP1 — Mock Gate | PASS |
| CP2 — Intake Gate | PASS |
| CP3 — Static Gate | PASS |
| CP4 — ML Gate | PASS |
| CP5 — Behavioral/Risk Gate | PASS — CODE + RUNTIME EVIDENCE VERIFIED (person2 @ 4849706f5eaad16cca5d54933fff75e6431ee41a; see `.planning/phases/05-behavioral-probing/VERIFICATION.md` §10). This is NOT VERIFIED-REAL production authorization. |
| CP6 — Demo Gate | NOT REACHED |

Only a `PASS` checkpoint permits advancement.

CP5 evidence summary (documentation sync only; no new measurement; NOT VERIFIED-REAL production authorization):
- D3 calibration evidence/methodology: committed calibration artifact `data/calibration/calibration_data.json` + verified replay (`python scripts/finalize_calibration_artifact.py --check` → exit code 0).
- D4 normalization / behavioral score: implemented and tested.
- D5 static risk aggregation: implemented.
- D6 highest-risk-layer selection: implemented.
- D7 MAD Z-score logic: implemented and tested.
- MRS/verdict logic: implemented and tested.
- D8 generation-commit enforcement: implemented and tested.
- Still OUTSIDE CP5 code-runtime PASS scope: VERIFIED-REAL production validation; fresh real-model STRIP measurement; authoritative production artifact generation using real upstream P1/P3 inputs.
- VISION: ResNet18, 30 obs, median `5.085757341909422`, MAD `0.026241989955190892`; replayed via `compute_statistics`, `new_measurement_performed=false`.
- NLP: DistilBERT, 30 obs, median `6.881156798617935`, MAD `0.0007370728479614286`; replayed via `compute_statistics`, `new_measurement_performed=false`.
- VISION non-quant E2E (`mock_mode=True`): `s_behavior=0.0`, `mrs_score=47.18`, `REVIEW` — PASS, schema-valid.
- NLP non-quant E2E (`mock_mode=True`): `s_behavior=1.0`, `mrs_score=72.18`, `FAIL` — PASS, schema-valid.
- Quantized E2E: `s_behavior=null`, `mrs_score=63.63`, `REVIEW`, probing bypassed — PASS, schema-valid.
- `python -m pytest tests -q` → `75 passed`; D4/D5/D6/D7/MRS/verdict/D8/adversarial/schema all PASS for the CP5 code-runtime evidence scope.
- Tracked `data/outputs/risk_results.json` is schema-valid but was NOT freshly regenerated in this documentation session. It contains `mock_status: "MOCK"` and the current placeholder generation-commit value; do not represent it as a fresh production artifact.
- Risk-result provenance remains excluded by the current contract (`additionalProperties:false`); E2E used stub models, so no VERIFIED-REAL production gate is claimed.

## Verified Implementation Status (authoritative-production scope — distinct from CP5 code-runtime PASS)

- Real P1 zero-trust intake: **not verified**
- Real P1 static feature extractor: **not verified**
- Real P3 classifier: **not verified**
- Real P2 risk engine: **not verified**
- Final integration: **not verified**

CP5 code-runtime PASS (see `## Checkpoint Status`) covers repository implementation verification, replayed calibration statistics, calibration-artifact verification, automated tests (`75 passed`), and mock/stub E2E runtime checks. It does NOT claim the authoritative-production validations listed above.

Locked decisions state requirements for implementation; checkpoint evidence is recorded separately in `## Checkpoint Status` (for CP5 code-runtime evidence see VERIFICATION.md §10).

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

When a decision is staged as methodologically resolved with empirical, implementation, or verification evidence pending, preserve that distinction explicitly and require the agent to return to the decision record when the pending evidence becomes available. Pending evidence must not be invented or implied by the locked methodology alone.

## Architecture Integrity

The architecture remains frozen:

```text
P1 → P3 → P2 → P3
```

with P1 zero-trust intake → static steganalysis → `features.json` → P3 LightGBM + TreeSHAP → `ml_results.json` → P2 STRIP + risk aggregation → `risk_results.json` → P3 security report.

Quantized models bypass behavioral probing under the finalized format-adaptive design. TreeSHAP attribution and highest-risk-layer determination remain separate mechanisms.

## Next Permitted Action

> Historical Phase-2 planning text (superseded for Phase 5 status; preserved for history): Phase 1 was recorded as complete with CP1 PASS while Phase 2 was the then-current permitted implementation phase. D2 was RESOLVED as a project decision, with implementation/verification COMPLETE — CP2 PASS. D3 was RESOLVED as a methodology decision, with empirical calibration/evidence then pending. D4–D6 were then REQUIRED. The instruction at that time was to continue Phase 2 only within the approved D2 handoff boundary and existing Phase 2 plan/verification, and not to implement D3–D6 or silently resolve remaining D9 details.

Current status: CP5 is PASS for code-runtime evidence (see `## Checkpoint Status`); CP6 is NOT YET VERIFIED. The next permitted phase is Phase 6 — Integration + Demo. D9 remains partially resolved; D9.1–D9.20 are LOCKED, while D9.21+ remain REQUIRED.

**Current D9 frontier: D9.21 — remaining dependency-policy details.**

## Final Rule

> **When the required information is unavailable, the correct action is BLOCKED — not invention.**
