import base64
from html import escape
from pathlib import Path
import streamlit as st

HERE = Path(__file__).resolve().parent

@st.cache_data
def asset_uri(name):
    return 'data:image/png;base64,' + base64.b64encode((HERE/'assets'/name).read_bytes()).decode()

def style():
    st.html('<style>' + (HERE/'styles.css').read_text() + '</style>')
    st.html('<style>:root { --hands:url("' + asset_uri('hero/hands-both.png') + '"); --mesh:url("' + asset_uri('shared/mesh-full.png') + '"); --dots:url("' + asset_uri('hero/hero-dot-field.png') + '"); }</style>')
    st.html('<style>:root { --hand-left:url("' + asset_uri('hero/hand-left.png') + '"); --hand-right:url("' + asset_uri('hero/hand-right.png') + '"); }</style>')

def status(title, body, kind='info'):
    st.html(f'<section class="status {kind}"><h2>{escape(title)}</h2><p>{escape(body)}</p></section>')

def header(stage, title, subtitle):
    st.html(f'<div class="eyebrow">{escape(stage)}</div>')
    st.title(title)
    st.write(subtitle)

def snapshot():
    value = st.session_state.get('snapshot')
    if value is None:
        status('Awaiting an artifact', 'Start a new scan to inspect evidence for your model.')
        st.stop()
    if value.get('contract_version') != 'sigtensor-ui-assessment-v3':
        status('New scan required', 'This session predates the current assessment contract. Start a new scan to obtain a consistent report.')
        st.stop()
    artifact = value['backend']['artifact']
    text = f"{value['upload']['filename']}  /  {value['upload']['size_bytes']/1048576:.2f} MiB  /  SHA {artifact['sha256'][:16]}…  /  Scan {value['scan_id'][:8]}"
    if artifact.get('architecture'):
        text += f"  /  {artifact['architecture']} · {artifact['input_domain']} · {artifact['dtype']}"
    st.html(f'<div class="artifact-strip">{escape(text)}</div>')
    return value

def successful(value):
    if 'structured_stego' not in value['backend']:
        status('Assessment withheld', 'This scan did not produce complete detector evidence.')
        st.write(value['backend']['error']['message'])
        st.stop()
    return value['backend']['structured_stego']

def link(title, label=None):
    st.page_link(st.session_state['page_objects'][title], label=label or title)
