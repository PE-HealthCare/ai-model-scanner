# src/p2_behavioral_risk — DOMAIN-AWARE PROBING + RISK AGGREGATION

## 1. OWNERSHIP & SCOPE
- **Owner:** P2 (behavioral probing + MRS authority)
- **Purpose:** STRIP-style probing + MAD-calibrated Model Risk Score aggregation
- **Allowed Files:** prober.py, risk_aggregator.py, strip_baseline.py, tests/
- **FORBIDDEN FILES:** Static analysis, ML training, dashboard rendering, model loading

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- CP4 != PASS (P3 real P_tamper unavailable)
- STRIP baseline undefined (D3) or S_behavior normalization undefined (D4)
- Quantized model attempting behavioral probing (SKIP per format-adaptive design)
- MRS formula deviates from approved: min(100, 55*S_static + 45*P_tamper) for quantized
- Behavioral evidence sourced from mock artifacts
- Agent invents aggregation method not in approved design (D5)

## 3. INPUT CONTRACT
- **Required Artifacts:** Verified-REAL features.json + ml_results.json + domain tag
- **Schema:** contracts/risk_results.schema.json
- **Preconditions:** CP4 = PASS + D3/D4/D5 resolved (or explicitly BLOCKED)
- **Domain Routing:** VISION/NLP probes selected by input_domain; quantized -> SKIP probing

## 4. OUTPUT CONTRACT
- **Produced Artifact:** risk_results.json matching risk_results.schema.json
- **Mandatory Fields:** mrs_score in [0,100], verdict in {PASS,REVIEW,FAIL}, s_static, p_tamper; `s_behavior` is required for non-quantized models and may be null for quantized models.
- **Quantized Branch:** MRS = `min(100, 55*S_static + 45*P_tamper)` - NO behavioral component
- **Non-Quantized Branch:** MRS = `min(100, 40*S_static + 35*P_tamper + 25*S_behavior)`
- **Verdict Thresholds:** PASS 0–34; REVIEW 35–69; FAIL 70–100
- **MAD Guard:** Follow the approved D7 behavior for zero/near-zero MAD and small layer counts; do not invent a fallback.

## 5. SECURITY BOUNDARIES
- Bounded inference ONLY - no unbounded model execution
- Resource limits on probe iterations/memory/time
- Fail CLOSED on probe failure - NO fabricated S_behavior

## 6. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** 05 Behavioral Probing + Risk
- **Trigger:** CP4 = PASS
- **Consumed By:** P3 dashboard (Phase 06 integration)
- **Parallel Work:** Probing machinery CAN be developed with mocks BEFORE CP4; FINAL integration BLOCKED until CP4 PASS
