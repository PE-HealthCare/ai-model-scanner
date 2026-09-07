# Phase 4 — ML Classification

## Status

**Owner:** P3 — Brain & Voice  
**Checkpoint:** CP4  
**Prerequisite:** CP3 = APPROVED  
**Branch:** `phase-4/ml-classification`

Phase 4 converts verified P1 features into the final LightGBM classifier, P_tamper, TreeSHAP evidence, and approved ML contract.

## 1. Agent Execution Control

Before final training, verify CP3 APPROVED.

If P1 real features are unavailable or unverified, final training is BLOCKED.

P3 may prepare:

- clean pretrained model fixtures;
- synthetic tampering generation;
- training scaffolding;
- TreeSHAP scaffolding

before CP3, but such work remains non-authoritative.

## 2. Allowed Files

Allowed:

- `src/p3_ml_dashboard/classifier.py`
- `src/p3_ml_dashboard/dashboard.py` only where Phase-4 functionality requires it
- Phase-4 tests under `tests/...`
- approved ML artifact path

Forbidden:

- P1 implementation;
- P2 implementation;
- unauthorized `scan_model.py`;
- planning governance files;
- Master Graph.

Shared utility changes require explicit authorization and impact/reverification.

## 3. Training Data Rule

Final training MUST directly invoke the verified P1 feature extractor.

No copied/reimplemented feature extraction logic is permitted.

The training path must use the same P1 producer, feature semantics, representation, and ordering as inference.

## 4. Mock Protection

Mock/placeholder features may enter scaffold tests only.

They MUST NEVER enter final classifier artifact generation.

Final model generation MUST fail if provenance is not VERIFIED-REAL P1 feature data.

A mock-trained model is not a production classifier.

## 5. Synthetic Tampering

Synthetic tampering is permitted for training-data creation, provided:

- provenance is explicit;
- tampered/clean labels are explicit;
- generation is reproducible;
- training features are extracted through the real P1 path after CP3;
- synthetic generation does not redefine P1 semantics.

## 6. LightGBM / TreeSHAP

Implement the approved LightGBM workflow and P_tamper.

TreeSHAP must use the exact feature names/order supplied by P1.

TreeSHAP feature attribution is separate from highest-risk-layer determination.

Phase 4 MUST NOT invent the feature→layer aggregation mechanism D6.

## 7. D8 — Staleness

Until D8 is explicitly resolved, use the conservative rule:

```text
P1 feature semantic/name/order/representation change
→ lightgbm_model.txt = STALE
→ CP4 BLOCKED
→ retrain
→ TreeSHAP remap/reverify
```

A manual memory-based check is not sufficient to keep an artifact authoritative.

## 8. Provenance

The classifier artifact and `ml_results.json` must identify/record, as applicable:

- training feature source;
- P1 producer commit/version;
- feature semantic version;
- schema/contract version;
- training dataset provenance;
- model artifact version/hash where available;
- generation run;
- mock/real state.

## 9. Commit / PR / Merge

Branch: `phase-4/ml-classification`.

Commit only Phase-4 changes.

PR only after verification evidence.

Agent MUST NOT self-merge.

Merge requires CP4 approval and required independent review.

## 10. Exact CP4 Gate

CP4 PASS requires:

- CP3 approved;
- final training uses verified-real P1 extraction;
- no mock leakage;
- LightGBM artifact generated;
- P_tamper verified;
- TreeSHAP names/order verified;
- provenance complete;
- staleness status valid;
- adversarial regression passes;
- evidence complete.

Unresolved required D8 or another required decision = BLOCKED.

Only CP4 APPROVED permits final P2 risk integration.
