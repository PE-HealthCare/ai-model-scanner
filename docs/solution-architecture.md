# AI Model Scanner — Solution Architecture

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights  
**Status:** FROZEN FOR EXECUTION  
**Architecture Authority:** Final Master Discovery & Dependency Graph

This document is an implementation-facing architecture summary. It MUST NOT override the Master Graph or current decision records.

## 1. Frozen Pipeline

```text
Untrusted .safetensors + declared architecture
        ↓
P1 — Zero-Trust Intake / Trusted Graph
        ↓
P1 — Static Steganalysis
        ↓
features.json
        ↓
P3 — LightGBM + TreeSHAP
        ↓
ml_results.json
        ↓
P2 — Behavioral + Risk
        ↓
risk_results.json
        ↓
P3 — Security Report / Dashboard
```

`scan_model.py` is orchestration only and MUST NOT become a fourth implementation stage.

## 2. Trust Boundary

The uploaded model artifact is untrusted. The scanner MUST NOT execute uploader-supplied code, `model.py`, arbitrary plugins, or unrestricted pickle content.

Only scanner-controlled trusted architecture definitions may construct the model graph. Unsupported or incompatible architectures fail closed.

## 3. Supported Prototype Architectures

| Declared architecture | Domain | Trusted implementation |
|---|---|---|
| `resnet18` | VISION | `torchvision.models` |
| `distilbert` | NLP | `transformers` |

No automatic architecture detection and no uploader-supplied executable architecture.

## 4. Zero-Trust Intake Limits

The following are the current locked production hard limits:

| Resource | Limit |
|---|---:|
| SafeTensors header | **5 MB** |
| Metadata | 1 MB |
| Tensor count | 10,000 |
| Maximum tensor rank | 8 |
| Maximum dimension | 1,000,000 |
| Model file size | 2 GB |

Operational targets, not hard security walls: intake memory `<50 MB`; processing time `<0.5 sec`.

A hard-limit violation fails closed and reports the exceeded limit. These values are current locked decisions; the superseded 100 MB header value is not authoritative.

## 5. D2 Trusted-Model Handoff

P1 constructs the trusted, weight-loaded model and trusted metadata. During the same execution, `scan_model.py` passes the same in-memory trusted context to P2.

No serialization, persistence, downstream reload, original-artifact reload, or alternative P2 architecture is permitted by D2.

P2 consumes the received model for bounded inference-only analysis.

## 6. Static Feature Contract

For FP32/FP16, the authoritative feature order is:

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

Quantized models use the finalized format-adaptive whole-weight KS path. Mantissa/LSB-specific features are not invented for quantized representations.

Layer identity and `generation_commit` provenance are preserved in the real P1 feature artifact.

## 7. P3 Classification

Final P3 training MUST consume verified-real P1 features through the real P1 producer. It MUST use the exact feature names, order, semantics, and representation supplied by P1.

Mock/scaffold features are permitted only in scaffold tests and MUST NOT produce the authoritative classifier artifact.

TreeSHAP maps features to classifier contribution/explanation. It is explicitly separate from highest-risk-layer reporting.

D8 requires generation/staleness validation. Material P1 semantic/name/order/representation changes stale the classifier and require retraining and TreeSHAP reverification.

## 8. P2 Behavioral + Risk

Non-quantized models use the approved domain-aware STRIP methodology. Quantized models bypass behavioral probing and use the quantized MRS path.

Frozen MRS formulas:

```text
non-quantized:
MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)

quantized:
MRS = min(100, 55*S_static + 45*P_tamper)

PASS: 0–34
REVIEW: 35–69
FAIL: 70–100
```

D3 methodology is locked but empirical calibration remains pending. D4 behavioral normalization remains required.

## 9. D5 Risk Aggregation Boundary

D5 owns reduction of valid per-layer static/tampering evidence to model-level evidence consumed by MRS.

D5 operates only on valid eligible per-layer evidence after D7 handling and MUST preserve authoritative per-layer evidence and layer identity for D6.

The exact aggregation operator remains pending explicit authorization/evidence. No `max`, mean, median, top-k, weighted operator, or other aggregation may be selected merely for implementation convenience.

## 10. D6 Highest-Risk-Layer Boundary

D6 is a **selection/reporting** decision, not a second model-level risk aggregation stage.

```text
per-layer authoritative evidence + layer identity
                    ↓
                  D6
                    ↓
highest-risk-layer selection/reporting
                    ↓
             P3 security report
```

D6 MUST consume authoritative upstream per-layer evidence and MUST NOT manufacture layer-level `P_tamper` or `S_behavior`, recalculate MRS, introduce a new statistical baseline, or use TreeSHAP as a layer-selection algorithm.

The exact deterministic selection rule, ownership wording, input contract, layer identity semantics, and tie behavior remain required decisions.

## 11. D7 MAD Guard

D7 is resolved/locked:

- finite nonzero MAD → actual MAD, no epsilon;
- MAD = 0 and target = median → deterministic zero anomaly;
- MAD = 0 and target ≠ median → `DEGENERATE_DEVIATION`;
- 1–2 comparable layers → baseline unavailable and downstream scoring blocked;
- invalid numeric data → invalid, no imputation;
- very small nonzero MAD → actual value.

## 12. Artifact Provenance / Staleness

Artifacts carry `generation_commit`. Consumers MUST reject/block generation mismatches rather than silently reusing stale outputs.

Authoritative downstream artifacts require VERIFIED-REAL upstream inputs, current contracts/semantics, provenance, and applicable checkpoint verification.

## 13. Current Decision Boundary

- D1: RESOLVED / LOCKED.
- D2: RESOLVED / LOCKED; CP2 PASS.
- D3: methodology RESOLVED / LOCKED; empirical calibration pending.
- D4: REQUIRED.
- D5: methodology boundary RESOLVED / LOCKED; exact aggregation operator/evidence pending.
- D6: boundary revised to highest-risk-layer selection/reporting; exact rule/input/tie semantics pending.
- D7: RESOLVED / LOCKED.
- D8: RESOLVED / LOCKED.
- D9: PARTIALLY RESOLVED; remaining reproducibility artifacts/hashes/verification evidence pending.

## 14. Governance

No phase advances without its verification gate. Unresolved decisions, missing evidence, stale artifacts, invented formulas/thresholds, mock-to-real leakage, and unauthorized architecture changes are blockers.

The current phase baseline is Phase 4 after CP3 PASS. See the current phase `PLAN.md`, `VERIFICATION.md`, and `docs/DECISION_STATUS.md` for execution-specific requirements.