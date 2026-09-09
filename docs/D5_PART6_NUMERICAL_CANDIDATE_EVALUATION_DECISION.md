# D5 Part 6 — Numerical Candidate Evaluation

**Status:** RESOLVED / LOCKED — Part 6 sub-decision only  
**Parent decision:** D5 — Per-layer → model-level risk aggregation  
**Date:** 2026-09-09

## 1. Decision

D5 Part 6 locks the **evidence-backed numerical evaluation methodology** for the remaining mathematically viable constructions of model-level `S_static`.

Part 6 does **not** select the final D5 operator.

The purpose of Part 6 is to evaluate the complete mathematical reduction from the authoritative D7-governed per-layer × per-feature evidence entering D5 to a bounded model-level `S_static`, without silently introducing an implementation-defined normalization or aggregation rule.

## 2. Locked evaluation boundary

Part 5 establishes that D5 receives structured evidence at the layer × feature level:

```text
P1 feature evidence
        ↓
intra-model feature-specific baseline
        ↓
D7 robust Z / validity handling
        ↓
(layer, feature, evidence_value, validity, provenance)
        ↓
D5 candidate evaluation
        ↓
S_static ∈ [0,1]
```

Therefore Part 6 must evaluate the **full reduction path**, including any candidate bounded-evidence mapping required before model-level aggregation.

Part 6 must not assume that raw `Z` is already a probability or `[0,1]` quantity. Raw `Z` is signed and unbounded.

## 3. Candidate-evaluation structure

The evaluation is separated into two conceptual stages where required:

### Stage A — bounded evidence mapping

Candidate mappings from valid anomaly magnitude to bounded evidence may be evaluated only if they are:

- deterministic;
- monotone in anomaly magnitude;
- parameter-free unless a parameter is independently evidence-backed and explicitly authorized;
- symmetric with respect to anomaly direction where the threat semantics require magnitude rather than signed direction;
- bounded in the range required by the downstream aggregation;
- explicitly documented as a mathematical transformation rather than silently embedded in implementation.

A two-sided normal-CDF-derived mapping such as

```text
e = 2 * Phi(|Z|) - 1
```

is retained as a **candidate for evaluation only**. It is not authorized by Part 6 as the final mapping, and no Gaussian-distribution assumption may be claimed merely because the robust-Z formula uses the 1.4826 MAD consistency factor.

### Stage B — model-level aggregation

Candidate aggregators are evaluated after any candidate bounded-evidence mapping required by the construction.

The parameter-free cumulative-evidence family

```text
S_static = 1 - product_i (1 - e_i)
```

is retained as the leading candidate from Part 4, but remains unselected until numerical evaluation establishes that its complete reduction path is appropriate.

Part 6 does **not** authorize flattening all layer × feature observations into one undifferentiated product. Feature/layer reduction must itself be evaluated for sensitivity and layer-count dependence.

## 4. Hierarchical evaluation requirement

Because Part 5 preserves ten feature identities for each eligible layer, Part 6 must explicitly test whether a candidate should reduce evidence hierarchically:

```text
per-feature evidence
        ↓
per-layer evidence
        ↓
model-level S_static
```

versus another mathematically defined reduction.

The evaluation must detect whether a construction is merely increasing because the number of feature/layer observations increases.

No new `S_static_layer` or equivalent production contract is authorized by this decision. A temporary mathematical intermediate used solely for candidate comparison must not be treated as an implementation contract or final decision.

## 5. Required numerical test families

Every surviving candidate construction must be evaluated against the following controlled cases.

### 5.1 Localized manipulation

A small subset of eligible layers contains substantially stronger anomaly evidence while the remaining eligible layers are normal or near-normal.

Requirement: concentrated evidence must materially increase `S_static` and must not be arbitrarily diluted by normal layers.

### 5.2 Distributed manipulation

Many eligible layers contain moderate anomaly evidence without one extreme layer.

Requirement: broad moderate evidence must materially increase `S_static`.

### 5.3 Mixed manipulation

Strong concentrated evidence coexists with weaker evidence distributed across additional layers.

Requirement: the construction must retain both evidence patterns coherently.

### 5.4 Dilution test

Compare an evidence set against the same set with additional zero/normal evidence.

Requirement: adding unrelated normal evidence must not arbitrarily erase existing nonzero anomaly evidence.

### 5.5 Layer-count test

Evaluate equivalent evidence patterns across different eligible layer counts.

Requirement: the score must not become high or low solely because a model has more layers.

### 5.6 Feature-count test

Evaluate equivalent evidence patterns while varying the number of eligible feature observations.

Requirement: the score must not be driven solely by the number of observations.

### 5.7 Zero and near-zero evidence

Test exact zero evidence and small valid anomaly evidence.

Requirement: zero evidence behaves deterministically and small valid evidence does not trigger an undocumented threshold.

### 5.8 Invalid and blocked evidence

Test D7 invalid values, unavailable baselines, and `DEGENERATE_DEVIATION` states.

Requirement: invalid/blocked evidence is never silently converted to zero, imputed, or treated as normal evidence. D7 remains authoritative.

### 5.9 Monotonicity

For every eligible evidence element, strengthening valid anomaly evidence must not decrease the resulting `S_static`.

### 5.10 Boundedness

Every candidate reaching the final model-level output must satisfy the required `S_static ∈ [0,1]` contract without arbitrary clipping that hides an invalid mathematical construction.

### 5.11 Determinism

Identical authoritative evidence must produce identical `S_static`.

### 5.12 Layer-order invariance

Permuting layer order or feature-record order must not change `S_static`.

## 6. Candidate disposition framework

Part 6 does not predeclare a winner. Candidates are evaluated against the locked requirements from Parts 2–5.

A candidate is rejected if it materially fails one or more mandatory requirements, including:

- localized sensitivity;
- distributed sensitivity;
- mixed-pattern behavior;
- monotonicity;
- dilution resistance;
- layer-count or feature-count invariance;
- D7 compliance;
- deterministic behavior;
- bounded output;
- layer-order invariance;
- absence of unapproved parameters or hidden calibration.

A candidate may only advance to Part 7 if its complete mathematical construction is supported by the numerical evaluation and remains compatible with the frozen architecture and D5 semantics.

## 7. External cross-verification boundary

Independent robust-statistics literature supports the methodology of testing competing aggregation behaviors rather than assuming one universally optimal operator. Robust anomaly-detection literature identifies mean sensitivity to aberrant observations and the robustness of median/MAD; robust aggregation literature similarly documents trade-offs among mean, median, trimmed and other aggregation families.

These external sources are methodological cross-checks only. They do not determine the project's operator because the authoritative P1/D7 evidence semantics and the locked localized/distributed/mixed threat model remain primary.

In particular, the literature does **not** justify assuming that the robust-Z evidence is Gaussian or that the CDF mapping above is correct for this project's data. That mapping therefore remains a candidate to be empirically evaluated.

## 8. Explicit non-decisions

Part 6 does **not** authorize or define:

- the final D5 aggregation operator;
- a production `S_static_layer`;
- a production `e_i` contract;
- a final `Z → [0,1]` mapping;
- a Gaussian-distribution assumption for P1/D7 evidence;
- flattening all layer × feature evidence into a single cumulative product;
- max, mean, median, top-k, trimmed mean, weighted aggregation, voting, or cumulative aggregation as the final operator;
- new baselines or thresholds;
- layer-level `P_tamper` or `S_behavior`;
- TreeSHAP-based layer selection;
- D6 highest-risk-layer selection;
- changes to P1 feature definitions;
- changes to D7 validity/degeneracy rules;
- changes to the frozen MRS formulas.

## 9. Part 7 handoff

After Part 6 evaluation is completed, the numerical evidence must identify the surviving complete mathematical construction. **D5 Part 7** will then lock the exact operator and any mathematically necessary transformation/parameter semantics.

No production implementation of the D5 operator should precede that Part 7 lock.

## 10. Parent D5 status

This sub-decision resolves **Part 6 only**: the candidate-evaluation methodology and acceptance/rejection criteria.

D5 remains:

> **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING**
