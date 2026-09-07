# Phase 04 — ML Classification — PLAN

**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`
**Owner:** P3 — Brain & Voice (`src/p3_ml_dashboard/classifier.py`)
**Status:** FROZEN FOR EXECUTION — implement only what is specified below.

## 0. Purpose and Scope

This phase implements LightGBM classification and TreeSHAP explainability, per
Master Graph §1, §7, §11 Phase 4. It does not redesign the pipeline, does not
invent a feature-vector dimensionality, and does not resolve any DECISION
REQUIRED item.

## 1. Temporal Dependency (Hard Gate — Do Not Violate)

Per Master Graph §7 and §12 (Parallel Work table):

```text
P3 Phase 2 preparation
        |
        v
P1 Phase 3 VERIFIED REAL FEATURE EXTRACTOR
        |
        v
same extraction code/semantics applied to
clean + tampered synthetic models
        |
        v
training feature dataset
        |
        v
P3 Phase 4 LightGBM training
        |
        v
lightgbm_model.txt
        |
        v
TreeSHAP verification
```

**"P3 final classifier: NO until P1 real feature semantics verified (P1 Phase 3)"**
is a hard gate (Master Graph §12). This plan does not permit final classifier
training to begin, or to be treated as authoritative, before Phase 03 (P1)
passes CP3 (Static Gate) and delivers verified real feature extraction with
locked semantics.

## 2. What May Proceed Now (P3 Phase 2 Preparation)

The following may be prepared in parallel with, or ahead of, P1 Phase 3, per
Master Graph §11 Phase 2 and §12:

- Clean public pretrained model corpus assembly.
- Synthetic tampering generation methodology (design and scaffolding).
- LightGBM training scaffold (code structure, not final trained artifact).
- TreeSHAP explanation scaffold (code structure, not final verified attribution).

These are preparatory only. None of these constitute, or may be presented as,
a final trained classifier.

## 3. What May NOT Proceed Until P1 Phase 3 Is Verified

- Final LightGBM training on real feature data.
- Production of the authoritative `lightgbm_model.txt`.
- TreeSHAP verification against a final trained model.
- Any claim that `ml_results.json` reflects a verified, real classification.

## 4. Training-Data / Feature-Semantics Contract

Per Master Graph §7 and Hidden Dependency #1–2:

- The **same extraction code/semantics** used by P1 for inference-time feature
  extraction must be applied to generate training features for both the clean
  and synthetically tampered model corpus. Training data must not be produced
  by a separate or reimplemented extraction path.
- Feature **names, meaning, and order** must remain consistent between the
  training dataset and inference-time `features.json` output. This is the
  explicit "feature semantic lock between P1 and P3" (Master Graph §15, item 1).
- The trained `lightgbm_model.txt` artifact corresponds to, and is only valid
  for, the exact feature semantics/version it was trained against.

### 4.1 Change-impact rule (non-negotiable)

Per Master Graph §7 and §14 (Change-Impact Map):

> If P1 changes feature name, meaning, representation, or ordering after P3
> training: **P3 retrain + TreeSHAP remap/reverify + Phase 4 re-verification.**
> This can fail silently because LightGBM may still run.

This plan requires that any detected or reported change to P1's feature
semantics after training triggers mandatory P3 retraining and TreeSHAP
reverification — this is not optional or best-effort. The plan does not resolve
**D8** (whether `lightgbm_model.txt` receives an automated staleness/hash check)
— that mechanism remains open. Absent an automated check, this remains a
manual process obligation.

## 5. Feature-Vector Dimensionality — Explicit Non-Invention

This plan does **not** assume, hardcode, or instruct implementation of a fixed
feature-vector dimensionality (e.g., an "18-D" vector or any other invented
fixed size) for LightGBM training or inference. The exact shape of the feature
vector is governed by:

- `features.schema.json` (D1 — DECISION REQUIRED, currently EMPTY), and
- P1's Phase 3 verified real feature extractor (Phase 03 of this project).

LightGBM training scaffold work (§2) may use placeholder/mock feature shapes
strictly for scaffold testing purposes, and any such placeholder shape must be
clearly marked as non-authoritative and discarded/replaced once real P1
features are available.

## 6. TreeSHAP vs. Highest-Risk-Layer — Explicit Separation

Per Master Graph §6 and Master Rule 7 ("TreeSHAP feature attribution and
highest-risk-layer determination are separate relationships"):

- **TreeSHAP** explains the contribution of each *feature* to the LightGBM
  classifier's prediction (P_tamper). This is feature-level explainability.
- **Highest-risk-layer determination** is a *separate* mapping from
  feature-to-layer association plus layer-level anomaly aggregation
  (Master Graph §6B). TreeSHAP does not, by itself, determine the highest-risk
  neural-network layer.
- These two outputs must not be conflated, merged into a single undifferentiated
  "explanation," or presented as if one derives the other without the explicit
  intermediate feature↔layer aggregation step.
- The **exact feature-to-layer aggregation mechanism** is registered as
  **D6 — DECISION REQUIRED** in the Master Graph and is not resolved by this
  plan. This phase implements TreeSHAP feature attribution; it does not
  implement or assume a specific highest-risk-layer aggregation algorithm.

## 7. Outputs

- `data/outputs/ml_results.json` — populated only once real training (per §1–§4)
  has occurred; must include P_tamper and feature-level SHAP attribution.
- `artifacts/lightgbm_model.txt` — the trained model artifact, valid only for
  the feature semantics it was trained against (§4).
- Conformance to `ml_results.schema.json` once finalized (D1 — DECISION REQUIRED,
  currently EMPTY).

## 8. Explicit Non-Goals for This Phase

- Do not implement P2 STRIP probing or risk aggregation.
- Do not implement the final security report/dashboard.
- Do not define or finalize the feature-to-layer aggregation method (D6).
- Do not define or finalize artifact staleness protection (D8).
- Do not populate `ml_results.schema.json` fields unilaterally (D1).

## 9. Carried-Forward Unresolved Decisions (Not Invented Here)

| ID | Item |
|---|---|
| D1 | Exact `ml_results.schema.json` fields/types/layout |
| D6 | Exact feature-to-layer aggregation method for highest-risk-layer reporting |
| D8 | Whether/how `lightgbm_model.txt` gets a feature-semantic/version/hash staleness check |

These remain open per the Master Graph Decision-Required Register (§16) and must
not be silently resolved during implementation of this phase.
