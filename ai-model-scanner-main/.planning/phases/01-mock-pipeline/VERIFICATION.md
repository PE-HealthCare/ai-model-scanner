# Phase 01 — Mock Pipeline — VERIFICATION

**Gate:** CP1 — Phase 1 Mock Gate (per Master Graph Section 13)

No phase advances until its VERIFICATION.md gate passes. This is CP1; Phase 02 (Zero-Trust Intake) real implementation may only proceed after all checks below pass.

## Pass/Fail Checklist

### Required Files Exist

- [ ] `data/outputs/features.json` exists (P1 mock output)
- [ ] `data/outputs/ml_results.json` exists (P3 mock output)
- [ ] `data/outputs/risk_results.json` exists (P2 mock output)
- [ ] `features.schema.json` exists and has the team-agreed (D1) field definitions populated (no longer empty)
- [ ] `ml_results.schema.json` exists and has the team-agreed (D1) field definitions populated (no longer empty)
- [ ] `risk_results.schema.json` exists and has the team-agreed (D1) field definitions populated (no longer empty)

### Mock Pipeline Executes

- [ ] `scan_model.py` runs end-to-end against mock inputs without an unhandled exception
- [ ] `scan_model.py` invokes stages in the frozen order: P1 → P3 → P2 → P3 (final report)
- [ ] Each stage's mock output is written to disk (or handed off per the agreed mechanism) before the next stage begins

### JSON Contracts Validate

- [ ] `features.json` validates against `features.schema.json`
- [ ] `ml_results.json` validates against `ml_results.schema.json`
- [ ] `risk_results.json` validates against `risk_results.schema.json`
- [ ] Schema validation is performed programmatically (not visually inspected only) and its result is recorded

### P1 → P3 Handoff Works

- [ ] P3 mock stage successfully reads the P1 mock `features.json`
- [ ] P3 mock stage does not require any field not present in the agreed `features.schema.json`
- [ ] Handoff failure (missing/malformed `features.json`) is detected and reported by the pipeline, not silently skipped

### P3 → P2 Handoff Works

- [ ] P2 mock stage successfully reads the P3 mock `ml_results.json`
- [ ] P2 mock stage does not require any field not present in the agreed `ml_results.schema.json`
- [ ] Handoff failure (missing/malformed `ml_results.json`) is detected and reported by the pipeline, not silently skipped

### Final Orchestration Works

- [ ] `scan_model.py` produces a final report surface consuming the mock `risk_results.json`
- [ ] The final report surface reflects the mock verdict/MRS fields as defined in the agreed `risk_results.schema.json`
- [ ] A single `scan_model.py` invocation completes the full mock chain (P1 → P3 → P2 → P3) without manual intervention between stages

### Failures Are Visible, Not Silently Ignored

- [ ] A deliberately malformed mock `features.json` causes a visible, non-zero-exit failure (not a silently empty or partially-populated downstream result)
- [ ] A deliberately malformed mock `ml_results.json` causes a visible, non-zero-exit failure
- [ ] A missing mock output file at any stage causes a visible failure rather than the pipeline continuing with default/empty values
- [ ] Schema validation failures are surfaced with the specific field(s)/reason(s), not a generic pass/fail with no detail

## Gate Result

- [ ] **PASS** — all checks above are satisfied; Phase 02 real implementation may proceed
- [ ] **FAIL** — one or more checks unsatisfied; remain in Phase 01 until resolved

## Notes

- This gate validates interface and orchestration correctness only. It does not validate detection accuracy, real feature semantics, or real model behavior, none of which exist yet at this phase.
- If any contract field required for a check above is still marked DECISION REQUIRED (D1) and unresolved by the team, that check cannot be marked PASS — record it as blocked on D1 rather than skipping it.
