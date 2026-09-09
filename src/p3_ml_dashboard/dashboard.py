"""
SigTensor Security Scanner — Dashboard (P3 owner)
==================================================
Streamlit frontend entrypoint.

Launch:
    streamlit run src/p3_ml_dashboard/dashboard.py

Chunk 1 implements:
    - Application shell & global CSS
    - Persistent sidebar navigation
    - Page routing
    - Overview / landing page

Chunk 2 implements:
    - Scan Model multi-step intake workflow
      Step 1: Upload (.safetensors)
      Step 2: Configure domain / precision / architecture
      Step 3: Review & Begin Security Scan

Future chunks will implement:
    - Dashboard / results  (Chunk 3)
    - Evidence & Explainability  (Chunk 4)
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — MUST be the first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="SigTensor | AI Model Security",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design tokens (mirrored in CSS below for colour-consistency reference)
# ---------------------------------------------------------------------------

COLORS = {
    "bg_base":       "#0B1020",
    "bg_surface":    "#121A2B",
    "bg_elevated":   "#182235",
    "accent_cyan":   "#22D3EE",
    "accent_blue":   "#3B82F6",
    "pass_green":    "#22C55E",
    "review_amber":  "#F59E0B",
    "fail_red":      "#EF4444",
    "text_primary":  "#F1F5F9",
    "text_muted":    "#64748B",
    "border":        "#1E2D45",
}

# ---------------------------------------------------------------------------
# Global CSS injection
# ---------------------------------------------------------------------------

def _inject_global_css() -> None:
    """Inject the application-wide design system CSS."""
    css = f"""
    <style>
    /* ── Google Font ──────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* ── Reset & base ─────────────────────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* ── App background ───────────────────────────────────────────────── */
    .stApp {{
        background-color: {COLORS["bg_base"]};
        color: {COLORS["text_primary"]};
    }}

    /* ── Main content area ────────────────────────────────────────────── */
    .main .block-container {{
        padding: 2rem 2.5rem 4rem 2.5rem;
        max-width: 1200px;
    }}

    /* ── Sidebar ──────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background-color: {COLORS["bg_surface"]};
        border-right: 1px solid {COLORS["border"]};
        min-width: 240px !important;
        max-width: 240px !important;
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        padding: 1.5rem 1.25rem;
    }}

    /* ── Sidebar brand block ──────────────────────────────────────────── */
    .sig-brand {{
        padding-bottom: 1.5rem;
        border-bottom: 1px solid {COLORS["border"]};
        margin-bottom: 1.5rem;
    }}
    .sig-brand-name {{
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, {COLORS["accent_cyan"]}, {COLORS["accent_blue"]});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        line-height: 1.2;
    }}
    .sig-brand-sub {{
        font-size: 0.60rem;
        font-weight: 600;
        letter-spacing: 0.18em;
        color: {COLORS["text_muted"]};
        margin-top: 3px;
        text-transform: uppercase;
    }}

    /* ── Nav items ────────────────────────────────────────────────────── */
    .nav-section-label {{
        font-size: 0.62rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        color: {COLORS["text_muted"]};
        text-transform: uppercase;
        margin: 0.25rem 0 0.5rem 0;
    }}
    .nav-item {{
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 500;
        color: {COLORS["text_primary"]};
        cursor: pointer;
        transition: background 0.15s ease, color 0.15s ease;
        margin-bottom: 2px;
        border: none;
        width: 100%;
        text-align: left;
        background: transparent;
        text-decoration: none;
    }}
    .nav-item:hover {{
        background-color: {COLORS["bg_elevated"]};
    }}
    .nav-item.active {{
        background-color: rgba(34, 211, 238, 0.10);
        color: {COLORS["accent_cyan"]};
        font-weight: 600;
    }}
    .nav-item.active .nav-icon {{
        color: {COLORS["accent_cyan"]};
    }}
    .nav-item.locked {{
        color: {COLORS["text_muted"]};
        cursor: default;
    }}
    .nav-item.locked:hover {{
        background: transparent;
    }}
    .nav-lock-badge {{
        font-size: 0.60rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        color: {COLORS["text_muted"]};
        background: {COLORS["bg_elevated"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 4px;
        padding: 1px 5px;
        margin-left: auto;
    }}

    /* ── Sidebar status block ─────────────────────────────────────────── */
    .sig-status-block {{
        border-top: 1px solid {COLORS["border"]};
        padding-top: 1.25rem;
        margin-top: 1.25rem;
    }}
    .status-dot-idle {{
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: {COLORS["text_muted"]};
        margin-right: 6px;
        vertical-align: middle;
    }}
    .status-dot-ready {{
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: {COLORS["pass_green"]};
        margin-right: 6px;
        vertical-align: middle;
    }}
    .status-label {{
        font-size: 0.75rem;
        color: {COLORS["text_muted"]};
        font-weight: 500;
    }}
    .status-value {{
        font-size: 0.72rem;
        color: {COLORS["text_muted"]};
        margin-top: 0.35rem;
    }}

    /* ── Page hero ────────────────────────────────────────────────────── */
    .hero-container {{
        padding: 3.5rem 0 2.5rem 0;
    }}
    .hero-eyebrow {{
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.16em;
        color: {COLORS["accent_cyan"]};
        text-transform: uppercase;
        margin-bottom: 1rem;
    }}
    .hero-headline {{
        font-size: 3.0rem;
        font-weight: 800;
        line-height: 1.08;
        letter-spacing: -1.5px;
        color: {COLORS["text_primary"]};
        margin: 0 0 1.25rem 0;
    }}
    .hero-headline span {{
        background: linear-gradient(135deg, {COLORS["accent_cyan"]} 0%, {COLORS["accent_blue"]} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .hero-body {{
        font-size: 1.05rem;
        font-weight: 400;
        line-height: 1.65;
        color: {COLORS["text_muted"]};
        max-width: 580px;
        margin-bottom: 2.25rem;
    }}

    /* ── CTA button ───────────────────────────────────────────────────── */
    .cta-button-wrap {{
        margin-bottom: 4rem;
    }}
    div[data-testid="stButton"] > button {{
        background: linear-gradient(135deg, {COLORS["accent_cyan"]}, {COLORS["accent_blue"]});
        color: #0B1020;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 700;
        font-size: 0.9rem;
        border-radius: 8px;
        letter-spacing: 0.02em;
        transition: opacity 0.2s ease, transform 0.15s ease;
        cursor: pointer;
    }}
    div[data-testid="stButton"] > button:hover {{
        opacity: 0.88;
        transform: translateY(-1px);
    }}
    div[data-testid="stButton"] > button:active {{
        transform: translateY(0px);
    }}

    /* ── Capability cards ─────────────────────────────────────────────── */
    .capability-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.25rem;
        margin-top: 0.5rem;
    }}
    @media (max-width: 900px) {{
        .capability-grid {{ grid-template-columns: 1fr; }}
    }}
    .capability-card {{
        background: {COLORS["bg_surface"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 14px;
        padding: 1.75rem 1.5rem;
        transition: border-color 0.2s ease, transform 0.2s ease;
    }}
    .capability-card:hover {{
        border-color: rgba(34, 211, 238, 0.30);
        transform: translateY(-2px);
    }}
    .cap-icon {{
        font-size: 1.6rem;
        margin-bottom: 1rem;
    }}
    .cap-label {{
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: {COLORS["accent_cyan"]};
        margin-bottom: 0.5rem;
    }}
    .cap-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        margin-bottom: 0.65rem;
        letter-spacing: -0.3px;
    }}
    .cap-body {{
        font-size: 0.83rem;
        line-height: 1.6;
        color: {COLORS["text_muted"]};
    }}

    /* ── Divider ──────────────────────────────────────────────────────── */
    .sig-divider {{
        border: none;
        border-top: 1px solid {COLORS["border"]};
        margin: 2rem 0;
    }}

    /* ── Section label ────────────────────────────────────────────────── */
    .section-label {{
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: {COLORS["text_muted"]};
        margin-bottom: 1.25rem;
    }}

    /* ── Coming-soon banner ───────────────────────────────────────────── */
    .coming-soon-banner {{
        background: {COLORS["bg_surface"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        margin: 2rem 0;
    }}
    .coming-soon-icon {{
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }}
    .coming-soon-title {{
        font-size: 1.1rem;
        font-weight: 600;
        color: {COLORS["text_primary"]};
        margin-bottom: 0.5rem;
    }}
    .coming-soon-body {{
        font-size: 0.85rem;
        color: {COLORS["text_muted"]};
        max-width: 380px;
        margin: 0 auto;
        line-height: 1.6;
    }}
    .pending-badge {{
        display: inline-block;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {COLORS["review_amber"]};
        background: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.25);
        border-radius: 4px;
        padding: 2px 8px;
        margin-bottom: 1rem;
    }}

    /* ══════════════════════════════════════════════════════════════════
       Chunk 2 — Scan Intake Styles
       ══════════════════════════════════════════════════════════════════ */

    /* ── Visual stepper ───────────────────────────────────────────────── */
    .intake-stepper {{
        display: flex;
        align-items: center;
        gap: 0;
        margin: 1.5rem 0 2.5rem 0;
        padding: 1.25rem 1.75rem;
        background: {COLORS["bg_surface"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 14px;
    }}
    .stepper-step {{
        display: flex;
        align-items: center;
        gap: 0.7rem;
        flex: 1;
        position: relative;
    }}
    .stepper-step:not(:last-child)::after {{
        content: '';
        flex: 1;
        height: 1px;
        background: {COLORS["border"]};
        margin: 0 0.5rem;
    }}
    .step-circle {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        flex-shrink: 0;
        transition: background 0.2s ease, border-color 0.2s ease;
    }}
    .step-circle-done {{
        background: rgba(34,211,238,0.15);
        border: 2px solid {COLORS["accent_cyan"]};
        color: {COLORS["accent_cyan"]};
    }}
    .step-circle-active {{
        background: linear-gradient(135deg, {COLORS["accent_cyan"]}, {COLORS["accent_blue"]});
        border: 2px solid transparent;
        color: #0B1020;
        box-shadow: 0 0 14px rgba(34,211,238,0.35);
    }}
    .step-circle-pending {{
        background: transparent;
        border: 2px solid {COLORS["border"]};
        color: {COLORS["text_muted"]};
    }}
    .step-meta {{
        display: flex;
        flex-direction: column;
        gap: 1px;
    }}
    .step-num {{
        font-size: 0.58rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {COLORS["text_muted"]};
    }}
    .step-name-active {{
        font-size: 0.82rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
    }}
    .step-name-done {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {COLORS["accent_cyan"]};
    }}
    .step-name-pending {{
        font-size: 0.82rem;
        font-weight: 500;
        color: {COLORS["text_muted"]};
    }}
    .stepper-connector {{
        flex: 1;
        height: 1px;
        background: {COLORS["border"]};
        margin: 0 0.75rem;
    }}
    .stepper-connector-done {{
        background: linear-gradient(90deg, {COLORS["accent_cyan"]}, {COLORS["border"]});
    }}

    /* ── Upload zone ──────────────────────────────────────────────────── */
    .upload-zone-wrap {{
        background: {COLORS["bg_surface"]};
        border: 2px dashed {COLORS["border"]};
        border-radius: 16px;
        padding: 2.5rem 2rem;
        text-align: center;
        transition: border-color 0.2s ease;
        margin-bottom: 1.5rem;
    }}
    .upload-zone-wrap:hover {{
        border-color: rgba(34,211,238,0.40);
    }}
    .upload-icon {{
        font-size: 2.8rem;
        margin-bottom: 0.75rem;
        line-height: 1;
    }}
    .upload-headline {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        margin-bottom: 0.4rem;
        letter-spacing: -0.3px;
    }}
    .upload-sub {{
        font-size: 0.8rem;
        color: {COLORS["text_muted"]};
        margin-bottom: 1.25rem;
    }}
    .format-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: {COLORS["accent_cyan"]};
        background: rgba(34,211,238,0.08);
        border: 1px solid rgba(34,211,238,0.25);
        border-radius: 6px;
        padding: 3px 10px;
        text-transform: uppercase;
    }}

    /* ── Upload success card ──────────────────────────────────────────── */
    .upload-success-card {{
        background: {COLORS["bg_surface"]};
        border: 1px solid rgba(34,211,238,0.30);
        border-radius: 14px;
        padding: 1.5rem 1.75rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
    }}
    .upload-success-icon {{
        font-size: 2rem;
        flex-shrink: 0;
        color: {COLORS["pass_green"]};
    }}
    .upload-success-meta {{
        flex: 1;
    }}
    .upload-success-name {{
        font-size: 1rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        margin-bottom: 0.35rem;
        word-break: break-all;
    }}
    .upload-success-pills {{
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
    }}
    .upload-pill {{
        font-size: 0.67rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        background: {COLORS["bg_elevated"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 5px;
        padding: 2px 9px;
        color: {COLORS["text_muted"]};
        text-transform: uppercase;
    }}
    .ready-badge {{
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: {COLORS["pass_green"]};
        background: rgba(34,197,94,0.10);
        border: 1px solid rgba(34,197,94,0.30);
        border-radius: 5px;
        padding: 2px 9px;
        text-transform: uppercase;
    }}

    /* ── Option selector cards ────────────────────────────────────────── */
    .option-grid {{
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin: 0.5rem 0 1.75rem 0;
    }}
    .option-card {{
        background: {COLORS["bg_surface"]};
        border: 2px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 1.1rem 1.4rem;
        cursor: pointer;
        transition: border-color 0.18s ease, background 0.18s ease, transform 0.15s ease;
        min-width: 130px;
        text-align: left;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        user-select: none;
    }}
    .option-card:hover {{
        border-color: rgba(34,211,238,0.35);
        transform: translateY(-1px);
    }}
    .option-card-selected {{
        border-color: {COLORS["accent_cyan"]} !important;
        background: rgba(34,211,238,0.07) !important;
        transform: translateY(-1px);
    }}
    .option-card-icon {{
        font-size: 1.3rem;
        margin-bottom: 0.2rem;
    }}
    .option-card-label {{
        font-size: 0.9rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        letter-spacing: -0.2px;
    }}
    .option-card-sub {{
        font-size: 0.72rem;
        color: {COLORS["text_muted"]};
        line-height: 1.4;
    }}

    /* ── Intake field label ───────────────────────────────────────────── */
    .intake-field-label {{
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: {COLORS["accent_cyan"]};
        margin-bottom: 0.6rem;
    }}

    /* ── Security notice ─────────────────────────────────────────────── */
    .security-notice {{
        display: flex;
        gap: 0.85rem;
        align-items: flex-start;
        background: rgba(59,130,246,0.07);
        border: 1px solid rgba(59,130,246,0.20);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-top: 1.5rem;
    }}
    .security-notice-icon {{
        font-size: 1.05rem;
        flex-shrink: 0;
        margin-top: 1px;
        color: {COLORS["accent_blue"]};
    }}
    .security-notice-text {{
        font-size: 0.8rem;
        color: {COLORS["text_muted"]};
        line-height: 1.55;
    }}
    .security-notice-text strong {{
        color: {COLORS["text_primary"]};
        font-weight: 600;
    }}

    /* ── Review panel ────────────────────────────────────────────────── */
    .review-panel {{
        background: {COLORS["bg_surface"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 16px;
        padding: 2rem 2.25rem;
        margin-bottom: 1.75rem;
    }}
    .review-panel-title {{
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: {COLORS["text_muted"]};
        margin-bottom: 1.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid {COLORS["border"]};
    }}
    .review-row {{
        display: flex;
        align-items: baseline;
        gap: 1rem;
        padding: 0.65rem 0;
        border-bottom: 1px solid {COLORS["border"]};
    }}
    .review-row:last-child {{
        border-bottom: none;
    }}
    .review-key {{
        font-size: 0.75rem;
        font-weight: 600;
        color: {COLORS["text_muted"]};
        min-width: 155px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .review-val {{
        font-size: 0.92rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        letter-spacing: -0.2px;
    }}
    .review-val-accent {{
        font-size: 0.92rem;
        font-weight: 700;
        color: {COLORS["accent_cyan"]};
        letter-spacing: -0.2px;
    }}
    .review-val-muted {{
        font-size: 0.85rem;
        font-weight: 500;
        color: {COLORS["text_muted"]};
    }}

    /* ── Validation error ─────────────────────────────────────────────── */
    .intake-error {{
        display: flex;
        gap: 0.6rem;
        align-items: center;
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.25);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.8rem;
        color: {COLORS["fail_red"]};
        font-weight: 500;
        margin-bottom: 1rem;
    }}

    /* ── Streamlit widget overrides ───────────────────────────────────── */
    /* Hide the default Streamlit header bar and footer */
    #MainMenu {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ display: none; }}
    footer {{ visibility: hidden; }}

    /* Streamlit selectbox dark theme overrides */
    div[data-baseweb="select"] > div {{
        background-color: {COLORS["bg_elevated"]} !important;
        border-color: {COLORS["border"]} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="select"] span {{
        color: {COLORS["text_primary"]} !important;
    }}
    div[data-baseweb="popover"] {{
        background-color: {COLORS["bg_elevated"]} !important;
        border: 1px solid {COLORS["border"]} !important;
    }}
    div[data-baseweb="menu"] li {{
        color: {COLORS["text_primary"]} !important;
    }}
    div[data-baseweb="menu"] li:hover {{
        background-color: rgba(34,211,238,0.10) !important;
    }}

    /* Scrollbar styling */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {COLORS["bg_base"]}; }}
    ::-webkit-scrollbar-thumb {{ background: {COLORS["border"]}; border-radius: 3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLORS["text_muted"]}; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    """Ensure all required session-state keys are present."""
    defaults: dict[str, object] = {
        # ── Routing ────────────────────────────────────────────────────────
        "active_page": "Overview",
        # ── Scan pipeline state ────────────────────────────────────────────
        "scan_result": None,       # populated after a real scan (Chunk 3)
        "scan_status": "idle",     # idle | running | complete | error
        # ── Chunk 2: scan intake wizard ────────────────────────────────────
        "intake_step": 1,          # 1=Upload 2=Configure 3=Review
        "upload_filename": None,   # str
        "upload_size_bytes": None, # int
        "upload_file_obj": None,   # UploadedFile object (BytesIO-like)
        "scan_domain": None,       # "Vision" | "NLP"
        "scan_precision": None,    # "FP32" | "FP16" | "INT8"
        "scan_architecture": None, # e.g. "ResNet18"
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    {"id": "Overview",       "icon": "⬡",  "label": "Overview",       "locked": False},
    {"id": "Scan Model",     "icon": "◈",  "label": "Scan Model",     "locked": False},
    {"id": "Dashboard",      "icon": "◉",  "label": "Dashboard",      "locked": True},
    {"id": "Evidence",       "icon": "◎",  "label": "Evidence",       "locked": True},
    {"id": "Explainability", "icon": "◍",  "label": "Explainability", "locked": True},
]

VERSION = "0.1.0-alpha"


def _render_sidebar() -> None:
    """Render the persistent sidebar navigation."""
    with st.sidebar:
        # ── Brand ──────────────────────────────────────────────────────
        st.markdown(
            """
            <div class="sig-brand">
                <p class="sig-brand-name">SigTensor</p>
                <p class="sig-brand-sub">AI Model Security</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Navigation ─────────────────────────────────────────────────
        st.markdown('<p class="nav-section-label">Navigation</p>', unsafe_allow_html=True)

        scan_done = st.session_state.get("scan_status") == "complete"

        for item in NAV_ITEMS:
            page_id = item["id"]
            icon    = item["icon"]
            label   = item["label"]
            locked  = item["locked"] and not scan_done
            active  = st.session_state["active_page"] == page_id

            if locked:
                st.markdown(
                    f"""
                    <div class="nav-item locked">
                        <span class="nav-icon">{icon}</span>
                        {label}
                        <span class="nav-lock-badge">No scan</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                active_class = " active" if active else ""
                btn_key = f"nav_{page_id}"
                # Use Streamlit button for interactivity; overlay custom styling via HTML label
                clicked = st.button(
                    f"{icon}  {label}",
                    key=btn_key,
                    use_container_width=True,
                )
                if clicked:
                    st.session_state["active_page"] = page_id
                    st.rerun()

                # Inject active highlight after button renders
                if active:
                    st.markdown(
                        f"""
                        <style>
                        div[data-testid="stButton"][key="{btn_key}"] > button {{
                            background: rgba(34,211,238,0.08) !important;
                            color: {COLORS["accent_cyan"]} !important;
                            font-weight: 600 !important;
                        }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

        # ── Status / version block ──────────────────────────────────────
        status_label = st.session_state.get("scan_status", "idle")
        dot_class = "status-dot-ready" if status_label == "complete" else "status-dot-idle"
        status_display = {
            "idle":     "No scan loaded",
            "running":  "Scanning…",
            "complete": "Results available",
            "error":    "Scan error",
        }.get(status_label, "Unknown")

        st.markdown(
            f"""
            <div class="sig-status-block">
                <span class="{dot_class}"></span>
                <span class="status-label">{status_display}</span>
                <div class="status-value">SigTensor v{VERSION}</div>
                <div class="status-value" style="margin-top:4px;">P3 / person3 branch</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Page: Overview
# ---------------------------------------------------------------------------

CAPABILITIES = [
    {
        "icon": "◈",
        "tag":  "Static Steganalysis",
        "title": "Weight-Level Inspection",
        "body": (
            "Analyze model weights for suspicious entropy profiles, hidden bit patterns, "
            "abnormal statistical distributions, and KL-divergence anomalies at the layer level."
        ),
    },
    {
        "icon": "◉",
        "tag":  "ML Threat Classification",
        "title": "Tampering Probability",
        "body": (
            "Estimate model tampering probability using LightGBM anomaly classification "
            "and TreeSHAP feature attribution pinpointing the most suspicious signals."
        ),
    },
    {
        "icon": "◎",
        "tag":  "Behavioral Risk Analysis",
        "title": "Perturbation Response",
        "body": (
            "Evaluate model behavior under controlled input perturbations to surface "
            "suspicious trigger-like response patterns indicative of hidden backdoors."
        ),
    },
]


def _render_capability_cards() -> None:
    """Render the three capability sections as a responsive grid."""
    cards_html = '<div class="capability-grid">'
    for cap in CAPABILITIES:
        cards_html += f"""
        <div class="capability-card">
            <div class="cap-icon">{cap["icon"]}</div>
            <div class="cap-label">{cap["tag"]}</div>
            <div class="cap-title">{cap["title"]}</div>
            <div class="cap-body">{cap["body"]}</div>
        </div>
        """
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)


def page_overview() -> None:
    """Render the Overview / landing page."""

    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="hero-container">
            <div class="hero-eyebrow">AI Supply Chain Security</div>
            <h1 class="hero-headline">
                Secure your<br><span>AI supply chain.</span>
            </h1>
            <p class="hero-body">
                Detect hidden manipulation, steganographic payloads, and suspicious
                anomalies embedded inside AI model weights before deployment.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── CTA ────────────────────────────────────────────────────────────────
    col_cta, col_spacer = st.columns([1, 3])
    with col_cta:
        if st.button("→  Start Security Scan", key="hero_cta", use_container_width=True):
            st.session_state["active_page"] = "Scan Model"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<hr class="sig-divider">', unsafe_allow_html=True)

    # ── Capabilities ───────────────────────────────────────────────────────
    st.markdown('<p class="section-label">Platform Capabilities</p>', unsafe_allow_html=True)
    _render_capability_cards()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<hr class="sig-divider">', unsafe_allow_html=True)

    # ── Stats row ──────────────────────────────────────────────────────────
    st.markdown('<p class="section-label">Detection Methodology</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    _stat(c1, "10", "Statistical Features",  "per layer — entropy, KL, KS, moments, sparsity")
    _stat(c2, "LightGBM", "Anomaly Classifier", "trained on synthetic tampering methodology")
    _stat(c3, "TreeSHAP", "Attribution Engine", "feature-level explainability")
    _stat(c4, "MRS", "Risk Score (0–100)", "PASS · REVIEW · FAIL verdicts")


def _stat(col: st.delta_generator.DeltaGenerator, value: str, label: str, sub: str) -> None:
    """Render a single stat block inside a column."""
    col.markdown(
        f"""
        <div style="
            background:{COLORS['bg_surface']};
            border:1px solid {COLORS['border']};
            border-radius:12px;
            padding:1.25rem 1.2rem;
            height:100%;
        ">
            <div style="
                font-size:1.4rem;
                font-weight:800;
                color:{COLORS['accent_cyan']};
                letter-spacing:-0.5px;
                margin-bottom:0.3rem;
            ">{value}</div>
            <div style="
                font-size:0.8rem;
                font-weight:600;
                color:{COLORS['text_primary']};
                margin-bottom:0.35rem;
            ">{label}</div>
            <div style="
                font-size:0.72rem;
                color:{COLORS['text_muted']};
                line-height:1.5;
            ">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Page: Scan Model — Chunk 2 implementation
# ---------------------------------------------------------------------------

# ── Stepper data ─────────────────────────────────────────────────────────

STEPS = [
    {"num": "01", "name": "Upload"},
    {"num": "02", "name": "Configure"},
    {"num": "03", "name": "Review"},
]

# Architectures within project scope (Vision + NLP, matching existing pipeline)
ARCHITECTURES_VISION = ["ResNet18", "ResNet50"]
ARCHITECTURES_NLP    = ["DistilBERT"]
ARCHITECTURES_ALL    = ARCHITECTURES_VISION + ARCHITECTURES_NLP


def _fmt_bytes(n: int) -> str:
    """Return a human-readable file size string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    if n < 1024 ** 3:
        return f"{n / 1024 ** 2:.1f} MB"
    return f"{n / 1024 ** 3:.2f} GB"


def _render_stepper(current_step: int) -> None:
    """Render the visual progress stepper (1-indexed)."""
    parts: list[str] = ['<div class="intake-stepper">']
    for i, step in enumerate(STEPS):
        step_idx = i + 1
        if step_idx < current_step:
            circle_cls = "step-circle step-circle-done"
            name_cls   = "step-name-done"
            circle_txt = "✓"
        elif step_idx == current_step:
            circle_cls = "step-circle step-circle-active"
            name_cls   = "step-name-active"
            circle_txt = step["num"]
        else:
            circle_cls = "step-circle step-circle-pending"
            name_cls   = "step-name-pending"
            circle_txt = step["num"]

        parts.append(
            f'<div class="stepper-step">'
            f'  <div class="{circle_cls}">{circle_txt}</div>'
            f'  <div class="step-meta">'
            f'    <div class="step-num">Step {step["num"]}</div>'
            f'    <div class="{name_cls}">{step["name"]}</div>'
            f'  </div>'
            f'</div>'
        )
        if i < len(STEPS) - 1:
            conn_cls = "stepper-connector stepper-connector-done" if step_idx < current_step else "stepper-connector"
            parts.append(f'<div class="{conn_cls}"></div>')

    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def _render_validation_error(msg: str) -> None:
    """Show an inline validation error strip."""
    st.markdown(
        f'<div class="intake-error">⚠ {msg}</div>',
        unsafe_allow_html=True,
    )


# ── Step 1: Upload ────────────────────────────────────────────────────────

def _step_upload() -> None:
    """Render the model upload interface (Step 1)."""

    # If a file is already staged, show the success card
    if st.session_state.get("upload_filename"):
        fname = st.session_state["upload_filename"]
        fsize = st.session_state["upload_size_bytes"]
        st.markdown(
            f"""
            <div class="upload-success-card">
                <div class="upload-success-icon">✔</div>
                <div class="upload-success-meta">
                    <div class="upload-success-name">{fname}</div>
                    <div class="upload-success-pills">
                        <span class="upload-pill">{_fmt_bytes(fsize)}</span>
                        <span class="upload-pill">.safetensors</span>
                        <span class="ready-badge">Ready</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_replace, col_spacer = st.columns([1, 3])
        with col_replace:
            if st.button("↺  Replace file", key="btn_replace_file", use_container_width=True):
                st.session_state["upload_filename"]  = None
                st.session_state["upload_size_bytes"] = None
                st.session_state["upload_file_obj"]  = None
                st.rerun()
    else:
        # ── Upload zone instructions ──
        st.markdown(
            """
            <div class="upload-zone-wrap">
                <div class="upload-icon">⬆</div>
                <div class="upload-headline">Drag &amp; drop your model file</div>
                <div class="upload-sub">or click <strong>Browse files</strong> below to select</div>
                <span class="format-badge">✓ .safetensors</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded = st.file_uploader(
            "Select model file",
            type=["safetensors"],
            key="file_uploader_widget",
            label_visibility="collapsed",
            help="Only .safetensors format is accepted. The file is never executed.",
        )

        if uploaded is not None:
            st.session_state["upload_filename"]  = uploaded.name
            st.session_state["upload_size_bytes"] = uploaded.size
            st.session_state["upload_file_obj"]  = uploaded
            st.rerun()

    st.markdown('<hr class="sig-divider">', unsafe_allow_html=True)

    col_spacer, col_next = st.columns([3, 1])
    with col_next:
        if st.button("Continue →", key="btn_upload_next", use_container_width=True):
            if not st.session_state.get("upload_filename"):
                st.session_state["_intake_error"] = "Please upload a .safetensors file before continuing."
                st.rerun()
            else:
                st.session_state.pop("_intake_error", None)
                st.session_state["intake_step"] = 2
                st.rerun()

    if err := st.session_state.pop("_intake_error", None):
        _render_validation_error(err)


# ── Step 2: Configure ─────────────────────────────────────────────────────

_DOMAIN_OPTIONS = [
    {"id": "Vision",  "icon": "🖼",  "label": "Vision",  "sub": "Image classification\n& feature extraction"},
    {"id": "NLP",     "icon": "💬",  "label": "NLP",     "sub": "Text encoding\n& language models"},
]

_PRECISION_OPTIONS = [
    {"id": "FP32", "icon": "◈", "label": "FP32", "sub": "Full precision"},
    {"id": "FP16", "icon": "◇", "label": "FP16", "sub": "Half precision"},
    {"id": "INT8", "icon": "◻", "label": "INT8", "sub": "8-bit quantized"},
]


def _option_cards(
    options: list[dict],
    state_key: str,
    card_key_prefix: str,
) -> None:
    """Render a row of clickable option cards; selection persisted in session state."""
    current = st.session_state.get(state_key)
    cols = st.columns(len(options))
    for i, opt in enumerate(options):
        with cols[i]:
            selected_cls = "option-card option-card-selected" if current == opt["id"] else "option-card"
            btn_label = f"{opt['icon']}  {opt['label']}"
            if st.button(
                btn_label,
                key=f"{card_key_prefix}_{opt['id']}",
                use_container_width=True,
                help=opt.get("sub", ""),
            ):
                st.session_state[state_key] = opt["id"]
                st.rerun()
            # Render a visual card overlay underneath the button via HTML
            tick = "✓ " if current == opt["id"] else ""
            st.markdown(
                f"""
                <div style="
                    background: {'rgba(34,211,238,0.07)' if current == opt['id'] else 'transparent'};
                    border: 2px solid {'#22D3EE' if current == opt['id'] else 'transparent'};
                    border-radius: 10px;
                    padding: 0.3rem 0.75rem 0.6rem 0.75rem;
                    margin-top: -6px;
                    font-size: 0.72rem;
                    color: {'#22D3EE' if current == opt['id'] else '#64748B'};
                    font-weight: 600;
                ">{tick}{opt['sub']}</div>
                """,
                unsafe_allow_html=True,
            )


def _step_configure() -> None:
    """Render the configuration step (Step 2)."""

    # ── Domain ──
    st.markdown('<div class="intake-field-label">Domain</div>', unsafe_allow_html=True)
    _option_cards(_DOMAIN_OPTIONS, "scan_domain", "domain")

    # ── Tensor precision ──
    st.markdown('<div class="intake-field-label">Tensor Precision / Type</div>', unsafe_allow_html=True)
    _option_cards(_PRECISION_OPTIONS, "scan_precision", "precision")

    # ── Architecture ──
    st.markdown('<div class="intake-field-label">Declared Architecture</div>', unsafe_allow_html=True)
    domain = st.session_state.get("scan_domain")
    if domain == "Vision":
        arch_options = ARCHITECTURES_VISION
    elif domain == "NLP":
        arch_options = ARCHITECTURES_NLP
    else:
        arch_options = ARCHITECTURES_ALL

    current_arch = st.session_state.get("scan_architecture")
    # Reset architecture if it doesn't match current domain options
    if current_arch and current_arch not in arch_options:
        st.session_state["scan_architecture"] = None
        current_arch = None

    placeholder_idx = 0
    select_options = [""] + arch_options
    selected_arch = st.selectbox(
        "Architecture",
        options=select_options,
        index=select_options.index(current_arch) if current_arch in select_options else 0,
        key="arch_selectbox",
        label_visibility="collapsed",
        format_func=lambda x: "— Select architecture —" if x == "" else x,
        help="Select the architecture you believe this model implements. Only architectures within the scanner's verification scope are listed.",
    )
    if selected_arch and selected_arch != st.session_state.get("scan_architecture"):
        st.session_state["scan_architecture"] = selected_arch

    # ── Security explanation ──
    st.markdown(
        """
        <div class="security-notice">
            <div class="security-notice-icon">🔒</div>
            <div class="security-notice-text">
                <strong>Execution-free analysis.</strong>
                The scanner validates uploaded tensor structures against the declared trusted
                architecture. User-provided executable model code is <em>never</em> executed.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="sig-divider">', unsafe_allow_html=True)

    col_back, col_spacer, col_next = st.columns([1, 2, 1])
    with col_back:
        if st.button("← Back", key="btn_configure_back", use_container_width=True):
            st.session_state.pop("_intake_error", None)
            st.session_state["intake_step"] = 1
            st.rerun()
    with col_next:
        if st.button("Continue →", key="btn_configure_next", use_container_width=True):
            errors: list[str] = []
            if not st.session_state.get("scan_domain"):
                errors.append("domain")
            if not st.session_state.get("scan_precision"):
                errors.append("tensor precision")
            if not st.session_state.get("scan_architecture"):
                errors.append("architecture")
            if errors:
                st.session_state["_intake_error"] = (
                    f"Please select the following before continuing: {', '.join(errors)}."
                )
                st.rerun()
            else:
                st.session_state.pop("_intake_error", None)
                st.session_state["intake_step"] = 3
                st.rerun()

    if err := st.session_state.pop("_intake_error", None):
        _render_validation_error(err)


# ── Step 3: Review ────────────────────────────────────────────────────────

def _step_review() -> None:
    """Render the review + begin-scan step (Step 3)."""
    fname  = st.session_state.get("upload_filename", "—")
    fsize  = st.session_state.get("upload_size_bytes", 0)
    domain = st.session_state.get("scan_domain", "—")
    prec   = st.session_state.get("scan_precision", "—")
    arch   = st.session_state.get("scan_architecture", "—")

    st.markdown(
        f"""
        <div class="review-panel">
            <div class="review-panel-title">Scan Configuration — Review</div>
            <div class="review-row">
                <div class="review-key">Model File</div>
                <div class="review-val">{fname}</div>
            </div>
            <div class="review-row">
                <div class="review-key">File Size</div>
                <div class="review-val-muted">{_fmt_bytes(fsize)}</div>
            </div>
            <div class="review-row">
                <div class="review-key">Format</div>
                <div class="review-val-accent">.safetensors</div>
            </div>
            <div class="review-row">
                <div class="review-key">Domain</div>
                <div class="review-val">{domain}</div>
            </div>
            <div class="review-row">
                <div class="review-key">Tensor Precision</div>
                <div class="review-val">{prec}</div>
            </div>
            <div class="review-row">
                <div class="review-key">Declared Architecture</div>
                <div class="review-val-accent">{arch}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="security-notice">
            <div class="security-notice-icon">🔒</div>
            <div class="security-notice-text">
                <strong>Ready for analysis.</strong>
                The scanner will inspect tensor structures for entropy anomalies, hidden
                bit patterns, and statistical divergence — without executing any model code.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    col_back, col_spacer, col_scan = st.columns([1, 1, 2])
    with col_back:
        if st.button("← Back", key="btn_review_back", use_container_width=True):
            st.session_state["intake_step"] = 2
            st.rerun()
    with col_scan:
        if st.button("◈  Begin Security Scan", key="btn_begin_scan", use_container_width=True):
            # Chunk 3 will hook the real pipeline here.
            # For now, transition to a 'scan initiated' holding state.
            st.session_state["scan_status"] = "running"
            st.session_state["active_page"] = "Dashboard"
            st.rerun()


# ── Page entry-point ──────────────────────────────────────────────────────

def page_scan_model() -> None:
    """Scan Model page — multi-step intake workflow (Chunk 2)."""
    # ── Page header ──
    st.markdown(
        f"""
        <div style="padding:2rem 0 0.5rem 0;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:{COLORS['accent_cyan']};margin-bottom:0.75rem;">
                Scan Model
            </div>
            <h2 style="font-size:1.9rem;font-weight:800;letter-spacing:-0.8px;
                       color:{COLORS['text_primary']};margin:0 0 0.35rem 0;">
                Security Intake
            </h2>
            <p style="font-size:0.88rem;color:{COLORS['text_muted']};max-width:580px;
                      line-height:1.6;margin-bottom:0;">
                Complete the intake workflow to prepare your model for tensor-level
                security analysis.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_step = int(st.session_state.get("intake_step", 1))
    _render_stepper(current_step)

    if current_step == 1:
        _step_upload()
    elif current_step == 2:
        _step_configure()
    elif current_step == 3:
        _step_review()
    else:
        # Safety fallback — reset to step 1
        st.session_state["intake_step"] = 1
        st.rerun()


# ---------------------------------------------------------------------------
# Page: Dashboard (stub — Chunk 3)
# ---------------------------------------------------------------------------

def page_dashboard() -> None:
    """Dashboard page — to be implemented in Chunk 3."""
    st.markdown(
        f"""
        <div style="padding:2rem 0 1rem 0;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:{COLORS['accent_cyan']};margin-bottom:0.75rem;">
                Dashboard
            </div>
            <h2 style="font-size:1.9rem;font-weight:800;letter-spacing:-0.8px;
                       color:{COLORS['text_primary']};margin:0 0 0.6rem 0;">
                Scan Results
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _coming_soon_banner(
        icon="◉",
        title="Results dashboard — coming in Chunk 3",
        body="Run a scan first to see the full security analysis dashboard with MRS, verdict, and layer breakdown.",
    )


# ---------------------------------------------------------------------------
# Page: Evidence (stub — Chunk 4)
# ---------------------------------------------------------------------------

def page_evidence() -> None:
    """Evidence page — to be implemented in Chunk 4."""
    st.markdown(
        f"""
        <div style="padding:2rem 0 1rem 0;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:{COLORS['accent_cyan']};margin-bottom:0.75rem;">
                Evidence
            </div>
            <h2 style="font-size:1.9rem;font-weight:800;letter-spacing:-0.8px;
                       color:{COLORS['text_primary']};margin:0 0 0.6rem 0;">
                Detection Evidence
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _coming_soon_banner(
        icon="◎",
        title="Evidence viewer — coming in Chunk 4",
        body="Per-layer statistical evidence, SHAP feature attribution, and behavioral signal breakdown.",
    )


# ---------------------------------------------------------------------------
# Page: Explainability (stub — Chunk 4)
# ---------------------------------------------------------------------------

def page_explainability() -> None:
    """Explainability page — to be implemented in Chunk 4."""
    st.markdown(
        f"""
        <div style="padding:2rem 0 1rem 0;">
            <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:{COLORS['accent_cyan']};margin-bottom:0.75rem;">
                Explainability
            </div>
            <h2 style="font-size:1.9rem;font-weight:800;letter-spacing:-0.8px;
                       color:{COLORS['text_primary']};margin:0 0 0.6rem 0;">
                Model Attribution
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _coming_soon_banner(
        icon="◍",
        title="Explainability — coming in Chunk 4",
        body="TreeSHAP waterfall charts, highest-risk-layer attribution, and feature importance breakdown.",
    )


# ---------------------------------------------------------------------------
# Shared component: coming-soon banner
# ---------------------------------------------------------------------------

def _coming_soon_banner(icon: str, title: str, body: str) -> None:
    """Render a polished 'not yet available' state block."""
    st.markdown(
        f"""
        <div class="coming-soon-banner">
            <div class="coming-soon-icon">{icon}</div>
            <div class="pending-badge">In progress</div>
            <div class="coming-soon-title">{title}</div>
            <div class="coming-soon-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

PAGE_REGISTRY: dict[str, object] = {
    "Overview":       page_overview,
    "Scan Model":     page_scan_model,
    "Dashboard":      page_dashboard,
    "Evidence":       page_evidence,
    "Explainability": page_explainability,
}


def _route() -> None:
    """Call the page function for the currently active page."""
    page_id = st.session_state.get("active_page", "Overview")
    page_fn = PAGE_REGISTRY.get(page_id, page_overview)
    page_fn()  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session_state()
    _inject_global_css()
    _render_sidebar()
    _route()


if __name__ == "__main__" or True:
    # Streamlit re-runs the whole module on every interaction;
    # the guard `or True` ensures main() always executes.
    main()
