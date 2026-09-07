# AI Model Scanner — Roadmap

**Status:** DISCOVERY → EXECUTION

No phase advances until its VERIFICATION.md gate passes.

## Critical Dependency

**P3 Phase 2 preparation → P1 Phase 3 real feature extraction → P3 Phase 4 final ML training.**

P3's Phase 2 activity is ML/training *scaffolding preparation only* — it is provisional and must not be treated as, or described as, final or demo-ready training. Final LightGBM training and TreeSHAP verification (Phase 4) cannot begin until P1's real, verified feature extractor and exact feature semantics (Phase 3) are complete.

---

## 01 — Mock Pipeline

- **Owner(s):** P1, P2, P3 (in parallel)
- **Main deliverable:** Mock `features.json`, mock `ml_results.json`, mock `risk_results.json`; end-to-end `scan_model.py` run against mocks; schema validation.
- **Main dependency:** Team agreement on exact contract fields (DECISION REQUIRED — D1).
- **Verification gate:** CP1 — Phase 1 Mock Gate: all three mock outputs produced; schema validation passes; runner E2E succeeds.

## 02 — Zero-Trust Intake

- **Owner(s):** P1 (implementation); P3 may prepare ML/training scaffolding in parallel (provisional, not final).
- **Main deliverable:** Bounded SafeTensors header parsing, trusted standard-library architecture instantiation, `input_domain` tagging, `is_quantized` tagging.
- **Main dependency:** Phase 1 gate passed; dependencies installed.
- **Verification gate:** CP2 — Intake Gate: declared architecture handled, bounded SafeTensors handling confirmed, trusted graph instantiated, domain tag present, quantization flag present.

## 03 — Static Steganalysis

- **Owner(s):** P1 (implements and verifies real feature extraction). This is the critical handoff to P3.
- **Main deliverable:** Real per-layer static feature extraction (format-adaptive: full feature set for FP32/FP16, whole-weight KS only for quantized), intra-model baseline evidence, `features.json` contract fulfilled.
- **Main dependency:** Phase 2 (Intake) verified.
- **Verification gate:** CP3 — Static Gate: real features produced, format gate correct, intra-model baseline present, layer identity preserved, feature contract satisfied.

## 04 — ML Classification

- **Owner(s):** P3 (uses P1's verified extractor/semantics to train the real LightGBM model and verify TreeSHAP).
- **Main deliverable:** Trained LightGBM classifier, `P_tamper`, TreeSHAP feature attribution, `ml_results.json` contract fulfilled, `lightgbm_model.txt`.
- **Main dependency:** P1 Phase 3 real feature semantics verified (critical dependency — see above). Final training explicitly cannot proceed on Phase 2 scaffolding alone.
- **Verification gate:** CP4 — ML Gate: same P1 extractor used for training data as inference; LightGBM produced; `P_tamper` present; TreeSHAP feature names verified; ML contract satisfied.

## 05 — Behavioral Probing

- **Owner(s):** P2 (can design/refine probing using mocks before this phase; final real integration depends on verified upstream outputs).
- **Main deliverable:** Domain-aware STRIP probing (bounded inference), `H_STRIP`, `S_behavior`; quantized-model bypass applied per format-adaptive design.
- **Main dependency:** Verified upstream outputs, including P3's real `P_tamper` (Phase 4).
- **Verification gate:** CP5 — Behavioral/Risk Gate: domain probes correct, bounded inference confirmed, quantized bypass applied, `S_behavior` produced, MAD guard behavior applied, MRS computed, verdict produced, risk contract satisfied.

## 06 — Risk Integration & Demo

- **Owner(s):** P2 (risk aggregation/MRS/verdict), P3 (final security report/dashboard integration) — all upstream owners' verified outputs.
- **Main deliverable:** Final MRS + verdict, `risk_results.json`, complete P3 Security Report (MRS, verdict, highest-risk layer, TreeSHAP evidence, behavioral note, assumptions & limitations).
- **Main dependency:** All upstream gates (CP1–CP5) passed.
- **Verification gate:** CP6 — Demo Gate: complete end-to-end run; verdict present; MRS present; highest-risk layer reported; SHAP evidence present; behavioral note present; assumptions/limitations stated.

---

## Preserved Unresolved Decisions (do not silently invent)

- D1 — Exact contract schema fields/types/layout for all three JSON schemas.
- D2 — Exact in-process trusted-graph handoff mechanism between P1 and P2 via `scan_model.py`.
- D3 — STRIP entropy baseline definition (expected baseline for `H_STRIP`).
- D4 — Exact `S_behavior` normalization from baseline-relative entropy evidence to [0,1].
- D5 — Exact per-layer → model-level aggregation method for static/tampering evidence.
- D6 — Exact highest-risk-layer feature/layer aggregation method (if not separately specified).
- D7 — MAD zero/near-zero and low-layer-count guard behavior.
- D8 — Whether `lightgbm_model.txt` receives a feature-semantic/version/hash staleness check.
- D9 — Population and pinning of `requirements.txt` for reproducible setup.
