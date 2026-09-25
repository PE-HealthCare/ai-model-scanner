# Phase 4 — ML Classification

## Status

**Owner:** P3 — Brain & Voice  
**Checkpoint:** CP4  
**Current integration baseline:** `recovery-mainline`  
**Historical development branch:** `phase-4/ml-classification`  
**Current audit date:** 2026-09-25

Phase 4 converts verified P1 features into the LightGBM classifier, D10 `P_tamper`, TreeSHAP evidence, and the approved ML contract.

> **Recovery-mainline clarification:** Historical Phase-4 work was substantially implemented across fragmented branches and was subsequently recovered/reconciled into the shared recovery lineage. Do **not** restart Phase 4 or treat historical branch copies of P1 as authoritative. Historical Phase-4 branches are forensic provenance only. The current P1 implementation on `recovery-mainline` is the authoritative upstream contract.

## 1. Current Phase-4 State

The current recovery implementation contains:

- FP LightGBM classification;
- real P1 extraction in the training path;
- canonical ten-feature ordering;
- mock/placeholder leakage guards;
- classifier provenance and D8 generation checks;
- D10 `P_tamper = max_l p_l`;
- FP TreeSHAP;
- a separate quantized `ks_stat`-only LightGBM path;
- quantized D10 and TreeSHAP;
- quantized routing;
- Phase-4 classifier and integration tests.

This means Phase 4 is **not missing and must not be restarted**.

However, implementation presence is not equivalent to a current CP4 PASS.

## 2. Historical Recovery / P1 Boundary

Historical Phase-4 branches contain older copies of P1. Those copies are not authoritative.

The recovery process established the following rule:

```
historical Phase-4 branch
        ↓
retain valid downstream Phase-4 implementation
        ↓
compare embedded P1 against current recovery P1
        ↓
use current recovery P1 as authoritative
```

The historical record does **not** contain an exhaustive manifest proving that every fragmented historical P1 commit was enumerated, compared against every newer P1 version, and individually promoted. Therefore future recovery must be bounded and evidence-based: recover only a genuinely missing/newer P1 component and never overwrite current P1 with an older Phase-4 snapshot.

## 3. Training Data Rule

Final training MUST directly invoke the verified P1 feature extractor.

No copied/reimplemented feature extraction logic is permitted.

The training path must use the same P1 producer, feature semantics, representation, and ordering as inference.

Synthetic tampering is permitted for training-data creation when provenance is explicit, labels are explicit, generation is reproducible, and the real P1 path is used after CP3.

Synthetic training data is engineering evidence; it is not real-world validation.

## 4. Mock Protection

Mock/placeholder features may enter scaffold tests only.

They MUST NEVER enter final classifier artifact generation.

Final model generation MUST fail if provenance is not VERIFIED-REAL P1 feature data.

## 5. LightGBM / TreeSHAP

TreeSHAP must use the exact feature names/order supplied by P1.

TreeSHAP feature attribution is separate from highest-risk-layer determination.

Phase 4 MUST NOT invent or redefine D5/D6.

For quantized models, the separate classifier consumes only the authoritative `ks_stat` feature. The nine unsupported FP-specific fields remain JSON `null`.

## 6. D8 — Generation / Staleness

Generation identity is mandatory.

A classifier or downstream generated artifact is not current merely because its provenance says VERIFIED-REAL.

At minimum, current use requires consistency between:

- P1 generation identity;
- classifier provenance;
- `ml_results.json`;
- applicable feature/schema contract;
- current implementation semantics.

If a P1 feature semantic/name/order/representation change invalidates the model artifact:

```
artifact = STALE
CP4 = BLOCKED
retrain
reverify TreeSHAP
```

The committed historical FP artifacts identified during the 2026-09-25 audit have older generation identities than the current recovery lineage and therefore are **not sufficient by themselves as current CP4 evidence**.

## 7. Current Verification / Evidence State

Current production code is substantially implemented, but the repository verification layer is not fully synchronized with that implementation.

Known reconciliation items:

1. current generated FP/ML artifacts require current-generation verification;
2. historical CP4 PASS text must not be treated as a current PASS certificate;
3. some tests still target pre-recovery P1/P2 APIs;
4. D6 implementation/tie tests remain inconsistent with the locked `layer_name` lexical decision;
5. current end-to-end current-generation evidence has not been established by this read-only audit.

Therefore:

> **Phase 4 implementation: substantially present.  
> Current CP4 verification: not yet certified.**

## 8. Ownership / Integration Rules

Phase 4 may modify P3-owned classifier/reporting code and authorized Phase-4 tests.

P3 MUST NOT silently modify P1 or P2 implementation to make Phase-4 tests pass.

Shared changes require owner authorization and impact/reverification.

All future publication follows the project-wide controlled Git integration protocol:

```
current remote SHA
    ↓
read-only audit
    ↓
isolate exact payload
    ↓
disposable integration worktree
    ↓
Git + logical + contract + provenance checks
    ↓
relevant tests
    ↓
owner authorization
    ↓
publish exact payload
    ↓
independently verify remote SHA
    ↓
next owner refreshes baseline
```

`TASK COMPLETE ≠ READY TO PUSH ≠ SAFE TO PUSH ≠ ALREADY INTEGRATED`.

## 9. Exact CP4 Gate

CP4 PASS requires:

- CP3 PASS;
- final training uses verified-real P1 extraction;
- no mock leakage;
- applicable LightGBM artifact generated from current-compatible P1 semantics;
- D10 verified;
- TreeSHAP names/order verified;
- provenance complete;
- D8 staleness status valid;
- adversarial regression passes against the current API;
- current-generation evidence complete;
- required downstream decisions/contracts reconciled.

Unresolved required evidence or interface conflict = **BLOCKED**.

Only a separately evidenced CP4 PASS permits final CP5 integration.

## 10. Do Not Restart Phase 4

The correct continuation state is:

```
historical Phase-4 implementation
        +
current recovery-mainline P1
        +
current P3/P2 contracts
        ↓
continue Phase 4 from the reconciled baseline
```

Historical branches should be reopened only to answer a specific provenance/missing-component question.
