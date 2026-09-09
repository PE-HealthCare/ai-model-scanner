# AI Model Scanner — Execution State

**Project Status:** FROZEN FOR EXECUTION  
**Architecture Status:** FROZEN  
**Current Phase:** Phase 3 — Static Steganalysis  
**Current Checkpoint:** CP2 — COMPLETE  
**Current Gate Status:** PASS — CP2 VERIFIED  
**Last Verified Phase:** Phase 2 — Zero-Trust Intake  
**Next Permitted Phase:** Phase 3 — Static Steganalysis

---

## Authority

The Final Master Discovery & Dependency Graph is the authoritative architecture source.

This state file records execution status only. It SHALL NOT redefine the architecture or silently resolve design decisions.

The explicit project decisions recorded below are persistent execution decisions already agreed by the project team. They do not by themselves constitute implementation verification or checkpoint PASS.

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

**Implementation / verification status:** COMPLETE — D2 implementation and verification passed at CP2. The trusted P1→P2 handoff was independently reviewed and accepted.

### D3 — STRIP Entropy Baseline

**Status: RESOLVED / LOCKED — METHODOLOGY ONLY; EMPIRICAL CALIBRATION PENDING.**

For non-quantized models, behavioral probing SHALL compute Shannon entropy over the model's softmax output probability distribution for the existing 32 domain-appropriate probes.

The STRIP baseline SHALL be empirical and domain-specific. Separate `VISION` and `NLP` baseline distributions SHALL be established from a fixed, scanner-controlled set of clean reference models for the corresponding domain.

The reference models and resulting calibration evidence SHALL be explicitly recorded before D3 is considered fully evidenced for authoritative behavioral scoring.

The baseline SHALL NOT be derived from the uploaded model itself, and no arbitrary universal numeric entropy threshold may be introduced without corresponding calibration evidence.

D3 defines the entropy measurement and baseline methodology only. The conversion of baseline deviation into `S_behavior ∈ [0,1]` remains D4. Final behavioral anomaly thresholds and risk aggregation remain governed by their respective decisions.

Quantized models do not use the behavioral baseline because behavioral probing is skipped under the finalized quantized path.

**Implementation / empirical-evidence status:** The D3 methodology is locked, but calibration execution, measured baseline distributions, and supporting evidence remain pending. Agents MUST NOT invent baseline values.

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

Only the explicitly locked D9.1–D9.20 sub-decisions are settled. Remaining D9.21+ details remain REQUIRED.

## Intentionally Unresolved Decisions

| Decision | Status |
|---|---|
| D4 — Behavioral normalization | REQUIRED |
| D5 — Risk aggregation | REQUIRED |
| D6 — Highest-risk-layer aggregation | REQUIRED |

D4–D6 are not resolved by any implementation branch, placeholder, or prior agent choice. They remain blocked pending explicit project decisions.

## Next Permitted Action

Phase 1 is complete with CP1 PASS. Phase 2 is complete with CP2 PASS. D2 implementation and verification are COMPLETE. D3 is RESOLVED as a methodology decision, with empirical calibration/evidence pending. D4–D6 remain REQUIRED. D9 remains partially resolved; D9.1–D9.20 are LOCKED, while D9.21+ remain REQUIRED. **Phase 3 is now the current permitted implementation phase.**

**Current D9 frontier: D9.21 — remaining dependency-policy details.**

## Final Rule

> **When the required information is unavailable, the correct action is BLOCKED — not invention.**
