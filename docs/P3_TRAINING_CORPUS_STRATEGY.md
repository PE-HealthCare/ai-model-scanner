# P3 Training Corpus Strategy — Master Final

**Status:** RESOLVED / LOCKED FOR PHASE 4 EXECUTION  
**Scope:** P3 final classifier training corpus and provenance strategy  
**Architecture status:** Frozen; this document does not reopen D1, D4, D5, D6, D7, D8, D10, or D11.  
**Checkpoint status:** This document does **not** constitute CP4 PASS or independent checkpoint approval.

## 1. Purpose

This document is the authoritative Phase 4 strategy for constructing the real training corpus used by the final P3 LightGBM classifiers. Training and runtime inference must use the same verified-real P1 feature-extraction semantics.

The corpus has two deliberately separate classifier paths:

1. **FP32/FP16 path:** all 10 authoritative P1 statistical features.
2. **Quantized path:** the D11 dedicated `ks_stat`-only classifier input.

No mock or synthetic feature vectors may enter final classifier training.

## 2. Authoritative FP32/FP16 Feature Contract

The FP32/FP16 classifier input is exactly these 10 features, in this exact order:

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

These names and ordering are authoritative. Older aliases such as `byte_entropy`, `pov_chi2_p_value`, and `lsb_kl_divergence` are not part of the final contract.

Every eligible FP32/FP16 training layer must provide all 10 finite numeric values in this order. Missing, nonnumeric, NaN, or infinite values are invalid and must fail closed rather than being imputed.

## 3. Quantized D11 Contract

Quantized training is a separate path and must not synthesize FP32/FP16-only evidence.

The public P1 feature record retains the same 10 named fields for schema compatibility, but for a validated quantized representation:

- `ks_stat` is finite numeric evidence.
- The other nine FP-specific fields are explicitly unavailable as JSON `null`.
- `null` is not replaced by zero, NaN, a sentinel, or an invented estimate.

The **quantized P3 classifier input is only `ks_stat`**. It uses a dedicated one-feature LightGBM artifact. Quantized behavioral probing remains bypassed. Model-level quantized `P_tamper` uses the already locked D10 MAX rule.

## 4. Clean and Tampered Corpus Construction

### 4.1 Clean models

Use trusted, publicly obtainable pretrained models with reproducible identity/version provenance. Candidate model families may include recognizable architectures such as ResNet, VGG, DenseNet, DistilBERT, and RoBERTa, subject to the supported-architecture boundary.

For each clean model:

1. Obtain the trusted model artifact.
2. Record model identity, source, version/revision, and artifact hash.
3. Pass the model through the production P1 intake and extraction path.
4. Record the resulting verified-real per-layer feature evidence.
5. Label the model `clean` (`0`).

### 4.2 Tampered models

Create controlled tampered variants from clean base models using defensive, reproducible weight-manipulation procedures. Candidate families include:

- LSB manipulation.
- Mantissa-bit pattern encoding.
- Localized weight shifts/noise.
- Controlled sparsity/zero injection.
- For supported quantized models, quantized-preserving perturbation or controlled bit manipulation.

These are **candidate tampering families**, not newly frozen numerical parameters. Exact manipulation intensities must remain implementation parameters unless separately justified and approved.

Each tampered variant must:

1. Be derived from a known clean base model.
2. Record the base-model identity and tampering method/parameters.
3. Produce a reproducible tampered artifact and hash.
4. Enter the same production P1 intake/extraction path as its clean counterpart.
5. Be labeled `tampered` (`1`).

A target percentage of model-accuracy degradation is **not** a corpus requirement. The corpus is intended to teach detection of weight-level steganographic/manipulation evidence, not to require a particular accuracy loss.

## 5. Model-Level Dataset Splitting

Dataset splitting is performed at the **base-model identity level**, never independently at the layer-row level.

A clean model and all tampered variants derived from that same base model must remain in the same train, validation, or test partition.

This prevents layer-level or sibling-variant leakage from making evaluation artificially optimistic.

Recommended partitions are train/validation/test, with the exact model counts determined by the available verified-real corpus. The split itself must be deterministic and recorded in provenance.

## 6. Corpus Size Guidance

The following are planning targets, not hard frozen requirements:

### FP32/FP16

- Approximately 5–8 supported base models.
- Approximately 100–800 clean layer samples.
- Approximately 100–800 tampered layer samples.
- Approximately 200–1,600 total layer samples.

### Quantized

- Approximately 3–5 supported quantized base models.
- Approximately 50–300 clean layer samples.
- Approximately 50–300 tampered layer samples.
- Approximately 100–600 total layer samples.

Actual corpus size must be driven by availability of trustworthy, reproducible, supported models and valid P1 outputs. These targets do not authorize fabricated or mock samples merely to reach a number.

## 7. Balance and Tampering Diversity

The final corpus should avoid a trivial class imbalance where feasible. Clean and tampered examples should cover multiple supported model families and multiple tampering families.

Where practical, rotate two or more tampering families across different base models so that the classifier does not simply memorize one manipulation signature.

No undocumented oversampling, synthetic feature generation, hidden weighting, or calibration may be introduced as a substitute for a real corpus.

## 8. Mandatory P1 Lineage

The final classifier training path must directly use the authoritative P1 implementation for feature extraction.

Training is valid only when provenance demonstrates:

`model artifact → P1 zero-trust intake → trusted representation → P1 real feature extraction → training record`

The final training code must not use:

- Random NumPy feature vectors.
- Hand-authored feature rows.
- Mock P1 outputs.
- Legacy Phase 1 mock-pipeline records.
- Uploader-provided `model.py` execution.
- Unsafe pickle/model deserialization.

The same feature semantics used to train the final artifact must be used at runtime by P3 inference.

## 9. Quantized Training Lineage

Quantized corpus construction must demonstrate the D11 path:

`quantized SafeTensors → trusted P1 quantized representation → whole-weight KS extraction → finite ks_stat → dedicated quantized LightGBM`

The original validated quantized representation must be preserved for P1 statistical analysis. Converting quantized values to a statistical working representation does not authorize conversion of the model into an ordinary floating graph or execution of uploader code.

Unsupported quantized representations must fail closed.

## 10. Training Labels and Granularity

Training labels originate at the **model level**:

- clean model = `0`
- tampered model = `1`

The model-level label is repeated across that model's eligible layer rows for classifier training. This does not turn a layer prediction into a calibrated independent probability of malware; it remains classifier evidence.

The FP32/FP16 classifier consumes the exact 10-feature layer vector. The quantized classifier consumes only `ks_stat`.

## 11. Artifact Provenance and Reproducibility

Every final classifier artifact must have reproducible provenance sufficient to establish:

- dataset/corpus identity;
- train/validation/test model-level split;
- source model identities and revisions;
- clean/tampered lineage;
- tampering method and parameters;
- P1 implementation/generation identity;
- exact feature contract used for training;
- classifier path (FP32/FP16 or quantized);
- training configuration and deterministic seed;
- artifact hash;
- generation identity required by D8.

The final artifact must be rejected by consumers when its generation identity is stale or its feature contract/domain is wrong.

Separate artifacts are required for the two classifier domains:

- **Non-quantized:** ten-feature LightGBM.
- **Quantized:** one-feature `ks_stat` LightGBM.

## 12. Final Classifier Training Requirements

For the FP32/FP16 path, final training must:

1. Build all training rows from verified-real P1 outputs.
2. Validate the exact ten-feature contract and order.
3. Preserve model-level labels across layer rows.
4. Use deterministic LightGBM configuration and recorded provenance.
5. Produce a versioned, hashed artifact.
6. Validate the artifact against the same feature contract used at inference.

For the quantized path, final training must:

1. Use verified-real P1 quantized outputs.
2. Use only finite `ks_stat` as the classifier input.
3. Never fabricate the nine unavailable FP-specific features.
4. Use clean and reproducibly tampered quantized models.
5. Produce a separate versioned, hashed artifact with its own provenance.

## 13. Runtime Alignment

P3 runtime inference must reproduce the training-domain contract exactly.

For non-quantized layers:

`X_l = [entropy, pov_chi2, lsb_kl, ks_stat, mean, std, skewness, kurtosis, sparsity, outlier_pct]`

For quantized layers:

`X_l^Q = [ks_stat]`

Required authoritative layers must be classified. Missing, invalid, stale, or incompatible inputs/artifacts fail closed; P3 must not silently omit a layer or replace invalid values with zero.

## 14. Locked D10 / D5 / D6 Boundaries

This strategy does not redefine downstream aggregation or layer selection.

### D10 — model-level classifier aggregation

For each required layer:

`p_l = LightGBM(X_l)`

and exactly:

`P_tamper = max_{l in L_required} p_l`

The same MAX rule applies to the dedicated quantized classifier predictions. No averaging, voting, top-k reduction, layer-count correction, hidden weighting, or additional calibration is authorized by this strategy.

### D5 — static evidence aggregation

D5 remains the locked construction:

`e(l,f)=|Z(l,f)|/(1+|Z(l,f)|)`  
`E(l)=max_f e(l,f)`  
`S_static=1-product_l(1-E(l))`

Only D7-valid eligible evidence participates. This corpus strategy does not modify D5.

### D6 — highest-risk-layer selection

D6 remains the locked selection over eligible static evidence:

`l*=argmax_l E(l)`

TreeSHAP explanation-layer selection remains separate from D6. The classifier evidence layer may be the layer with maximum P3 `p_l`; it must not be conflated with the D6 highest-risk layer.

## 15. Validation Before Final Artifact Acceptance

Before a final artifact is considered ready for downstream integration, evidence must establish:

- Real clean and tampered model artifacts were used.
- No mock/random feature vectors entered final training.
- P1 real extraction was used for every training sample.
- Model-level splitting prevents base-model leakage.
- Exact ten-feature FP contract is preserved.
- Quantized training is KS-only and uses real P1 quantized outputs.
- Training is reproducible from recorded provenance.
- Final artifacts have correct domain, feature contract, generation identity, and hash.
- Runtime inference produces finite predictions in `[0,1]`.
- D10 MAX is applied over the complete required layer set.
- TreeSHAP uses the classifier's selected evidence layer and remains separate from D6.
- D8 stale-artifact rejection is demonstrated.
- Quantized behavioral probing remains bypassed.
- The resulting classifier output is correctly consumed by the frozen MRS path.

These are implementation/verification requirements, not a claim that they have already been satisfied merely because this strategy is locked.

## 16. Explicit Non-Goals

This document does **not** authorize:

- reopening the frozen architecture;
- resolving D4 STRIP normalization;
- changing the D5 operator;
- changing D6 selection;
- changing D7 validity/degeneracy semantics;
- changing D8 staleness semantics;
- changing D10 MAX aggregation;
- changing D11 quantized classifier semantics;
- changing MRS formulas or verdict thresholds;
- introducing a fifth implementation owner through `scan_model.py`;
- treating TreeSHAP as the highest-risk-layer selector;
- claiming CP4 PASS.

Any change to these locked decisions requires the project's decision-governance process and a new decision record where applicable.

## 17. Execution Lock

This document is the **master final P3 Training Corpus Strategy** for Phase 4 execution.

**Locked rules:**

- All 10 authoritative FP32/FP16 features are mandatory.
- Final training uses verified-real P1 extraction only.
- Clean/tampered lineage is preserved at model level.
- Dataset splitting is model-level to prevent leakage.
- Quantized training is a separate `ks_stat`-only classifier path under D11.
- Candidate tampering families and corpus-size ranges remain implementation guidance, not hidden frozen constants.
- No accuracy-drop target is required.
- D10 MAX, D5, D6, D7, D8, and D11 boundaries remain exactly as already locked.
- No mock data may enter final classifier training.
- Final artifacts require reproducible provenance and D8-compatible generation identity.

**Governance note:** Strategy lock authorizes execution within these boundaries. It does not by itself approve implementation, artifact quality, or CP4.
