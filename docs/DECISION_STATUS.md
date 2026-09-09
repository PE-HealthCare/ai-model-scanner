# AI Model Scanner — Synchronized Decision Status

**Status:** Documentation synchronization registry — 2026-09-09  
**Canonical branch:** `main`  
**Current execution baseline:** Phase 3 Static Steganalysis completed and merged; Phase 4 is the active downstream workstream from `main`.  
**Purpose:** Record the current approved decision state without changing the frozen architecture or silently resolving unresolved decisions.

## Decision Register

| Decision | Current status | Locked scope / evidence state |
|---|---|---|
| D1 | **RESOLVED / LOCKED** | Exact 10-feature FP32/FP16 feature set and order: entropy, pov_chi2, lsb_kl, ks_stat, mean, std, skewness, kurtosis, sparsity, outlier_pct. Phase 3 implementation and verification evidence are recorded. |
| D2 | **RESOLVED / LOCKED** | Trusted graph handoff is an in-process Python object reference during the same execution. No serialization, persistence, reload, or alternative downstream model construction. Implementation/verification COMPLETE — CP2 PASS; integrated into main. |
| D3 | **RESOLVED / LOCKED (methodology)** | STRIP methodology is locked. Empirical calibration/evidence is still pending. No numerical calibration value may be invented. |
| D4 | **REQUIRED** | STRIP entropy baseline / exact `H_STRIP → S_behavior` normalization remains unresolved. |
| D5 | **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING** | D5 owns reduction of valid per-layer static/tampering evidence to model-level evidence consumed by the frozen MRS formulas. Part 1 locks the authoritative per-layer evidence lineage and preservation of layer identity/validity provenance. Part 2 locks the semantic target and evaluation requirements for model-level `S_static`. The exact aggregation operator and evidence-backed parameters remain pending explicit authorization; no `max`, mean, median, top-k, weighted operator, or other operator may be inferred from implementation convenience. See `docs/D5_PART1_PER_LAYER_EVIDENCE_DECISION.md` and `docs/D5_PART2_MODEL_LEVEL_S_STATIC_SEMANTICS_DECISION.md`. |
| D6 | **REQUIRED — BOUNDARY REVISED** | D6 is scoped as highest-risk-layer **selection and reporting from authoritative per-layer evidence**, not a second model-level risk aggregation stage. Exact selection rule, final ownership wording, input contract, layer-identity semantics, and tie behavior remain unresolved. TreeSHAP is not a layer-selection mechanism. See `docs/D6_HIGHEST_RISK_LAYER_DECISION.md`. |
| D7 | **RESOLVED / LOCKED** | Finite nonzero MAD uses actual MAD; exact MAD=0 with target==median gives deterministic zero anomaly; exact MAD=0 with target!=median gives `DEGENERATE_DEVIATION`; 1–2 layers have unavailable baseline evidence and block downstream scoring; invalid numeric data is invalid; no epsilon or near-zero threshold. |
| D8 | **RESOLVED / LOCKED** | Artifacts carry `generation_commit`; consumers reject generation mismatches. |
| D9 | **PARTIALLY RESOLVED** | D9.1–D9.20 are locked: Python 3.11.x; CPU-only authoritative execution; exact direct pins; fully pinned transitive lock; hashes; Windows/Linux x86-64; clean hashed installation; mismatch BLOCKED; dependency changes require a new decision. Actual complete lock artifact, hashes and verification evidence remain required for full D9 resolution. |

## Governance Vocabulary

- **REQUIRED / RESOLVED:** decision state only.
- **PASS / BLOCKED / FAIL:** checkpoint or verification state.
- **RECORDED / NOT RECORDED:** independent or human review state.
- **APPROVED:** use only when actual independent/human approval exists.

A populated file, passing test, or implementation artifact does not by itself resolve a project decision.

## Current Execution Boundary

- Phase 1: complete.
- Phase 2: complete; CP2 PASS and D2 handoff independently approved/integrated.
- Phase 3: complete; CP3 evidence recorded, independently reviewed, and merged into `main` at `b19a26cef97c3980d80f3784679ec314e35a4492`.
- Phase 4: **ACTIVE**; downstream P3 work proceeds from the verified Phase 3 baseline and current Phase 4 branch.
- Phase 5: pending CP4 PASS and its own decision/evidence gates.
- Phase 6: pending CP4/CP5 PASS and its own decision/evidence gates.

This registry does not authorize silent implementation of D4–D6 or completion claims for unresolved D9 evidence. The frozen architecture remains authoritative.
