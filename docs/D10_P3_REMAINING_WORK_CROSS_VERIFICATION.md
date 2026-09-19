# D10/P3 — Remaining Work Cross-Verification and Implementation Lock

**Status:** RESOLVED / LOCKED — execution contract
**Date:** 2026-09-09
**Scope:** Phase 4 P3 work remaining after D10 model-level `P_tamper` aggregation and D11 quantized-path locks.

## 1. Cross-verification result

The remaining Phase 4 work was checked against the locked D1–D11 decision boundaries, the Phase 4 plan/verification requirements, the current P1 feature contract, the current `ml_results` contract, the frozen format-adaptive quantized methodology, and the frozen architecture.

No additional model-level aggregation decision is required for P3. The remaining items are implementation, artifact-generation, provenance, regression, and checkpoint-evidence work. The previously identified quantized P3 design gap is resolved by D11.

## 2. Locked execution paths

Non-quantized:

`verified-real P1 ten-feature static_features -> LightGBM_FP -> per-layer p_l -> D10 P_tamper=max(p_l) -> TreeSHAP for l_ML=argmax(p_l) -> ml_results`

Quantized:

`verified-real P1 quantized ks_stat -> LightGBM_Q(ks_stat) -> per-layer p_l^Q -> D10 P_tamper=max(p_l^Q) -> TreeSHAP on l_ML=argmax(p_l^Q) -> ml_results`

P3 must preserve the separation:

- D5 owns `S_static`.
- D6 owns highest-risk-layer selection using its locked `E(l)` rule.
- D10 owns model-level `P_tamper` aggregation.
- D11 owns the quantized classifier feature/artifact contract.
- TreeSHAP explains classifier evidence and does not select the D6 layer.

## 3. Implementation requirements

1. Final inference must invoke the verified-real P1 extractor directly.
2. FP32/FP16 must use the exact ten D1 features and order.
3. Quantized inference must use only finite `ks_stat`; FP-specific unavailable fields must not be imputed.
4. Mock, placeholder, stale, reordered, missing, non-finite, or semantically incompatible feature input must never reach final artifact generation or valid final inference.
5. Every required layer must receive a finite `[0,1]` classifier prediction from the applicable artifact.
6. Required-layer failure must fail closed; no omission, zero-imputation, partial aggregation, or invented public status field.
7. Apply D10 exactly as `max(p_l)` for the applicable classifier path.
8. Compute TreeSHAP for the D10 classifier-evidence layer and preserve exact feature-name mapping/order.
9. Do not add `classifier_evidence_layer` to the closed public `ml_results` schema solely for these decisions.
10. Enforce D8 generation/staleness semantics.
11. Persist complete training/artifact provenance required by the Phase 4 contract.

## 4. Training contract

The final artifacts must be generated only from reproducible verified-real P1 outputs produced from declared clean/tampered training inputs.

- Non-quantized artifact: ten-feature LightGBM.
- Quantized artifact: one-feature `ks_stat` LightGBM.
- Synthetic tampering is permitted only when reproducible and explicitly provenance-bound.
- Model-level clean/tampered labels remain the training labels on layer-level rows; classifier outputs are evidence, not calibrated independent malware probabilities.

## 5. Required verification suite

The implementation must provide reproducible evidence for:

- exact FP32/FP16 D1 feature names/order;
- verified-real P1 producer and no mock leakage;
- valid quantized P1 entry and whole-weight KS-only behavior;
- no fabricated quantized FP-specific features;
- real classifier artifact generation for each applicable path;
- valid `[0,1]` per-layer predictions and exact D10 MAX aggregation;
- deterministic TreeSHAP names/order for both applicable paths;
- D10 localized-evidence behavior;
- layer-count/extreme-value sensitivity characterization without introducing runtime correction;
- stale generation rejection;
- NaN/Inf rejection;
- missing/extra/wrong-order feature rejection;
- invalid artifact rejection;
- malformed ML result rejection;
- mock provenance/placeholder/stale-feature rejection;
- complete provenance and artifact identity;
- quantized behavioral bypass;
- quantized MRS consumption of `P_tamper`.

## 6. Quantized boundary

D11 resolves the former quantized P3 gap. P1 must safely support validated supported quantized representations without uploader code or unsafe conversion; P3 must consume the resulting `ks_stat` and dedicated quantized artifact. Unsupported quantized representations still fail closed.

## 7. Checkpoint boundary

These requirements do not constitute CP4 PASS. CP4 remains blocked until the required implementation and evidence are complete and independently/human reviewed according to project governance.

No remaining execution item authorizes changing D10, D11, D5, D6, D7, D8, D4, MRS, thresholds, or the frozen architecture.

## 8. Locked outcome

**D10 and D11 resolve the P3 classifier aggregation and quantized-path design gaps. The remaining Phase 4 work is implementation and verification only.**
