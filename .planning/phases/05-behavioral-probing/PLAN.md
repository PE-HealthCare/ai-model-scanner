# Phase 5 — Behavioral + Risk (Behavioral Probing) — PLAN

**Owner:** P2 — Muscle
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md` (frozen architecture — this plan does not redesign it)
**Status:** Planning only. No code implemented here.

## 1. Scope

This phase covers P2's behavioral probing responsibility as defined in the Master Graph:

- STRIP probing → `H_STRIP`, `S_behavior`
- Risk aggregation is also owned by P2, but the **final** risk aggregation/report step is executed in Phase 6 (Risk Integration & Demo). This document scopes the behavioral-probing portion of Phase 5; risk aggregation mechanics that feed into MRS are described here only insofar as they are P2 inputs, not as the final integration.

Per the Master Graph (§11, Phase 5):
> P2 can design/refine before this using mocks. Final real probing/risk integration depends on verified upstream outputs, including P3's `P_tamper`.

## 2. Inputs (from upstream, per File/Contract/Data Graph)

- Trusted graph (from P1, handoff mechanism = **D2, DECISION REQUIRED**)
- `input_domain` (P1) — VISION (4D float tensors) or NLP (2D/3D integer token tensors)
- `is_quantized` (P1) — TRUE for INT8/FP8, FALSE otherwise
- `ml_results.json` (P3) — including `P_tamper` (final real integration blocked until this is verified per Phase 4 gate)

P2 work in this phase may proceed against **mocked** versions of these inputs (per Master Graph §11/§12: "P2 probe design — YES — can use mocks"). Final real integration is explicitly **NOT allowed** until required real upstream outputs exist (§12: "P2 final risk integration — NO until required real upstream outputs — P1/P3").

## 3. Domain-aware synthetic probes

Per Master Graph §8 (Behavioral Probing graph):

```
trusted graph + input_domain + is_quantized
                    |
                    v
               format/domain gate
```

- **VISION** → float/image-noise probes
- **NLP** → integer token-ID probes

Probe construction must be domain-aware: the probe generator selects the correct construction path based on `input_domain` as tagged by P1. No other domain-selection logic is authorized; if a domain outside VISION/NLP is ever reported by P1, this is out of scope for this frozen pipeline and must be surfaced, not silently handled.

## 4. Bounded inference-only passes

Per Master Graph §8:

```
bounded inference-only passes (e.g. 32)
        |
        v
softmax entropy H_STRIP
```

- Probing performs **inference-only** passes against the trusted graph — no backpropagation, no gradient computation (consistent with Master Graph §17: "no core backpropagation").
- Pass count is **bounded** (Master Graph gives "e.g. 32" as an illustrative bound, not a fixed mandated constant). The exact bound is an implementation parameter for this phase but must remain bounded and inference-only, matching the "bounded inference" principle stated for Practical Feasibility (§17).
- No uploader-supplied code is executed at any point (Master Graph §0 Master Rule / architecture security boundary: "No uploader-supplied `model.py` is executed. No unrestricted pickle loading is used.")

## 5. STRIP-style entropy measurement

- Each bounded inference pass produces a softmax output; entropy is computed over these outputs to produce `H_STRIP`.
- `H_STRIP` is then compared against a baseline.

**DECISION REQUIRED (D3 — STRIP entropy baseline):** The Master Graph explicitly leaves the definition of the expected baseline for `H_STRIP` unresolved. This plan does **not** invent a baseline definition. Implementation of this step must surface D3 rather than silently choosing one.

## 6. Behavioral score normalization

Per Master Graph §8:

```
compare against baseline
        |
        v
behavioral anomaly normalization
        |
        v
S_behavior ∈ [0,1]
```

**DECISION REQUIRED (D4 — S_behavior normalization):** The exact conversion from baseline-relative entropy evidence to a `[0,1]` value is explicitly unresolved in the Master Graph. This plan does not invent this formula. Implementation must treat this as a blocking open decision, surface it to the team, and only proceed once resolved (or proceed against a clearly-labeled mock/placeholder if working ahead using mocks, per §11/§12).

## 7. Quantized-model behavioral probing bypass

Per Master Graph §8 and Master Rule 8:

```
is_quantized = TRUE
        |
        v
SKIP behavioral probing
        |
        v
use quantized MRS formula
```

- If `is_quantized == TRUE`, behavioral probing is **skipped entirely** — no probes are constructed or run.
- The downstream risk path uses the quantized MRS formula (Phase 6 concern), which excludes `S_behavior` (see Master Graph §9: `MRS = min(100, 55*S_static + 45*P_tamper)` for quantized models).
- This bypass is a hard architectural rule (Master Rule 8), not a tunable behavior.

## 8. Behavioral score generation — output

- For non-quantized models, this phase's job is to produce `S_behavior ∈ [0,1]` per the (currently unresolved) normalization in §6.
- For quantized models, no `S_behavior` is generated (bypass per §7); downstream consumers must expect its absence for quantized models.
- Output feeds into `risk_results.json` (via P2 prober.py), whose exact schema is **D1, DECISION REQUIRED** (empty schema, exact fields TBD).

## 9. Interaction with upstream P1/P3 outputs

- `input_domain` and `is_quantized` (from P1) gate probe construction and the bypass decision (§3, §7).
- `P_tamper` (from P3's `ml_results.json`) is **not** consumed by the behavioral-probing step itself but is a required upstream verified output before P2's **final** risk integration (which combines `S_static`, `P_tamper`, `S_behavior` into MRS) can proceed — that combination step belongs to Phase 6.
- Per Master Graph §12 (Parallel Work table): P2 probe design can proceed now using mocks; P2 final risk integration is blocked ("NO until required real upstream outputs — P1/P3").
- Per Change-Impact Map (§14): if P1's `input_domain` or `is_quantized` semantics change, P2 must reverify. If P3's `P_tamper` semantics change, P2 recalibration/reverification is required. If STRIP baseline/normalization changes, P2 and downstream risk/report verification is required.

## 10. Explicit non-goals for this phase

- Do not implement the final MRS formula or risk aggregation across S_static/P_tamper/S_behavior — that is Phase 6.
- Do not resolve D3 (STRIP baseline) or D4 (normalization) by inventing a formula.
- Do not resolve D1 (contract schema fields) here — track as open dependency.
- Do not execute any uploaded/untrusted code beyond bounded inference passes on the trusted graph.
- Do not redesign the quantized-bypass rule.

## 11. Exit criteria for this phase (feeds Phase 5 VERIFICATION.md)

- Domain-aware probe construction implemented for VISION and NLP paths.
- Bounded, inference-only pass execution implemented (no backprop, bounded count).
- Quantized bypass implemented and enforced.
- `H_STRIP` computation implemented.
- Baseline comparison and `S_behavior` normalization are either (a) explicitly gated behind the unresolved D3/D4 decisions with the gate visible and not silently defaulted, or (b) implemented per a decision the team has explicitly and separately resolved and recorded (not invented mid-implementation).
- Behavioral output correctly withheld/absent for quantized models.
