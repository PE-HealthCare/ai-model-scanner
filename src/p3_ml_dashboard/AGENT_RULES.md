# src/p3_ml_dashboard — EXPLAINABLE CLASSIFICATION + REPORTING

## 1. OWNERSHIP & SCOPE
- **Owner:** P3 (ML classification + explainability + dashboard authority)
- **Purpose:** LightGBM tamper classification + TreeSHAP attribution + final security report
- **Allowed Files:** classifier.py, dashboard.py, tree_shap_explainer.py, lightgbm_model.txt, tests/
- **FORBIDDEN FILES:** Static analysis, probing code, risk aggregation, model loading

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- Final training/integration requested while CP3 != PASS (P1 real features unavailable)
- Final highest-risk-layer aggregation is required for the current task but D6 is unresolved
- Final artifact/report behavior requires D8 but the staleness policy is unresolved
- Training on mock features (MUST use VERIFIED-REAL P1 features ONLY)
- TreeSHAP claimed as highest-risk-layer determinant (it explains FEATURES, not layers)
- Feature-to-layer aggregation mechanism invented (D6 = DECISION REQUIRED)
- LightGBM trained on provisional Phase 2 scaffolding (NOT demo-ready)

## 3. INPUT CONTRACT
- **Required Artifact:** Verified-REAL features.json from P1 Phase 3
- **Schema:** contracts/ml_results.schema.json
- **Preconditions for final training:** CP3 = PASS and verified P1 feature semantics are available.
- **Additional final-report dependencies:** D6 is required for highest-risk-layer reporting; D8 is required where artifact staleness protection is part of the final behavior.
- **Training Data:** Synthetic tampering + P1 verified extractor ONLY

## 4. OUTPUT CONTRACT
- **Produced Artifact:** ml_results.json matching ml_results.schema.json
- **Mandatory Fields:** Only fields explicitly required by `contracts/ml_results.schema.json`. Do not require `feature_importance` unless it is explicitly added to the approved contract.
- **TreeSHAP Scope:** Explains feature contribution to `P_tamper` prediction ONLY.
- **Highest-Risk-Layer:** Requires a SEPARATE layer-level aggregation mechanism (D6); TreeSHAP feature attribution MUST NOT be used as a substitute.

## 5A. PREPARATORY WORK VS FINAL GATE
- P3 may prepare synthetic tampering, classifier scaffolding, and TreeSHAP scaffolding before CP3/D6/D8 are resolved when the phase plan explicitly permits that work.
- Such preparatory outputs are non-authoritative and MUST NOT be presented as final classifier evidence.
- Final training/integration MUST use the verified P1 feature extractor and the explicitly approved feature semantics.

## 5. SECURITY BOUNDARIES
- Bounded inference ONLY - no unbounded model execution
- Resource limits on training/inference time/memory
- Fail CLOSED on training failure - NO fabricated P_tamper

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 04 ML Classification (training) + 06 Dashboard (reporting)
- **Trigger:** CP3 = PASS (for training); CP5 = PASS (for final report)
- **Consumed By:** P2 risk aggregation (P_tamper input) + human reviewers (dashboard)
- **Critical Dependency:** P3 Phase 2 PREPARATION -> P1 Phase 3 VERIFIED -> P3 Phase 4 TRAINING (NON-NEGOTIABLE ORDER)
