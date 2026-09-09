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
| D5 | **RESOLVED / LOCKED — EXACT OPERATOR** | D5 owns reduction of valid per-layer static/tampering evidence to model-level evidence consumed by the frozen MRS formulas. Exact construction: `e(l,f)=|Z(l,f)|/(1+|Z(l,f)|)` for D7-valid finite evidence; `E(l)=max_f e(l,f)`; `S_static=1-product_l(1-E(l))`. Invalid/blocked/degenerate evidence is not silently imputed or converted to zero. No Gaussian assumption, hidden calibration, new threshold, or MRS change is authorized. |
| D6 | **RESOLVED / LOCKED — PARTS 1 & 2** | P1 owns authoritative production/preservation of per-layer evidence and authoritative layer identity; P3/D6 owns final highest-risk-layer selection and security-report presentation. D6 selects `argmax E(l)` over eligible D5 per-layer evidence, where `E(l)=max_f(|Z(l,f)|/(1+|Z(l,f)|))` using only D7-valid finite evidence. Invalid/missing evidence is not imputed or fabricated; `DEGENERATE_DEVIATION` and unavailable baseline remain non-eligible states. Exact ties use canonical authoritative `layer_id` ordering. TreeSHAP remains separate and is not used for layer selection. |
| D7 | **RESOLVED / LOCKED** | Finite nonzero MAD uses actual MAD; exact MAD=0 with target==median gives deterministic zero anomaly; exact MAD=0 with target!=median gives `DEGENERATE_DEVIATION`; 1–2 layers have unavailable baseline evidence and block downstream scoring; invalid numeric data is invalid; no epsilon or near-zero threshold. |
| D8 | **RESOLVED / LOCKED** | Artifacts carry `generation_commit`; consumers reject generation mismatches. |
| D9 | **PARTIALLY RESOLVED** | D9.1–D9.20 are locked: Python 3.11.x; CPU-only authoritative execution; exact direct pins; fully pinned transitive lock; hashes; Windows/Linux x86-64; clean hashed installation; mismatch BLOCKED; dependency changes require a new decision. Actual complete lock artifact, hashes and verification evidence remain required for full D9 resolution. |
| D10 | **RESOLVED / LOCKED** | P3 model-level classifier aggregation is exactly `P_tamper = max_{l in L_required} p_l`, where `p_l=LightGBM(X_l)` and `L_required` is the complete authoritative P1 layer set supplied to P3. No averaging, voting, top-k reduction, layer-count correction, hidden weighting, or additional calibration. Required-layer classification failure invalidates the model-level classifier result rather than silently omitting/imputing a layer. TreeSHAP explanation may use `l_ML=argmax_l p_l`, which remains separate from D6. D10 does not modify D5, D6, D7, D8, D4, MRS, thresholds, or the public `ml_results` schema. |
| D11 | **RESOLVED / LOCKED** | Quantized P3 classifier path is format-adaptive: validated quantized P1 output exposes finite whole-weight `ks_stat` while the nine FP-specific fields are explicitly unavailable (`null`), never NaN/zero-imputed. P3 uses a dedicated one-feature quantized LightGBM artifact on `ks_stat`; per-layer `p_l^Q` is aggregated by the already-locked D10 MAX rule into `P_tamper`. Quantized behavioral probing remains bypassed and the frozen quantized MRS is unchanged. P1 must safely support the validated quantized representation without unsafe conversion or uploader code. See `docs/D11_QUANTIZED_P3_CLASSIFIER_DECISION.md`. |

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

This registry does not authorize silent implementation of D4 or completion claims for unresolved D9 evidence. **D5 Part 7, D6 Parts 1 & 2, D10, and D11 are now locked; production implementation must reproduce their exact approved boundaries.** The frozen architecture remains authoritative.
