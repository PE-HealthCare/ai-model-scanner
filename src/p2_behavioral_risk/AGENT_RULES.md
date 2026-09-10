# P2 — Agent Rules (Hackathon Option 2)

## Scope
P2 owns: `src/p2_behavioral_risk/`
P2 output: `data/outputs/risk_results.json`

## In Scope (Option 2)
- Simple VISION STRIP probing (ResNet18)
- Bounded inference (32 probes)
- Shannon entropy → H_STRIP
- S_behavior via calibration data
- S_static from P1 layer features (D5)
- Highest-risk layer (D6)
- MRS + PASS/REVIEW/FAIL verdict
- Quantized bypass

## Out of Scope
- NLP / DistilBERT probing
- Neural Cleanse / trigger inversion
- Advanced STRIP research
- Large calibration study
- New decision documents

## Rules
1. Reuse existing `prober.py`, `risk_aggregator.py`, `handoff.py`.
2. Do not fabricate S_behavior, MRS, or highest-risk layer.
3. Fail closed on NaN/Inf, invalid probabilities, or missing trusted model.
4. Do not reload the untrusted SafeTensors inside P2.
5. Do not modify the MRS formula.

## MRS Formulas (frozen)
Non-quantized: `min(100, 40*S_static + 35*P_tamper + 25*S_behavior)`
Quantized:     `min(100, 55*S_static + 45*P_tamper)`

Verdict: 0–34 PASS, 35–69 REVIEW, 70–100 FAIL