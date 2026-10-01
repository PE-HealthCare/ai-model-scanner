"""Integration checks; production data is only read, never regenerated."""
import hashlib
import json
from pathlib import Path

import pytest
from frontend.adapter import ROOT, canonical_bytes, json_export, scan_upload
from frontend.report import pdf_export

CLEAN = ROOT / 'data/models/resnet18_pretrained.safetensors'
S6 = ROOT / 'data/training/s6_structured_generalization/8ce8fd79b1064148863d3d9e.safetensors'


@pytest.fixture(scope='module')
def clean_snapshot():
    if not CLEAN.exists():
        pytest.skip('Local development fixture unavailable')
    return scan_upload(CLEAN.name, CLEAN.read_bytes())


def test_real_backend_equivalence(clean_snapshot):
    from scan_model import run_structured_scan
    direct = run_structured_scan(CLEAN)
    assert clean_snapshot['backend']['structured_stego'] == direct['structured_stego']
    assert direct['verdict'] == 'PASS'
    runtime = clean_snapshot['backend']['canonical']
    assert runtime['features']['layer_count'] == 102
    assert clean_snapshot['backend']['verdict'] == direct['verdict'] == 'PASS'
    assert clean_snapshot['backend']['roles']['legacy_mrs'] == 'experimental_excluded'
    assert runtime['p2_evidence']['behavior']['successful_probe_count'] == 32
    assert len(runtime['ml_results']['shap_attributions']) == 10
    assert len(clean_snapshot['evidence']) == 5
    assert all(e['category'] == 'STRUCTURED_LSB' for e in clean_snapshot['evidence'])
    from src.p3_ml_dashboard.structured_stego import scan
    assert direct['structured_stego'] == scan(CLEAN)
    assert not list((ROOT/'tmp/uploads').glob('scan-*'))


def test_real_s6():
    if not S6.exists():
        pytest.skip('Local development fixture unavailable')
    value = scan_upload(S6.name, S6.read_bytes())
    from src.p3_ml_dashboard.structured_stego import scan
    assert value['backend']['structured_stego'] == scan(S6)
    assert value['backend']['structured_stego']['verdict'] == 'FAIL'
    assert value['backend']['verdict'] == 'FAIL'
    import fitz
    text = ''.join(p.get_text() for p in fitz.open(stream=pdf_export(value), filetype='pdf'))
    assert 'Final verdict: FAIL' in text
    assert value['backend']['artifact']['sha256'] == hashlib.sha256(S6.read_bytes()).hexdigest()


@pytest.mark.parametrize('filename,content', [('invalid.safetensors', b'bad'), ('bad.pkl', b'bad')])
def test_failures_withheld(filename, content):
    value = scan_upload(filename, content)
    assert value['backend']['verdict'] == 'WITHHELD'
    assert not value['evidence']
    assert value['backend']['error']['message']
    assert pdf_export(value).startswith(b'%PDF')


def test_snapshot_exports(clean_snapshot):
    value = json.loads(json_export(clean_snapshot))
    digest = value.pop('evidence_sha256')
    assert digest == hashlib.sha256(canonical_bytes(value)).hexdigest()
    fitz = pytest.importorskip('fitz')
    pdf = fitz.open(stream=pdf_export(clean_snapshot), filetype='pdf')
    text = ''.join(page.get_text() for page in pdf)
    assert clean_snapshot['scan_id'] in text
    assert digest in text.replace('\n', '')
    assert 'Final verdict: '+clean_snapshot['backend']['verdict'] in text
    assert 'Diagnostic only' in text
    compact = text.replace('\n', ' ')
    detector = value['backend']['structured_stego']
    for token in (value['backend']['artifact']['sha256'], str(detector['threshold']),
                  format(detector['score'], '.12g'), detector['reference_hash']):
        assert token in compact
    for evidence in value['evidence']:
        assert evidence['feature'] in compact
        assert format(evidence['value'], '.12g') in compact
    for limitation in value['limitations']:
        assert limitation in compact


@pytest.mark.parametrize('kind', ['half', 'nonfinite', 'infinite', 'integer_weight', 'quantized', 'mismatch'])
def test_unsupported_backend_inputs(tmp_path, kind, monkeypatch):
    # Small controlled inputs exercise guards, not detection performance.
    import scan_model
    import torch
    from safetensors.torch import save_file
    from types import SimpleNamespace
    state = {'weight': torch.ones(10)}
    if kind == 'half': state['weight'] = state['weight'].half()
    if kind == 'nonfinite': state['weight'][0] = float('nan')
    if kind == 'infinite': state['weight'][0] = float('inf')
    if kind == 'integer_weight': state['weight'] = state['weight'].to(torch.int64)
    if kind == 'quantized': state['weight'] = state['weight'].to(torch.int8)
    path = tmp_path/'unsupported.safetensors'
    save_file(state, path)
    if kind != 'mismatch':
        monkeypatch.setattr(scan_model, 'intake_model', lambda *a: SimpleNamespace(is_quantized=kind == 'quantized'))
    with pytest.raises(ValueError):
        scan_model.run_structured_scan(path)


@pytest.mark.parametrize('dtype_name', ['int64', 'int32', 'int16', 'bool'])
def test_supported_counter_dtype_preserved(tmp_path, monkeypatch, dtype_name):
    import scan_model
    import torch
    from safetensors.torch import save_file
    from types import SimpleNamespace
    state = {'weight': torch.ones(10), 'bn1.num_batches_tracked': torch.tensor(0, dtype=getattr(torch, dtype_name))}
    path = tmp_path/'counter.safetensors'
    save_file(state, path)
    monkeypatch.setattr(scan_model, 'intake_model', lambda *a: SimpleNamespace(
        is_quantized=False, input_domain='VISION', model=SimpleNamespace(state_dict=lambda: state)))
    returned = {'verdict': 'PASS'}
    monkeypatch.setattr(scan_model, 'scan_structured', lambda *a: returned)
    assert scan_model.run_structured_scan(path)['structured_stego'] is returned


def test_nonfinite_backend_evidence_is_withheld(monkeypatch):
    import scan_model
    monkeypatch.setattr(scan_model, 'run_structured_scan', lambda *a, **kw: {
        'artifact': {}, 'verdict': 'PASS', 'structured_stego': {'score': float('nan')}})
    assert scan_upload('bad.safetensors', b'bad')['backend']['verdict'] == 'WITHHELD'


@pytest.mark.parametrize('fault', ['missing_feature', 'wrong_sha', 'null_score', 'string_feature', 'infinite_signal'])
def test_incomplete_or_mismatched_result_is_withheld(clean_snapshot, monkeypatch, fault):
    import scan_model
    from copy import deepcopy
    result = deepcopy(clean_snapshot['backend'])
    result['verdict'] = result['structured_stego']['verdict']
    result['artifact']['layer_count'] = result['artifact']['tensor_count']
    if fault == 'missing_feature':
        result['structured_stego']['features'].pop('min_window_entropy')
    elif fault == 'wrong_sha':
        result['artifact']['sha256'] = '0' * 64
    elif fault == 'null_score':
        result['structured_stego']['score'] = None
    elif fault == 'string_feature':
        result['structured_stego']['features']['min_window_entropy'] = 'unavailable'
    else:
        result['structured_stego']['z_scores']['entropy'] = float('inf')
    monkeypatch.setattr(scan_model, 'run_structured_scan', lambda *a, **kw: result)
    value = scan_upload(CLEAN.name, CLEAN.read_bytes())
    assert value['backend']['structured_status']['status'] == 'unavailable'
    assert value['backend']['canonical']['risk_results']
    assert value['backend']['verdict'] == 'WITHHELD'
    assert value['evidence'] == []


def test_pages(clean_snapshot):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT/'frontend/app.py')).run(timeout=30)
    assert not app.exception
    assert app.button[0].disabled
    app.session_state['snapshot'] = clean_snapshot
    app.run(timeout=30)
    # st.navigation's callable pages use their function name as URL pathname.
    for title in ['INTAKE','STATIC','EXPLAINABILITY','BEHAVIOR','RISK','REPORT','STATIC','REPORT']:
        page = app.session_state['page_objects'][title]
        # AppTest's public switch_page supports files only; our pages are callables.
        app._page_hash = page._script_hash
        app.run(timeout=30)
        assert not app.exception, (title, list(app.exception))
        assert app.session_state['snapshot']['scan_id'] == clean_snapshot['scan_id']
    assert app.session_state['report_downloads']['pdf'].startswith(b'%PDF')


def test_downstream_failure_preserves_current_evidence(clean_snapshot, monkeypatch):
    import scan_model
    from copy import deepcopy
    def failed(path, *, evidence, **kwargs):
        evidence.update(deepcopy(clean_snapshot['backend']['canonical']))
        evidence.pop('risk_results')
        evidence.pop('dashboard_results')
        evidence['stages']['behavior_risk'] = {'status':'failed', 'reason':'controlled P2 failure'}
        raise RuntimeError('controlled P2 failure')
    monkeypatch.setattr(scan_model, 'run_pipeline', failed)
    value = scan_upload(CLEAN.name, CLEAN.read_bytes())
    assert value['backend']['verdict'] == 'PASS'
    assert value['backend']['execution_status'] == 'PARTIAL'
    assert len(value['backend']['canonical']['features']['static_features']) == 102
    assert value['backend']['canonical']['ml_results']['shap_attributions']
    assert value['backend']['structured_stego']['verdict'] == 'PASS'
    assert 'controlled P2 failure' in value['backend']['error']['message']


def test_contribution_exposure_preserves_scores():
    from src.p2_behavioral_risk.risk_aggregator import compute_mrs
    for quantized in (True, False):
        for s,p,b in ((0,0,0), (.7,.8,.4), (1,1,1)):
            evidence = {}
            original = compute_mrs(s,p,b,quantized)
            exposed = compute_mrs(s,p,b,quantized,evidence=evidence)
            assert original == exposed
            assert round(sum(r['contribution'] for r in evidence['contributions'] if r['contribution'] is not None),2) == exposed['mrs_score']
            if quantized: assert evidence['contributions'][-1]['contribution'] is None
