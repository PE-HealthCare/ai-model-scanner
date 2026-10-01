"""Opt-in local browser QA: uses real development models, never sealed data.

Start frontend/app.py on 127.0.0.1:8502 first. Requires Playwright and Edge.
"""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright, expect
expect.set_options(timeout=30000)

OUT = ROOT/'tmp/ui-qa'
OUT.mkdir(parents=True, exist_ok=True)
CLEAN = ROOT/'data/models/resnet18_pretrained.safetensors'
S6 = ROOT/'data/training/s6_structured_generalization/8ce8fd79b1064148863d3d9e.safetensors'

with sync_playwright() as driver:
    browser = driver.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1050}, accept_downloads=True)
    page.set_default_timeout(30000)
    page.goto('http://127.0.0.1:8502')
    expect(page.get_by_role('button',name='START SCAN')).to_be_disabled()
    def ready():
        expect(page.get_by_test_id('stApp')).to_have_attribute('data-test-script-state','notRunning')
        expect(page.locator('[data-testid="stSkeleton"]')).to_have_count(0)
    ready()
    page.screenshot(path=str(OUT/'landing.png'), full_page=True)

    def navigate(label, heading):
        page.get_by_test_id('stPageLink').get_by_text(label, exact=True).first.click()
        expect(page.get_by_role('heading',name=heading,exact=True)).to_be_visible()
        ready()
        expect(page.get_by_test_id('stException')).to_have_count(0)

    def upload(path):
        page.locator('input[type=file]').set_input_files(str(path))
        page.get_by_role('button',name='START SCAN').click()
        expect(page.get_by_role('heading',name='Validate before you analyze.')).to_be_visible(timeout=180000)
        ready()

    upload(CLEAN)
    expect(page.get_by_role('heading',name='INTAKE VERIFIED')).to_be_visible()
    page.screenshot(path=str(OUT/'intake.png'),full_page=True)
    for label,heading in [('STATIC','Inspect what the weights reveal.'),('EXPLAINABILITY','Explain the classifier response.'),('BEHAVIOR','Test how the model behaves.'),('RISK','Combine the evidence.'),('REPORT','From evidence to assessment.')]:
        navigate(label,heading)
        if label in ('RISK','REPORT'):
            expect(page.get_by_role('heading',name='PASS',exact=True)).to_be_visible()
        if label in ('STATIC','EXPLAINABILITY','BEHAVIOR','RISK'):
            expect(page.get_by_test_id('stPlotlyChart')).to_have_count(2 if label == 'RISK' else 1)
            expect(page.locator('.js-plotly-plot').first).to_be_visible()
        page.screenshot(path=str(OUT/(label.lower()+'.png')),full_page=True)
        if label in ('STATIC','EXPLAINABILITY','BEHAVIOR','RISK'):
            for index,chart in enumerate(page.get_by_test_id('stPlotlyChart').all()):
                chart.screenshot(path=str(OUT/f'{label.lower()}-chart-{index}.png'))
    exports={}
    for kind,label in [('json','Download Evidence — JSON'),('pdf','Download Security Report — PDF')]:
        with page.expect_download() as download:
            page.get_by_role('button',name=label).click()
        target=OUT/('clean-report.'+kind)
        download.value.save_as(target)
        exports[kind]=target
    value=json.loads(exports['json'].read_text())
    assert value['backend']['verdict']=='PASS'
    assert value['backend']['roles']['legacy_mrs']=='experimental_excluded'
    assert value['backend']['structured_stego']['verdict']=='PASS'
    assert len(value['backend']['canonical']['features']['static_features']) == 102
    assert value['backend']['canonical']['p2_evidence']['behavior']['successful_probe_count']==32
    import fitz
    document=fitz.open(exports['pdf'])
    assert 'Final verdict: PASS' in ''.join(p.get_text() for p in document)
    for i,pdf_page in enumerate(document):
        pdf_page.get_pixmap(matrix=fitz.Matrix(1,1)).save(str(OUT/f'report-pdf-{i+1}.png'))
    first_id=value['scan_id']
    navigate('STATIC','Inspect what the weights reveal.')
    page.get_by_role('combobox').click()
    page.get_by_role('combobox').fill('conv1.weight')
    page.get_by_role('option',name='conv1.weight',exact=True).click()
    page.get_by_role('tab',name='RAW STATISTICS').click()
    navigate('REPORT','From evidence to assessment.')
    with page.expect_download() as download:
        page.get_by_role('button',name='Download Evidence — JSON').click()
    download.value.save_as(OUT/'repeat-report.json')
    assert json.loads((OUT/'repeat-report.json').read_text())['scan_id']==first_id

    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(OUT/'report-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile overflow'
    navigate('NEW SCAN','Analyze AI weights.\nDetect hidden payloads.')
    page.screenshot(path=str(OUT/'landing-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1050})
    upload(S6)
    navigate('RISK','Combine the evidence.')
    expect(page.get_by_role('heading',name='FAIL',exact=True)).to_be_visible()
    page.screenshot(path=str(OUT/'risk-s6.png'),full_page=True)
    navigate('REPORT','From evidence to assessment.')
    expect(page.get_by_role('heading',name='FAIL',exact=True)).to_be_visible()
    for kind,label in [('json','Download Evidence — JSON'),('pdf','Download Security Report — PDF')]:
        with page.expect_download() as download:
            page.get_by_role('button',name=label).click()
        download.value.save_as(OUT/('s6-report.'+kind))
    suspicious=json.loads((OUT/'s6-report.json').read_text())
    assert suspicious['scan_id']!=first_id
    assert suspicious['backend']['verdict']==suspicious['backend']['structured_stego']['verdict']=='FAIL'
    assert 'Final verdict: FAIL' in ''.join(p.get_text() for p in fitz.open(OUT/'s6-report.pdf'))
    navigate('NEW SCAN','Analyze AI weights.\nDetect hidden payloads.')
    page.locator('input[type=file]').set_input_files({'name':'invalid.safetensors','mimeType':'application/octet-stream','buffer':b'bad'})
    page.get_by_role('button',name='START SCAN').click()
    expect(page.get_by_role('heading',name='SCAN BLOCKED · ASSESSMENT WITHHELD')).to_be_visible()
    navigate('REPORT','From evidence to assessment.')
    expect(page.get_by_role('heading',name='WITHHELD',exact=True)).to_be_visible()
    with page.expect_download() as download:
        page.get_by_role('button',name='Download Evidence — JSON').click()
    download.value.save_as(OUT/'failure-report.json')
    failure=json.loads((OUT/'failure-report.json').read_text())
    assert failure['scan_id'] != first_id
    assert failure['backend']['verdict']=='WITHHELD' and not failure['evidence']
    assert not failure['backend'].get('canonical', {}).get('features')
    page.screenshot(path=str(OUT/'failure.png'),full_page=True)
    navigate('NEW SCAN','Analyze AI weights.\nDetect hidden payloads.')
    upload(ROOT/'data/outputs/quantized_corpus/resnet18_int8_clean.safetensors')
    expect(page.get_by_role('heading',name='INTAKE VERIFIED')).to_be_visible()
    navigate('BEHAVIOR','Test how the model behaves.')
    expect(page.get_by_role('heading',name='BEHAVIOR NOT APPLICABLE')).to_be_visible()
    page.screenshot(path=str(OUT/'quantized-behavior.png'),full_page=True)
    navigate('RISK','Combine the evidence.')
    expect(page.get_by_role('heading',name='ASSESSMENT WITHHELD')).to_be_visible()
    page.reload()
    ready()
    expect(page.get_by_role('heading',name='Awaiting an artifact')).to_be_visible()
    expect(page.get_by_role('heading',name='PASS',exact=True)).to_have_count(0)
    navigate('NEW SCAN','Analyze AI weights.\nDetect hidden payloads.')
    expect(page.get_by_role('button',name='START SCAN')).to_be_disabled()
    print('PASS: seven pages, five real Plotly graphs, CLEAN/S6, selection, reruns, downloads, mobile, invalid replacement, quantized bypass, refresh clears session')
    browser.close()
