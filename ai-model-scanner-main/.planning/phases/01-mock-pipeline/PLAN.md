# Phase 01 — Mock Pipeline — PLAN

**Status:** Current execution target
**Owners:** P1, P2, P3 (in parallel), integration surface: `scan_model.py`

## Objective

Establish and validate the end-to-end interface between all three subsystems using controlled mock outputs. This phase validates **orchestration and contract shape**, not detection quality. It does **not** involve real SafeTensors analysis, real ML training, or real behavioral probing.

## Data Flow Under Test

```text
P1 (mock) → features.json → P3 (mock) → ml_results.json → P2 (mock) → risk_results.json → scan_model.py final report surface
```

## Contract Fields

Per the Master Graph (Section 4, "Contracts"), all three schemas — `features.schema.json`, `ml_results.schema.json`, and `risk_results.schema.json` — are currently **EMPTY**, with exact fields marked **DECISION REQUIRED (D1)**.

This plan does not invent contract field contents (e.g. no assumed "18-dimensional feature vector" or similar). Before mock generation can begin, **the team must first agree the exact contract fields for D1**. Once agreed, the mocks in this phase must populate those exact agreed fields with placeholder/synthetic values only — field names and shapes must match the agreed contract, not be invented independently by any one owner.

## P1 Mock Responsibility

- Produce a mock `data/outputs/features.json` that conforms to the agreed `features.schema.json` (once D1 is resolved).
- Values are placeholder/synthetic; no real SafeTensors parsing or feature extraction occurs in this phase.
- Mock output must still distinguish `input_domain` and `is_quantized` as agreed contract fields, since downstream mocks (P2, P3) depend on their presence and shape, not their real values.

## P3 Mock Responsibility

- Consume the mock `features.json`.
- Produce a mock `data/outputs/ml_results.json` conforming to the agreed `ml_results.schema.json`, including placeholder values for `P_tamper` and feature-level SHAP attribution fields as agreed in the contract.
- No real LightGBM training or TreeSHAP computation occurs in this phase; values are synthetic placeholders only.
- Also produces a placeholder `artifacts/lightgbm_model.txt` presence marker if required by the agreed contract (content is not a trained model).

## P2 Mock Responsibility

- Consume the mock `ml_results.json` (and mock `features.json` where the agreed contract requires direct P1→P2 fields).
- Produce a mock `data/outputs/risk_results.json` conforming to the agreed `risk_results.schema.json`, including placeholder `S_static`, `S_behavior`, MRS, and verdict fields.
- No real STRIP probing or MAD aggregation occurs in this phase; values are synthetic placeholders only.

## `scan_model.py` Orchestration Responsibility

- Orchestrates the mock run in the frozen order: P1 → P3 → P2 → P3 (final report).
- Does not implement subsystem logic itself (per Master Graph Rule 5 — `scan_model.py` is an integration surface, not a fourth implementation owner).
- Invokes each mock stage, passes the correct file paths/handles between stages, and produces a final report surface consuming the mock `risk_results.json`.
- Surfaces any stage failure rather than continuing silently.

## Contract Validation Points

1. **P1 mock output → `features.schema.json`** — validate immediately after P1 mock stage runs.
2. **P3 mock output → `ml_results.schema.json`** — validate immediately after P3 mock stage runs, using the P1 mock output as its declared input.
3. **P2 mock output → `risk_results.schema.json`** — validate immediately after P2 mock stage runs, using the P3 mock output as its declared input.
4. **End-to-end** — validate that `scan_model.py` completes a full run consuming all three mock outputs in order and produces a final report surface without silent failure.

## Expected Mock Handoffs

- P1 mock → P3 mock: via `features.json` on disk (or equivalent in-process handle per D2, if already agreed for this phase; otherwise file-based handoff only).
- P3 mock → P2 mock: via `ml_results.json` on disk.
- P2 mock → P3 (dashboard/report): via `risk_results.json` on disk.

## Explicit Non-Goals for This Phase

- No real SafeTensors parsing (Phase 2).
- No real static feature extraction (Phase 3).
- No real LightGBM training or TreeSHAP (Phase 4).
- No real STRIP probing or MAD aggregation (Phase 5).
- No redesign of the frozen architecture or contract semantics.

## Preserved Unresolved Decision

- **D1 — Contract schemas** must be resolved by the team before mock field values can be finalized. This plan does not resolve D1; it depends on it.
