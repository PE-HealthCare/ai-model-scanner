# D5 Part 5 — Authoritative Per-Layer Evidence Representation

**Status:** RESOLVED / LOCKED — Part 5 sub-decision only  
**Parent decision:** D5 — Per-layer → model-level risk aggregation  
**Date:** 2026-09-09

## 1. Decision

The authoritative mathematical input to D5 is the **D7-governed per-layer, per-feature static anomaly evidence set** produced from P1's authoritative feature evidence and the locked intra-model layer-vs-layer baseline.

D5 receives evidence with, at minimum:

- authoritative layer identity;
- authoritative feature identity;
- the corresponding D7-governed anomaly evidence (`Z` where the D7 state permits a numeric value);
- D7 validity/degeneracy state;
- provenance sufficient to preserve the P1 → baseline → D7 lineage.

The evidence remains structured at the **layer × feature** level when it enters D5. Part 5 does not collapse features into a new scalar per-layer score.

## 2. Authoritative lineage

```text
P1 per-layer feature evidence
        ↓
feature-specific intra-model layer-vs-layer baseline
        ↓
D7 robust Z / MAD validity and degeneracy handling
        ↓
D7-governed per-layer × per-feature evidence
        ↓
D5 model-level aggregation
        ↓
S_static ∈ [0,1]
```

For a valid numeric observation, the authoritative upstream form is:

```text
Z(l,f) = [X(l,f) - median(X_base,f)]
        / [1.4826 × MAD(X_base,f)]
```

The `Z` value is evidence supplied to D5; it is **not itself a bounded probability or a `[0,1]` score**.

## 3. Required evidence object

Conceptually, D5 operates on a collection of records of the form:

```text
{
  layer_id,
  feature_id,
  evidence_value,
  validity_state,
  provenance
}
```

The exact serialization/schema of this object is an implementation contract to be defined separately. This decision locks the mathematical information that must be preserved, not a new JSON schema.

The authoritative evidence must remain traceable back to the P1 feature value and its intra-model baseline calculation.

## 4. D7 boundary

D7 remains authoritative for all validity and degeneracy behavior. D5 must not reinterpret, repair, impute, or silently replace D7 states.

In particular:

- finite nonzero MAD: retain the actual robust-Z calculation;
- exact MAD = 0 with target equal to the median: deterministic zero anomaly evidence;
- exact MAD = 0 with target different from the median: `DEGENERATE_DEVIATION`;
- 1–2 comparable layers: baseline unavailable and downstream baseline-dependent scoring is blocked;
- missing, NaN, +Inf, or -Inf numeric evidence: invalid; no imputation;
- very small nonzero MAD: use the actual MAD; no epsilon or near-zero replacement.

Only evidence explicitly eligible under D7 may participate in the eventual D5 operator.

## 5. No new normalization or per-layer score

Part 5 explicitly does **not** authorize a transformation from `Z` into a new bounded evidence scalar such as:

```text
S_static_layer
 e_i
layer probability
Z → sigmoid/probability
Z → arbitrary [0,1] mapping
```

Any such transformation would be a new mathematical contract and must be separately justified and locked if required by the final D5 operator.

This preserves the distinction between:

- authoritative upstream anomaly evidence;
- the eventual D5 model-level aggregation operator;
- the final bounded `S_static` consumed by the frozen MRS formulas.

## 6. Feature and layer preservation

D5 must preserve feature identity and layer identity while reducing evidence to model-level `S_static`.

This is required because:

- feature identity preserves the provenance of static evidence and prevents semantic mixing of the ten P1 features;
- layer identity is required for the downstream D6 highest-risk-layer path;
- D5 must not become an implicit layer-selection mechanism;
- TreeSHAP remains a separate P3 classifier-attribution path and is not substituted for D5 evidence.

The authoritative P1 implementation currently attaches `layer_name` to each extracted feature record and computes the finalized feature set layer-by-layer. The Part 5 contract therefore preserves that upstream identity rather than introducing a second layer namespace.

## 7. Eligibility and aggregation boundary

The eventual D5 operator must consume only the evidence records that are valid and eligible under D7.

D5 may not:

- invent evidence for blocked layers;
- replace invalid values with zeros or imputed values;
- treat unavailable baselines as normal evidence;
- change the meaning of a D7 degeneracy state;
- discard layer identity merely because an aggregation is being performed.

The exact treatment of a completely empty eligible evidence set remains a downstream operator/decision concern and is not silently resolved by Part 5.

## 8. Threat-model compatibility

This representation is intentionally prior to model-level reduction so that Part 6 can test candidate operators against all three patterns locked by D5 Part 3:

1. **Localized:** a small subset of layers carries substantially stronger anomaly evidence.
2. **Distributed:** many layers carry moderate anomaly evidence.
3. **Mixed:** concentrated strong evidence coexists with broader weaker evidence.

No candidate operator is selected by this Part 5 decision.

## 9. D5 Part 4 compatibility

Part 4 rejected or deferred candidate operators based on their behavior under the locked threat model and contract constraints. It retained the parameter-free cumulative-evidence family only as a candidate, conditional on a future legitimate bounded per-layer evidence representation.

Part 5 deliberately does **not** create that bounded representation. Therefore the cumulative family remains a Part 6 candidate rather than becoming an accidental Part 5 decision.

## 10. What this decision does NOT authorize

Part 5 does not authorize or define:

- the final D5 aggregation operator;
- `S_static_layer`;
- `e_i` or another bounded per-layer scalar;
- any `Z` normalization/mapping;
- max, mean, median, top-k, trimmed mean, weighted aggregation, voting, or cumulative aggregation as the final operator;
- a new baseline or threshold;
- layer-level `P_tamper` or `S_behavior`;
- TreeSHAP-based layer selection;
- D6 highest-risk-layer selection;
- changes to P1 feature definitions;
- changes to D7 validity/degeneracy rules;
- changes to the frozen MRS formulas.

## 11. Next D5 step

With the authoritative evidence representation now locked, **D5 Part 6** must evaluate the remaining mathematically viable aggregation families using explicit numerical test cases covering:

- localized, distributed, and mixed manipulation;
- different eligible layer counts;
- zero/near-zero anomaly evidence;
- invalid and blocked evidence;
- monotonicity;
- boundedness requirements for eventual `S_static`;
- dilution resistance;
- determinism and layer-order invariance.

Only after that evidence-backed comparison should Part 7 lock the exact D5 operator.

## 12. Parent D5 status

This sub-decision resolves **Part 5 only**.

D5 remains:

> **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING**
