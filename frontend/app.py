"""Launch with: python -m streamlit run frontend/app.py"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from frontend import views
from frontend.components import style

st.set_page_config(page_title='SIGTENSOR | Model security', page_icon=str(Path(__file__).parent/'assets/hero/logo-mark-sigtensor-dark.png'), layout='wide')
style()
pages = [st.Page(function, title=title, default=index == 0) for index, (title, function) in enumerate(views.PAGES)]
current = st.navigation(pages, position='hidden')
st.session_state['page_objects'] = dict(zip([title for title, _ in views.PAGES], pages))
with st.container(key='navigation'):
    brand, links = st.columns([1.5, 6])
    with brand:
        st.image(str(Path(__file__).parent/'assets/hero/logo-full-sigtensor-dark.png'), width=210)
    with links:
        columns = st.columns(7)
        for col, page in zip(columns, pages):
            with col:
                st.page_link(page, disabled=page.title != 'NEW SCAN' and 'snapshot' not in st.session_state)
with st.container(key='analysis-shell' if current.title != 'NEW SCAN' else 'landing-shell'):
    current.run()
st.html('<div class="footer">SIGTENSOR &nbsp; / &nbsp; TRUSTED INTAKE. TRACEABLE EVIDENCE. &nbsp; / &nbsp; RESNET18 · SAFETENSORS</div>')
