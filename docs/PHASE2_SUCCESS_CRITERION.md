# Phase 2 — Frozen Success Criterion

## Objective
Given an unseen ResNet18 SafeTensors artifact, Phase 2 must produce a model-level
tamper score that meaningfully separates CLEAN from TAMPERED models.

## Development Acceptance Gate
- Artifact/model-level evaluation only.
- Grouped by parent_lineage_id.
- Final-test and S4 sealed during development.
- Development OOF artifact ROC-AUC >= 0.80.
- Every held-out fold ROC-AUC >= 0.70.
- Development-only threshold selected after representation is finalized.
- At most 1 false positive among the 13 development clean artifacts.
- Overall tampered recall >= 85%.
- S1 recall >= 70%.
- S2 recall >= 70%.
- S3 recall >= 70%.
- Always report 0.5%, 1%, 2%, and 5% attack-strength performance.

## Feature Rule
Every added feature must improve CLEAN-vs-TAMPERED artifact discrimination.
Implement -> unit test -> development evaluation.
One justified correction is allowed if broken.
If still ineffective, stop and move on.

## Not Sufficient
- Strong layer metrics with chance-level artifact metrics.
- PR-AUC near the positive prevalence baseline.
- High recall caused by flagging clean models.
- Training-set performance.
- Improvement isolated to one held-out lineage.

## Freeze Rule
After the development gate passes:
1. Freeze features.
2. Freeze model.
3. Freeze threshold.
4. Run final-test once.
5. Run S4 OOD once.
6. Do not tune from either result.

These are hackathon engineering acceptance criteria, not production guarantees.
