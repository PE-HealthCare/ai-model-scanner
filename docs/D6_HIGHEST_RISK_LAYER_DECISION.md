# D6 — Highest-Risk-Layer Selection & Reporting

**Owner:** P3 reporting / security report surface  
**Phase:** Phase 6 — Risk Integration + Demo  
**Gate:** CP6  
**Status:** **PART 1 RESOLVED / LOCKED — AUTHORITY & EVIDENCE CONTRACT; PART 2 PENDING**

## 1. Purpose

D6 defines how the final security report identifies the highest-risk neural-network layer from authoritative per-layer evidence preserved by the upstream pipeline.

D6 is a **selection/reporting decision**, not a second model-level risk aggregation algorithm.

## 2. Part 1 Locked Architectural Boundary

Part 1 locks the following ownership and evidence boundary:

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

This resolves the historical ownership wording that listed “highest-risk layer” under P1 by distinguishing **production/preservation of the evidence and identity** from **final selection/reporting**. The current architecture assigns static analysis to P1 and reporting/dashboard responsibilities to P3; this Part 1 wording preserves both responsibilities without introducing a fourth owner or redesigning the pipeline.

## 3. Locked D6 Input Contract — Part 1

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

The exact serialization/schema remains an implementation contract and is not invented by Part 1.

The following semantics are locked:

- `layer_id` is the authoritative upstream layer identifier.
- `per_layer_evidence` is evidence already produced through the authoritative P1 → baseline/D7 → D5 path; D6 does not manufacture a new evidence quantity.
- `validity_state` preserves applicable D7 validity/degeneracy semantics.
- `provenance` is retained sufficiently to establish that the evidence belongs to the current upstream production path; exact fields are an implementation/schema matter.

Layer identity SHALL remain attached to its evidence throughout the handoff to D6.

## 4. D6 Does NOT Own

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

## 5. D7 Validity Boundary — Part 1 Lock

D6 SHALL respect D7 as the upstream authority for evidence validity and degeneracy.

Therefore D6 SHALL NOT silently:

- convert invalid evidence to zero;
- impute missing evidence;
- convert `DEGENERATE_DEVIATION` into normal evidence;
- fabricate evidence when the baseline is unavailable.

The exact selection treatment of these states belongs to Part 2's final selection/edge-case decision; Part 1 only locks that D6 cannot rewrite them into valid evidence.

## 6. Layer Granularity — Part 1 Lock

D6 SHALL use the authoritative layer identity supplied by the upstream contract.

D6 SHALL NOT invent a new layer/module/block hierarchy solely for reporting.

The identifier semantics must therefore be inherited from the authoritative P1 contract rather than reconstructed from dashboard order, tensor position, or implementation convenience.

## 7. TreeSHAP Separation — Part 1 Lock

TreeSHAP and highest-risk-layer reporting remain separate relationships:

```text
TreeSHAP:
feature → classifier contribution / explanation

D6:
per-layer evidence + layer identity → highest-risk-layer report
```

TreeSHAP SHALL NOT be used as a shortcut for layer selection and SHALL NOT create a layer-risk score under this decision.

## 8. Quantized Models — Part 1 Lock

D6 SHALL NOT invent behavioral evidence for quantized models.

If valid per-layer evidence exists on the quantized static-analysis path, D6 uses that authoritative evidence under the same selection contract to be finalized in Part 2.

The absence of `S_behavior` for quantized models does not create a separate D6 algorithm.

## 9. What Part 1 Does Not Resolve

Part 1 intentionally does **not** select the final mathematical operation used to identify the highest-risk layer.

The following remain Part 2 decisions:

- exact selection operation;
- tie semantics;
- no-eligible-layer behavior;
- single-layer behavior as a final selection rule;
- final invalid/degenerate eligibility treatment;
- exact implementation/reporting representation.

Part 1 therefore does not authorize `argmax`, thresholding, voting, weighted scoring, or another selection operation.

## 10. Verification Basis

Part 1 was cross-checked against the authoritative project graph and the current D6 boundary.

The cross-check confirms:

1. P1 is the static-analysis/evidence producer.
2. P3 owns ML/explainability/dashboard/reporting.
3. Layer identity must remain available for highest-risk-layer reporting.
4. Highest-risk-layer determination is separate from TreeSHAP attribution.
5. D6 is a reporting/selection boundary rather than a new model-level risk aggregation stage.
6. Quantized models do not receive invented behavioral evidence.
7. The frozen architecture and existing D5/D7 decisions are not changed by Part 1.

The historical Master Graph phrase that P1 is responsible for “highest-risk layer” is reconciled here as P1's responsibility for the authoritative evidence/identity needed for that determination; **final selection/reporting remains P3/D6-owned**.

## 11. Implementation Gate

Part 1 being locked does **not** authorize Phase 6 implementation yet.

The implementation gate remains:

```text
D6 Part 1 locked
↓
D6 Part 2 locked
↓
update authoritative decision/status records
↓
implement Phase 6 report selection
↓
run D6-specific tests
↓
run Phase 6 integration / E2E verification
↓
CP6
```

## 12. Current Classification

**D6 Part 1: RESOLVED / LOCKED.**

> P1 owns authoritative production/preservation of per-layer evidence and layer identity; P3/D6 owns final highest-risk-layer selection and security-report presentation. D6 consumes preserved upstream evidence without recalculating upstream signals, rewriting D7 validity, inventing layer granularity, inventing quantized behavioral evidence, or using TreeSHAP for layer selection.

**D6 Part 2 remains pending and will lock the exact selection operation and edge-case semantics.**
