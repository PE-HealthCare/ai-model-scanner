# Current runtime integration — 2026-10-01

The UI calls `scan_model.run_pipeline` in a unique temporary output directory,
then runs `run_structured_scan` as the authoritative assessment. No HTTP API is needed.
Both outputs belong to the uploaded artifact; historical output JSON is never
used. The CLI remains the separate structured scanner; the UI explicitly calls
the canonical Python API.

| Page | Current snapshot source |
|---|---|
| Intake | `backend.artifact`, `backend.canonical.stages.intake` |
| Static | `backend.canonical.features.static_features` (102 × 10 on torchvision fixture) |
| Authoritative assessment | `backend.structured_stego`, returned by `src.p3_ml_dashboard.structured_stego.scan` |
| Explainability | `canonical.ml_results.shap_attributions`, `canonical.explanation` |
| Behavior | `canonical.p2_evidence.behavior` and `.calibration` |
| Final decision | `backend.verdict`: validated structured detector verdict, passed through unchanged |
| D6 | `canonical.dashboard_results.highest_risk_layer/highest_risk_evidence` |
| Report | Same finalized v3 snapshot as every other page; JSON/PDF share its digest |

Historical FP MRS formula is `min(100,40*S_static+35*P_tamper+25*S_behavior)`;
quantized uses 55/45 and null behavioral contribution. Backend verdict uses
unrounded score: PASS <=34, REVIEW <=69, otherwise FAIL; published MRS rounds
to two decimals. The backend exposes the ledger; UI does not calculate scores.
P_tamper contributes to historical MRS only; both are excluded from the final
assessment. LightGBM/TreeSHAP is advisory, behavior supporting, and structured
LSB authoritative. No new 0–100 score is defined. D10's explained layer and D6's selected
static layer are separate and explicitly identified.

Runtime verification on clean `data/models/resnet18_pretrained.safetensors`
completed P1, LightGBM, TreeSHAP, 32 VISION probes, MRS and D6. Canonical result:
S_static=1, P_tamper=0.9255387214552797, MRS=72.39/FAIL when S_behavior=0.
Separate structured result: 0.6744907594765952 < 3.180525532491262, PASS.
Historical MRS is confined to technical details; the final clean assessment is
PASS from the structured detector. Its threshold and mathematics are unchanged.
No detection-performance guarantee follows from pipeline completion.

Behavior uses random image-noise probes, not trigger verification. H_STRIP and
30 stored calibration observations are exposed without changing normalization.
Probes are stochastic; calibration comparability across differing heads is not
established. No fabricated trigger plots, per-probe series or weight histograms.

P1 and ML evidence survive later stage failure. Structured failure withholds the
final assessment even when historical MRS exists. Advisory/supporting failure
does not invalidate a successfully completed authoritative assessment.
The canonical call serializes P2's process-local handoff. Sessions have unique
temporary directories and immutable export snapshots; navigation never rescans.

The heatmap uses raw P1 values with a separate raw color range per feature,
explicitly labeled as display scales, not risk scores. SHAP is in raw-margin
units. Behavior plots calibration repetitions and current mean entropy. Risk
plots the genuine structured score, frozen threshold, and four normalized
signals. Historical MRS values remain in the technical details only. Quantized
behavior remains N/A and authoritative assessment is WITHHELD (requires FP32).

Run locally with the required venv:

```powershell
& '.\.venv\Scripts\python.exe' -m streamlit run frontend/app.py --server.address 127.0.0.1
```

Test with `pytest frontend/tests/test_integration.py tests/test_real_pipeline.py`.
Browser QA: start on port 8502 and run `frontend/tests/browser_smoke.py`.
Screenshots and exported QA reports remain under ignored `tmp/ui-qa/`.
The existing assets and seven-page shell are reused. Plotly is the only new
runtime dependency. LightGBM model bytes and `.gitattributes` stay unchanged.
