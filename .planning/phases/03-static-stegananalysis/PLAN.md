# Phase 3 — Static Steganalysis

## Status

**Owner:** P1 — Eyes  
**Checkpoint:** CP3  
**Prerequisite:** CP2 = PASS  
**Branch:** `phase-3/static-stegananalysis`

Phase 3 produces the first verified real `features.json` using the verified Phase-2 intake path.

## 1. Agent Execution Control

If CP2 is not APPROVED, the agent is BLOCKED for real static implementation.

The agent may prepare tests and isolated scaffolding while waiting, but must not mark any feature artifact VERIFIED-REAL.

The agent must inspect the merged Phase-2 state before starting.

## 2. Allowed / Forbidden Files

Allowed:

- `src/p1_static_engine/analyzer.py`
- Phase-3 tests/fixtures under `tests/...`
- approved feature-output implementation files if already part of P1 scope

Forbidden:

- P2 implementation;
- P3 implementation;
- unauthorized `scan_model.py`;
- planning governance files;
- Master Graph.

Shared utility changes require explicit cross-owner authorization, impact analysis, affected-owner notification, and reverification.

## 3. Feature Semantics

For FP32/FP16, implement the finalized feature family:

- byte-position Shannon entropy;
- PoV chi-square;
- LSB KL-divergence;
- KS statistic;
- mean;
- standard deviation;
- skewness;
- kurtosis;
- sparsity;
- outlier percentage.

For quantized models:

- whole-weight KS only;
- mantissa/LSB-specific tests are skipped.

Baseline is intra-model, layer-vs-layer. No external clean reference is required at runtime.

## 4. Statistical Definition Lock

The implementation MUST NOT use "standard formula" as permission to choose materially different semantics.

Where downstream feature meaning can change, the project must explicitly establish:

- mathematical definition;
- population/sample estimator;
- binning method;
- normalization;
- NaN/Inf handling;
- empty/small-sample behavior;
- constant-array behavior;
- feature ordering.

If a required semantic choice remains unresolved, the affected feature contract is BLOCKED.

Do not invent epsilon values, bins, thresholds, or fallbacks.

## 5. D7 — MAD Guard

Detection of degenerate MAD or insufficient comparable layers is allowed.

Choosing an unapproved numerical fallback is forbidden.

Until D7 is resolved:

```text
condition detected
→ record condition
→ do not invent fallback
→ final risk evidence BLOCKED
```

Do not silently replace zero MAD with an arbitrary epsilon.

## 6. Mock / Real Lifecycle

Mock/static fixtures may be used for algorithm tests.

They are not authoritative.

A real feature artifact becomes VERIFIED-REAL only after:

1. real Phase-2 intake;
2. real feature extraction;
3. approved semantics;
4. schema validation;
5. provenance verification;
6. Phase-3 verification PASS.

## 7. Provenance

`features.json` must be traceable to:

- source model/run;
- producer version/commit;
- feature semantic version/commit;
- contract version;
- mock/real state;
- generation run/time identifier where available.

Any mismatch or unknown provenance makes the artifact STALE or BLOCKED.

## 8. Handoff to P3

CP3 is the critical handoff.

P3 may use the real feature extractor only after CP3 approval.

If feature name, meaning, representation, ordering, or extraction semantics change later, downstream P3 artifacts become STALE and require retraining/reverification.

## 9. Commit / PR / Merge

Branch: `phase-3/static-stegananalysis`.

Commit only Phase-3-authorized changes.

PR only after evidence is complete.

Agent MUST NOT self-merge.

Merge requires verification PASS and required review/CP3 approval.

## 10. Exact CP3 Gate

CP3 PASS requires:

- real intake path;
- verified static features;
- exact approved semantics;
- format-adaptive quantization behavior;
- intra-model baseline;
- layer identity;
- feature contract;
- provenance;
- mandatory adversarial tests;
- evidence.

Any unresolved required semantic decision = BLOCKED.

Only CP3 PASS permits P3 final real training work.
