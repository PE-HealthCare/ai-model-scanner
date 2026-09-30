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
CLEAN = ROOT/'data/training/sources/behradg_resnet18_mri_brain_canonical.safetensors'
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
        expect(page.get_by_role('heading',name='Validate before you analyze.')).to_be_visible(timeout=60000)
        ready()

    upload(CLEAN)
    expect(page.get_by_role('heading',name='INTAKE VERIFIED')).to_be_visible()
    page.screenshot(path=str(OUT/'intake.png'),full_page=True)
    for label,heading in [('STATIC','Inspect what the weights reveal.'),('EXPLAINABILITY','Explain the detector response.'),('BEHAVIOR','Test how the model behaves.'),('RISK','Combine the evidence.'),('REPORT','From evidence to assessment.')]:
        navigate(label,heading)
        page.screenshot(path=str(OUT/(label.lower()+'.png')),full_page=True)
    expect(page.get_by_role('heading',name='PASS',exact=True)).to_be_visible()
    exports={}
    for kind,label in [('json','Download Evidence — JSON'),('pdf','Download Security Report — PDF')]:
        with page.expect_download() as download:
            page.get_by_role('button',name=label).click()
        target=OUT/('clean-report.'+kind)
        download.value.save_as(target)
        exports[kind]=target
    value=json.loads(exports['json'].read_text())
    assert value['backend']['verdict']=='PASS'
    first_id=value['scan_id']
    navigate('STATIC','Inspect what the weights reveal.')
    page.get_by_role('combobox').click()
    page.get_by_role('option',name='max_window_printable_fraction',exact=True).click()
    page.get_by_role('tab',name='RAW EVIDENCE').click()
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
    page.screenshot(path=str(OUT/'failure.png'),full_page=True)
    navigate('NEW SCAN','Analyze AI weights.\nDetect hidden payloads.')
    upload(ROOT/'data/outputs/quantized_corpus/resnet18_int8_clean.safetensors')
    expect(page.get_by_role('heading',name='SCAN BLOCKED · ASSESSMENT WITHHELD')).to_be_visible()
    expect(page.get_by_text('Structured-LSB assessment is unavailable for quantized artifacts; FP32 is required.',exact=True)).to_be_visible()
    page.reload()
    ready()
    expect(page.get_by_role('heading',name='Awaiting an artifact')).to_be_visible()
    expect(page.get_by_role('heading',name='PASS',exact=True)).to_have_count(0)
    navigate('NEW SCAN','Analyze AI weights.\nDetect hidden payloads.')
    expect(page.get_by_role('button',name='START SCAN')).to_be_disabled()
    print('PASS: seven pages, real CLEAN/S6, selection, repeat navigation, downloads, mobile, invalid/quantized replacement, refresh clears session')
    browser.close()
