# AI Model Scanner — Execution Roadmap

**Status:** EXECUTION  
**Canonical architecture source:** Final Master Discovery & Dependency Graph  
**Current execution phase:** Phase 4 — ML Classification  
**Current gate:** CP3 PASS; CP4 in progress  

The frozen detection architecture is implemented through six execution phases. Phase 6 is final integration/demo, not a sixth detection stage. No phase advances without its verification gate.

## Gate Outcomes

**PASS** — all applicable verification criteria are satisfied and no required unresolved decision/dependency blocks completion.

**BLOCKED** — a required dependency, contract, decision, calibration item, or evidence item is unresolved/unavailable.

**FAIL** — verification was attempted and one or more required criteria failed.

Unresolved decisions MUST NOT be guessed or silently implemented.

## Phase 1 — Mock Pipeline

**Owners:** P1 + P2 + P3  
**Gate:** CP1 PASS

Establish and validate the initial artifact contracts and mock end-to-end flow. Mocks MUST remain explicitly marked as mocks.

D1 is RESOLVED / LOCKED.

## Phase 2 — Zero-Trust Intake

**Owner:** P1  
**Gate:** CP2 PASS

Requires bounded SafeTensors intake, declared-architecture validation, trusted architecture construction, domain/quantization tagging, safe weight access, and the D2 trusted-model handoff.

D2 is RESOLVED / LOCKED and independently approved/integrated.

## Phase 3 — Static Steganalysis

**Owner:** P1  
**Gate:** CP3 PASS

Produces verified-real per-layer static features using the frozen format-adaptive contract.

FP32/FP16 feature order:

1. entropy
2. pov_chi2
3. lsb_kl
4. ks_stat
5. mean
6. std
7. skewness
8. kurtosis
9. sparsity
10. outlier_pct

Quantized path uses the approved whole-weight KS behavior and does not invent mantissa/LSB features. Layer identity and provenance are preserved in `features.json`.

CP3 is complete and merged into `main`.

## Phase 4 — ML Classification

**Owner:** P3  
**Branch:** `phase-4/ml-classification`  
**Gate:** CP4

Deliverables:

- synthetic tampering methodology;
- LightGBM classifier;
- `P_tamper`;
- TreeSHAP feature attribution;
- `ml_results.json`;
- approved model artifact.

Final training MUST use the verified-real P1 extractor and the exact frozen feature names/order/semantics. Mock data may be used only for scaffolding tests and MUST NOT generate the authoritative classifier artifact.

TreeSHAP is feature attribution/explanation. It is NOT a highest-risk-layer selection mechanism.

D8 staleness protection applies: material upstream semantic/name/order/representation changes stale the classifier and require retraining/reverification.

CP4 requires real P1 provenance, no mock leakage, classifier/P_tamper verification, TreeSHAP name/order verification, provenance, staleness validity, adversarial regression evidence, and independent approval.

## Phase 5 — Behavioral + Risk

**Owner:** P2  
**Gate:** CP5

Deliverables:

- domain-aware STRIP probing;
- bounded inference;
- `H_STRIP`;
- `S_behavior`;
- quantized behavioral bypass;
- per-layer/model-level risk aggregation;
- MAD handling;
- MRS;
- verdict;
- `risk_results.json`.

Decision boundaries:

- **D3:** methodology RESOLVED / LOCKED; empirical calibration/evidence pending; values MUST NOT be invented.
- **D4:** REQUIRED — exact `H_STRIP → S_behavior` normalization remains unresolved.
- **D5:** RESOLVED / LOCKED at methodology boundary. D5 owns valid per-layer → model-level aggregation and preserves authoritative per-layer evidence/layer identity for D6. Exact aggregation operator and supporting evidence remain pending explicit authorization.
- **D6:** REQUIRED — boundary revised. D6 owns highest-risk-layer selection/reporting from authoritative per-layer evidence. It does NOT perform model-level aggregation and does NOT use TreeSHAP. Exact selection rule, ownership wording, input contract, layer identity semantics, and tie behavior remain pending.
- **D7:** RESOLVED / LOCKED — MAD zero/near-zero and insufficient-layer guards.

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

CP5 is BLOCKED while required D4, the exact D5 aggregation rule/evidence, the exact D6 selection rule/evidence, or required D3 empirical calibration remains incomplete.

## Phase 6 — Integration + Demo

**Owners:** P2 risk/MRS/verdict; P3 security report; `scan_model.py` orchestration only  
**Gate:** CP6

Requires CP1–CP5 PASS and current VERIFIED-REAL artifacts. The final report presents MRS, verdict, highest-risk layer, TreeSHAP feature evidence, behavioral evidence or explicit quantized bypass, provenance, assumptions, limitations, and failure behavior.

Phase 6 MUST NOT duplicate P1/P2/P3 algorithms. `scan_model.py` invokes owner implementations and does not become a second risk engine.

D6 reporting MUST consume authoritative upstream per-layer evidence and MUST NOT manufacture layer-level `P_tamper`/`S_behavior` or use TreeSHAP as a layer selector.

## Critical Dependency Chain

```text
CP1 PASS
  ↓
CP2 PASS
  ↓
CP3 PASS
  ↓
Phase 4 / CP4
  ↓
Phase 5 / CP5
  ↓
Phase 6 / CP6
```

## Decision Register

| Decision | Current state |
|---|---|
| D1 | RESOLVED / LOCKED |
| D2 | RESOLVED / LOCKED; CP2 PASS |
| D3 | RESOLVED / LOCKED methodology; empirical calibration pending |
| D4 | REQUIRED |
| D5 | RESOLVED / LOCKED methodology boundary; exact operator/evidence pending |
| D6 | REQUIRED; boundary revised to selection/reporting; exact rule/evidence pending |
| D7 | RESOLVED / LOCKED |
| D8 | RESOLVED / LOCKED |
| D9 | PARTIALLY RESOLVED; remaining lock/hash/verification evidence required |

## Non-Negotiable Rules

1. The Master Graph is the architecture authority.
2. Current committed decision records override historical audit wording.
3. Scaffolding is not implementation; mocks are not real outputs.
4. Verified-real provenance is required for authoritative downstream artifacts.
5. TreeSHAP attribution and highest-risk-layer reporting are separate mechanisms.
6. Quantized models do not receive invented behavioral evidence.
7. D4–D6 unresolved portions MUST remain explicit; agents may not silently invent formulas, operators, thresholds, or fallbacks.
8. Artifact generation mismatches are stale/blocked under D8.
9. `scan_model.py` is orchestration only.
10. Every phase requires its own verification and independent/human approval where specified.
