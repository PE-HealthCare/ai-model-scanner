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

When a decision is methodologically locked but implementation, calibration, or verification evidence is pending, the agent MUST preserve that distinction and MUST NOT invent the pending evidence.

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

D3 methodology is **RESOLVED / LOCKED**, but empirical calibration/evidence is pending.

The locked methodology is:

- non-quantized models only;
- Shannon entropy over the model's softmax output probability distribution;
- existing 32 domain-appropriate probes;
- empirical, domain-specific baseline distributions;
- fixed, scanner-controlled clean reference models for the corresponding domain;
- no baseline derived from the uploaded model itself.

The actual calibrated baseline distributions and supporting evidence are not yet populated. **Do not invent baseline values.** After the approved calibration run completes, return to the D3 decision record in `.planning/STATE.md`, record the measured evidence/evidence-dependent parameters, and re-verify downstream consistency.

D3 does not determine the conversion from baseline deviation to `S_behavior ∈ [0,1]`; that remains D4.

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

D5 is **RESOLVED / LOCKED at the methodology boundary**: it owns per-layer → model-level risk aggregation and must preserve authoritative per-layer evidence and layer identity for D6. The exact aggregation operator and supporting evidence remain DECISION REQUIRED; no operator may be silently selected.

D6 is **REQUIRED — BOUNDARY REVISED**: it owns highest-risk-layer selection/reporting from authoritative per-layer evidence, not model-level aggregation. Its exact selection rule, ownership wording, input contract, layer identity semantics, and tie behavior remain DECISION REQUIRED. TreeSHAP is not a D6 layer-selection mechanism.

D7 is **RESOLVED / LOCKED**. The approved zero/near-zero MAD and insufficient-layer behavior is recorded in `.planning/STATE.md` and must be followed exactly; no fallback may be invented.

Do not silently choose D4, the D5 aggregation operator, or D6 selection semantics.

## 7. Mock / Real Lifecycle

Mock probing and risk data may be used for unit/scaffold tests.

They cannot produce an authoritative `risk_results.json`.

A real risk artifact requires:

- verified-real P1 inputs;
- verified-real P3 `ml_results.json`;
- approved D3/D4/D5/D6/D7 semantics and all required D3 calibration evidence;
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
- approved H_STRIP baseline methodology and completed calibration evidence;
- approved S_behavior normalization;
- approved aggregation;
- approved MAD handling;
- MRS;
- verdict;
- risk contract;
- provenance;
- adversarial tests;
- evidence.

D3 methodology being locked does not by itself complete D3 evidence. Required unresolved D4, pending D5 aggregation rule/evidence, unresolved D6 selection rule/evidence, or pending D3 empirical calibration/evidence blocks CP5; never substitute guessed values.