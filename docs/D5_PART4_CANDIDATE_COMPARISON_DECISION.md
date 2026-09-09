# D5 Part 4 — Mathematical Candidate Comparison

**Status:** RESOLVED / LOCKED — Part 4 sub-decision only  
**Parent decision:** D5 — Per-layer → model-level risk aggregation  
**Date:** 2026-09-09

## 1. Decision

D5 Part 4 locks the **candidate-comparison boundary and elimination criteria** for the eventual model-level `S_static` aggregation operator.

Part 4 does **not** select the final mathematical operator.

The final operator remains pending until the authoritative mathematical representation of the eligible per-layer evidence entering D5 is explicitly established. In particular, this decision does not invent a new bounded per-layer scalar such as `e_i` or `S_static_layer`.

## 2. Candidate families evaluated

The following candidate families were compared against the requirements locked by D5 Parts 1–3.

| Candidate | Localized sensitivity | Distributed sensitivity | Mixed-pattern behavior | Part 4 disposition |
|---|---|---|---|---|
| `max` | Strong | Weak | Partial | Reject as sole operator candidate |
| Mean | Weak when a small number of layers dominate | Strong | Partial | Reject as sole operator candidate |
| Median | Weak for minority localized evidence | Limited | Weak | Reject |
| Trimmed mean | Weak for concentrated extremes | Strong | Weak for localized evidence | Reject |
| Top-k mean | Strong | Strong | Strong | Not selected; introduces an additional `k` decision/parameter |
| Parameter-free cumulative-evidence family | Potentially strong | Potentially strong | Potentially strong | Carry forward only if the upstream evidence contract legitimately supplies bounded per-layer evidence |

These dispositions are requirements-driven, not implementation-driven. No disposition above authorizes implementation of the candidate or changes the frozen MRS formulas.

## 3. Candidate comparison reasoning

### 3.1 Max

A maximum operator is naturally sensitive to a strongly anomalous layer and therefore covers the localized threat model well. However, it can remain insensitive to a distributed pattern in which many layers are moderately anomalous but no single layer dominates.

**Disposition:** reject as the sole D5 operator.

### 3.2 Mean

A mean can represent broad distributed evidence, but a small number of strongly anomalous layers can be diluted by many normal layers. The mean is also classically sensitive to extreme observations, which makes its behavior dependent on the scale and representation of the incoming evidence.

**Disposition:** reject as the sole D5 operator.

### 3.3 Median

A median is robust to minority outliers, but that robustness is counterproductive for the localized threat model when a small number of compromised layers are precisely the evidence that must materially affect model-level static risk.

**Disposition:** reject.

### 3.4 Trimmed mean

A trimmed mean can improve robustness to extreme values, but deliberately removing extremes can suppress exactly the concentrated evidence that D5 Part 3 requires the eventual operator to preserve.

**Disposition:** reject for the primary D5 objective.

### 3.5 Top-k mean

A top-k mean can combine localized and distributed sensitivity, but it introduces an additional parameter (`k`) or selection rule. D5 has not authorized such a parameter, and selecting it merely for implementation convenience would violate the unresolved-decision boundary.

**Disposition:** do not select at Part 4; it may only be reconsidered if a future decision explicitly defines and justifies the required parameter semantics.

### 3.6 Parameter-free cumulative-evidence family

If the authoritative per-layer evidence is eventually defined as a valid bounded quantity `e_i ∈ [0,1]`, a cumulative-evidence family such as

`S_static = 1 - ∏_i (1 - e_i)`

has attractive qualitative properties for the Part 3 threat model:

- one strong layer can materially increase `S_static`;
- multiple moderate layers can accumulate into meaningful model-level evidence;
- mixed strong and moderate evidence is retained;
- adding zero-evidence normal layers does not dilute an existing nonzero result;
- the function is deterministic and monotone in each `e_i`;
- the result is naturally bounded in `[0,1]` when all `e_i` are in `[0,1]`.

However, **Part 4 does not authorize this formula**. The current D5 contract has not established that a bounded per-layer scalar `e_i` exists, what it means, or how it would be derived from the authoritative P1/D7 evidence. Introducing such a scalar or transformation here would silently create a new upstream semantic contract.

**Disposition:** retain only as a candidate family for later evaluation after the evidence representation is locked.

## 4. Cross-verification against external statistical literature

External literature supports the need to distinguish isolated/concentrated contamination from broader contamination and to avoid assuming that a simple aggregation rule is universally robust. Robust anomaly-detection literature describes the mean as sensitive to aberrant observations and the median/MAD family as more resistant to outliers. Recent robust-aggregation work likewise shows that simple or weighted averages can be vulnerable to contamination, while robust alternatives trade off different robustness and efficiency properties.

These sources are used only as independent methodological cross-checks. They are **not** treated as authority for selecting the D5 operator because the project's authoritative input semantics and threat model remain primary.

## 5. Locked evaluation requirements for the eventual operator

Before D5's exact operator is locked, the candidate must be evaluated against all of the following:

1. **Localized sensitivity** — concentrated strong evidence can materially increase `S_static`.
2. **Distributed sensitivity** — broad moderate evidence can materially increase `S_static` without requiring one extreme layer.
3. **Mixed-pattern behavior** — concentrated and distributed evidence combine coherently.
4. **Monotonicity** — strengthening valid anomaly evidence cannot reduce `S_static`.
5. **Dilution resistance** — unrelated normal layers cannot arbitrarily erase strong localized evidence.
6. **Determinism** — identical authoritative evidence produces identical output.
7. **D7 compliance** — invalid, unavailable, or blocked evidence states remain governed by D7.
8. **D6 preservation** — aggregation must not destroy authoritative per-layer evidence or layer identity needed for highest-risk-layer reporting.
9. **Bounded output** — the eventual `S_static` must satisfy the Part 2 semantic requirement of a bounded model-level static evidence summary.
10. **No hidden calibration** — the operator must not introduce unapproved learned or empirical parameters.
11. **Layer-identity independence** — the model-level scalar must summarize evidence rather than select a layer; D6 remains the downstream selection/reporting boundary.

## 6. Explicit non-decisions

Part 4 does **not** authorize or define:

- a final D5 aggregation formula;
- `e_i` or `S_static_layer`;
- a per-layer probability;
- a Z-to-probability or Z-to-score transformation;
- max, mean, median, top-k, weighted aggregation, voting, or any other final operator;
- layer-level `P_tamper`;
- layer-level `S_behavior`;
- a new baseline or threshold;
- TreeSHAP-based layer selection;
- D6 highest-risk-layer selection;
- changes to the frozen MRS formulas;
- changes to P1 feature definitions or D7 validity rules.

## 7. Next D5 sub-decision

The next required sub-decision is **Part 5 — authoritative per-layer evidence representation**:

> What exact mathematical object, with what validity/provenance semantics, reaches D5 from the P1 → intra-model baseline → D7 path for each eligible layer?

Once that representation is locked, the remaining candidate families can be evaluated numerically against localized, distributed, mixed, layer-count, zero-evidence, invalid/blocked, monotonicity, boundedness, and determinism cases. Only then should the exact D5 operator be selected and locked.

## 8. Parent D5 status

This sub-decision resolves **Part 4 only**: candidate comparison, elimination, and the boundary for carrying candidates forward.

D5 as a whole remains:

> **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING**
