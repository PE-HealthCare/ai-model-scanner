# Phase 5 — Behavioral Probing + Risk

## Status

**Owner:** P2 — Muscle  
**Checkpoint:** CP5  
**Prerequisites:** CP4 = PASS and required P1/P3 real upstream outputs available  
**Branch:** `phase-5/behavioral-probing`

Phase 5 owns final behavioral probing, behavioral anomaly scoring, MAD risk aggregation, MRS, and verdict.

Phase 6 does NOT recalculate these algorithms.

## 1. Agent Execution Control

P2 may design probes and test logic with mocks before upstream readiness.

Final authoritative risk processing MUST WAIT until required real upstream artifacts are verified.

If CP4 is not PASS, final P_tamper consumption is BLOCKED.

If required upstream artifacts are missing/stale/malformed, final risk output is BLOCKED.

## 2. Allowed Files

Allowed:

- `src/p2_behavioral_risk/prober.py`
- Phase-5 tests under `tests/...`
- approved risk-output implementation paths

Forbidden:

- P1 implementation;
- P3 implementation;
- unauthorized `scan_model.py`;
- planning governance files;
- Master Graph.

Shared utilities require explicit authorization, impact analysis, affected-owner notification, and reverification.

## 3. Format-Adaptive Probing

Quantized:

```text
is_quantized = TRUE
→ skip behavioral probing
→ use quantized MRS formula
```

Non-quantized:

- VISION → float/image-noise probes;
- NLP → integer token-ID probes.

Inference must be bounded.

The production probe-pass limit MUST be finite and explicitly approved. An agent may not select the production limit autonomously.

Time and resource limits must also be respected where required.

## 4. D3 — STRIP Baseline

The exact STRIP entropy baseline remains DECISION REQUIRED until explicitly resolved.

Do not invent a baseline.

## 5. D4 — Behavioral Normalization

The exact conversion from H_STRIP evidence to `S_behavior ∈ [0,1]` remains DECISION REQUIRED until resolved.

Do not invent thresholds, clipping, normalization, or fallback behavior.

## 6. Risk Aggregation

P2 owns:

- per-layer static/tampering evidence aggregation;
- behavioral score integration;
- MAD handling;
- MRS;
- verdict.

Final formulas are fixed by the Master Graph:

```text
non-quantized:
MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)

quantized:
MRS = min(100, 55*S_static + 45*P_tamper)

PASS: 0–34
REVIEW: 35–69
FAIL: 70–100
```

D5 remains DECISION REQUIRED for exact per-layer→model aggregation.

D7 remains DECISION REQUIRED for zero/near-zero MAD and insufficient-layer handling.

Do not silently choose those semantics.

## 7. Mock / Real Lifecycle

Mock probing and risk data may be used for unit/scaffold tests.

They cannot produce an authoritative `risk_results.json`.

A real risk artifact requires:

- verified-real P1 inputs;
- verified-real P3 `ml_results.json`;
- approved D3/D4/D5/D7 semantics;
- actual P2 execution;
- provenance;
- verification PASS.

## 8. Failure Behavior

Any upstream failure causes:

```text
STOP
non-zero/failure status
NO MRS
NO verdict
NO fabricated risk_results.json
```

No fallback score may be invented.

## 9. Provenance

`risk_results.json` must trace:

- source `features.json`;
- source `ml_results.json`;
- source versions/commits;
- semantic/contract versions;
- P2 producer version;
- mock/real state;
- run identifier;
- artifact identity/hash where available.

If an upstream semantic change invalidates the result, mark it STALE and block final use.

## 10. Commit / PR / Merge

Branch: `phase-5/behavioral-probing`.

Commit only Phase-5 scope.

PR after verification evidence.

Agent MUST NOT self-merge.

Merge requires CP5 approval, evidence, and independent review.

## 11. Exact CP5 Gate

CP5 PASS requires all required decisions resolved and:

- real upstream inputs;
- domain-adaptive probes;
- approved bounded inference;
- quantized bypass;
- approved H_STRIP baseline;
- approved S_behavior normalization;
- approved aggregation;
- approved MAD handling;
- MRS;
- verdict;
- risk contract;
- provenance;
- adversarial tests;
- evidence.

Required unresolved D3/D4/D5/D7 = BLOCKED, never PASS.
