# D11 — Quantized P3 Classifier Path Decision

**Status:** RESOLVED / LOCKED — implementation contract
**Decision owner:** P1/P3 joint boundary; P3 owns classifier behavior
**Decision date:** 2026-09-09
**Scope:** Operational P3 classifier support for the already-frozen quantized static-analysis branch.

## 1. Problem resolved

The frozen architecture requires quantized models to contribute `P_tamper` to the quantized MRS formula while using only the format-valid whole-weight KS static test. The current implementation rejects quantized artifacts before P3 and therefore cannot supply the required classifier signal.

The existing `features.schema.json` also requires all ten feature properties as numeric values, while the finalized quantized static methodology intentionally does not define nine FP-specific measurements. Emitting NaN or fabricated zero values is not an acceptable solution.

## 2. Decision

Quantized models use a **separate quantized LightGBM classifier artifact whose sole authoritative input feature is `ks_stat`**.

For each authoritative quantized P1 layer:

`p_l^Q = LightGBM_Q([ks_stat_l])`

The model-level classifier signal remains the already-locked D10 operator:

`P_tamper = max_{l in L_required} p_l^Q`

No FP32/FP16-only feature is synthesized for a quantized model.

## 3. Why this is the compatible resolution

This preserves the frozen format-adaptive rule:

- FP32/FP16: ten approved static features.
- Quantized: whole-weight KS only.
- Quantized behavioral probing remains bypassed.
- Quantized MRS remains `min(100, 55*S_static + 45*P_tamper)`.

The classifier therefore learns from exactly the evidence that P1 is authorized to produce for the quantized representation rather than treating nonexistent mantissa/LSB measurements as data.

## 4. Feature-contract representation

The public P1 feature artifact continues to identify the same ten named fields for the overall static contract, but quantized records must represent unsupported FP-specific measurements as **JSON null**, not NaN, infinity, zero, or another sentinel.

The quantized contract semantics are:

- `ks_stat`: required finite numeric value;
- `entropy`, `pov_chi2`, `lsb_kl`, `mean`, `std`, `skewness`, `kurtosis`, `sparsity`, `outlier_pct`: present but explicitly unavailable (`null`);
- `is_quantized`: `true`.

The schema must therefore permit `null` for those nine fields while retaining numeric constraints for values that are actually defined. This is a representation clarification for the already-finalized format-adaptive methodology, not imputation.

## 5. P3 classifier artifacts

P3 maintains separate artifact identities:

- non-quantized artifact: ten-feature LightGBM;
- quantized artifact: one-feature `ks_stat` LightGBM.

Each artifact must carry its own feature contract, model version, generation identity, dataset provenance, and hash. D8 staleness applies to the representation and semantics of the applicable feature contract.

A quantized artifact must never be used for a non-quantized model and vice versa.

## 6. Training

Quantized classifier training must use verified-real P1 quantized outputs generated from clean and reproducibly tampered quantized model artifacts. Training must not use NaN, fabricated zeros, mock vectors, or copied feature extraction.

The label remains the model-level clean/tampered label attached to the layer-level training row, consistent with D10 semantics. The resulting `p_l^Q` is classifier evidence, not calibrated independent malware probability.

## 7. TreeSHAP

TreeSHAP for the quantized classifier uses only `ks_stat` and is calculated for the D10 classifier-evidence layer:

`l_ML = argmax_l p_l^Q`

The public result may contain the applicable approved feature attribution (`ks_stat`); D11 does not add a new layer field. TreeSHAP remains separate from D6.

## 8. P1 implementation boundary

P1 must stop rejecting a validated supported quantized SafeTensors artifact solely because it is quantized. It must safely load only the supported quantized representation into a trusted scanner-controlled representation without executing uploader code or performing an unapproved floating-point conversion.

The P1 quantized representation must preserve the original quantized values needed for the whole-weight KS calculation. Any architecture/dtype/shape combination that cannot be safely represented remains unsupported and fails closed.

This requires an owner-authorized P1 implementation change; P3 must not bypass or duplicate P1's trust boundary.

## 9. D5/D6 boundary

D11 does not alter D5 or D6.

D5 static anomaly aggregation remains exactly the locked D5 rule where valid D7 evidence exists. D6 continues to select the highest-risk layer from authoritative static evidence and does not use `P_tamper` or TreeSHAP.

If the quantized representation does not permit a required D7/D5 evidence calculation, that evidence remains unavailable according to the existing validity rules; it is not fabricated from classifier output.

## 10. Failure semantics

- Missing/invalid `ks_stat` → quantized classifier result invalid; no imputation.
- Missing required quantized layer prediction → fail closed; no partial MAX.
- Invalid/stale quantized artifact → reject/block under D8.
- Non-quantized input presented to the quantized artifact → reject.
- Quantized input presented to the FP artifact → reject.
- No new public `BLOCKED`, `PARTIAL`, or `COMPLETE` fields are introduced solely by D11.

## 11. Verification requirements

The implementation must prove:

1. valid INT8/FP8 artifacts enter the quantized P1 path;
2. no uploader-supplied code or unsafe conversion is executed;
3. only whole-weight KS is computed;
4. nine FP-specific features are represented as unavailable, never imputed;
5. quantized training uses real P1 output;
6. the quantized LightGBM artifact is reproducible and provenance-bound;
7. every required layer produces finite `[0,1]` `p_l^Q`;
8. D10 MAX is applied exactly;
9. TreeSHAP uses `ks_stat` and exact feature identity;
10. D8 stale artifact rejection works;
11. quantized behavioral probing remains bypassed;
12. the quantized MRS formula consumes the resulting `P_tamper`.

## 12. Governance

D11 resolves the previously identified quantized P3 design/contract gap. It does not constitute CP4 PASS.

P1 changes must be implemented and verified by the P1 owner branch. P3 changes must be implemented and verified in the Phase 4 branch. Cross-owner changes require the normal review and checkpoint governance.

No change to the frozen MRS weights, verdict thresholds, D5 operator, D6 selection rule, or D10 MAX operator is authorized by D11.

## 13. Locked outcome

**D11 is RESOLVED / LOCKED.**

The quantized path is now fully specified: trusted quantized P1 representation → whole-weight `ks_stat` → dedicated quantized LightGBM → per-layer `p_l^Q` → D10 `max` → quantized `P_tamper` → frozen quantized MRS. Any change to this path requires a new decision.
