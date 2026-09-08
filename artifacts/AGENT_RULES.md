# artifacts — PERSISTENT P3 ML ARTIFACT STORAGE

## 1. OWNERSHIP & SCOPE
- **Owner:** P3 (ML artifact authority)
- **Purpose:** Persistent storage for the trained LightGBM model used by the P3 classifier.
- **Canonical Artifact:** `artifacts/lightgbm_model.txt`
- **Not for:** transient JSON handoff outputs, planning files, schemas, model inputs, or arbitrary uploaded content.

## 2. HARD STOP CONDITIONS (MANDATORY)
Agent MUST HALT and report BLOCKED if ANY of these are true:
- A model artifact is used without its required provenance/version information.
- The artifact is stale relative to the approved P1 feature semantics or classifier contract.
- A mock/scaffold model is represented as a verified production model.
- An agent attempts to store unrelated content in this directory.

## 3. INPUT CONTRACT
- **Producer:** P3 classifier/training workflow only.
- **Training Dependency:** Final training MUST use the verified P1 feature extractor and exact approved feature semantics.
- **Preconditions:** Applicable ML checkpoint and required upstream verification must be PASS.
- **Mock Protection:** Preparatory/mock artifacts MUST remain explicitly identified as MOCK and MUST NOT be silently promoted to final artifacts.

## 4. ARTIFACT PROVENANCE
A persistent model artifact MUST be traceable to:
- producer/owner;
- model version;
- training data/source status;
- P1 feature semantics/version used;
- generation commit;
- applicable checkpoint/verification evidence.

`generation_commit` identifies the producer code revision. `contract_version` identifies the applicable data contract; these values MUST NOT be conflated.

## 5. STALENESS / RE-VERIFICATION
If P1 changes feature names, meanings, representation, ordering, or other semantics consumed by the classifier, the existing LightGBM artifact MUST be treated as stale until P3 retrains and re-verifies the model and TreeSHAP mapping.

If the project has not explicitly resolved D8 (artifact staleness protection), do not invent a different production policy. Record the dependency as DECISION REQUIRED where it blocks final behavior.

## 6. SECURITY BOUNDARIES
- Never execute arbitrary uploaded content from this directory.
- Do not treat a model artifact as trusted merely because it is stored under `artifacts/`.
- Fail closed on malformed or untraceable artifacts.

## 7. WHEN THIS FOLDER IS USED IN PIPELINE
- **Phase:** P3 ML training and downstream verified consumption.
- **Trigger:** After the applicable upstream checkpoint and training prerequisites are PASS.
- **Consumed By:** P3 classifier/reporting and verified integration.
- **Lifecycle:** Persistent artifact; it is not a transient phase handoff directory.
