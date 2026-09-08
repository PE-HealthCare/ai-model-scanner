# outputs — FINAL VERIFIED RESULTS

## 1. OWNERSHIP & SCOPE
- **Owner:** P3 (final reporting authority)
- **Purpose:** Production-grade final results for human review/demo; NO intermediate/mock data
- **Allowed Files:** risk_results.json, security_report.html/md, dashboard artifacts ONLY
- **FORBIDDEN FILES:** Mock artifacts, intermediate features.json/ml_results.json, debug logs

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- ANY artifact with mock_status=MOCK enters outputs/ -> IMMEDIATE REJECT
- Upstream VERIFICATION.md chain broken (any CP[N] != PASS)
- Final verdict missing or ambiguous (must be PASS/REVIEW/FAIL)
- MRS value outside [0,100] range
- TreeSHAP attributions missing for FAIL/REVIEW verdicts

## 3. INPUT CONTRACT
- **Required Artifacts:** Verified-REAL ml_results.json + behavioral evidence + risk aggregation
- **Schema:** Must validate against contracts/risk_results.schema.json
- **Preconditions:** CP5 = APPROVED (all upstream gates passed)

## 4. OUTPUT CONTRACT
- **Produced Artifact:** risk_results.json + human-readable security report
- **Verdict Format:** Exactly PASS | REVIEW | FAIL with supporting evidence
- **Mandatory Fields:** mrs_score, verdict, shap_attribution_summary, highest_risk_layer, assumptions_limitations

## 5. SECURITY BOUNDARIES
- NEVER include raw model weights or sensitive metadata in outputs
- Fail CLOSED on incomplete evidence chain -> NO partial reports

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 06 Risk Integration & Demo ONLY
- **Trigger:** CP5 = APPROVED + all upstream artifacts VERIFIED-REAL
- **Consumed By:** Human judges / demo presentation
- **Immutability:** Once written, outputs are READ-ONLY; corrections require new CP6 cycle
