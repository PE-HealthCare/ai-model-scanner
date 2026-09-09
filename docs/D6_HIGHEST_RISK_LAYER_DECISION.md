# D6 — Highest-Risk-Layer Selection & Reporting

**Owner:** P3 reporting / security report surface  
**Phase:** Phase 6 — Risk Integration + Demo  
**Gate:** CP6  
**Status:** **UNRESOLVED — DECISION BOUNDARY REVISED; EXACT SELECTION RULE PENDING**

## 1. Purpose

D6 defines how the final security report identifies the highest-risk neural-network layer from authoritative per-layer evidence preserved by the upstream pipeline.

D6 is a **selection/reporting decision**, not a second model-level risk aggregation algorithm.

## 2. Architectural Boundary

The intended relationship is:

```text
P1
↓
per-layer feature / layer identity
↓
D7 validity / degeneracy handling
↓
D5 per-layer → model-level risk aggregation
│
├── model-level risk evidence
│
└── preserved per-layer evidence + identity
                    ↓
                   D6
                    ↓
          highest-risk-layer selection
                    ↓
               P3 security report
```

The exact ownership boundary between P1's production/preservation of layer identity and P3's final selection/reporting must be reconciled against the authoritative Master Graph before D6 is locked. The current execution state treats D6 as P3-owned reporting semantics; no implementation change is authorized from this draft alone.

## 3. D6 Inputs

D6 SHALL consume only authoritative, valid per-layer evidence already produced/preserved by the upstream pipeline.

The final input contract must explicitly identify:

- the authoritative layer identifier;
- the per-layer anomaly/risk evidence available to D6;
- validity status after applicable D7 handling;
- any provenance/contract information required to ensure the evidence is current.

D6 SHALL NOT manufacture new upstream evidence.

## 4. D6 Does NOT Own

D6 SHALL NOT:

- calculate static steganalysis features;
- calculate `S_static` normalization;
- calculate behavioral entropy or `S_behavior`;
- calculate `P_tamper`;
- create a layer-level `P_tamper` unless an authoritative upstream contract explicitly defines one;
- create a layer-level `S_behavior` unless an authoritative upstream contract explicitly defines one;
- calculate or modify MRS;
- modify PASS / REVIEW / FAIL thresholds;
- replace or duplicate D5's per-layer → model-level risk aggregation;
- introduce a new statistical baseline or threshold merely for layer selection;
- use TreeSHAP as a highest-risk-layer algorithm.

## 5. TreeSHAP Separation

TreeSHAP and highest-risk-layer reporting are separate relationships.

```text
TreeSHAP:
feature → classifier contribution / explanation

D6:
per-layer evidence + layer identity → highest-risk-layer report
```

TreeSHAP SHALL NOT be used as a shortcut for selecting the highest-risk layer, nor used to create a layer-risk score unless an explicit future decision changes this contract.

## 6. Selection Rule — Still Pending

The exact deterministic selection rule remains **DECISION REQUIRED**.

Before locking it, the project must determine whether D5's final per-layer evidence contract already implies the selection operation. In particular, an `argmax`-style selection must not be assumed merely because it is implementation-convenient.

No choice among `max`, weighted scoring, thresholding, voting, or another mechanism is authorized by this draft.

## 7. Layer Granularity

D6 SHALL use the authoritative layer identity supplied by the upstream contract.

D6 SHALL NOT invent a new tensor/module/block hierarchy solely for reporting.

The exact identifier semantics must be confirmed before implementation.

## 8. Edge Cases

The locked decision must define deterministic handling for:

- **Tie:** do not silently select an arbitrary layer; exact tie behavior must be explicitly specified.
- **No eligible layer:** report highest-risk-layer as unavailable and do not fabricate a fallback.
- **Single eligible layer:** that layer is the highest-risk layer, subject to the final validity contract.
- **Invalid/missing per-layer evidence:** reject/block the affected selection rather than impute or fabricate values.

D6 does not introduce a separate special rule such as “fewer than five layers”; upstream D7 validity/degeneracy rules remain authoritative.

## 9. Quantized Models

D6 SHALL NOT invent behavioral evidence for quantized models.

Quantized models follow the authoritative format-adaptive upstream path. If valid per-layer evidence is available, D6 applies the same locked selection semantics to that evidence unless an explicit decision states otherwise.

The absence of `S_behavior` for quantized models does not by itself require a separate D6 algorithm.

## 10. Dependencies

### Direct decision dependencies

- D5 per-layer evidence contract and its preservation of layer identity;
- D7 validity/degeneracy handling;
- authoritative layer identity semantics.

### Execution dependencies

Phase 6 requires the current project gates and artifacts specified by the Phase 6 plan, including CP4 PASS, CP5 PASS, and VERIFIED-REAL/current upstream artifacts.

D6 does not independently redefine those checkpoint dependencies.

## 11. Required Pre-Lock Audit

Before D6 is resolved:

1. Reconcile the authoritative Master Graph's P1/P3 ownership wording for highest-risk-layer.
2. Inspect the authoritative D5 contract and determine exactly what per-layer evidence survives to D6.
3. Confirm the layer identifier/granularity.
4. Determine whether the final selection operation is already implied by D5 or remains an explicit project decision.
5. Define tie and no-eligible-layer behavior.
6. Confirm quantized handling without introducing behavioral evidence.
7. Confirm TreeSHAP remains feature-level only.
8. Record the final decision in `STATE.md` before implementation.

## 12. Implementation Gate

No Phase 6 dashboard implementation may rely on this draft as if D6 were resolved.

After D6 is explicitly locked:

```text
D6 locked
↓
update authoritative decision records
↓
implement Phase 6 report selection
↓
run D6-specific tests
↓
run Phase 6 integration / E2E verification
↓
CP6
```

## 13. Verification Requirements

At minimum:

- valid per-layer evidence selects the expected layer;
- repeated execution is deterministic;
- ties follow the locked rule;
- no eligible layer produces no fabricated layer;
- invalid/missing evidence is handled safely;
- single-layer case is handled correctly;
- quantized path is handled according to the locked rule;
- TreeSHAP is not used for layer selection;
- report displays the authoritative layer identity;
- D6 does not recalculate MRS or upstream risk signals.

## 14. Current Classification

**D6 remains UNRESOLVED.**

What is now resolved at the planning level is the **boundary**:

> D6 is highest-risk-layer **selection and reporting from authoritative per-layer evidence**; it is not a new model-level risk aggregation stage and is not TreeSHAP attribution.

The exact selection rule, final ownership wording, input contract, tie semantics, and implementation remain pending explicit resolution.
