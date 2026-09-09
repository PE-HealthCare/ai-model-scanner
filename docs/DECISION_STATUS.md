# AI Model Scanner — Synchronized Decision Status

**Status:** Documentation synchronization registry — 2026-09-09
**Branch:** `docs/synchronize-decision-status`
**Purpose:** Record the current approved decision state without changing the frozen architecture or silently resolving unresolved decisions.

## Decision Register

| Decision | Current status | Locked scope / evidence state |
|---|---|---|
| D1 | **RESOLVED / LOCKED** | Exact 10-feature FP32/FP16 feature set and order: entropy, pov_chi2, lsb_kl, ks_stat, mean, std, skewness, kurtosis, sparsity, outlier_pct. Implementation/verification evidence remains subject to phase gates. |
| D2 | **RESOLVED / LOCKED** | Trusted graph handoff is an in-process Python object reference during the same execution. No serialization, persistence, reload, or alternative downstream model construction. Implementation/verification evidence COMPLETE — CP2 PASS. |
| D3 | **RESOLVED / LOCKED (methodology)** | STRIP methodology is locked. Empirical calibration/evidence is still pending. No numerical calibration value may be invented. |
| D4 | **REQUIRED** | STRIP entropy baseline remains unresolved. |
| D5 | **REQUIRED** | Behavioral normalization / `H_STRIP → S_behavior` remains unresolved. |
| D6 | **REQUIRED** | Model-level / highest-risk-layer aggregation details remain unresolved where specified by the authoritative phase/decision context. |
| D7 | **RESOLVED / LOCKED** | Finite nonzero MAD uses actual MAD; exact MAD=0 with target==median gives deterministic zero anomaly; exact MAD=0 with target!=median gives `DEGENERATE_DEVIATION`; 1–2 layers have unavailable baseline evidence and block downstream scoring; invalid numeric data is invalid; no epsilon or near-zero threshold. |
| D8 | **RESOLVED / LOCKED** | Artifacts carry `generation_commit`; consumers reject generation mismatches. |
| D9 | **PARTIALLY RESOLVED** | D9.1–D9.20 are locked: Python 3.11.x; CPU-only authoritative execution; exact direct pins; fully pinned transitive lock; hashes; Windows/Linux x86-64; clean hashed installation; mismatch BLOCKED; dependency changes require a new decision. Actual complete lock artifact, hashes and verification evidence remain required for full D9 resolution. |

## Governance Vocabulary

- **REQUIRED / RESOLVED:** decision state only.
- **PASS / BLOCKED / FAIL:** checkpoint or verification state.
- **RECORDED / NOT RECORDED:** independent or human review state.
- **APPROVED:** use only when actual independent/human approval exists.

A populated file, passing test, or implementation artifact does not by itself resolve a project decision.

## Current Synchronization Boundary

This registry does not modify the frozen Master Graph and does not authorize implementation of D4–D6 or unresolved D9 completion work. It is a synchronization aid while lower-authority documentation is reconciled.
