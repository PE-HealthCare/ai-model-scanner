# Phase 03 — Static Steganalysis — VERIFICATION

**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`
**Gate:** CP3 — Static Gate (Master Graph §13)
**Applies to:** `PLAN.md` in this same directory.

This phase does not pass CP3 until every gate below is satisfied. Any DECISION
REQUIRED item referenced here remains open; verification of this phase does not
imply those decisions have been made.

## G1 — FP32/FP16 Path

- [ ] Byte-position Shannon entropy is computed for FP32/FP16 tensors.
- [ ] PoV chi-square is computed for FP32/FP16 tensors.
- [ ] LSB KL-divergence is computed for FP32/FP16 tensors.
- [ ] KS statistic is computed for FP32/FP16 tensors.
- [ ] All six statistical moments/descriptors are computed: mean, standard
      deviation, skewness, kurtosis, sparsity, outlier percentage.
- [ ] No additional, unspecified statistical tests are silently added.
- [ ] No specified test is silently omitted.

**Fail condition:** any FP32/FP16 test listed in PLAN.md §2.2 is missing,
substituted, or produces `null`/undefined without explicit, surfaced reason.

## G2 — Quantized Path

- [ ] Quantized models (`is_quantized = TRUE`) receive whole-weight KS statistic
      only.
- [ ] Mantissa/LSB-specific tests (byte-position entropy, PoV chi-square, LSB
      KL-divergence) are **not** computed or applied to quantized weights.
- [ ] `is_quantized` flag from P1 Intake is respected as the sole path selector
      (no re-derivation or overriding within this phase).

**Fail condition:** any FP-specific bit-level test is applied to a quantized
tensor, or whole-weight KS is skipped for a quantized tensor.

## G3 — Statistical Calculation Correctness

- [ ] Each statistic is computed over the correct population (documented: per
      layer vs per tensor vs whole-weight) and this population is consistent
      with what PLAN.md declares for that statistic.
- [ ] Statistical formulas match standard definitions (Shannon entropy, chi-square,
      KL-divergence, KS test, skewness, kurtosis) — no ad hoc redefinition.
- [ ] Units/scales of each output value are internally consistent across layers
      of the same model.

**Fail condition:** a statistic is computed with a non-standard formula without
explicit documented justification, or population scope is inconsistent between
layers.

## G4 — Intra-Model Baseline

- [ ] Baseline comparison is confirmed to be intra-model (layer-vs-layer), not
      against an external reference model.
- [ ] No runtime dependency on an external "clean" reference model is introduced.
- [ ] Baseline construction logic is documented and traceable to specific
      comparable layers used.

**Fail condition:** any code path fetches, loads, or requires an external clean
reference model at runtime.

## G5 — Edge Case: Insufficient Comparable Layers

- [ ] A condition exists that detects when too few comparable layers are present
      to form a meaningful baseline.
- [ ] When this condition triggers, it is surfaced explicitly in the output
      (flag, limitation note, or equivalent) rather than silently producing a
      baseline value that appears normal.
- [ ] The exact numeric threshold/guard behavior is **not** asserted as finalized
      by this verification — D7 remains open. Verification only confirms the
      condition is *detected and surfaced*, not that a specific threshold is
      "correct."

**Fail condition:** low-layer-count models silently produce baseline-derived
values with no indication that the baseline was weak or degenerate.

## G6 — Semantic Consistency for Downstream (P3) Consumption

- [ ] Every emitted feature has a fixed, documented name.
- [ ] Every emitted feature has documented semantics (what it measures, over what
      scope).
- [ ] Feature order/representation is deterministic across repeated runs on the
      same input.
- [ ] Quantized-path and FP32/FP16-path outputs are distinguishable by downstream
      consumers (i.e., a consumer can tell which extraction path produced a given
      feature set).
- [ ] Layer identity is attached to and retrievable from each feature record.
- [ ] No fixed feature-vector dimensionality (e.g., an invented "18-D" vector) is
      hardcoded anywhere in the implementation absent an agreed D1 schema.

**Fail condition:** feature names, order, or semantics differ between two runs
on identical input; or a fixed dimensionality is hardcoded without traceability
 to an agreed schema.

## G7 — Numerical Stability

- [ ] No division-by-zero or undefined-log conditions occur unguarded (e.g., KL-
      divergence with zero-probability bins, chi-square with zero expected
      counts).
- [ ] Degenerate distributions (all-zero weights, constant weights) do not crash
      the pipeline and produce a defined, documented output or explicit flag.
- [ ] Floating-point outputs are finite (`no NaN/Inf leaking into features.json`
      without an explicit, documented representation for such cases).

**Fail condition:** any statistic silently returns `NaN`/`Inf`/exception on
degenerate but realistic input without a documented, explicit handling path.

## G8 — Non-Invention Check

- [ ] Implementation does not resolve D1 (schema fields) unilaterally without
      team agreement.
- [ ] Implementation does not resolve D7 (MAD/baseline guard specifics) by
      inventing an unstated threshold and treating it as final/authoritative.
- [ ] No architecture redesign has occurred relative to Master Graph §1, §5, §18.

**Fail condition:** any DECISION REQUIRED item from the Master Graph is treated
as resolved without explicit team sign-off recorded elsewhere.

## Gate Outcome

CP3 passes only when **all** boxes in G1–G8 are checked. Partial completion does
not authorize advancing to Phase 04 per Master Graph §19 ("Advance only after
VERIFICATION.md passes").
