# src/p1_static_engine — P1 STATIC ANALYSIS RULES

## 1. OWNERSHIP & SCOPE

- **Owner:** P1 (static analysis authority)
- **Primary implementation:** `src/p1_static_engine/analyzer.py`
- **Purpose:** Zero-trust model intake, trusted representation, and per-layer static steganalysis.
- **Consumed by:** downstream classifier stages through the approved feature contract.

The current P1 implementation is consolidated in `analyzer.py`. Separate `intake.py` or trusted-model implementation modules are not required by the current recovery-mainline design.

P1 owns:
- SafeTensors intake and structural validation;
- trusted architecture instantiation;
- input-domain and quantization tagging;
- scanner-controlled trusted representation;
- static feature extraction;
- P1 feature artifact semantics and provenance.

P1 does **not** own:
- LightGBM classifier behavior;
- TreeSHAP;
- behavioral probing;
- risk aggregation;
- MRS/verdict;
- dashboard/report presentation.

## 2. HARD STOP CONDITIONS

P1 MUST halt and report BLOCKED when any of the following applies:

- the required upstream contract/decision is unresolved;
- a submitted model cannot be safely validated against an approved architecture;
- a required security boundary cannot be enforced;
- layer identity or feature semantics cannot be preserved;
- required feature evidence is unavailable or invalid;
- a requested implementation would invent a schema, formula, threshold, normalization, fallback, or representation.

Unsupported or unsafe inputs fail closed. No best-effort architecture remapping is permitted.

## 3. CURRENT INPUT CONTRACT

The P1 input is an untrusted SafeTensors artifact plus the declared architecture.

The current intake path:
1. enforces finite file/header/metadata/tensor/rank/dimension limits;
2. instantiates only the approved trusted architecture;
3. validates exact tensor-name and shape compatibility;
4. validates allowed dtypes and quantization consistency;
5. materializes only scanner-controlled tensor state;
6. preserves supported quantized tensors without assigning them into the floating-point trusted graph.

## 4. FORMAT-ADAPTIVE ANALYSIS CONTRACT

### Non-quantized FP path

For FP32/FP16 representations, P1 produces the authoritative ten-feature record:

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

The baseline is intra-model: each selected layer is compared against the other layers of the same validated model.

### Quantized path

For supported quantized representations, P1:
- marks `is_quantized = true`;
- preserves the original quantized tensor representation in a scanner-controlled state;
- computes whole-weight `ks_stat` only;
- does not synthesize FP-only measurements.

The quantized feature representation is:
- `ks_stat`: finite numeric value;
- `entropy`, `pov_chi2`, `lsb_kl`, `mean`, `std`, `skewness`, `kurtosis`, `sparsity`, `outlier_pct`: JSON `null`.

This follows the locked D11 representation and does not impute unavailable FP evidence.

## 5. FEATURE ARTIFACT CONTRACT

Authoritative P1 feature artifacts use:

- `producer = P1`;
- `mock_status` explicitly identifying MOCK or VERIFIED-REAL;
- `contract_version`;
- `generation_commit`;
- `input_domain`;
- `is_quantized`;
- `layer_count`;
- `static_features` using the canonical layer fields.

The current carried-forward FP artifact at `data/outputs/features.json` was audited against the current analyzer and schema. No material FP feature-semantic mismatch was demonstrated, so it is retained rather than regenerated solely because its generation commit predates the current branch head.

## 6. SECURITY BOUNDARIES

- Use `safetensors.safe_open` for SafeTensors access.
- Do not execute uploader-supplied Python/model code.
- Do not use unrestricted pickle loading.
- Do not import uploader-controlled modules.
- Do not perform unauthorized external network access.
- Fail closed on malformed, inconsistent, unsupported, or unsafe input.
- Do not fabricate partial feature output after a failed required validation.

## 7. VERIFICATION / PROVENANCE

A P1 artifact is not authoritative merely because the file exists.

Verification must establish, as applicable:
- real SafeTensors intake was used;
- the current approved P1 extraction semantics were used;
- the artifact validates against `contracts/features.schema.json`;
- producer and generation identity are recorded;
- mock/real status is correct;
- quantized output uses KS-only semantics with unsupported FP fields represented as unavailable.

Changes to feature names, meanings, representation, ordering, or extraction formulas are material P1 changes and must trigger downstream staleness/reverification under the approved contract.

## 8. CHANGE SCOPE

For P1-owned work:
- keep implementation in `src/p1_static_engine/`;
- keep P1 tests under `tests/`;
- do not modify P2/P3 implementation to satisfy a P1 issue;
- do not move P1 detection logic into `scan_model.py`;
- shared-contract changes require affected-owner impact analysis and reverification.

When a downstream consumer disagrees with the locked P1 representation, preserve the approved P1 contract and surface the downstream compatibility issue to its owner.

## 9. CURRENT P1 BOUNDARY

The current recovery-mainline P1 boundary is:

```text
untrusted SafeTensors
        ↓
P1 zero-trust intake
        ↓
validated trusted/scanner-controlled representation
        ↓
P1 static features
        ↓
features.json
```

P1 stops at the feature artifact boundary. Downstream classifier, behavioral, risk, and reporting behavior remain outside P1 ownership.
