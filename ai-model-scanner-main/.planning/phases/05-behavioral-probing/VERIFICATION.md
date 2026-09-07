# Phase 5 — Behavioral + Risk (Behavioral Probing) — VERIFICATION

**Owner:** P2 — Muscle
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`
**Gate:** CP5 — Behavioral/Risk Gate (partial — behavioral-probing scope only; full CP5 risk-formula checks belong to Phase 6)

This checklist verifies the behavioral-probing portion of Phase 5 only. It does not verify final MRS aggregation (Phase 6).

## Pass/Fail Checklist

### 1. Correct domain handling
- [ ] PASS/FAIL: When `input_domain == VISION`, probes are constructed as float/image-noise probes (per Master Graph §8).
- [ ] PASS/FAIL: When `input_domain == NLP`, probes are constructed as integer token-ID probes.
- [ ] PASS/FAIL: Probe construction path is selected solely from P1's `input_domain` tag — no independent re-derivation of domain within P2.
- [ ] PASS/FAIL: An `input_domain` value outside {VISION, NLP} is surfaced as an error/unhandled case, not silently defaulted to one of the two paths.

### 2. Bounded probing
- [ ] PASS/FAIL: The number of inference passes per probing run is bounded by a fixed, documented limit.
- [ ] PASS/FAIL: The bound is enforced in code (not merely a comment/intent) — probing cannot run unbounded passes.

### 3. Inference-only behavior
- [ ] PASS/FAIL: No gradient computation or backpropagation occurs during probing.
- [ ] PASS/FAIL: No uploader-supplied code (e.g., `model.py`) is executed at any point during probing.
- [ ] PASS/FAIL: No unrestricted pickle loading occurs anywhere in the probing path.
- [ ] PASS/FAIL: Probing only invokes forward passes on the P1-provided trusted graph.

### 4. Quantized bypass
- [ ] PASS/FAIL: When `is_quantized == TRUE`, no probes are constructed and no inference passes are executed.
- [ ] PASS/FAIL: When `is_quantized == TRUE`, no `S_behavior` value is produced/emitted (absence is correct, not a placeholder zero/default unless separately and explicitly decided).
- [ ] PASS/FAIL: The bypass decision is driven strictly by P1's `is_quantized` flag, with no independent re-derivation.

### 5. Entropy calculation
- [ ] PASS/FAIL: `H_STRIP` is computed as softmax entropy over the bounded set of inference-pass outputs (per Master Graph §8).
- [ ] PASS/FAIL: Entropy computation is applied identically regardless of domain (VISION/NLP), operating on the softmax output rather than raw domain-specific inputs.

### 6. Baseline handling
- [ ] PASS/FAIL: The code does not hardcode/invent a specific numeric or heuristic STRIP entropy baseline without an explicit, separately recorded team decision resolving D3.
- [ ] PASS/FAIL: If a baseline is used for development/mock purposes, it is clearly labeled as a mock/placeholder, not presented as final.

### 7. Unresolved normalization decision explicitly respected
- [ ] PASS/FAIL: The conversion from baseline-relative entropy evidence to `S_behavior ∈ [0,1]` is not silently invented; D4 is either explicitly gated/flagged in the implementation or implemented against an explicitly recorded team decision (not an ad hoc choice made during coding).
- [ ] PASS/FAIL: Any interim/mock normalization used for Phase 1-style mock development is clearly distinguished from "final" behavior and does not leak into real-pipeline output without being labeled.

### 8. Valid downstream output
- [ ] PASS/FAIL: For non-quantized models, output includes `S_behavior ∈ [0,1]` (once D3/D4 are resolved) or is explicitly withheld/flagged pending resolution — never a silently fabricated value.
- [ ] PASS/FAIL: For quantized models, output correctly omits `S_behavior`.
- [ ] PASS/FAIL: Output structure is consistent with what `risk_results.json` / `risk_results.schema.json` will require once D1 is resolved (no premature invention of final field names beyond what's agreed).

### 9. Failure/edge-case handling
- [ ] PASS/FAIL: Model with degenerate/near-uniform softmax outputs across all bounded passes does not crash the probing step.
- [ ] PASS/FAIL: Model with a trusted graph that fails to produce valid outputs during a bounded pass is handled with an explicit error/failure path (not a silent fallback score).
- [ ] PASS/FAIL: Behavior is defined (not undefined/crashing) when `input_domain` or `is_quantized` are missing/malformed from upstream — this is surfaced as an integration/contract failure, not silently patched over.
- [ ] PASS/FAIL: No behavior in this phase silently invents a resolution to D2 (trusted graph handoff mechanism) — the handoff mechanism used is either a documented interim/mock approach or an explicitly agreed one.

## Gate Outcome

- [ ] All applicable items PASS, or open items are explicitly tied to unresolved Master Graph decisions (D2, D3, D4) and tracked rather than silently resolved.
- [ ] This phase does NOT claim completion of full CP5 (Behavioral/Risk Gate) — CP5 additionally requires MAD guard, MRS, and verdict, which belong to Phase 6.
