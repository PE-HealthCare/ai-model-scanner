# D5 Part 1 — Authoritative Per-Layer Evidence

**Status:** RESOLVED / LOCKED — Part 1 sub-decision only  
**Parent decision:** D5 — Per-layer → model-level risk aggregation  
**Date:** 2026-09-09

## 1. Decision

The authoritative input evidence for D5 originates from **P1's per-layer statistical feature evidence**, evaluated against the model's **intra-model layer-vs-layer baseline** using the locked **D7 robust Z/MAD validity and degeneracy rules**.

Each layer's evidence must remain associated with its authoritative layer identity and its D7 validity state/provenance as it proceeds toward D5 and, where required, D6.

This Part 1 decision does **not** introduce a new per-layer score name or define the D5 aggregation operator.

## 2. Evidence lineage

```text
P1
↓
per-layer statistical feature evidence
↓
intra-model baseline (layer vs. layer)
↓
D7 robust Z / MAD validity and degeneracy handling
↓
valid per-layer anomaly evidence
↓
D5 model-level aggregation
```

The authoritative Master Graph specifies the static anomaly path as:

```text
per-layer feature evidence
        ↓
X vs intra-model X_base
        ↓
Z = (X - median(X_base)) / (1.4826 * MAD(X_base))
        ↓
S_static ∈ [0,1]
```

The exact reduction from per-layer evidence to model-level `S_static` remains the unresolved D5 operator decision.

## 3. D7 validity boundary

D7 remains authoritative for MAD validity and degeneracy handling:

- finite nonzero MAD: use the actual MAD directly;
- exact MAD = 0 with target equal to median: deterministic zero anomaly;
- exact MAD = 0 with target different from median: `DEGENERATE_DEVIATION`;
- 1–2 comparable layers: baseline evidence unavailable and downstream scoring requiring that baseline is blocked;
- missing, NaN, positive-infinity, or negative-infinity numeric data: invalid; no imputation;
- very small nonzero MAD: use the actual MAD; no epsilon or near-zero replacement.

D5 must not override or silently replace these D7 rules.

## 4. What this decision does NOT authorize

This Part 1 decision does not authorize or define:

- `S_static_layer` or another newly named per-layer score;
- layer-level `P_tamper`;
- layer-level `S_behavior`;
- `max`, mean, median, top-k, weighted aggregation, voting, or another D5 operator;
- a new baseline or threshold;
- TreeSHAP-based layer selection;
- any change to the frozen MRS formulas.

Those remain governed by their respective decisions and contracts.

## 5. Layer identity and preservation

The authoritative layer identity supplied by P1 remains attached to the corresponding evidence. D5 must preserve the per-layer evidence and identity required by the downstream highest-risk-layer path.

TreeSHAP remains a separate feature-level explanation path and is not a substitute for per-layer evidence or layer selection.

## 6. Parent D5 status

This sub-decision resolves **Part 1 only**. It does **not** resolve D5 as a whole.

D5 remains:

> **RESOLVED / LOCKED — METHODOLOGY BOUNDARY; EXACT OPERATOR PENDING**

The next D5 sub-decision is to establish the exact meaning and required properties of model-level `S_static` before evaluating candidate aggregation operators.
