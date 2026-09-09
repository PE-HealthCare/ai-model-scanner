# D5 Part 7 — Exact Static Aggregation Operator Decision

**Status:** RESOLVED / LOCKED — Part 7 sub-decision
**Parent decision:** D5 — Per-layer → model-level static evidence aggregation
**Date:** 2026-09-09

## 1. Decision

D5 Part 7 locks the exact mathematical construction of model-level `S_static` from the authoritative D7-governed layer × feature evidence entering D5.

The locked construction is hierarchical, deterministic, parameter-free, bounded, and preserves the layer identity needed by D6.

For each D7-valid finite observation at layer `l` and feature `f`:

```text
e(l,f) = |Z(l,f)| / (1 + |Z(l,f)|)
```

For each eligible layer:

```text
E(l) = max_f e(l,f)
```

For the model:

```text
S_static = 1 - product_l (1 - E(l))
```

Equivalently:

```text
S_static = 1 - product_l [1 - max_f(|Z(l,f)| / (1 + |Z(l,f)|))]
```

Only D7-valid eligible evidence participates in these mathematical reductions. Invalid, unavailable-baseline, and `DEGENERATE_DEVIATION` states are not silently converted to zero, imputed, or treated as normal evidence.

## 2. Evidence semantics

`e(l,f)` is bounded anomaly evidence, not a probability.

`E(l)` is a temporary mathematical layer-level reduction used by the locked D5 construction; it does not create a separately owned production scoring contract for P1 or D6.

`S_static` is bounded model-level static anomaly evidence consumed by the frozen MRS formulas. It is not a probability of malware.

No Gaussian-distribution assumption is made for the D7 robust-Z evidence. The `1.4826` MAD consistency factor does not establish Gaussianity of the project evidence distribution.

## 3. Why this construction is selected

### 3.1 Feature → layer

The maximum over valid feature evidence preserves a strong anomaly in any authoritative static feature and prevents a localized feature-level signal from being diluted merely because other features are normal.

It is invariant to feature order and adding zero evidence.

### 3.2 Layer → model

The cumulative-evidence operator preserves localized evidence while allowing independent moderate evidence across many layers to accumulate:

```text
1 - product_l (1 - E(l))
```

It is parameter-free and commutative, so layer ordering does not affect the result.

### 3.3 Threat-model behavior

The construction supports the three locked D5 Part 3 patterns:

- **Localized:** a strong layer remains materially represented and is not diluted by normal layers.
- **Distributed:** moderate evidence across many layers accumulates instead of being reduced to only the strongest layer.
- **Mixed:** concentrated strong evidence and broader weaker evidence are retained together.

## 4. Controlled numerical cross-check

Representative controlled values were evaluated against the locked Part 6 requirements.

Using `e=|Z|/(1+|Z|)` and the layer-level maximum:

| Scenario | Layer Z evidence | S_static |
|---|---|---:|
| Localized | `[4, 0, 0, 0, 0]` | `0.80` |
| Distributed | `[1, 1, 1, 1, 1]` | `0.96875` |
| Mixed | `[4, 1, 1]` | `0.95` |
| Localized + 19 normal layers | `[4, 0, ..., 0]` | `0.80` |
| Zero | `[0, 0, 0]` | `0.0` |
| Near-zero | `[1e-6, 0, 0]` | approximately `1e-6` |

These cases demonstrate localized sensitivity, distributed accumulation, mixed-pattern preservation, dilution resistance, deterministic zero behavior, and continuous near-zero behavior without an undocumented threshold.

## 5. Locked mathematical properties

The construction must preserve:

- `S_static ∈ [0,1)` for finite valid evidence;
- monotonicity in every valid anomaly magnitude;
- determinism;
- layer-order invariance;
- feature-order invariance;
- resistance to dilution by unrelated zero/normal evidence;
- no tunable `k`, threshold, learned calibration, or hidden parameter;
- compatibility with D7 validity/degeneracy rules;
- preservation of authoritative layer identity and provenance for D6;
- no modification to the frozen MRS formulas.

The mathematical output approaches 1 asymptotically as evidence strengthens; it does not require arbitrary clipping to enforce the bound.

## 6. D7 handling

D7 remains authoritative and unchanged:

- finite nonzero MAD → use the actual robust `Z`;
- MAD = 0 and target equals baseline median → deterministic zero anomaly;
- MAD = 0 and target differs from baseline median → `DEGENERATE_DEVIATION`;
- 1–2 comparable layers → baseline unavailable and downstream scoring blocked;
- missing, NaN, or Inf → invalid;
- no epsilon and no near-zero MAD threshold.

Part 7 does not reinterpret any of these states.

## 7. External cross-verification

Robust-statistics literature supports the use of median/MAD for robust anomaly evidence and explicitly notes that the `1.4826` factor makes MAD consistent under a Gaussian model; it does not imply that arbitrary robust-Z observations are Gaussian. This supports retaining the parameter-free bounded mapping above rather than introducing an unjustified Gaussian CDF mapping. citeturn0search0turn0search24

Recent AI-model steganalysis work reports materially different detection behavior across attack regimes and shows that simple statistical baselines can succeed or fail depending on conditions. This supports the D5 requirement to preserve sensitivity to both localized and distributed manipulation rather than assuming one universal attack geometry. citeturn0search2

External literature is a cross-check only. The authoritative project boundary remains the frozen architecture, P1 evidence, D7 rules, and D5 Parts 1–6.

## 8. Explicit non-decisions

Part 7 does not authorize:

- changes to P1 feature definitions;
- changes to D7 validity/degeneracy handling;
- layer-level `P_tamper` or `S_behavior`;
- TreeSHAP-based layer selection;
- D6 selection semantics;
- new baselines or thresholds;
- changes to the frozen MRS formulas;
- arbitrary clipping or post-hoc calibration of `S_static`.

## 9. Parent D5 status

D5 is now:

> **RESOLVED / LOCKED — EXACT OPERATOR**

The production implementation must reproduce the locked mathematical construction exactly. Any change to the mapping, feature→layer reduction, layer→model aggregation, or validity semantics requires a new D5 decision.
