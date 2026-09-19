# D10/P3 — Remaining Work Cross-Verification and Implementation Lock

**Status:** RESOLVED / LOCKED — execution contract
**Date:** 2026-09-09
**Scope:** Phase 4 P3 work remaining after D10 model-level `P_tamper` aggregation lock.

## 1. Cross-verification result

The remaining Phase 4 work was checked against the locked D1–D10 decision boundaries, the Phase 4 plan/verification requirements, the current P1 feature contract, the current `ml_results` contract, and the frozen architecture.

No additional model-level aggregation decision is required for P3. The remaining items are implementation, artifact-generation, provenance, regression, and checkpoint-evidence work.

## 2. Locked execution path

P3 must execute:

`verified-real P1 static_features -> exact D1 feature matrix -> LightGBM -> per-layer p_l -> D10 P_tamper=max(p_l) -> TreeSHAP for l_ML=argmax(p_l) -> ml_results`

P3 must preserve the separation:

- D5 owns `S_static`.
- D6 owns highest-risk-layer selection using its locked `E(l)` rule.
- D10 owns model-level `P_tamper` aggregation.
- TreeSHAP explains classifier evidence and does not select the D6 layer.

## 3. Implementation requirements

1. Final inference must invoke the verified-real P1 extractor directly.
2. The exact ten D1 features and order must be enforced.
3. Mock, placeholder, stale, reordered, missing, non-finite, or semantically incompatible feature input must never reach final artifact generation or valid final inference.
4. Every required P1 layer must receive a finite `[0,1]` LightGBM prediction.
5. Required-layer failure must fail closed; no omission, zero-imputation, partial aggregation, or invented public status field.
6. Compute `P_tamper` exactly as `max(p_l)`.
7. Compute TreeSHAP for the D10 classifier-evidence layer `argmax(p_l)` and preserve exact feature-name mapping/order.
8. Do not add `classifier_evidence_layer` to the closed public `ml_results` schema under this decision.
9. Enforce D8 `generation_commit` staleness semantics.
10. Persist complete training/artifact provenance required by the Phase 4 contract.

## 4. Training contract

The final LightGBM artifact must be generated only from reproducible verified-real P1 features produced from the declared clean/tampered training inputs. Synthetic tampering is permitted only when the tampering generation is reproducible and its provenance is recorded. Model-level clean/tampered labels are applied to layer-level feature rows; therefore `p_l` is classifier evidence and must not be represented as calibrated independent per-layer malware probability.

A real final artifact is required for CP4. The historical prototype's generated vectors are not acceptable as final training evidence.

## 5. Required verification suite

The implementation must provide reproducible evidence for:

- exact D1 feature names/order;
- verified-real P1 producer and no mock leakage;
- real classifier artifact generation;
- valid `[0,1]` per-layer predictions and exact D10 MAX aggregation;
- deterministic TreeSHAP names/order;
- D10 localized-evidence behavior;
- layer-count/extreme-value sensitivity characterization without introducing a new runtime correction;
- stale generation rejection;
- NaN/Inf rejection;
- missing/extra/wrong-order feature rejection;
- invalid artifact rejection;
- malformed ML result rejection;
- mock provenance/placeholder/stale-feature rejection;
- complete provenance and artifact identity.

## 6. Quantized boundary

Current upstream P1 quantized handling does not provide an operational final P3 classifier path. P3 must not fabricate one. Quantized classifier support remains blocked at the existing upstream contract boundary until separately implemented and verified.

## 7. Checkpoint boundary

These requirements do not constitute CP4 PASS. CP4 remains blocked until the required implementation and evidence are complete and independently/human reviewed according to project governance.

No remaining execution item authorizes changing D10, D5, D6, D7, D8, MRS, thresholds, or the frozen architecture.

## 8. Locked outcome

**The remaining P3 work is fully specified at the current decision boundary. No unresolved P3 aggregation/design gap remains.** Implementation and verification may proceed without reopening D10, subject to the explicit requirements above.
