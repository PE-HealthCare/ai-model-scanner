# Phase 5 — Behavioral Probing + Risk

## Status

**Owner:** P2 — Muscle  
**Checkpoint:** CP5  
**Current integration baseline:** `recovery-mainline`  
**Historical development branch:** `phase-5/behavioral-probing`  
**Current audit date:** 2026-09-25

Phase 5 owns behavioral probing, behavioral anomaly scoring, risk aggregation, MRS, verdict, and the final risk contract.

## 1. Current Recovery State

The current recovery implementation contains substantial Phase-5 production logic:

- D2 trusted in-process handoff;
- FP behavioral probing;
- quantized behavioral bypass;
- D4 H_STRIP normalization;
- D5 static evidence aggregation;
- D7 MAD/degeneracy handling;
- non-quantized MRS;
- quantized MRS;
- risk-results contract validation;
- generation consistency checks.

Therefore Phase 5 implementation is **substantially present**.

The historical Phase-5 planning text below was not synchronized with that later implementation and must not be read as proof that those algorithms are absent.

## 2. Gate Rule

Final authoritative risk processing still requires current verified upstream evidence.

If current CP4 is not PASS, final authoritative risk output remains blocked.

If required upstream artifacts are missing, stale, malformed, or generation-incompatible, risk output must fail closed.

## 3. Format-Adaptive Probing

Quantized:

```
is_quantized = true
→ bypass behavioral probing
→ use quantized MRS formula
```

Non-quantized:

- VISION → bounded float/image-noise probes;
- NLP → bounded integer token-ID probes.

The current implementation has a finite probe bound. The production bound and its formal approval must still be evidenced in the verification record rather than inferred from code alone.

## 4. D3 — STRIP Baseline

The current implementation consumes scanner-controlled calibration data containing the STRIP baseline statistics.

However, the current repository audit does **not** establish a clean standalone D3 decision record equivalent to the D4 record.

Therefore:

- implementation exists;
- calibration artifact exists;
- formal D3 decision/evidence synchronization remains required before CP5 PASS.

Do not invent or alter the baseline during this reconciliation.

## 5. D4 — Behavioral Normalization

D4 is explicitly resolved in the current project state.

Locked formula:

```
deviation = H_median - H_STRIP
Z = deviation / (1.4826 * H_MAD)
Z_clamped = max(0.0, Z)
S_behavior = min(1.0, Z_clamped / 3.0)
```

Zero-MAD handling is fail-closed:

- equal median/observation → `S_behavior = 0`;
- unequal median/observation → `DEGENERATE_DEVIATION`.

Current implementation and tests cover this behavior.

## 6. D5 / D7

Current production code implements:

```
E_l = max_f (|Z_lf| / (1 + |Z_lf|))

S_static = 1 - Π_l (1 - E_l)
```

with finite-evidence filtering and no zero-imputation.

Current D7 handling rejects/handles degenerate MAD and insufficient comparable evidence according to the implementation.

However, the formal verification record must distinguish:

```
implemented
tested
decision-recorded
current-generation evidenced
```

Do not mark CP5 PASS solely because production functions exist.

## 7. D6 Boundary

D6 is a downstream selection/reporting contract.

Current locked identity:

- conceptual `layer_id` = production P1 `layer_name`;
- no positional identity;
- exact ties = canonical lexical `layer_name`.

The current P2 risk implementation audited on 2026-09-25 still contains input-index tie behavior.

Therefore D6 remains a **cross-owner integration reconciliation item**.

Do not modify P1 identity or import unrelated P2 WIP merely to clear this dependency.

## 8. MRS

Current production formulas are:

```
non-quantized:
MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)

quantized:
MRS = min(100, 55*S_static + 45*P_tamper)
```

Verdict ranges remain:

```
PASS:   0–34
REVIEW: 35–69
FAIL:   70–100
```

These formulas are implemented; current CP5 certification still requires current evidence.

## 9. Mock / Real Lifecycle

Mock probing/risk data may be used for scaffold tests.

They cannot create authoritative final risk evidence.

A real risk artifact requires:

- current verified-real P1 inputs;
- current verified-real P3 `ml_results.json`;
- resolved required decisions;
- actual P2 execution;
- current provenance;
- verification evidence.

## 10. Failure Behavior

Any upstream failure causes:

```
STOP
non-zero/failure status
NO MRS
NO verdict
NO fabricated risk_results.json
```

The current orchestrator validates the resulting risk artifact and removes it on validation failure.

## 11. Provenance

`risk_results.json` must trace:

- source `features.json`;
- source `ml_results.json`;
- source versions/commits;
- semantic/contract versions;
- P2 producer/version;
- mock/real state;
- run identifier;
- artifact identity/hash where available.

Generation mismatch must block final use.

## 12. Controlled Multi-Owner Integration

All future Phase-5 publication follows the project-wide protocol:

```
current origin/recovery-mainline SHA
→ read-only audit
→ isolate exact P2 payload
→ disposable integration
→ Git + logical + contract + ownership checks
→ relevant tests
→ P1/project-owner authorization
→ controlled push
→ independent remote verification
→ next owner refreshes baseline
```

Never publish an entire dirty worktree.

`TASK COMPLETE ≠ READY TO PUSH ≠ SAFE TO PUSH ≠ ALREADY INTEGRATED`.

Held WIP must record owner, reason, dependency/blocker, and release condition.

## 13. Exact CP5 Gate

CP5 PASS requires:

- current CP4 PASS;
- current real P1 input;
- current real P3 `ml_results.json`;
- approved bounded probing;
- approved D3 baseline;
- approved D4 normalization;
- approved D5 aggregation;
- approved D7 handling;
- reconciled D6 behavior;
- exact MRS/verdict formulas;
- current risk contract;
- current provenance;
- current adversarial tests;
- independent evidence.

Required unresolved item = **BLOCKED**, never PASS.

## 14. Do Not Restart Phase 5

The correct state is:

```
existing P2 production implementation
+
current recovery-mainline upstream contracts
+
reconciled P1/P3 outputs
↓
continue verification/integration
```

Historical Phase-5 branches are provenance only unless a specific missing component is demonstrated.
