# AI Model Scanner — Execution State

**Project Status:** FROZEN FOR EXECUTION  
**Architecture Status:** FROZEN  
**Current Phase:** Phase 4 — ML Classification  
**Current Checkpoint:** CP3 — COMPLETE  
**Current Gate Status:** PASS — CP3 VERIFIED  
**Last Verified Phase:** Phase 3 — Static Steganalysis  
**Next Permitted Phase:** Phase 4 — ML Classification

---

## Authority

The Final Master Discovery & Dependency Graph is the authoritative architecture source.

This state file records execution status only. It SHALL NOT redefine the architecture or silently resolve design decisions.

The explicit project decisions recorded below are persistent execution decisions already agreed by the project team. They do not by themselves constitute implementation verification or checkpoint PASS.

## Persistent Locked Decisions

### D1 — Exact Static Feature Contract

**Status: RESOLVED / LOCKED.**

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

The D2 handoff SHALL NOT serialize or persist the trusted model for downstream loading, independently reload the model in P2, provide the original untrusted artifact as P2's loading source, or create an alternative architecture in P2.

P2 SHALL consume the received trusted model for bounded, inference-only behavioral analysis. P2's inference-only contract prohibits training, gradient/backward execution, optimizer use, weight modification, or independent model loading.

The handoff SHALL carry `input_domain` (`VISION` or `NLP`) and `is_quantized` (`true` or `false`). The exact Python class/function representation is an implementation detail.

**Implementation / verification status:** D2 implementation and verification evidence are COMPLETE. D2 was implemented, tested, independently reviewed, accepted at CP2, and integrated into main.

### D3 — STRIP Entropy Baseline

**Status: RESOLVED / LOCKED — METHODOLOGY ONLY; EMPIRICAL CALIBRATION PENDING.**

For non-quantized models, behavioral probing SHALL compute Shannon entropy over the model's softmax output probability distribution for the existing 32 domain-appropriate probes.

The STRIP baseline SHALL be empirical and domain-specific, using fixed scanner-controlled clean reference models. It SHALL NOT be derived from the uploaded model and no arbitrary universal numeric entropy threshold may be introduced without calibration evidence.

D3 defines entropy measurement and baseline methodology only. Conversion of baseline deviation into `S_behavior ∈ [0,1]` remains D4.

**Implementation / empirical-evidence status:** methodology is locked; calibration execution, measured baseline distributions, and supporting evidence remain pending. Agents MUST NOT invent baseline values.

### D4 — Behavioral Normalization

**Status: TEAM-AGREED / FORMULA-LOCKED; IMPLEMENTATION/CALIBRATION UNDERWAY.**

The team-agreed D4 formula is locked and P2 is currently implementing/calibrating it. This state record intentionally does not restate the mathematical formula or calibration values; agents MUST use the authoritative D4 decision artifact for exact technical semantics and MUST NOT invent or reinterpret them.

### D5 — Per-Layer → Model-Level Risk Aggregation

**Status: RESOLVED / LOCKED — EXACT OPERATOR.**

D5 owns the reduction of valid per-layer static/tampering evidence to the model-level evidence consumed by the frozen MRS formulas.

The exact D5 operator is authoritative in `docs/D5_PART7_EXACT_OPERATOR_DECISION.md` and SHALL be followed exactly. It SHALL operate only on valid, eligible per-layer evidence after applicable D7 validity/degeneracy handling, preserve authoritative per-layer evidence/layer identity required by D6, and SHALL NOT fabricate, impute, or silently substitute missing/invalid evidence.

The exact operator is not redefined in this execution-state summary.

**Implementation / verification status:** the D5 decision is locked; implementation and verification evidence remain governed by the applicable phase gates.

### D6 — Highest-Risk-Layer Selection & Reporting

**Status: RESOLVED / LOCKED — PARTS 1 & 2.**

D6 owns highest-risk-layer selection and reporting from authoritative per-layer evidence. It is not a second model-level risk aggregation stage and is not TreeSHAP attribution.

The exact D6 selection semantics, input boundary, eligibility, and deterministic tie behavior are authoritative in `docs/D6_HIGHEST_RISK_LAYER_DECISION.md` and SHALL be followed exactly. D6 SHALL NOT recalculate upstream evidence, manufacture layer-level `P_tamper`/`S_behavior`, recalculate MRS, or use TreeSHAP as its selection algorithm.

**Implementation / verification status:** the D6 decision is locked; implementation and verification remain governed by Phase 6 and CP6 evidence.

### Decision 1 — Trusted Architecture Registry

**Status: RESOLVED / LOCKED.**

The trusted architecture registry is intentionally limited to:

| Declared architecture | Domain | Trusted implementation |
|---|---|---|
| `resnet18` | VISION | `torchvision.models` |
| `distilbert` | NLP | `transformers` |

Rules: uploader declares architecture; no automatic detection; no uploader-supplied `model.py` or custom executable architecture; unsupported architecture fails closed; malformed/incompatible tensor names/shapes/dtypes fail closed; no best-effort graph construction, silent omission, shape correction, or fallback.

### Decision 2 — Zero-Trust Intake Resource Limits

**Status: RESOLVED / LOCKED.**

| Resource | Hard limit |
|---|---:|
| SafeTensors header | **5 MB** |
| Metadata | 1 MB |
| Tensor count | 10,000 |
| Maximum tensor rank | 8 |
| Maximum dimension | 1,000,000 |
| Model file size | 2 GB |

Operational targets: intake memory `<50 MB`; processing time `<0.5 sec`.

The SafeTensors header limit is **5 MB** and supersedes the previous 100 MB value. Hard-limit exceedance fails closed with the exact exceeded limit. No per-tensor quota heuristics, configuration override, or limit-tuning CLI flag is authorized.

### D7 — MAD Degenerate Baseline Guard

**Status: RESOLVED / LOCKED.**

- Finite nonzero MAD: use actual MAD directly; no epsilon.
- Exact MAD = 0 and target equals median: deterministic zero anomaly.
- Exact MAD = 0 and target differs from median: `DEGENERATE_DEVIATION`.
- 1–2 comparable layers: baseline evidence unavailable; block downstream scoring requiring it.
- Missing/NaN/+/-inf numeric data: invalid; no imputation.
- Very small nonzero MAD: use actual value.
- Quantized behavior retains finalized format-adaptive rules; no new semantics are invented.

### D8 — Artifact Staleness Protection

**Status: RESOLVED / LOCKED.**

Downstream stages consume outputs from the current pipeline execution only. `generation_commit` provides artifact provenance/generation identity. A stale/mismatched artifact must be rejected or blocked rather than silently reused.

### D9 — Dependency Pinning

**Status: REQUIRED — PARTIALLY RESOLVED.**

D9 sub-decisions D9.1–D9.20 are locked as policy. Full D9 resolution still requires the actual authoritative lock artifacts, hashes, installation procedure, and verification evidence.

Locked direct runtime versions:

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

Authoritative environment: Python 3.11.x, CPU-only, Windows x86-64 and Linux x86-64. Standard dependencies use PyPI; torch/torchvision use the official PyTorch CPU wheel index. Direct and transitive dependencies must be fully pinned; package hashes must be present and enforced; clean installation must use the generated hashed requirements lock artifact; verification mismatches are BLOCKED; dependency changes require explicit decision/change control.

D9.16 requires verification of Python version, exact direct pins, all transitive lock entries, hash enforcement, and CPU-only execution. D9.17 defines Windows/Linux x86-64 scope. D9.18 defines clean hashed installation. D9.19 requires explicit dependency change control. D9.20 defines full-completion criteria: all sub-decisions locked, authoritative platform lock artifacts exist, direct/transitive versions and hashes are populated/enforced, installation is documented, and authoritative environment verification passes.

D9.21 and later remain REQUIRED until explicitly resolved.

## Intentionally Unresolved Decisions

| Decision | Status |
|---|---|
| D3 — STRIP empirical calibration/evidence | METHODOLOGY LOCKED; CALIBRATION PENDING |
| D4 — Behavioral normalization | TEAM-AGREED / FORMULA-LOCKED; IMPLEMENTATION/CALIBRATION UNDERWAY |
| D9 — Dependency pinning | PARTIALLY RESOLVED; required lock/evidence work remains |

D5 and D6 are locked; D10 and D11 are resolved on the authoritative decision branch but their detailed records are not yet part of the current `main` baseline. Do not invent replacement D10/D11 records on `main`; synchronize them when the authoritative records are incorporated through the normal integration process.

A locked methodology, decision, or boundary does not constitute implementation or checkpoint evidence.

## Phase Status

| Phase | Status | Gate |
|---|---|---|
| Phase 1 — Mock Pipeline | COMPLETE | CP1 PASS |
| Phase 2 — Zero-Trust Intake | COMPLETE | CP2 PASS |
| Phase 3 — Static Steganalysis | COMPLETE | CP3 PASS |
| Phase 4 — ML Classification | ACTIVE | CP4 IN PROGRESS |
| Phase 5 — Behavioral + Risk | PENDING | CP5 |
| Phase 6 — Integration + Demo | PENDING | CP6 |

## Checkpoint Status

| Checkpoint | Status |
|---|---|
| CP1 — Mock Gate | PASS |
| CP2 — Intake Gate | PASS |
| CP3 — Static Gate | PASS |
| CP4 — ML Gate | IN PROGRESS |
| CP5 — Behavioral/Risk Gate | NOT REACHED |
| CP6 — Demo Gate | NOT REACHED |

Only a `PASS` checkpoint permits advancement.

## Verified Implementation Status

- Real P1 zero-trust intake: **VERIFIED — CP2**
- Real P1 static feature extractor: **VERIFIED-REAL — CP3**
- Real P3 classifier: **IN PROGRESS — CP4 not yet passed**
- Real P2 risk engine: **NOT VERIFIED — blocked on upstream CP4 and required decisions/evidence**
- Final integration: **NOT VERIFIED**

## Current Dependency Chain

```text
CP1 PASS
 ↓
CP2 PASS
 ↓
CP3 PASS
 ↓
Phase 4 P3 final ML training
 ↓
CP4 PASS
 ↓
Phase 5 P2 Behavioral + Risk
 ↓
CP5 PASS
 ↓
Phase 6 Integration
 ↓
CP6 PASS
```

## Hard-Stop Conditions

The agent MUST stop dependent work when a required decision remains unresolved, an upstream checkpoint is not PASS, a required contract is undefined, feature semantics are not verified, a dependency is unavailable/unverified, verification cannot legitimately be evaluated, implementation would require inventing a schema/formula/threshold/normalization/baseline/aggregation/dependency/feature meaning, the frozen architecture would be redesigned without an explicit reopening decision, ownership is unclear, or mock/scaffold behavior would be represented as real implementation.

## Execution Rules

When not blocked, the agent SHALL inspect current repository state, identify the applicable phase, read that phase's PLAN and VERIFICATION, confirm upstream gates, implement only within permitted scope, preserve subsystem ownership, run applicable verification, record the resulting gate status, and update this state only with verified facts.

## State Update Rules

This file SHALL describe actual verified state, not intended state. Do not mark code implemented when scaffolded, outputs produced when mocks, phases complete before verification, decisions resolved because an agent selected an implementation, or dependencies verified merely because they appear in a file.

When a decision is staged as methodologically resolved with empirical, implementation, or verification evidence pending, preserve that distinction explicitly. Pending evidence must not be invented or implied by the locked methodology alone.

## Architecture Integrity

The architecture remains frozen:

```text
P1 → P3 → P2 → P3
```

with P1 zero-trust intake → static steganalysis → `features.json` → P3 LightGBM + TreeSHAP → `ml_results.json` → P2 STRIP + risk aggregation → `risk_results.json` → P3 security report.

Quantized models bypass behavioral probing under the finalized format-adaptive design. TreeSHAP attribution and highest-risk-layer determination remain separate mechanisms.

## Next Permitted Action

**Phase 4 — ML Classification.** CP3 is PASS and the verified-real Phase 3 output is the required upstream baseline. Phase 4 MUST use the exact frozen P1 feature contract and MUST NOT invent D4, the D5 aggregation operator, or D6 selection semantics. CP4 requires independent verification/approval before Phase 5 proceeds.

D9 remains partially resolved; D9.21+ remain REQUIRED.

## Final Rule

> **When the required information is unavailable, the correct action is BLOCKED — not invention.**
