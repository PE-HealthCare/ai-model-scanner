# D5 Part 2 — Model-Level `S_static` Semantics

**Status:** RESOLVED / LOCKED — Part 2 sub-decision only  
**Parent decision:** D5 — Per-layer → model-level risk aggregation  
**Date:** 2026-09-09

## 1. Decision

`S_static` is the **bounded model-level summary of valid static anomaly evidence across the model's eligible layers**, derived solely from the authoritative P1 static-analysis evidence and the locked D7 robust Z/MAD validity and degeneracy rules.

`S_static` represents the model's overall **static evidence of anomalous weight manipulation**. It is the model-level static evidence consumed by the frozen MRS formulas.

This semantic definition does **not** select the mathematical operator used to reduce per-layer evidence to `S_static`. That operator remains a separate unresolved D5 sub-decision.

## 2. Required separation of meanings

The following signals remain distinct:

- **`S_static`** — model-level static anomaly evidence from weight-level statistical analysis;
- **`P_tamper`** — model-level classifier output from the P3 LightGBM path;
- **`S_behavior`** — model-level behavioral anomaly evidence from the bounded P2 STRIP path;
- **TreeSHAP** — feature-level classifier attribution/explanation;
- **D6 highest-risk layer** — final layer selection/reporting from authoritative per-layer evidence.

No one of these signals is a substitute for another.

## 3. Evidence lineage

```text
P1 per-layer statistical feature evidence
                ↓
       intra-model layer-vs-layer baseline
                ↓
       D7 robust Z / MAD validity handling
                ↓
       valid per-layer anomaly evidence
                ↓
       D5 model-level aggregation
                ↓
          model-level S_static
                ↓
       frozen MRS formula
```

The authoritative Master Graph specifies the static path as:

```text
per-layer feature evidence
        ↓
X vs intra-model X_base
        ↓
Z = (X - median(X_base)) / (1.4826 * MAD(X_base))
        ↓
S_static ∈ [0,1]
```

The exact reduction from valid per-layer evidence to model-level `S_static` is intentionally not specified by this Part 2 decision.

## 4. Semantic requirements for the eventual operator

The eventual D5 operator must be evaluated against the following requirements before it is locked:

1. **Bounded output:** produce `S_static` in the range required by the frozen MRS contract, `[0,1]`.
2. **Static-only provenance:** use only the authoritative static evidence assigned to D5; do not import behavioral evidence, TreeSHAP attribution, or unrelated classifier outputs into `S_static`.
3. **Validity-aware:** respect D7 validity and degeneracy states and do not override blocked/invalid evidence.
4. **Model-level meaning:** represent overall static anomaly evidence for the model rather than silently becoming a highest-risk-layer selector.
5. **Deterministic and reproducible:** the same authoritative evidence must yield the same `S_static`.
6. **No hidden calibration:** do not introduce arbitrary thresholds, learned weights, or parameters unless separately evidence-backed and explicitly authorized.
7. **Layer-identity independence:** aggregation must operate on the authoritative evidence set without changing the meaning of evidence because layer names or ordering change.
8. **D6 preservation:** aggregation must not discard the authoritative per-layer evidence and layer identity required for downstream highest-risk-layer selection/reporting.

These are requirements for evaluating candidate operators; they do not choose one.

## 5. What this decision does NOT authorize

This Part 2 decision does not authorize or define:

- `max`, mean, median, top-k, weighted aggregation, voting, or any other D5 operator;
- a new per-layer score name such as `S_static_layer`;
- layer-level `P_tamper`;
- layer-level `S_behavior`;
- a new baseline or threshold;
- TreeSHAP-based layer selection;
- D6 highest-risk-layer selection;
- any change to the frozen MRS formulas;
- any change to the P1 feature definitions or D7 validity rules.

## 6. Parent D5 status

This sub-decision resolves **Part 2 only**: the semantic target and evaluation requirements for model-level `S_static`.

D5 as a whole remains:

> **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING**

The next D5 sub-decision is to determine the threat-model behavior the aggregation must capture, especially localized versus distributed static manipulation, before selecting and evidence-testing candidate operators.
