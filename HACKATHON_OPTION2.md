# Hackathon Option 2

## Goal

Deliver a working prototype demo of the AI Model Scanner.

## Authoritative references

1. Precision Care Challenge 2026 problem statement
2. Final Pipeline (Resolved)
3. This file controls hackathon execution scope only.

## Demo scope

ResNet18 + SafeTensors only.

Pipeline:

Untrusted SafeTensors
→ Zero-Trust Intake
→ Static Steganalysis
→ LightGBM
→ TreeSHAP
→ Simple Behavioral Probe
→ MRS
→ PASS / REVIEW / FAIL
→ Security Report

## P1

Own:
- SafeTensors intake
- Trusted ResNet18
- Static analysis
- 10-feature extraction
- features.json

Do not:
- add architectures
- add new features
- do new research
- create new decision documents

## P3

Own:
- small synthetic training set
- LightGBM
- P_tamper
- TreeSHAP
- ml_results.json
- simple report output

Do not:
- build dashboard
- search for large malware datasets
- perform extensive hyperparameter tuning

## P2

Own:
- simple vision STRIP probe
- behavioral anomaly score
- static/risk aggregation
- MRS
- verdict
- highest-risk layer
- risk_results.json

Do not:
- expand D5/D6 research
- implement NLP for this demo
- build advanced trigger inversion

## Integration

scan_model.py is the single entry point.

Required demo:

python scan_model.py clean.safetensors --arch resnet18

python scan_model.py tampered.safetensors --arch resnet18

Both must produce a visible security result.

## Definition of done

A clean model produces a low-risk result.

A controlled tampered model produces elevated risk.

The output shows:
- evidence
- P_tamper
- TreeSHAP explanation
- behavioral evidence
- MRS
- verdict
- highest-risk layer

## Upgrade path

If Option 2 is complete early, upgrade toward Option 3.

Option 3 may add:
- stronger behavioral analysis
- additional architecture support
- richer reporting
- additional validation

No Option 3 work starts until Option 2 works end-to-end.

## Team operating rule

Keep `main` untouched. Work only on `hackathon/option-2` for today's prototype.

Do not spend time editing `.planning/` unless needed to understand existing code.

Prefer working integration over additional documentation.

Do not add new architecture decisions during the hackathon sprint.
