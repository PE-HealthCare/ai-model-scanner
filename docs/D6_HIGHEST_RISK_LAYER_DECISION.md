# D6 — Highest-Risk-Layer Selection & Reporting

**Owner:** P3 reporting / security report surface  
**Phase:** Phase 6 — Risk Integration + Demo  
**Gate:** CP6  
**Status:** **RESOLVED / LOCKED — PARTS 1 & 2**

## 1. Purpose

D6 defines how the final security report identifies the highest-risk neural-network layer from authoritative per-layer evidence preserved by the upstream pipeline.

D6 is a **selection/reporting decision**, not a second model-level risk aggregation algorithm.

## 2. Locked Architectural Boundary

The locked relationship is:

```text
P1
↓
authoritative per-layer static evidence + authoritative layer identity
↓
D7 validity / degeneracy handling
↓
D5 exact per-layer → model-level aggregation
│
├── model-level static risk evidence
│
└── preserved per-layer evidence + identity
                    ↓
                   D6
                    ↓
          highest-risk-layer selection
                    ↓
               P3 security report
```

**Ownership lock:**

- **P1 owns authoritative production and preservation of per-layer evidence and authoritative layer identity.**
- **P3/D6 owns final highest-risk-layer selection and security-report presentation.**
- P1 does not create a competing final D6 selection result.
- D6 does not recalculate P1 evidence or duplicate D5 model-level aggregation.

This reconciles the historical ownership wording that listed “highest-risk layer” under P1 by distinguishing **production/preservation of the evidence and identity** from **final selection/reporting**. The current architecture assigns static analysis to P1 and reporting/dashboard responsibilities to P3; this wording preserves both responsibilities without introducing a fourth owner or redesigning the pipeline.

## 3. Locked D6 Input Contract

D6 SHALL consume preserved upstream per-layer evidence with its authoritative identity and validity/provenance context.

Conceptually, each D6 input record contains:

```text
{
  layer_id,
  per_layer_evidence,
  validity_state,
  provenance
}
```

The exact serialization/schema remains an implementation contract and is not invented by this decision.

The following semantics are locked:

- `layer_id` is the authoritative upstream layer identifier.
- `per_layer_evidence` is evidence already produced through the authoritative P1 → baseline/D7 → D5 path; D6 does not manufacture a new evidence quantity.
- `validity_state` preserves applicable D7 validity/degeneracy semantics.
- `provenance` is retained sufficiently to establish that the evidence belongs to the current upstream production path; exact fields are an implementation/schema matter.

Layer identity SHALL remain attached to its evidence throughout the handoff to D6.

## 4. Exact Selection Rule — LOCKED

For every eligible layer `l`, D6 SHALL use the authoritative D5 per-layer reduction:

\[
E(l)=\max_f\left(\frac{|Z(l,f)|}{1+|Z(l,f)|}\right)
\]

where only D7-valid finite layer×feature evidence participates.

D6 SHALL select the highest-risk layer as:

\[
\boxed{l^*=\operatorname*{arg\,max}_{l\in L_{eligible}} E(l)}
\]

Therefore D6 performs **selection over authoritative per-layer evidence**. It does not create a new risk score or a second aggregation stage.

D6 SHALL NOT select a layer using model-level `S_static`, MRS, `P_tamper`, `S_behavior`, or TreeSHAP contribution.

## 5. Eligibility and Edge Cases — LOCKED

### 5.1 Valid evidence

A layer is eligible when its authoritative D5 per-layer value `E(l)` is finite and derived only from D7-valid finite evidence.

### 5.2 Invalid or missing evidence

Invalid, missing, NaN, or infinite evidence SHALL NOT be imputed, converted to zero, or otherwise fabricated. A layer without eligible evidence is excluded from the D6 candidate set.

### 5.3 `DEGENERATE_DEVIATION`

D6 SHALL preserve the D7 state. `DEGENERATE_DEVIATION` SHALL NOT be silently converted into ordinary numeric evidence or treated as a zero anomaly for selection.

### 5.4 Unavailable baseline

When the upstream baseline is unavailable, D6 SHALL NOT fabricate per-layer evidence. No affected layer is eligible solely because it exists.

### 5.5 No eligible layer

If no layer has eligible evidence, D6 SHALL report:

```text
highest_risk_layer = unavailable
```

No fallback layer is fabricated.

### 5.6 Single eligible layer

If exactly one layer is eligible, that layer SHALL be selected.

### 5.7 Ties

If multiple eligible layers have exactly the same maximum `E(l)`, D6 SHALL resolve the tie deterministically using the **canonical ordering of the authoritative `layer_id`** and select the first identifier in that ordering.

D6 SHALL NOT use dashboard order, dictionary insertion order, tensor position, or another implementation-dependent ordering as a tie-breaker.

No new layer-ID naming or ordering scheme is introduced by this decision; the canonical ordering semantics are inherited from the authoritative layer-identity contract.

## 6. D6 Does NOT Own

D6 SHALL NOT:

- calculate static steganalysis features;
- recalculate or redefine `S_static`;
- calculate behavioral entropy or `S_behavior`;
- calculate `P_tamper`;
- create a layer-level `P_tamper` unless an authoritative upstream contract explicitly defines one;
- create a layer-level `S_behavior` unless an authoritative upstream contract explicitly defines one;
- calculate or modify MRS;
- modify PASS / REVIEW / FAIL thresholds;
- replace or duplicate D5's per-layer → model-level risk aggregation;
- introduce a new statistical baseline or threshold merely for layer selection;
- invent a new tensor/module/block hierarchy for reporting;
- use TreeSHAP as a highest-risk-layer algorithm.

## 7. D7 Validity Boundary

D6 SHALL respect D7 as the upstream authority for evidence validity and degeneracy.

D6 SHALL NOT silently rewrite D7 states or manufacture replacement evidence. D7 remains authoritative for finite/non-finite handling, MAD degeneracy, and baseline availability.

## 8. Layer Granularity

D6 SHALL use the authoritative layer identity supplied by the upstream contract.

D6 SHALL NOT invent a new layer/module/block hierarchy solely for reporting.

The identifier semantics are inherited from the authoritative upstream contract rather than reconstructed from dashboard order, tensor position, or implementation convenience.

## 9. TreeSHAP Separation

TreeSHAP and highest-risk-layer reporting remain separate relationships:

```text
TreeSHAP:
feature → classifier contribution / explanation

D6:
per-layer evidence + layer identity → highest-risk-layer report
```

TreeSHAP SHALL NOT be used as a shortcut for layer selection and SHALL NOT create a layer-risk score under this decision.

## 10. Quantized Models

D6 SHALL NOT invent behavioral evidence for quantized models.

If valid per-layer static evidence exists on the quantized static-analysis path, D6 applies the same locked selection rule to that evidence.

The absence of `S_behavior` for quantized models does not create a separate D6 algorithm.

## 11. Relationship to D5

D5 remains the owner of model-level static aggregation:

\[
S_{static}=1-\prod_l(1-E(l))
\]

D6 does not use this model-level value to reconstruct a layer. Instead:

```text
D5:
per-layer E(l) values → model-level S_static

D6:
per-layer E(l) values → argmax → highest-risk layer
```

This preserves the distinction between **model-level aggregation** and **layer-level reporting selection**.

## 12. Determinism and Reporting

For identical authoritative upstream evidence and identical authoritative layer identities, D6 SHALL produce the same selected layer on repeated execution.

The report SHALL preserve the authoritative selected `layer_id` and SHALL expose the corresponding authoritative per-layer evidence value `E(l)` where the report schema permits it.

Where the upstream contract preserves the feature identity attaining the layer reduction, the report MAY identify that feature as supporting evidence; D6 SHALL NOT invent a separate feature-scoring method.

## 13. Verification Requirements

At minimum, D6 implementation tests SHALL verify:

1. a valid set of per-layer evidence selects the layer with the largest `E(l)`;
2. repeated execution is deterministic;
3. exact ties follow canonical authoritative `layer_id` ordering;
4. no eligible layer produces `highest_risk_layer = unavailable`;
5. invalid/missing evidence is not imputed or fabricated;
6. `DEGENERATE_DEVIATION` is not converted to ordinary evidence;
7. unavailable baseline does not fabricate a candidate;
8. a single eligible layer is selected;
9. quantized valid static evidence follows the same selection rule;
10. TreeSHAP is not used for layer selection;
11. the report displays the authoritative layer identity;
12. D6 does not recalculate MRS or upstream risk signals;
13. layer-order permutation does not change the selected layer except where canonical tie ordering itself determines the documented tie result.

## 14. Implementation Gate

With D6 Parts 1 and 2 locked, the decision gate is complete. The implementation sequence is:

```text
D6 Parts 1 & 2 locked
↓
update authoritative decision/status records and STATE.md
↓
implement Phase 6 report selection
↓
run D6-specific tests
↓
run Phase 6 integration / E2E verification
↓
CP6
```

This decision does not itself claim CP6 PASS or completed implementation.

## 15. Final Classification

**D6: RESOLVED / LOCKED.**

> P1 owns authoritative production/preservation of per-layer evidence and layer identity; P3/D6 owns final highest-risk-layer selection and security-report presentation. D6 selects `argmax E(l)` over eligible D5 per-layer evidence, with deterministic canonical-layer-ID tie handling, while respecting D7 validity/degeneracy and without recalculating upstream signals, inventing layer granularity, inventing quantized behavioral evidence, or using TreeSHAP for layer selection.
