# D10 — Model-Level `P_tamper` Aggregation Decision

**Status:** RESOLVED / LOCKED  
**Decision owner:** P3 / Phase 4  
**Decision date:** 2026-09-09  
**Scope:** Model-level aggregation of P3 LightGBM classifier outputs only.

## 1. Decision

For every authoritative P1 layer eligible for the Phase 4 classifier path, P3 computes one LightGBM tamper score:

`p_l = LightGBM(X_l)`

The authoritative model-level classifier signal is:

`P_tamper = max_{l in L_required} p_l`

where `L_required` is the complete set of authoritative P1 layers supplied to the P3 classifier for that execution.

This is the exact D10 aggregation operator. No averaging, voting, top-k reduction, layer-count correction, hidden weighting, or additional calibration is introduced by D10.

## 2. Semantic meaning

`P_tamper` is a bounded `[0,1]` model-level classifier output representing the strongest classifier evidence among the evaluated authoritative layers.

It is **not** declared to be a calibrated probability of malware, a proof of maliciousness, or independent ground-truth probability for any individual layer.

The Phase 4 training contract currently uses model-level clean/tampered labels on layer-level feature rows. Therefore the resulting layer predictions are classifier evidence learned from those labels, and D10 must not overstate their probabilistic interpretation.

## 3. Ownership

- P1 owns authoritative feature production, layer identity, validity, and provenance.
- P3 owns LightGBM inference and D10 model-level `P_tamper` aggregation.
- D10 does not transfer ownership to `scan_model.py` or create a fourth implementation owner.

## 4. Required input contract

Each classifier input row must come directly from the verified-real P1 static feature contract and preserve the locked D1 feature names and order:

1. `entropy`
2. `pov_chi2`
3. `lsb_kl`
4. `ks_stat`
5. `mean`
6. `std`
7. `skewness`
8. `kurtosis`
9. `sparsity`
10. `outlier_pct`

P3 must not substitute copied, mock, stale, reordered, missing, non-finite, or otherwise semantically incompatible features for final classifier inference.

## 5. Completeness and failure semantics

All required authoritative P1 layers must produce valid finite classifier predictions in `[0,1]`.

If a required layer cannot be classified, P3 must not silently omit that layer, replace its prediction with zero, or aggregate only the surviving layers. The model-level classifier result is therefore not valid for that execution and must fail at the existing runtime/error boundary rather than invent a partial result.

D10 does not add new public status fields such as `BLOCKED`, `PARTIAL`, or `COMPLETE` to `contracts/ml_results.schema.json`.

P1 tensors that are intentionally excluded by the authoritative P1 contract are not treated as missing P3 layers; D10 operates only on the authoritative P1 layer set actually designated for downstream classification.

## 6. TreeSHAP boundary

D10 does not merge TreeSHAP with D6.

For P3 classifier explanation, the classifier-evidence layer is the layer attaining the D10 maximum:

`l_ML = argmax_l p_l`

TreeSHAP may be computed for that layer to explain the classifier output. `l_ML` is an internal P3 explanation reference and is not added to the current public `ml_results` schema by D10.

The D10 classifier-evidence layer is independent of the D6 highest-risk-layer selection and the two may legitimately differ.

## 7. D5 boundary

D10 does not modify D5.

D5 remains exactly:

`e(l,f) = |Z(l,f)| / (1 + |Z(l,f)|)`

`E(l) = max_f e(l,f)`

`S_static = 1 - product_l (1 - E(l))`

D10 `P_tamper` is an independent P3 classifier signal consumed by the already-frozen MRS contract.

## 8. D6 boundary

D10 does not modify D6.

D6 remains the locked highest-risk-layer selection over eligible static evidence:

`l*_D6 = argmax_l E(l)`

using the D7-valid evidence and canonical authoritative layer identity/tie semantics already locked by D6.

D6 does not use `P_tamper` or TreeSHAP to redefine its selection rule.

## 9. Quantized boundary

D10 does not invent a quantized classifier path.

Where the current upstream P1 implementation rejects unsupported quantized graph handling before P3, D10 does not override that boundary or fabricate classifier evidence. Any future operational quantized P3 path requires its own upstream implementation/contract evidence and must remain consistent with the frozen architecture.

## 10. Verification boundary

Locking D10 resolves the architectural aggregation ambiguity. It does **not** constitute CP4 PASS.

The following remain verification/execution requirements, not unresolved D10 operator choices:

- real clean/tampered training corpus and reproducible provenance;
- generation of the final LightGBM artifact;
- empirical validation of D10 behavior, including localized evidence and layer-count sensitivity/extreme-value effects;
- persisted training/artifact provenance required by the Phase 4 contract;
- adversarial, stale-contract, and mock-leakage regression evidence;
- complete CP4 evidence and independent/human review.

These activities may validate or reject the implementation against the locked D10 contract, but they do not authorize replacing the D10 operator with another aggregation rule without a new D10 decision.

## 11. Explicit non-decisions

D10 does not:

- change the ten P1 features;
- change P1 static analysis;
- change D5 `S_static`;
- change D6 highest-risk-layer selection;
- change D7 robust-Z/MAD semantics;
- change D8 staleness semantics;
- change D4 behavioral normalization;
- change MRS weights or verdict thresholds;
- create layer-level `P_tamper` as a separate public contract;
- introduce a new public `classifier_evidence_layer` field;
- claim probability calibration;
- add layer-count normalization;
- invent quantized behavioral/classifier evidence.

## 12. Locked outcome

**D10 is RESOLVED / LOCKED.**

Production Phase 4 implementation must reproduce the exact operator and boundaries above. Any change to the aggregation operator, required-layer semantics, prediction-completeness rule, or classifier-evidence/TreeSHAP boundary requires a new D10 decision.
