# Phase 6 — Integration + Demo — VERIFICATION

**Owner:** Integration surface (`scan_model.py`), plus final P3 Security Report
**Source of truth:** `AI_Model_Scanner_FINAL_MASTER_DISCOVERY_GRAPH.md`
**Gate:** CP6 — Demo Gate (and closes out CP2–CP5 dependencies)

## Pass/Fail Checklist

### 1. Real end-to-end pipeline execution
- [ ] PASS/FAIL: Running `scan_model.py` against a real (non-mock) `.safetensors` input executes the full chain P1 → P3 → P2 → P3 in that order, per §2/§18.
- [ ] PASS/FAIL: `scan_model.py` itself contains no P1/P2/P3 analysis logic — it only orchestrates (Master Rule 5).
- [ ] PASS/FAIL: No uploader-supplied `model.py` is executed anywhere in the run; no unrestricted pickle loading occurs.

### 2. Contract validation
- [ ] PASS/FAIL: `features.json` validates against `features.schema.json` before being consumed by P3/P2.
- [ ] PASS/FAIL: `ml_results.json` validates against `ml_results.schema.json` before being consumed by P2/P3 dashboard.
- [ ] PASS/FAIL: `risk_results.json` validates against `risk_results.schema.json` before being consumed by P3 dashboard.
- [ ] PASS/FAIL: Schema fields used in validation match an explicitly agreed team decision resolving D1 — not fields invented ad hoc during this phase.

### 3. Risk formula correctness
- [ ] PASS/FAIL: For non-quantized models, MRS is computed exactly as `min(100, 40*S_static + 35*P_tamper + 25*S_behavior)`.
- [ ] PASS/FAIL: For quantized models, MRS is computed exactly as `min(100, 55*S_static + 45*P_tamper)`.
- [ ] PASS/FAIL: No alternate weighting, additional terms, or reinterpretation of these formulas is present anywhere in the implementation.
- [ ] PASS/FAIL: `S_static` is derived via the intra-model MAD calibration `Z = (X - median(X_base)) / (1.4826 * MAD(X_base))` before being mapped into `[0,1]`, consistent with §9.
- [ ] PASS/FAIL: Per-layer → model-level aggregation (D5) and the MAD zero/near-zero guard (D7) are either implemented per an explicitly recorded team decision, or explicitly flagged as pending/blocking — not silently invented.

### 4. Quantized path
- [ ] PASS/FAIL: When `is_quantized == TRUE`, the quantized MRS formula is used and no `S_behavior` term is required or referenced.
- [ ] PASS/FAIL: When `is_quantized == FALSE`, the non-quantized MRS formula is used and requires a valid `S_behavior` value.
- [ ] PASS/FAIL: The quantized/non-quantized branch selection is driven solely by P1's `is_quantized` flag.

### 5. PASS / REVIEW / FAIL thresholds
- [ ] PASS/FAIL: MRS in [0, 34] maps to verdict PASS.
- [ ] PASS/FAIL: MRS in [35, 69] maps to verdict REVIEW.
- [ ] PASS/FAIL: MRS in [70, 100] maps to verdict FAIL.
- [ ] PASS/FAIL: Boundary values (34, 35, 69, 70) map to the correct verdict per the ranges above, with no off-by-one errors.

### 6. Report completeness
- [ ] PASS/FAIL: Final Security Report includes MRS + verdict.
- [ ] PASS/FAIL: Final Security Report includes highest-risk layer, derived via a method distinct from TreeSHAP attribution (Path B, §6), not conflated with it.
- [ ] PASS/FAIL: Final Security Report includes TreeSHAP feature-level evidence (Path A, §6), presented as feature attribution to the classifier prediction, not as layer risk.
- [ ] PASS/FAIL: Final Security Report includes a behavioral note (present for non-quantized models; appropriately represented — e.g., explicitly noted as skipped — for quantized models).
- [ ] PASS/FAIL: Final Security Report includes an Assumptions & Limitations section.
- [ ] PASS/FAIL: Report language does not claim PASS as a guarantee of absolute security (per §10 caveat).
- [ ] PASS/FAIL: TreeSHAP feature evidence, highest-risk layer, and the final model-level MRS are presented as three distinct elements, not merged or used interchangeably.

### 7. Reproducibility
- [ ] PASS/FAIL: `requirements.txt` / `pyproject.toml` dependencies are pinned (D9) such that a fresh environment install produces consistent results.
- [ ] PASS/FAIL: Running the pipeline twice on the same input with the same pinned environment produces the same MRS/verdict (given the training artifact `lightgbm_model.txt` is fixed).
- [ ] PASS/FAIL: If `lightgbm_model.txt` staleness protection (D8) has been agreed and implemented, stale-model detection behaves as agreed; if D8 is still unresolved, this is explicitly noted as open rather than assumed absent or present.

### 8. Graceful failure behavior
- [ ] PASS/FAIL: The pipeline's behavior on a failing/erroring stage (P1, P3, or P2) is defined by an explicitly agreed team decision — not a silently invented fallback such as "always return neutral scores."
- [ ] PASS/FAIL: If no graceful-failure policy has been agreed yet, failures surface as explicit errors rather than silently producing a plausible-looking but fabricated report.
- [ ] PASS/FAIL: Regardless of failure path, no uploader-supplied code is executed and no unrestricted pickle loading occurs (hard security boundary, not a fallback).

### 9. One-command demo execution
- [ ] PASS/FAIL: The full pipeline can be invoked with a single command (e.g., `python scan_model.py <input>`).
- [ ] PASS/FAIL: The one-command run produces the final Security Report as its end artifact without requiring manual intermediate steps.
- [ ] PASS/FAIL: The demo run only proceeds using verified real outputs (not mocks) once CP2–CP5 have passed; if any upstream gate has not passed, the demo is not represented as a "final" real run.

## Gate Outcome

- [ ] All applicable items PASS, or open items are explicitly and only tied to unresolved Master Graph decisions (D1, D5, D6, D7, D8, D9, or an unagreed graceful-failure policy) — none silently resolved.
- [ ] CP6 (Demo Gate) is considered met only when: complete E2E execution succeeds; verdict and MRS are correct per the exact formulas/thresholds; highest-risk layer and SHAP evidence are both present and distinct; behavioral note and Assumptions/Limitations are present — per §13.
