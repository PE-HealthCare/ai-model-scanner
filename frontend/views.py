"""Seven pages, one current-scan snapshot. No security calculations."""
import pandas as pd
import streamlit as st
from frontend.adapter import scan_upload, json_export
from frontend.components import header, snapshot, status, link
from frontend.report import pdf_export
from frontend import charts
from src.common.feature_names import FEATURE_NAMES


def plot(fig, key):
    st.plotly_chart(fig, width='stretch', theme=None, key=key, config={'displaylogo': False})


def unavailable(runtime, stage, title):
    state = runtime.get('stages', {}).get(stage, {})
    status(title, state.get('reason', 'This stage did not complete for the current artifact. Valid earlier evidence remains available.'))


def landing():
    st.html('<div class="hero"><div class="eyebrow">PRECISION THROUGH EVIDENCE</div><h1>Analyze AI weights.<br>Detect hidden payloads.</h1><p>Inspect a ResNet18 .safetensors model for statistical and behavioral evidence of hidden manipulation.</p></div>')
    with st.container(key='landing-art'):
        left, middle, right = st.columns([1, 1.6, 1])
        with left: st.caption('expected_distribution')
        with right: st.caption('anomalous_pattern')
        with middle, st.container(key='upload-card'):
            st.caption('UPLOAD MODEL ARTIFACT')
            uploaded = st.file_uploader('Drop a .safetensors file here', type=['safetensors'], max_upload_size=200, key='upload')
            st.caption('ResNet18 only · SafeTensors')
            if st.button('START SCAN', type='primary', disabled=uploaded is None, width='stretch'):
                st.session_state.pop('snapshot', None)
                st.session_state.pop('report_downloads', None)
                with st.status('Analyzing the current artifact…', expanded=True) as progress:
                    st.write('Trusted intake → statistical evidence → structured-LSB assessment')
                    st.caption('Real LightGBM / TreeSHAP and behavioral probes provide additional evidence. This may take a minute.')
                    value = scan_upload(uploaded.name, uploaded.getvalue())
                    st.session_state['snapshot'] = value
                    complete = value['backend'].get('execution_status') == 'COMPLETE'
                    progress.update(label='Scan complete' if complete else 'Partial or blocked assessment', state='complete' if complete else 'error')
                st.switch_page(st.session_state['page_objects']['INTAKE'])
            st.caption('.safetensors only · no uploader-supplied code executed')
    with st.expander('How does the scan work? →'):
        st.write('Validate trusted ResNet18 tensor structure and inspect per-layer statistics. The frozen structured-LSB detector supplies the final assessment. LightGBM / TreeSHAP is advisory; bounded behavioral probes supply supporting evidence.')
        st.caption('No trigger verifier executes. Classifier scores and MRS do not establish universal malware detection.')
    if st.session_state.get('snapshot'): link('REPORT', 'Return to the current scan →')


def intake():
    header('STAGE 01 / INTAKE', 'Validate before you analyze.', 'Verify the artifact and establish a trusted boundary before analysis begins.')
    value = snapshot(); result = value['backend']; runtime = result.get('canonical', {})
    if result['intake']['status'] != 'PASS':
        status('SCAN BLOCKED · ASSESSMENT WITHHELD', result.get('error', {}).get('message', 'Trusted intake did not complete.'))
        st.caption('An intake failure is not a security FAIL. Downstream analysis is not presented as completed.')
        link('NEW SCAN', 'Choose another file →'); return
    artifact = result['artifact']
    status('INTAKE VERIFIED', 'SafeTensors parsed · trusted ResNet18 structure accepted · uploader code not executed', 'pass')
    a,b,c = st.columns(3)
    a.metric('Architecture / domain', artifact['architecture']+' / '+artifact['input_domain'])
    b.metric('Weight precision', artifact['dtype']); c.metric('State-dict tensors', artifact['tensor_count'])
    with st.container(border=True):
        st.subheader('Validation evidence')
        st.write('Tensor names, shapes, dtypes and resource limits accepted by P1 intake against the declared trusted ResNet18 graph.')
        st.caption(f"Quantized: {artifact['is_quantized']} · Statistical rows: {runtime.get('features', {}).get('layer_count', 'unavailable')}")
    st.subheader('Current pipeline / runtime')
    st.dataframe(pd.DataFrame([{'Stage':k, **v} for k,v in runtime.get('stages', {}).items()]), hide_index=True, width='stretch')
    with st.expander('Tensor inventory / identity / provenance'):
        st.json(artifact); st.write('Generation commit: '+runtime.get('generation_commit', 'unavailable'))
        st.write(f"Elapsed: {value['duration_seconds']:.2f}s")
    link('STATIC', 'Inspect static evidence →')


def static():
    header('STAGE 02 / STATIC STEGANALYSIS', 'Inspect what the weights reveal.', 'Investigate measured layer statistics and the authoritative structured-LSB evidence.')
    value = snapshot(); result = value['backend']; runtime = result.get('canonical', {})
    features = runtime.get('features')
    if features:
        rows = features['static_features']; layers = [r['layer_name'] for r in rows]
        names = [n for n in FEATURE_NAMES if any(r.get(n) is not None for r in rows)]
        highest = runtime.get('dashboard_results', {}).get('highest_risk_layer')
        selected = st.selectbox('Investigate a layer', layers, index=layers.index(highest) if highest in layers else 0, key='layer_'+value['scan_id'])
        st.subheader('Layer evidence map')
        st.caption(f"{len(rows)} layers × {len(names)} features · Raw values on hover. Each column uses its own raw-value color range; darkness is not a risk score and is not comparable between columns. Outlined row = selected layer.")
        plot(charts.layer_map(rows, names, selected), 'layer-map')
        a,b = st.columns([2,1]); a.caption('D6 STATISTICAL OUTLIER · DIAGNOSTIC'); a.write(highest or 'Unavailable')
        a.caption('D6 evidence E(l): '+str(runtime.get('dashboard_results', {}).get('highest_risk_evidence', 'unavailable')))
        b.metric('Analyzed layers', len(rows))
        row = rows[layers.index(selected)]
        overview, distribution, bits, raw = st.tabs(['OVERVIEW','DISTRIBUTION','BIT EVIDENCE','RAW STATISTICS'])
        with overview:
            st.write('Selected layer: '+selected)
            st.dataframe(pd.DataFrame([{'Feature':n,'Raw value':row.get(n)} for n in names]), hide_index=True, width='stretch')
        with distribution: st.info('Per-weight histograms are not emitted. Mean, std, skewness and kurtosis are available in raw statistics.')
        with bits:
            st.json({n:row.get(n) for n in ('entropy','pov_chi2','lsb_kl','ks_stat')})
            st.caption('Aggregate indicators only; bit counts and window traces are not emitted.')
        with raw: st.json(row)
    else: unavailable(runtime, 'static', 'STATIC EVIDENCE UNAVAILABLE')
    with st.expander('Authoritative structured-LSB forensic assessment', expanded=not bool(features)):
        detector = result.get('structured_stego')
        if detector:
            st.write(f"{detector['verdict']} · score {detector['score']:.6g} · threshold {detector['threshold']:.6g}")
            st.caption('Final assessment source. These are model-level window statistics, not localization to the D6 layer. Repeat fraction is diagnostic only.')
            st.dataframe(pd.DataFrame([{'Measurement':k,'Value':v} for k,v in detector['features'].items()]), hide_index=True, width='stretch')
        else: st.write(result.get('structured_status', {'status':'unavailable'}))
    link('EXPLAINABILITY', 'Explain the classifier response →')


def explainability():
    header('STAGE 03 / EXPLAINABILITY', 'Explain the classifier response.', 'Real TreeSHAP contributions to the current LightGBM response.')
    value = snapshot(); runtime = value['backend'].get('canonical', {}); ml = runtime.get('ml_results')
    if not ml: unavailable(runtime, 'ml', 'EXPLAINABILITY UNAVAILABLE'); return
    explanation = runtime.get('explanation', {})
    authoritative_verdict = value['backend'].get('verdict')
    if authoritative_verdict == 'PASS':
        status('CLEAN MODEL', "No significant structured steganographic manipulation was detected. The TreeSHAP analysis below shows how the model's statistical features influenced the advisory classifier response.")
    elif authoritative_verdict == 'FAIL':
        status('TAMPERED MODEL', 'Structured steganographic manipulation was detected. The TreeSHAP analysis below shows which statistical features most influenced the advisory classifier response.')
    st.subheader('Feature contribution / TreeSHAP')
    plot(charts.shap_chart(ml, explanation), 'shap')
    contributions = ml['shap_attributions']
    positives = [k for k,v in contributions.items() if v > 0]; negatives = [k for k,v in contributions.items() if v < 0]
    a,b,c = st.columns(3)
    a.metric('P_tamper', f"{ml['p_tamper']:.6f}")
    b.metric('Top upward driver', max(positives,key=contributions.get) if positives else 'None')
    c.metric('Top downward driver', min(negatives,key=contributions.get) if negatives else 'None')
    st.caption(f"Classifier: {ml['model_version']} · Explained layer: {explanation.get('explained_layer', 'unavailable')}. D10 classifier selection differs from D6 static selection.")
    with st.expander('Attribution values / model identity / additivity'): st.json(explanation); st.json(ml)
    link('BEHAVIOR', 'Review behavioral evidence →')


def behavior():
    header('STAGE 04 / BEHAVIOR', 'Test how the model behaves.', 'Supporting evidence: bounded random-noise probes against stored ResNet18 calibration. This does not override the statistical assessment.')
    value = snapshot(); runtime = value['backend'].get('canonical', {}); p2 = runtime.get('p2_evidence', {})
    observation = p2.get('behavior')
    if not observation: unavailable(runtime, 'behavior_risk', 'BEHAVIORAL EVIDENCE UNAVAILABLE')
    elif observation['bypassed_behavior']: status('BEHAVIOR NOT APPLICABLE', 'The quantized backend bypasses probing. S_behavior is null, not zero.')
    else:
        calibration = p2.get('calibration', {})
        st.subheader('Behavioral calibration / current observation')
        if calibration.get('h_strip_values'): plot(charts.behavior_chart(observation, calibration), 'behavior-calibration')
        else: status('CALIBRATION OBSERVATIONS UNAVAILABLE', 'Summary values are available; no distribution is fabricated.')
        a,b,c = st.columns(3)
        a.metric('S_behavior', f"{observation['s_behavior']:.6g}")
        b.metric('Current H_STRIP', f"{observation['h_strip']:.6g}"); c.metric('Successful probes', observation['successful_probe_count'])
        st.caption(f"Baseline median {calibration.get('median')} · MAD {calibration.get('mad')} · {calibration.get('repetitions')} calibration repetitions. Histogram = calibration, not current per-probe observations.")
        with st.expander('Probe protocol / calibration / provenance'):
            st.write('32 random VISION noise inputs; eval/no_grad mode; mean softmax Shannon entropy. Runtime probes are stochastic. Calibration comparability across differing heads is not established.'); st.json(p2)
    st.caption('Trigger verification: unavailable — no trigger verifier executes.')
    link('RISK', 'Review the final assessment →')


def risk():
    header('STAGE 05 / FINAL ASSESSMENT', 'Combine the evidence.', 'One authoritative statistical assessment, with supporting and advisory evidence kept distinct.')
    value = snapshot(); result = value['backend']; runtime = result.get('canonical', {}); detector = result.get('structured_stego')
    if not detector:
        status('ASSESSMENT WITHHELD', result.get('structured_status', {}).get('reason', result.get('error', {}).get('message', 'Required statistical evidence is unavailable.')))
        st.caption('No historical MRS or advisory output is substituted for the missing authoritative result.')
        link('REPORT'); return
    message = ('No statistical evidence exceeded the configured criteria within the tested scope.' if result['verdict'] == 'PASS'
               else 'Structured-LSB evidence met or exceeded the configured detection threshold within the tested scope.')
    status(result['verdict'], message, result['verdict'].lower())
    st.subheader('Statistical evidence vs detection threshold')
    plot(charts.statistical_decision(detector), 'statistical-decision')
    a,b,c = st.columns(3)
    a.metric('Observed S_FULL', f"{detector['score']:.9g}"); b.metric('Frozen threshold', f"{detector['threshold']:.9g}"); c.metric('Dominant signal', detector['dominant_signal'])
    st.caption('None of the evaluated statistical signals exceeded the configured detection boundary.' if result['verdict'] == 'PASS'
               else f"{detector['dominant_signal']} was the dominant statistical anomaly and exceeded the configured detection boundary.")
    st.subheader('Evidence behind the decision'); plot(charts.statistical_signals(detector), 'statistical-signals')
    st.caption('S_FULL = max(0, entropy, printable, chi2, transition normalized signals). Repeat fraction is excluded. No 0–100 score is defined for this detector.')
    observation = runtime.get('p2_evidence', {}).get('behavior', {})
    st.write('SUPPORTING · Behavior: '+str(observation.get('status', 'unavailable'))+' · S_behavior: '+str(observation.get('s_behavior', 'unavailable')))
    st.write('ADVISORY · LightGBM output: '+str(runtime.get('ml_results', {}).get('p_tamper', 'unavailable'))+' · not used in the final assessment')
    with st.expander('Technical details / historical MRS diagnostic — excluded from final decision'):
        st.caption('The historical multi-signal MRS returned FAIL on the clean torchvision reference: 40 × 1 + 35 × 0.9255387 + 25 × 0 = 72.39. It is retained only as experimental engineering evidence.')
        st.json(runtime.get('risk_results', {})); st.json(runtime.get('p2_evidence', {})); st.json(detector)
    link('REPORT', 'Open the security report →')


def report():
    header('STAGE 06 / FINAL REPORT', 'From evidence to assessment.', 'One current-scan snapshot for the screen, JSON and PDF.')
    value = snapshot(); result = value['backend']; runtime = result.get('canonical', {}); risk_result = runtime.get('risk_results', {})
    status(result['verdict'], 'Authoritative structured-LSB assessment · '+('No evidence exceeded the configured criteria within the tested scope.' if result['verdict'] == 'PASS' else 'See the current detector evidence and scope below.'), result['verdict'].lower())
    left,right = st.columns([1.5,1])
    with left, st.container(border=True):
        st.subheader('Traceable findings')
        st.write('D6 statistical outlier (diagnostic): '+runtime.get('dashboard_results', {}).get('highest_risk_layer', 'unavailable'))
        st.write('Advisory LightGBM output: '+str(runtime.get('ml_results', {}).get('p_tamper', 'unavailable')))
        attributions = runtime.get('ml_results', {}).get('shap_attributions', {})
        if attributions:
            top = sorted(attributions, key=lambda name: abs(attributions[name]), reverse=True)[:3]
            st.caption('Largest TreeSHAP contributions: '+', '.join(f'{name} ({attributions[name]:+.4f})' for name in top))
        observation = runtime.get('p2_evidence', {}).get('behavior', {})
        st.write('Supporting behavior: '+str(observation.get('status','unavailable'))+' · S_behavior: '+str(observation.get('s_behavior', 'unavailable')))
        detector = result.get('structured_stego')
        if detector: st.write(f"Authoritative score: {detector['score']:.9g} · threshold: {detector['threshold']:.9g}")
        if result.get('error'): st.error(result['error']['message'])
    with right, st.container(border=True):
        st.subheader('Evidence trail')
        for title in ('INTAKE','STATIC','EXPLAINABILITY','BEHAVIOR','RISK'): link(title)
    with st.expander('Assurance, scope & limitations', expanded=True):
        for limitation in value['limitations']: st.write('• '+limitation)
    with st.expander('Complete snapshot / integrity / provenance'): st.code(value['evidence_sha256']); st.json(value)
    cached = st.session_state.get('report_downloads')
    if not cached or cached['scan_id'] != value['scan_id']:
        cached = {'scan_id':value['scan_id'], 'json':json_export(value), 'pdf':pdf_export(value)}
        st.session_state['report_downloads'] = cached
    a,b = st.columns(2)
    a.download_button('Download Security Report — PDF', cached['pdf'], file_name=f"sigtensor-{value['scan_id'][:8]}.pdf", mime='application/pdf', type='primary', width='stretch')
    b.download_button('Download Evidence — JSON', cached['json'], file_name=f"sigtensor-{value['scan_id'][:8]}.json", mime='application/json', width='stretch')


PAGES = [('NEW SCAN',landing),('INTAKE',intake),('STATIC',static),('EXPLAINABILITY',explainability),('BEHAVIOR',behavior),('RISK',risk),('REPORT',report)]
