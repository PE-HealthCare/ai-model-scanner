# src/p3_ml_dashboard — EXPLAINABLE CLASSIFICATION + REPORTING

## 1. OWNERSHIP & SCOPE
- **Owner:** P3 (ML classification + explainability + dashboard authority)
- **Purpose:** LightGBM tamper classification + TreeSHAP attribution + final security report
- **Allowed Files:** classifier.py, dashboard.py, tree_shap_explainer.py, lightgbm_model.txt, tests/
- **FORBIDDEN FILES:** Static analysis, probing code, risk aggregation, model loading

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- CP3 != APPROVED (P1 real features unavailable)
- TreeSHAP layer mapping undefined (D6) or staleness check undefined (D8)
- Training on mock features (MUST use VERIFIED-REAL P1 features ONLY)
- TreeSHAP claimed as highest-risk-layer determinant (it explains FEATURES, not layers)
- Feature-to-layer aggregation mechanism invented (D6 = DECISION REQUIRED)
- LightGBM trained on provisional Phase 2 scaffolding (NOT demo-ready)

## 3. INPUT CONTRACT
- **Required Artifact:** Verified-REAL features.json from P1 Phase 3
- **Schema:** contracts/ml_results.schema.json
- **Preconditions:** CP3 = APPROVED + D6/D8 resolved (or explicitly BLOCKED)
- **Training Data:** Synthetic tampering + P1 verified extractor ONLY

## 4. OUTPUT CONTRACT
- **Produced Artifact:** ml_results.json matching ml_results.schema.json
- **Mandatory Fields:** p_tamper, shap_attributions, feature_importance, model_version
- **TreeSHAP Scope:** Explains feature contribution to P_tamper prediction ONLY
- **Highest-Risk-Layer:** Requires SEPARATE aggregation mechanism (D6) - do not conflate with TreeSHAP

## 5. SECURITY BOUNDARIES
- Bounded inference ONLY - no unbounded model execution
- Resource limits on training/inference time/memory
- Fail CLOSED on training failure - NO fabricated P_tamper

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 04 ML Classification (training) + 06 Dashboard (reporting)
- **Trigger:** CP3 = APPROVED (for training); CP5 = APPROVED (for final report)
- **Consumed By:** P2 risk aggregation (P_tamper input) + human reviewers (dashboard)
- **Critical Dependency:** P3 Phase 2 PREPARATION -> P1 Phase 3 VERIFIED -> P3 Phase 4 TRAINING (NON-NEGOTIABLE ORDER)
