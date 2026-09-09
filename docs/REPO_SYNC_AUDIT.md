# Repository Synchronization Audit

**Audit date:** 2026-09-09  
**Audited baseline:** `main` after CP3 merge and D6-boundary revision  
**Current main:** `main`  

## Result

The repository has advanced beyond the earlier post-Phase-3 audit. This document is now a synchronization record for the current baseline and MUST NOT be treated as an independent architecture source.

## Current authoritative state

- The Final Master Discovery & Dependency Graph remains the architecture authority.
- `docs/DECISION_STATUS.md` is the current decision-state registry.
- `docs/D6_HIGHEST_RISK_LAYER_DECISION.md` is the current D6 boundary/decision record.
- `.planning/STATE.md` records execution status and persistent decisions but MUST NOT redefine architecture.
- Phase 4 is the active implementation workstream on `phase-4/ml-classification`.

## Verified decision boundaries

- D1: exact 10-feature FP32/FP16 contract is resolved/locked.
- D2: trusted-model handoff is resolved/locked and integrated.
- D3: STRIP methodology is resolved/locked; empirical calibration remains pending.
- D4: exact `H_STRIP → S_behavior` normalization remains required.
- D5: methodology boundary is resolved/locked: D5 owns per-layer → model-level aggregation and preserves authoritative per-layer evidence/layer identity; the exact aggregation operator remains pending.
- D6: boundary is revised and locked at the planning level as highest-risk-layer selection/reporting from authoritative per-layer evidence; the exact selection rule, ownership wording, input contract, layer identity semantics, and tie behavior remain pending.
- D7: MAD validity/degeneracy guard is resolved/locked.
- D8: generation/staleness protection is resolved/locked.
- D9: partially resolved; remaining reproducibility artifact/hash/verification evidence is still required.

## Known stale documentation patterns corrected by this audit

The previous audit incorrectly described D5 and D6 simply as unresolved aggregation decisions and stated that `.planning/STATE.md` still had a Phase-2 header. Those statements are no longer current.

The current STATE header records Phase 4 / CP3 complete. The current D6 record explicitly separates highest-risk-layer selection/reporting from model-level aggregation and from TreeSHAP attribution.

## Phase 4 handoff

Phase 4 MUST use the current `main` baseline and the frozen Phase 3 feature contract. Phase 4 MUST NOT invent D4, D5 aggregation, or D6 selection semantics. CP4 remains subject to its own verification and independent approval.

## Audit rule

Future agents MUST check current `main` decision records and phase plans before relying on historical audit text. Historical wording MUST NOT override newer committed decisions.