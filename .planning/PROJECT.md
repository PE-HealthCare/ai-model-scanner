# AI Model Scanner — Project Definition

**Project:** Precision Care Challenge 2026 — Detection of Steganographic Malware Hidden in AI Model Weights  
**Repository:** `PE-HealthCare/ai-model-scanner`  
**Status:** FROZEN FOR EXECUTION

## Problem Being Solved

Build a defensive scanner that inspects untrusted AI model weight files for statistical and behavioral evidence consistent with steganographic tampering, without executing uploader-supplied code.

The scanner provides evidence-backed `PASS / REVIEW / FAIL` signals. It detects within its defined scope; it does not extract malicious payloads or claim absolute security.

## Frozen Detection Pipeline

The finalized detection architecture contains five detection stages and six implementation phases. Phase 6 is final integration/demo, not a sixth detection stage.

```text
P1 Zero-Trust Intake / Trusted Graph
        ↓
P1 Static Steganalysis
        ↓
features.json
        ↓
P3 LightGBM + TreeSHAP
        ↓
ml_results.json
        ↓
P2 Behavioral + Risk
        ↓
risk_results.json
        ↓
P3 Security Report
```

Root orchestration follows `P1 → P3 → P2 → P3`; `scan_model.py` is not a fourth subsystem owner.

## Implementation Phase Mapping

| Phase | Purpose | Gate |
|---|---|---|
| Phase 1 | Mock pipeline/contracts | CP1 PASS |
| Phase 2 | Zero-trust intake | CP2 PASS |
| Phase 3 | Real static steganalysis | CP3 PASS |
| Phase 4 | ML classification | CP4 |
| Phase 5 | Behavioral probing + risk | CP5 |
| Phase 6 | Final integration + demo | CP6 |

**Current execution phase: Phase 4.** CP3 is complete and merged; CP4 is in progress.

## Stage 1 — Zero-Trust Intake

The uploader declares an approved architecture. The scanner instantiates only trusted scanner-controlled architecture definitions and maps the supplied weights into them.

Current prototype registry:

| Architecture | Domain | Trusted implementation |
|---|---|---|
| `resnet18` | VISION | `torchvision.models` |
| `distilbert` | NLP | `transformers` |

Current locked hard limits: SafeTensors header 5 MB, metadata 1 MB, tensor count 10,000, maximum rank 8, maximum dimension 1,000,000, model file size 2 GB. Operational targets are `<50 MB` intake memory and `<0.5 sec` processing time.

D2 requires an in-process trusted-model/context handoff from P1 through `scan_model.py` to P2; no downstream reload or uploader-code execution.

## Stage 2 — Static Steganalysis

P1 performs format-adaptive per-layer analysis against an intra-model baseline.

Authoritative FP32/FP16 feature order:

`entropy, pov_chi2, lsb_kl, ks_stat, mean, std, skewness, kurtosis, sparsity, outlier_pct`.

Quantized models use the finalized whole-weight KS path and do not receive invented mantissa/LSB features.

## Stage 3 — Explainable Anomaly Classification

P3 uses verified-real P1 features to train LightGBM and produce `P_tamper`. TreeSHAP provides feature-level classifier attribution.

TreeSHAP is explicitly separate from highest-risk-layer determination.

## Stage 4 — Domain-Aware Behavioral Probing

Non-quantized models use the approved domain-aware STRIP methodology. Quantized models bypass behavioral probing. D3 methodology is locked but empirical calibration remains pending. D4 normalization remains required.

## Stage 5 — Risk Aggregation

Frozen MRS formulas:

```text
non-quantized:
MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)

quantized:
MRS = min(100, 55*S_static + 45*P_tamper)
```

Verdicts: PASS 0–34, REVIEW 35–69, FAIL 70–100.

D5 owns valid per-layer → model-level aggregation and preserves authoritative per-layer evidence/layer identity for D6. The exact D5 aggregation operator remains pending explicit authorization/evidence.

D6 is a **highest-risk-layer selection/reporting** boundary from authoritative per-layer evidence. It is not a second model-level aggregation stage and is not TreeSHAP. Its exact selection rule, input contract, layer identity semantics, ownership wording, and tie behavior remain pending.

D7 MAD validity/degeneracy handling is resolved/locked. D8 artifact generation/staleness protection is resolved/locked.

## Ownership

| Owner | Responsibilities |
|---|---|
| P1 | zero-trust intake, trusted graph, static steganalysis, feature extraction |
| P2 | STRIP probing, behavioral scoring, risk aggregation, MRS, verdict |
| P3 | LightGBM, synthetic training, TreeSHAP, `P_tamper`, security report/dashboard |
| `scan_model.py` | orchestration only |

## Decision Status

- D1: RESOLVED / LOCKED.
- D2: RESOLVED / LOCKED; CP2 PASS.
- D3: methodology RESOLVED / LOCKED; empirical calibration pending.
- D4: REQUIRED.
- D5: methodology boundary RESOLVED / LOCKED; exact aggregation operator/evidence pending.
- D6: boundary revised to highest-risk-layer selection/reporting; exact rule/input/tie semantics pending.
- D7: RESOLVED / LOCKED.
- D8: RESOLVED / LOCKED.
- D9: PARTIALLY RESOLVED; D9.1–D9.20 locked and remaining dependency evidence pending.

## Source of Truth

The Final Master Discovery & Dependency Graph is the authoritative architecture source. Current decision status is maintained in `docs/DECISION_STATUS.md`, D6 specifics in `docs/D6_HIGHEST_RISK_LAYER_DECISION.md`, and execution status in `.planning/STATE.md`.

Historical audit text MUST NOT override newer committed decision records. When a required decision/evidence item is unavailable, the correct state is BLOCKED, not invention.