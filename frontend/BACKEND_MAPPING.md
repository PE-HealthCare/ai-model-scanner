# Verified integration

Entry point: `frontend/app.py` (Streamlit). Direct Python adapter calls
`scan_model.run_structured_scan`; no HTTP API or subprocess scanner is needed.

| UI | Current source |
|---|---|
| Intake | `artifact`, `intake` from `run_structured_scan` |
| Static | `structured_stego.features` (five model-level statistics) |
| Explanation | `structured_stego.z_scores`, `dominant_signal`; not SHAP |
| Behavior | `behavioral.validated_for_final_decision=False`; no probe output |
| Risk | Backend `verdict`, `structured_stego.score` and `threshold`; not MRS |
| Report | One session snapshot of this result, with upload metadata and evidence digest |

The CLI `__main__` uses the same scanner. The old `run_pipeline` remains a
separate legacy MRS/P_tamper/behavioral path and is never called by this UI.
TreeSHAP, trigger verification and highest-risk-layer outputs are unavailable
on the active path. Historical `data/outputs` files are never loaded for uploads.
No current HTTP API was found in the executable application source.

Four scored features: entropy, printable fraction, byte chi-square, transition
deviation. Repeat fraction is diagnostic only. No model probability is exposed.
The current backend derives a reference from all 13 development-clean cached
vectors while retaining an OOF-selected threshold. Reports disclose this
normalization distinction and do not claim independent external validation.

The original preview layer heatmap / SHAP / behavioral / MRS charts require
unavailable evidence. Their corresponding seven pages preserve the visual
shell and instead display actual model-level measurements, signed z-scores,
availability explanations, and the authoritative backend verdict.

Run: `.venv\Scripts\python.exe -m streamlit run frontend/app.py`
Install UI dependencies: `.venv\Scripts\python.exe -m pip install -r frontend/requirements.txt`
Uploads are staged in a unique temporary directory and removed after inference.
Reports live in session memory; JSON and PDF use the same finalized snapshot.
# Integration safety checks

The orchestration boundary rejects non-FP32/quantized weight representations and
non-finite source weights before running the unchanged structured detector. This
prevents partial bit-stream scans and false FP32 labels. The adapter checks result
completeness, finite JSON, artifact SHA and consistent backend verdict fields; it
does not recompute detector features, scores or decisions.
P1-supported integer/bool batch counters remain accepted; integer **weights** do
not. The guard changes neither P1 intake/feature definitions nor the structured
detector's extraction, normalization, score or threshold. Unsupported assessments
raise errors; the UI represents them as WITHHELD, not a security PASS/FAIL.

### Assurance trace

- `scripts/run_p3c_structured_generalization.py:score_eval`: 3 grouped folds;
  normalization uses only each training fold's clean rows.
- `scripts/run_p3d_structured_threshold.py:run`: selects the boundary from saved
  `full.scores`; the saved threshold artifact identifies DEVELOPMENT_ONLY and
  PROMPT3C_FULL_OOF. Its score map matches the evaluation artifact exactly.
- `src/p3_ml_dashboard/structured_stego.py:deployment_reference`: recomputes
  normalization using all 13 clean cached vectors, not the fold references.
- `data/external_validation/metadata/external_clean_discovery.json`: two accepted
  candidates, minimum five; decision EXTERNAL_CLEAN_SET_INSUFFICIENT. Acquisition
  is not a completed independent external performance evaluation.

The static page's measurements and `STATIC-*` evidence IDs are explicitly
categorized STRUCTURED_LSB. They are not P1 entropy/pov_chi2/lsb_kl/ks_stat or
B0/B1 per-layer rows. Those are unavailable on this execution path.

## Local verification

Run from the repository with the existing venv:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest frontend/tests/test_integration.py tests/test_intake.py -k 'not distilbert' -q
```

Optional browser QA (`frontend/requirements-dev.txt`, Microsoft Edge) requires
the app running on localhost:8502, then:

```powershell
& '.\.venv\Scripts\python.exe' frontend/tests/browser_smoke.py
```

Browser QA reads two existing DEVELOPMENT artifacts and a quantized fixture;
it never opens FINAL-TEST or S4. Temporary screenshots and exports go to
`tmp/ui-qa/`. Test examples are not runtime/demo results. The full intake suite
also contains two legacy DistilBERT tests requiring the absent `transformers`
package; those are outside this ResNet18 application scope.

This is a local single-process application, not an internet-facing hardened
upload service. Bind Streamlit to `127.0.0.1`. Uploads are capped at 200 MiB;
temporary files are deleted on success/failure. Results live in session state,
not a shared JSON result file. Refreshing/closing the session can discard them;
download the evidence to retain an assessment. Backend rescans run only on the
explicit START SCAN action, not navigation.
