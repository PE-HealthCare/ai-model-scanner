# Phase 03 — Static Steganalysis — PLAN

**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`
**Owner:** P1 — Eyes (`src/p1_static_engine/analyzer.py`)
**Status:** FROZEN FOR EXECUTION — implement only what is specified below.

## 0. Purpose and Scope

This phase implements and verifies **real** static feature extraction, following the
finalized format-adaptive design in the Master Graph (§5, §11 Phase 3). This is the
**critical handoff to P3**: the exact feature names, semantics, representation, and
order produced here become the frozen training/inference contract for Phase 04.

This plan does not redesign the pipeline, does not invent a feature-vector
dimensionality, and does not resolve any item marked DECISION REQUIRED in the
Master Graph — those are carried forward unresolved, not silently answered.

## 1. Inputs

- Trusted, weight-loaded graph (from P1 Zero-Trust Intake, Phase 02)
- `input_domain` (VISION / NLP)
- `is_quantized` (boolean, derived from SafeTensors dtype: INT8/FP8 → TRUE, otherwise FALSE)

## 2. Format-Adaptive Static Analysis Design

The static analysis path is selected per-layer/per-tensor based on `is_quantized`.
This is a binary format gate, not a spectrum — no intermediate or inferred formats
are introduced.

### 2.1 Quantized path (`is_quantized = TRUE`)

- Apply **whole-weight KS statistic only**.
- Mantissa/LSB-specific tests are **explicitly skipped** — do not apply FP-specific
  bit-level assumptions (byte-position entropy, PoV chi-square, LSB KL-divergence)
  to quantized weight representations, since those assumptions are not valid for
  INT8/FP8 layouts.

### 2.2 FP32/FP16 path (`is_quantized = FALSE`)

Compute, per layer/tensor:

- Byte-position Shannon entropy
- PoV (plane-of-value) chi-square
- LSB KL-divergence
- KS statistic
- Statistical moments/descriptors:
  - mean
  - standard deviation
  - skewness
  - kurtosis
  - sparsity
  - outlier percentage

No additional statistical tests are introduced beyond this list. No test in this
list is dropped for the FP32/FP16 path.

## 3. Intra-Model Baseline

- Baseline comparison is **intra-model, layer-vs-layer**.
- **No external clean reference model is required at runtime.**
- Each layer's statistics are evaluated against a baseline derived from other
  comparable layers within the same model.

### 3.1 Edge case — insufficient comparable layers

The Master Graph explicitly preserves this limitation (§9, MAD edge case) and
registers it as **D7 — DECISION REQUIRED**:

> Guard behavior for degenerate MAD / insufficient layer count is not finalized.

This plan does **not** invent a minimum layer-count threshold or a fallback
baseline strategy. Implementation must:

- Detect when too few comparable layers exist to establish a statistically
  meaningful intra-model baseline.
- Surface this condition explicitly (e.g., as a flag/limitation on the affected
  layer's evidence) rather than silently producing a numerically stable but
  semantically meaningless baseline.
- Leave the exact guard behavior (skip, warn, degrade gracefully, minimum-N
  threshold, etc.) as an open decision pending D7 resolution.

## 4. Feature Semantics — Stability Contract for P3

Because Phase 04 (P3) trains and infers using the **same extraction code/semantics**
as this phase (Master Graph §7, Hidden Dependency #1–2), this plan requires:

- Each emitted feature has a **stable, exact name**.
- Each emitted feature has **stable, exact semantics** (what it measures, on what
  unit/scale, over what population — e.g., per-layer vs per-tensor).
- Feature **order/representation** is deterministic and consistent across runs.
- The quantized-path feature set and the FP32/FP16-path feature set are **not**
  assumed to be the same shape — the format-adaptive design means these are
  distinct feature sets, and downstream consumers (P3) must be able to identify
  which path produced a given feature set.
- **No arbitrary feature-vector dimensionality is defined by this plan.** The
  exact field list, types, and layout are governed by `features.schema.json`,
  which is currently EMPTY and registered as **D1 — DECISION REQUIRED** in the
  Master Graph. This plan does not populate that schema or invent field counts
  (e.g., no assumed "18-D" or similar fixed-size vector).
- Layer identity must remain attached to each feature record, independent of
  TreeSHAP attribution, to support the separate highest-risk-layer path (§6B of
  the Master Graph) in later phases.

## 5. Outputs

- `data/outputs/features.json` — populated with real (non-mock) static features,
  per the field layout to be agreed under D1.
- Conformance to `features.schema.json` once that schema is finalized (D1).

## 6. Explicit Non-Goals for This Phase

- Do not implement P2 behavioral probing.
- Do not implement P3 LightGBM/TreeSHAP.
- Do not define the per-layer → model-level aggregation method (D5) — that is
  P2 Risk Aggregation's concern downstream, not this phase's output shape.
- Do not define the highest-risk-layer aggregation mechanism (D6) — this phase
  only guarantees layer identity is preserved and available.
- Do not resolve D1 (contract schema fields) unilaterally; surface for team
  agreement per Master Graph §19 execution sequence.

## 7. Carried-Forward Unresolved Decisions (Not Invented Here)

| ID | Item |
|---|---|
| D1 | Exact `features.schema.json` fields/types/layout |
| D7 | MAD / baseline degenerate-case guard behavior (zero/near-zero MAD, low layer count) |

These remain open per the Master Graph Decision-Required Register (§16) and must
not be silently resolved during implementation of this phase.
