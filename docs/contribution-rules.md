# AI Model Scanner — Contribution Rules

**Status:** FROZEN FOR EXECUTION
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`

## Ownership Boundaries

- **P1 — Eyes** owns `src/p1_static_engine/` (`analyzer.py`): safe intake, trusted graph instantiation, SafeTensors inspection, domain/quantization tagging, static steganalysis, feature extraction.
- **P2 — Muscle** owns `src/p2_behavioral_risk/` (`prober.py`): domain-aware STRIP probing, behavioral anomaly scoring, MAD risk aggregation, MRS, verdict.
- **P3 — Brain & Voice** owns `src/p3_ml_dashboard/` (`classifier.py`, `dashboard.py`): LightGBM, synthetic training workflow, TreeSHAP, `P_tamper`, reporting/dashboard.
- **`scan_model.py`** is the root orchestration/integration surface. It orchestrates P1 → P3 → P2 → P3. It is **not** a fourth implementation owner and must not accumulate subsystem logic.
- **`src/common/`** is shared infrastructure only (shared utilities). It is not owned by any single person, and it must not become a dumping ground for subsystem-specific logic belonging to P1, P2, or P3. Anything that is specific to one subsystem's detection, scoring, or reporting logic belongs in that subsystem's own directory, not in `common/`.

## Contract Files

- `features.schema.json`, `ml_results.schema.json`, and `risk_results.schema.json` are **shared interfaces** between owners, not the property of a single owner.
- Changes to any shared contract, or to the **name, meaning, units, representation, or ordering** of any feature or field it defines, require explicit coordination with every affected owner before merging.
- **No silent changes** to feature names, meanings, units, or semantics are permitted. A feature-semantic change made by P1 without coordination can cause P3's classifier and TreeSHAP attribution to become silently invalid (LightGBM may still run without erroring), so such changes must always be flagged and reverified downstream.

## Branching Strategy

Use owner- and scope-prefixed branch names so ownership and intent are visible at a glance, for example:

- `feature/p1-static` — P1 static engine work
- `feature/p2-behavioral` — P2 behavioral/risk work
- `feature/p3-ml-dashboard` — P3 ML/dashboard work
- `feature/shared-contracts` — changes to shared schema/contract files (requires coordination, see above)
- `feature/scan-model-orchestration` — root orchestration surface changes

## Phase Gating

- **No phase advances without its `VERIFICATION.md` gate passing.** This applies uniformly across all owners and all six project phases (see `ROADMAP.md`).
- Work that is provisional or preparatory (e.g. scaffolding, mocks) must not be represented as final or verified work, and must not be used to justify skipping a downstream gate.

## Independent vs. Blocked Work

- **Independent work** (may proceed without waiting on another owner): Phase 1 mocks for all three owners; P2 probe design against mocks; P3 synthetic tampering design and LightGBM/TreeSHAP scaffolding — all contingent only on contract agreement, not on another owner's real implementation.
- **Blocked work** (must wait on upstream verification): P3's final classifier training is blocked until P1's real feature extractor and exact feature semantics are verified (Phase 3 gate). P2's final risk integration is blocked until the required real upstream outputs (including P3's `P_tamper`) are verified. Final dashboard integration is blocked until all upstream gates have passed.
- Contributors must not treat provisional/preparatory work as satisfying a downstream dependency.

## Communicating Cross-Owner Dependencies and Change Impact

- Any change to a shared contract field, a P1 feature's name/semantics/order, P1's `input_domain` or `is_quantized` semantics, P3's `P_tamper` semantics, P2's MRS formula, STRIP baseline/normalization, or the layer aggregation method must be communicated to every owner listed as affected in the Master Graph's Change-Impact Map before the change is merged.
- The affected owner(s) must reverify or retrain as applicable (e.g. P3 retrain + TreeSHAP reverify on P1 feature changes; P2 reverify on `input_domain`/`is_quantized` or `P_tamper` changes; P3 + demo revalidation on MRS formula changes).
- Cross-owner dependency status and change impact should be recorded against the relevant phase's `VERIFICATION.md`, not communicated informally only, so the gate reflects the true state of upstream/downstream coordination.

## General Rule

Do not redesign the finalized pipeline or invent resolutions to items marked DECISION REQUIRED in the Master Graph. If implementation work touches an unresolved decision, surface it to the team before proceeding.
