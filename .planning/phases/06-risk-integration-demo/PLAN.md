# Phase 6 — Integration + Demo — PLAN

**Owner:** Integration surface (`scan_model.py`), consuming verified P1/P2/P3 outputs. Not a fourth implementation owner (Master Rule 5).
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md` (frozen architecture — this plan does not redesign it)
**Status:** Planning only. No code implemented here.

## 1. Scope

Per Master Graph §11 (Phase 6 — Integration + Demo):
> All verified outputs are integrated into the final report.

This phase connects the verified real components in the frozen order:

```
P1 static analysis → P3 ML classification → P2 behavioral probing → final risk aggregation/report
```

matching the orchestration order stated in Master Graph §2 (Ownership Graph): "Orchestrates P1 → P3 → P2 → P3."

This phase may only proceed once upstream gates are cleared (§12 Parallel Work: "Final dashboard integration — NO — All upstream gates").

## 2. Root `scan_model.py` orchestration

Per Master Graph §4 (File/Contract/Data Graph) and §2:

```
scan_model.py
  +--> P1 analyzer.py --> features.json
  +--> P3 classifier.py --> ml_results.json, lightgbm_model.txt
  +--> P2 prober.py --> risk_results.json
  +--> P3 dashboard.py --> final security report
```

- `scan_model.py` is the root orchestration/integration surface (Master Rule 5) — it calls into P1, P3, P2, P3 dashboard in sequence, but does not itself implement analysis, ML, or probing logic.
- Orchestration order is fixed: P1 → P3 (classification) → P2 (behavioral+risk) → P3 (report). This mirrors both the Final Project Graph (§1) and Final Architecture (§18).

## 3. Contract validation

Per Master Graph §4 (Contracts table) and §16 (D1):

- Before/at each handoff, the produced JSON output must validate against its corresponding schema:
  - `features.json` ↔ `features.schema.json` (P1 → P3, P2)
  - `ml_results.json` ↔ `ml_results.schema.json` (P3 → P2, P3 dashboard)
  - `risk_results.json` ↔ `risk_results.schema.json` (P2 → P3 dashboard)
- **DECISION REQUIRED (D1):** All three schemas are currently empty; exact fields/types/layout are unresolved. This plan does not invent these fields. Contract validation in this phase must be built against whatever schema fields the team has explicitly agreed (per §19 Execution Handoff step 1: "Team agrees exact contract fields"), not against fields invented during integration work.
- CP1 (Phase 1 Mock Gate) already requires schema validation for mock outputs; Phase 6 requires the same validation for real outputs.

## 4. Static score, ML tamper probability, behavioral score — inputs to final aggregation

Per Master Graph §9 (Risk Graph), the model-level flow is:

```
per-layer static evidence
        ↓
per-layer P_tamper / anomaly evidence
        ↓
MODEL-LEVEL AGGREGATION
        ↓
S_static + P_tamper + S_behavior
        ↓
MRS
```

- `S_static` — derived from P1's per-layer static evidence, normalized via intra-model MAD as described in §9:
  ```
  Z = (X - median(X_base)) / (1.4826 * MAD(X_base))
  ```
  producing `S_static ∈ [0,1]`.
- `P_tamper` — from P3's `ml_results.json` (LightGBM output).
- `S_behavior` — from P2's Phase 5 output (present for non-quantized models; absent for quantized models per the bypass rule).

**DECISION REQUIRED (D5 — per-layer → model-level aggregation):** The Master Graph explicitly leaves the exact aggregation method from per-layer evidence to model-level `S_static`/`P_tamper` evidence unresolved ("Exact per-layer → model-level aggregation: DECISION REQUIRED unless separately finalized," §9). This plan does not invent this aggregation method.

**DECISION REQUIRED (D7 — MAD zero/near-zero handling):** Per §9, when `MAD(X_base)` is zero/near-zero combined with a very small layer count, an implementation guard is required and is explicitly marked decision-required. This plan does not invent the guard behavior.

## 5. MAD-calibrated risk aggregation and final MRS formulas

Per Master Graph §9, the **final, frozen formulas** are:

- Non-quantized: `MRS = min(100, 40*S_static + 35*P_tamper + 25*S_behavior)`
- Quantized: `MRS = min(100, 55*S_static + 45*P_tamper)`

These exact formulas and weights must be used verbatim — they are not open decisions and must not be altered or reinterpreted during this phase.

## 6. Quantized risk path

- For quantized models (`is_quantized == TRUE`): behavioral probing was skipped in Phase 5 (Master Rule 8, §8), so the aggregation step must use the quantized MRS formula (`55*S_static + 45*P_tamper`) and must not expect or require an `S_behavior` value.
- For non-quantized models: the full formula (`40*S_static + 35*P_tamper + 25*S_behavior`) applies, requiring all three inputs.
- The choice of formula is strictly gated by P1's `is_quantized` flag, consistent with the Change-Impact Map (§14): "P1 `is_quantized` semantics → Static gate + behavioral bypass + MRS path → P2 reverify."

## 7. PASS / REVIEW / FAIL thresholds

Per Master Graph §9, verbatim:

- PASS: 0–34
- REVIEW: 35–69
- FAIL: 70–100

These thresholds apply to the computed MRS value and must be used exactly as specified — no reinterpretation or renumbering.

## 8. Distinguishing TreeSHAP evidence, highest-risk layer, and final model-level risk score

Per Master Graph §6 (TreeSHAP / Layer Distinction), these are **separate relationships** (Master Rule 7) and must remain explicitly distinguished in the final report and its construction:

- **TreeSHAP feature evidence (Path A):** P1 feature (exact name/semantics/representation/order) → LightGBM feature interpretation → TreeSHAP attribution → feature-level explanation. This explains feature contribution to the classifier's prediction.
- **Highest-risk layer (Path B):** P1 tensor/layer identity → feature↔layer association → layer-level anomaly aggregation → highest-risk-layer report. TreeSHAP does **not** by itself determine this.
  - **DECISION REQUIRED (D6):** the exact feature/layer aggregation method for highest-risk-layer determination is unresolved unless separately finalized (§6, §16). This plan does not invent it.
- **Final model-level risk score (MRS):** the single aggregated score from §5/§7 above, distinct from both of the above — it is a model-level number with a verdict, not a feature- or layer-level explanation.

The Security Report (Master Graph §10) must present all three as distinct elements:

```
MRS + verdict
      +
highest-risk layer
      +
TreeSHAP feature evidence
      +
behavioral note
      +
Assumptions & Limitations
      |
      v
P3 Security Report
```

Per §10: "The report communicates evidence of manipulation within the tool's detection scope. PASS is not a guarantee of absolute security." This caveat must be preserved verbatim in spirit in the final report.

## 9. Final security report

- Produced by P3 `dashboard.py`, consuming `risk_results.json` (and, transitively, upstream verified outputs).
- Must include, per §10: MRS + verdict, highest-risk layer, TreeSHAP feature evidence, behavioral note, and an Assumptions & Limitations section.
- Must not overstate guarantees — PASS is scoped to "within the tool's detection scope," not absolute security clearance.

## 10. Reproducibility

- Per Master Graph §15 (Hidden/Indirect Dependencies) item 10 and §16 (D9): `requirements.txt` must eventually be pinned for reproducibility. This is flagged as "a setup issue, not an architectural blocker" but is required for a reproducible one-command demo.
- Per §15 item 9 / §16 (D8): `lightgbm_model.txt` can become stale if P1 feature semantics change after training; whether a staleness check (e.g., version/hash) is added is **DECISION REQUIRED (D8)** and must not be silently assumed present or absent.
- The end-to-end run (P1 → P3 → P2 → P3) must be deterministic/reproducible given the same trusted inputs and pinned dependencies, consistent with the Execution Handoff sequence (§19): agree contracts → pin/install dependencies → implement mocks → run CP1 → advance only after verification passes.

## 11. Agreed graceful failure behavior

The Master Graph does not specify a universal fallback (e.g., "always return neutral scores") anywhere in its text, and Master Rule 9 requires that unresolved items not be silently invented. Accordingly:

- This plan does **not** define a fallback behavior such as defaulting to neutral/zero scores on failure, because the Master Graph does not establish one.
- Any graceful-failure behavior (e.g., what `scan_model.py` does if a stage fails, times out, or produces schema-invalid output) is itself an open implementation decision that must be explicitly proposed and agreed by the team before being implemented — it should be tracked alongside D1–D9 rather than assumed.
- What **is** established by the Master Graph as a hard constraint (not a fallback, but a boundary condition): no uploader-supplied code is ever executed, and no unrestricted pickle loading occurs, regardless of failure path (architecture security boundary, §1).

## 12. Dependency ordering recap (why this phase is last)

Per Master Graph §7 (P3 Training-Data Dependency) and the critical dependency confirmed at project start:

```
P3 Phase 2 preparation → P1 Phase 3 verified real feature extractor → P3 Phase 4 LightGBM training → TreeSHAP verification
```

Phase 6 additionally requires P2's Phase 5 real behavioral/risk work, which itself depends on P3's verified `P_tamper` (§11 Phase 5, §12). Phase 6 cannot begin for real (non-mock) integration until all of CP2 (Intake), CP3 (Static), CP4 (ML), and CP5 (Behavioral/Risk) gates have passed, per §12 ("Final dashboard integration — NO — All upstream gates") and §13 (CP1–CP6 checkpoint definitions).

## 13. Explicit non-goals for this phase

- Do not alter the MRS formulas or PASS/REVIEW/FAIL thresholds — use them exactly as given in §5/§7 above.
- Do not invent D1 (schema fields), D5 (per-layer aggregation), D6 (highest-risk-layer method), D7 (MAD guard), D8 (staleness check), or D9 (pinning specifics beyond "must be pinned").
- Do not invent a generic graceful-failure/fallback policy not stated in the Master Graph.
- Do not merge TreeSHAP feature evidence and highest-risk-layer reporting into a single mechanism — they remain separate per Master Rule 7.
