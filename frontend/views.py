"""Seven views, one backend snapshot; no scoring logic lives in the UI."""
from html import escape
import altair as alt
import pandas as pd
import streamlit as st
from frontend.adapter import scan_upload, json_export
from frontend.components import header, snapshot, successful, status, link
from frontend.report import pdf_export


def landing():
    st.html('<div class="hero"><div class="eyebrow">PRECISION THROUGH EVIDENCE</div><h1>Analyze AI weights.<br>Detect hidden payloads.</h1><p>Inspect a ResNet18 .safetensors model for statistical evidence of hidden manipulation.</p></div>')
    with st.container(key='landing-art'):
        left, middle, right = st.columns([1, 1.6, 1])
        with left: st.caption('expected_distribution')
        with right: st.caption('anomalous_pattern')
        with middle, st.container(key='upload-card'):
            st.caption('UPLOAD MODEL ARTIFACT')
            uploaded = st.file_uploader('Drop a .safetensors file here', type=['safetensors'], max_upload_size=200, key='upload')
            st.caption('ResNet18 only · FP32 structured-LSB analysis')
            if st.button('START SCAN', type='primary', disabled=uploaded is None, width='stretch'):
                st.session_state.pop('snapshot', None)
                with st.status('Validating the artifact and analyzing weight bytes…', expanded=True) as progress:
                    st.write('Trusted ResNet18 intake → structured-LSB detector → finalized evidence')
                    value = scan_upload(uploaded.name, uploaded.getvalue())
                    st.session_state['snapshot'] = value
                    progress.update(label='Scan complete' if 'structured_stego' in value['backend'] else 'Scan could not complete', state='complete' if 'structured_stego' in value['backend'] else 'error')
                st.switch_page(st.session_state['page_objects']['INTAKE'])
            st.caption('.safetensors only · no uploader-supplied code executed')
    with st.expander('How does the scan work? →'):
        st.write('Validate tensor names, shapes and values against trusted ResNet18. Extract the model-level FP32 bit-0 byte stream. Inspect its local structure and apply the backend threshold. Review the evidence and export the assessment.')
        st.write('Explanation uses the detector’s returned signals. Behavioral probes, trigger verification, TreeSHAP and MRS are unavailable in this scan path.')
    if st.session_state.get('snapshot'):
        link('REPORT', 'Return to the current scan →')


def intake():
    header('STAGE 01 / INTAKE', 'Validate before you analyze.', 'Verify the artifact and establish a trusted boundary before analysis begins.')
    value = snapshot(); result = value['backend']
    if 'structured_stego' not in result:
        status('SCAN BLOCKED · ASSESSMENT WITHHELD', 'An intake or detector requirement could not be satisfied.')
        with st.expander('View failure details', expanded=True):
            st.write(result['error']['message'])
            st.caption('This is an execution failure, not a security FAIL. No successful result from an earlier scan is reused.')
        link('NEW SCAN', 'Choose another file →')
        return
    artifact = result['artifact']
    status('INTAKE VERIFIED', 'SafeTensors parsed · trusted ResNet18 structure accepted · uploader code not executed', 'pass')
    a, b, c = st.columns(3)
    a.metric('Architecture', artifact['architecture']); b.metric('Representation', artifact['dtype']); c.metric('State-dict tensors', artifact['layer_count'])
    with st.container(border=True):
        st.subheader('Validation evidence')
        st.dataframe(pd.DataFrame([{'Check': 'Trusted graph', 'Observed': artifact['architecture'], 'Source': 'P1 intake'},
            {'Check': 'Input domain', 'Observed': artifact['input_domain'], 'Source': 'P1 intake'},
            {'Check': 'Quantization', 'Observed': str(artifact['is_quantized']), 'Source': 'P1 intake'},
            {'Check': 'Intake', 'Observed': result['intake']['status'], 'Source': 'Backend result'}]), hide_index=True, width='stretch')
    with st.expander('Scan details / full identity'):
        st.json(artifact)
        st.write(f"End-to-end duration: {value['duration_seconds']:.3f} seconds")
        st.caption('Individual stage timings and memory measurements are not exposed.')
    link('STATIC', 'Inspect static evidence →')


def static():
    header('STAGE 02 / STATIC STEGANALYSIS', 'Inspect what the weights reveal.', 'Local byte structure measured across the complete FP32 mantissa bit-0 stream.')
    value = snapshot(); detector = successful(value)
    with st.container(border=True):
        st.subheader('Structured LSB · model-level evidence')
        st.caption('Actual structured-detector measurements, not P1 per-layer B0/B1 forensic features or layer risk scores.')
        rows = [{'Evidence': x['id'], 'Feature': x['feature'], 'Value': x['value'], 'Role': 'Diagnostic only' if x['diagnostic_only'] else 'Scored'} for x in value['evidence']]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    choices = list(detector['features'])
    selected = st.selectbox('Investigate a feature', choices, key='selected_feature')
    overview, raw, scope = st.tabs(['OVERVIEW', 'RAW EVIDENCE', 'MEASUREMENT SCOPE'])
    with overview:
        st.metric(selected, format(detector['features'][selected], '.12g'))
        notes = {'min_window_entropy': 'Lowest normalized byte entropy over all windows.', 'max_window_printable_fraction': 'Largest fraction of bytes in ASCII range 32–126.', 'max_window_byte_chi2': 'Largest byte-histogram chi-square statistic against a uniform distribution.', 'max_window_transition_deviation': 'Largest absolute bit-transition-rate deviation from 0.5.', 'max_window_repeat_fraction': 'Largest repeated 16-byte-block fraction. Diagnostic only; excluded from the score.'}
        st.write(notes[selected])
    with raw: st.json(next(x for x in value['evidence'] if x['feature'] == selected))
    with scope:
        st.write('4096-byte windows · 2048-byte stride · canonical tensor ordering · little-endian packing')
        st.caption('The active scanner exposes aggregate model evidence. Layer rankings, layer heatmaps and per-window traces are not available.')
        st.write('P1 entropy, pov_chi2, lsb_kl, ks_stat, mean/std, skewness/kurtosis, sparsity and outlier_pct are NOT AVAILABLE in this scan result. They are not substituted by the structured window statistics above.')
    link('EXPLAINABILITY', 'Explain the detector response →')


def explainability():
    header('STAGE 03 / EXPLAINABILITY', 'Explain the detector response.', 'Inspect the four normalized signals returned by the backend.')
    value = snapshot(); detector = successful(value)
    with st.container(border=True):
        st.subheader('Signal comparison')
        frame = pd.DataFrame([{'Signal': name, 'Normalized deviation': number} for name, number in detector['z_scores'].items()])
        chart = alt.Chart(frame).mark_bar(color='#474747').encode(x=alt.X('Normalized deviation:Q', title='Signed normalized deviation'), y=alt.Y('Signal:N', sort=None), tooltip=['Signal', 'Normalized deviation']).properties(height=240).configure_axis(labelColor='#474747', titleColor='#474747', gridColor='#dddddd', labelFontSize=12, titleFontSize=12)
        st.altair_chart(chart, width='stretch', theme=None)
        st.caption('The score takes the maximum of zero and these signals; it does not sum contributions. Repeat fraction is excluded.')
    st.metric('Backend dominant signal', detector['dominant_signal'])
    with st.expander('Exact detector values and provenance'):
        st.json(detector)
    status('TREESHAP NOT AVAILABLE', 'No auxiliary learned classifier or SHAP explanation is executed for this scan. The chart shows statistical deviations, not feature attributions.')
    link('BEHAVIOR', 'Review behavioral coverage →')


def behavior():
    header('STAGE 04 / BEHAVIOR', 'Test how the model behaves.', 'Review what the current scan can establish about model behavior.')
    value = snapshot()
    status('BEHAVIORAL EVIDENCE NOT AVAILABLE', 'The current structured-LSB scan does not execute model probes or a behavioral classifier.')
    with st.container(border=True):
        st.subheader('Coverage boundary')
        st.write('Weight-byte anomalies do not demonstrate a behavioral backdoor. No trigger candidates, probe responses or calibrated behavioral baseline are returned by this scan.')
        st.caption('Quantized inputs are unsupported by the active FP32 detector. No zero-valued behavioral score is substituted.')
    with st.expander('Backend applicability record'):
        st.json(value['backend'].get('behavioral', {'status': 'NOT_AVAILABLE'}))
    link('RISK', 'Review the assessment →')


def risk():
    header('STAGE 05 / ASSESSMENT', 'Combine the evidence.', 'The current assessment is the backend structured-LSB decision.')
    value = snapshot(); detector = successful(value)
    verdict = value['backend']['verdict']
    status(verdict, 'The structured-LSB score is ' + ('below' if verdict == 'PASS' else 'at or above') + ' the backend threshold.', verdict.lower())
    a, b, c = st.columns(3)
    a.metric('Structured score', f"{detector['score']:.6g}"); b.metric('Threshold', f"{detector['threshold']:.6g}"); c.metric('Dominant signal', detector['dominant_signal'])
    with st.expander('Why this assessment?', expanded=True):
        st.write('Decision source: scan_model.run_structured_scan → structured_stego.scan.')
        st.code(f"score = {detector['score']!r}\nthreshold = {detector['threshold']!r}\nbackend verdict = {verdict}", language='text')
        st.write('This score is not a calibrated probability and has no 0–100 risk scale. MRS and P_tamper are not used.')
    link('STATIC', 'Trace measurements →'); link('REPORT', 'Open the security report →')


def report():
    header('STAGE 06 / FINAL REPORT', 'From evidence to assessment.', 'One traceable snapshot for the assessment, evidence and exports.')
    value = snapshot(); result = value['backend']
    status(result['verdict'], 'Assessment limited to the current detector and representation.', result['verdict'].lower() if result['verdict'] in ('PASS', 'FAIL') else 'info')
    left, right = st.columns([1.5, 1])
    with left, st.container(border=True):
        st.subheader('Traceable findings')
        st.caption('STRUCTURED LSB EVIDENCE · P1 per-layer forensic evidence is not emitted by this runtime.')
        for evidence in value['evidence']:
            st.write(f"**{evidence['id']}** · {evidence['feature']} · {evidence['value']:.9g}")
            if evidence['diagnostic_only']:
                st.caption('DIAGNOSTIC ONLY · Excluded from the score and verdict')
        if not value['evidence']: st.write('Required detector evidence was not produced. Assessment withheld.')
        link('STATIC', 'Return to source evidence →')
    with right, st.container(border=True):
        st.subheader('Evidence trail')
        for title in ('INTAKE', 'STATIC', 'EXPLAINABILITY', 'BEHAVIOR', 'RISK'): link(title)
    with st.expander('Detector assurance, scope & limitations', expanded=True):
        for limitation in value['limitations']: st.write('• ' + limitation)
    with st.expander('Evidence integrity & complete snapshot'):
        st.code(value['evidence_sha256'], language='text')
        st.caption('SHA256 of canonical snapshot excluding this digest field. Integrity digest, not a digital signature.')
        st.json(value)
    # Derive both downloads from this exact completed scan, never global output files.
    cached = st.session_state.get('report_downloads')
    if not cached or cached['scan_id'] != value['scan_id']:
        cached = {'scan_id': value['scan_id'], 'json': json_export(value), 'pdf': pdf_export(value)}
        st.session_state['report_downloads'] = cached
    a, b = st.columns(2)
    a.download_button('Download Security Report — PDF', cached['pdf'], file_name=f"sigtensor-{value['scan_id'][:8]}.pdf", mime='application/pdf', type='primary', width='stretch')
    b.download_button('Download Evidence — JSON', cached['json'], file_name=f"sigtensor-{value['scan_id'][:8]}.json", mime='application/json', width='stretch')


PAGES = [('NEW SCAN', landing), ('INTAKE', intake), ('STATIC', static), ('EXPLAINABILITY', explainability), ('BEHAVIOR', behavior), ('RISK', risk), ('REPORT', report)]
