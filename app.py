"""Installer Ecosystem — Streamlit App Entry Point."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))

import yaml
import bcrypt
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.loader import load_basedata, load_disti, load_basedata_from_bytes, load_disti_from_bytes
from src.classifier import run_full_classification
from src.abc_xyz import attach_abc_xyz, attach_abc_xyz_per_segment
from src.distributor import compute_top_distis
from src.db import get_overrides, get_last_snapshot_lost, save_snapshot, get_override_log
from src.views.installer_list import render_installer_list
from src.views.device_view import render_device_view
from src.views.summary import render_summary
from src.views.group_patterns import render_group_patterns
from src.views.inbox import render_inbox
from src.views.chatbot import render_chatbot
from src.views.insights import render_insights
from utils.helpers import quarter_label

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Installer Ecosystem",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Enphase Visuelt font (served from /app/static/fonts/) ── */
@font-face {
  font-family: 'Enphase Visuelt';
  src: url('/app/static/fonts/EnphaseVisuelt-Light.woff2') format('woff2');
  font-weight: 300; font-style: normal; font-display: swap;
}
@font-face {
  font-family: 'Enphase Visuelt';
  src: url('/app/static/fonts/EnphaseVisuelt-Regular.woff2') format('woff2');
  font-weight: 400; font-style: normal; font-display: swap;
}
@font-face {
  font-family: 'Enphase Visuelt';
  src: url('/app/static/fonts/EnphaseVisuelt-Medium.woff2') format('woff2');
  font-weight: 500; font-style: normal; font-display: swap;
}
@font-face {
  font-family: 'Enphase Visuelt';
  src: url('/app/static/fonts/EnphaseVisuelt-Bold.woff2') format('woff2');
  font-weight: 700; font-style: normal; font-display: swap;
}
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');

/* ═══════════════════════════════════════════════════════════
   ENPHASE DESIGN SYSTEM — LIGHT THEME
   Bg      #FAF6EF  · Surface  #FFFFFF  · Gray   #F4F3F0
   Orange  #EA6100  · Text     #3C3C3C  · Muted  #7D7D7D
   Border  #DCDCD6  · Font     Enphase Visuelt / DM Mono
   ═══════════════════════════════════════════════════════════ */

:root {
  --enph-bg:       #FAF6EF;
  --enph-surface:  #FFFFFF;
  --enph-fill:     #F4F3F0;
  --enph-orange:   #EA6100;
  --enph-orange-h: #C85400;
  --enph-text-1:   #3C3C3C;
  --enph-text-2:   #7D7D7D;
  --enph-border:   #DCDCD6;
  --enph-shadow:   0 1px 3px rgba(60,60,60,0.08), 0 4px 12px rgba(60,60,60,0.06);
  --enph-radius:   16px;
  --enph-font:     'Enphase Visuelt','Helvetica Neue',Helvetica,Arial,sans-serif;
  --enph-mono:     'DM Mono','IBM Plex Mono','Roboto Mono',monospace;
}

/* ── Global ──────────────────────────────────────────────── */
.stApp, body { background: var(--enph-bg) !important; }
.block-container { padding-top: 4.5rem; max-width: 100%; background: var(--enph-bg); }
/* DO NOT include span here — it breaks Streamlit's Material Icons font */
body, p, div, button, input, select, textarea, label {
    font-family: var(--enph-font) !important;
}
body, p, div { color: var(--enph-text-1); }

/* ── Top header bar ──────────────────────────────────────── */
header[data-testid="stHeader"] {
    background: var(--enph-surface) !important;
    border-bottom: 1px solid var(--enph-border) !important;
}
[data-testid="stToolbar"] { background: var(--enph-surface) !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stToolbar"] button { color: var(--enph-text-2) !important; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--enph-surface) !important;
    border-right: 1px solid var(--enph-border) !important;
    box-shadow: 2px 0 12px rgba(60,60,60,0.06);
}
[data-testid="stSidebar"] * { color: var(--enph-text-1) !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] strong { color: var(--enph-text-1) !important; font-weight: 500 !important; }
[data-testid="stSidebar"] label { color: var(--enph-text-2) !important; font-size: 11px !important;
    font-family: var(--enph-mono) !important; text-transform: uppercase; letter-spacing: 0.1em; }
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--enph-text-2) !important; font-size: 10px !important;
}
[data-testid="stSidebar"] hr { border-color: var(--enph-border) !important; margin: 12px 0 !important; }

/* Expanders in sidebar */
[data-testid="stSidebar"] details[data-testid="stExpander"] {
    background: var(--enph-fill) !important;
    border: 1px solid var(--enph-border) !important;
    border-radius: var(--enph-radius) !important;
    margin-bottom: 6px !important;
}
[data-testid="stSidebar"] details[data-testid="stExpander"]:hover {
    border-color: var(--enph-orange) !important;
}
[data-testid="stSidebar"] details[data-testid="stExpander"] summary {
    color: var(--enph-text-1) !important; font-size: 12px !important;
    font-weight: 500 !important; padding: 10px 12px !important;
}
[data-testid="stSidebar"] details[data-testid="stExpander"] summary:hover {
    color: var(--enph-orange) !important;
}
/* Inputs in sidebar */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background: var(--enph-fill) !important;
    border: 1px solid var(--enph-border) !important;
    color: var(--enph-text-1) !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input {
    background: var(--enph-fill) !important;
    border: 1px solid var(--enph-border) !important;
    color: var(--enph-text-1) !important;
}
/* Buttons in sidebar */
[data-testid="stSidebar"] .stButton button {
    background: var(--enph-fill) !important;
    border: 1px solid var(--enph-border) !important;
    color: var(--enph-text-1) !important;
    width: 100%; border-radius: 999px !important;
    font-size: 12px; font-weight: 500;
    padding: 9px 16px; transition: all 0.15s;
}
[data-testid="stSidebar"] .stButton button:hover {
    color: var(--enph-orange) !important;
    border-color: var(--enph-orange) !important;
    background: rgba(234,97,0,0.06) !important;
}
/* Sliders */
[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div {
    background: var(--enph-orange) !important;
}
[data-testid="stSidebar"] [data-testid="stToggle"] label {
    color: var(--enph-text-1) !important; font-size: 12px !important;
}

/* ── Page headings ───────────────────────────────────────── */
h1 { color: var(--enph-text-1) !important; font-weight: 400 !important;
     letter-spacing: -0.01em; border-bottom: 1px solid var(--enph-border);
     padding-bottom: 12px; margin-bottom: 1rem; }
h2, h3 { color: var(--enph-text-1) !important; font-weight: 500 !important; letter-spacing: -0.005em; }
h4, h5 { color: var(--enph-text-1) !important; font-weight: 500 !important; }
p, label, span { color: var(--enph-text-1); }

/* ── Metric / KPI cards ──────────────────────────────────── */
div[data-testid="metric-container"] {
    background: var(--enph-surface);
    border: 1px solid var(--enph-border);
    border-radius: var(--enph-radius);
    padding: 16px 20px;
    box-shadow: var(--enph-shadow);
    transition: border-color 0.15s, box-shadow 0.15s;
}
div[data-testid="metric-container"]:hover {
    border-color: var(--enph-orange);
    box-shadow: 0 4px 16px rgba(234,97,0,0.12);
}
div[data-testid="metric-container"] label {
    color: var(--enph-text-2) !important; font-size: 10px !important;
    font-family: var(--enph-mono) !important;
    text-transform: uppercase; letter-spacing: 0.15em; font-weight: 500;
}
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color: var(--enph-text-1) !important; font-weight: 400 !important;
    font-size: 28px !important; line-height: 1.1;
}
div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {
    font-size: 11px !important;
}
/* Tooltip icon */
div[data-testid="metric-container"] [data-testid="stTooltipHoverTarget"],
div[data-testid="metric-container"] [data-testid="stTooltipIcon"],
div[data-testid="metric-container"] svg[data-testid="stTooltipIcon"] {
    color: var(--enph-text-2) !important; fill: var(--enph-text-2) !important;
    opacity: 1 !important; visibility: visible !important; display: inline-flex !important;
}
div[data-testid="metric-container"] [data-testid="stTooltipHoverTarget"]:hover,
div[data-testid="metric-container"] [data-testid="stTooltipIcon"]:hover {
    color: var(--enph-orange) !important; fill: var(--enph-orange) !important;
}
[data-testid="stTooltipContent"] {
    background: var(--enph-surface) !important;
    border: 1px solid var(--enph-border) !important;
    color: var(--enph-text-1) !important;
    font-size: 12px !important; border-radius: var(--enph-radius) !important;
    box-shadow: var(--enph-shadow) !important;
    max-width: 260px !important; line-height: 1.5 !important; padding: 10px 12px !important;
}

/* ── Tabs (within page sections) ────────────────────────── */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    border-bottom: 1px solid var(--enph-border);
    gap: 0; background: transparent; padding: 0;
}
button[data-baseweb="tab"] {
    font-weight: 500; color: var(--enph-text-2) !important;
    border-radius: 0; padding: 10px 18px;
    font-size: 12px; transition: all 0.15s;
    border-bottom: 2px solid transparent !important;
    font-family: var(--enph-mono) !important;
    text-transform: uppercase; letter-spacing: 0.08em;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--enph-orange) !important;
    border-bottom: 2px solid var(--enph-orange) !important;
    background: transparent !important;
}
button[data-baseweb="tab"]:hover:not([aria-selected="true"]) {
    color: var(--enph-text-1) !important;
    background: var(--enph-fill) !important;
}

/* ── Buttons ─────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: var(--enph-text-1) !important; color: #fff !important;
    border: none !important; border-radius: 999px !important;
    font-weight: 500 !important; font-size: 13px !important;
    padding: 10px 22px !important; transition: all 0.15s !important;
}
.stButton > button[kind="primary"]:hover {
    background: var(--enph-orange) !important;
    transform: translateY(-1px);
}
.stButton > button {
    border-radius: 999px !important; font-weight: 500 !important; font-size: 13px !important;
    border: 1.5px solid var(--enph-text-1) !important;
    color: var(--enph-text-1) !important;
    background: transparent !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    color: var(--enph-orange) !important;
    border-color: var(--enph-orange) !important;
    background: rgba(234,97,0,0.05) !important;
}

/* ── Download button ─────────────────────────────────────── */
[data-testid="stDownloadButton"] button {
    background: rgba(234,97,0,0.08) !important;
    color: var(--enph-orange) !important;
    border: 1.5px solid var(--enph-orange) !important;
    border-radius: 999px !important;
    font-weight: 500 !important; font-size: 13px !important;
    transition: all 0.15s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: var(--enph-orange) !important;
    color: #fff !important;
}

/* ── Dataframe / table ───────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: var(--enph-radius);
    border: 1px solid var(--enph-border);
    box-shadow: var(--enph-shadow);
    overflow: hidden;
    background: var(--enph-surface);
}

/* ── Expander ────────────────────────────────────────────── */
details[data-testid="stExpander"] {
    border: 1px solid var(--enph-border) !important;
    border-radius: var(--enph-radius) !important;
    background: var(--enph-surface) !important;
}
details[data-testid="stExpander"]:hover { border-color: var(--enph-orange) !important; }
details[data-testid="stExpander"] summary {
    font-weight: 500 !important; color: var(--enph-text-1) !important;
    padding: 12px 16px; font-size: 12px;
    font-family: var(--enph-mono) !important;
    text-transform: uppercase; letter-spacing: 0.1em;
}
details[data-testid="stExpander"] summary:hover { color: var(--enph-orange) !important; }

/* ── Text input ──────────────────────────────────────────── */
[data-testid="stTextInput"] input {
    background: var(--enph-fill) !important;
    border-radius: var(--enph-radius) !important;
    border: 1px solid var(--enph-border) !important;
    color: var(--enph-text-1) !important; font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--enph-orange) !important;
    box-shadow: 0 0 0 2px rgba(234,97,0,0.15) !important;
}

/* ── Selectbox ───────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: var(--enph-fill) !important;
    border-radius: var(--enph-radius) !important;
    border: 1px solid var(--enph-border) !important;
    color: var(--enph-text-1) !important;
}
[data-baseweb="popover"] {
    background: var(--enph-surface) !important;
    border: 1px solid var(--enph-border) !important;
    border-radius: var(--enph-radius) !important;
    box-shadow: var(--enph-shadow) !important;
    overflow: hidden !important;
}
[data-baseweb="popover"] ul,[data-baseweb="select"] ul {
    background: var(--enph-surface) !important; padding: 4px !important;
}
[data-baseweb="popover"] li,[data-baseweb="select"] li {
    background: var(--enph-surface) !important; color: var(--enph-text-1) !important;
    border-radius: 8px !important; font-size: 13px !important;
    padding: 9px 14px !important; margin: 1px 0 !important;
    transition: background 0.12s, color 0.12s !important;
}
[data-baseweb="popover"] li:hover,[data-baseweb="select"] li:hover {
    background: rgba(234,97,0,0.08) !important; color: var(--enph-orange) !important;
}
[data-baseweb="popover"] li[aria-selected="true"],[data-baseweb="select"] li[aria-selected="true"] {
    background: rgba(234,97,0,0.12) !important;
    color: var(--enph-orange) !important; font-weight: 600 !important;
}
[data-baseweb="popover"] ::-webkit-scrollbar { width: 4px; }
[data-baseweb="popover"] ::-webkit-scrollbar-track { background: var(--enph-fill); }
[data-baseweb="popover"] ::-webkit-scrollbar-thumb { background: var(--enph-border); border-radius: 4px; }

/* ── Alerts ──────────────────────────────────────────────── */
div[data-testid="stAlert"] {
    background: rgba(234,97,0,0.06) !important;
    border: 1px solid rgba(234,97,0,0.2) !important;
    border-radius: var(--enph-radius) !important;
    color: var(--enph-text-1) !important;
}
div[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {
    background: rgba(67,158,88,0.08) !important;
    border-color: rgba(67,158,88,0.3) !important;
}
div[data-testid="stAlert"][data-baseweb="notification"][kind="error"] {
    background: rgba(222,33,0,0.06) !important;
    border-color: rgba(222,33,0,0.25) !important;
}

/* ── Divider ─────────────────────────────────────────────── */
hr { border-color: var(--enph-border) !important; margin: 0.8rem 0; }

/* ── Spinner ─────────────────────────────────────────────── */
.stSpinner > div { border-top-color: var(--enph-orange) !important; }

/* ── Toggle ──────────────────────────────────────────────── */
[data-testid="stToggle"] label { font-weight: 500; color: var(--enph-text-1) !important; font-size: 12px; }

/* ── Caption ─────────────────────────────────────────────── */
.stCaption, small, [data-testid="stCaptionContainer"] {
    color: var(--enph-text-2) !important; font-size: 11px !important;
    font-family: var(--enph-mono) !important; letter-spacing: 0.05em;
}

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--enph-border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--enph-orange); }

/* ── Success / info ──────────────────────────────────────── */
[data-testid="stSuccess"] {
    background: rgba(67,158,88,0.08) !important;
    border: 1px solid rgba(67,158,88,0.3) !important;
    border-radius: var(--enph-radius) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Auth ──────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _load_config():
    cfg_path = Path(__file__).parent / "config" / "users.yaml"
    with open(cfg_path, encoding="utf-8", errors="replace") as f:
        return yaml.safe_load(f)

config = _load_config()

# ── Custom role-based login ───────────────────────────────────────────────────
def _do_custom_login(cfg):
    all_users = cfg["credentials"]["usernames"]
    role_meta = {
        "admin":           {"label": "Default",           "icon": "🔧", "color": "#FF6900",  "desc": "Full platform access"},
        "country_manager": {"label": "Country Manager", "icon": "🌍", "color": "#0369A1",  "desc": "Country-level analytics"},
        "rsm":             {"label": "RSM",             "icon": "👤", "color": "#0F766E",  "desc": "Regional sales view"},
    }
    role_users = {r: {k: v for k, v in all_users.items() if v.get("role") == r}
                  for r in role_meta}

    # ── Branded header ────────────────────────────────────────────────────────
    st.markdown("""
    <style>
      #MainMenu,footer,[data-testid="stHeader"]{display:none}
      .login-wrap{min-height:80vh;display:flex;flex-direction:column;
                  align-items:center;justify-content:center;padding:3rem 1rem;}
      .login-sub{font-size:10px;color:#7D7D7D;margin-bottom:2.5rem;
                 font-weight:500;letter-spacing:0.15em;text-transform:uppercase;
                 font-family:'DM Mono','IBM Plex Mono',monospace;}
      .role-card{background:#FFFFFF;border-radius:16px;
                 border:1px solid #DCDCD6;
                 padding:28px 20px;text-align:center;
                 box-shadow:0 1px 3px rgba(60,60,60,0.08);
                 transition:all 0.2s;cursor:pointer;}
      .role-card:hover{border-color:#EA6100;
                       box-shadow:0 4px 16px rgba(234,97,0,0.12);
                       transform:translateY(-3px);}
      .login-card{background:#FFFFFF;border-radius:16px;
                  border:1px solid #DCDCD6;
                  box-shadow:0 1px 3px rgba(60,60,60,0.08);
                  padding:28px 32px;}
    </style>
    <div class='login-wrap'>
      <div style='width:48px;height:48px;background:#EA6100;border-radius:12px;
                  display:flex;align-items:center;justify-content:center;
                  font-size:1.4rem;font-weight:700;color:#fff;margin-bottom:16px'>E</div>
      <div style='font-size:1.6rem;font-weight:400;color:#3C3C3C;letter-spacing:-0.02em;margin-bottom:6px'>
        Installer Ecosystem
      </div>
      <div class='login-sub'>Enphase Installer Analytics &nbsp;·&nbsp; Euro &amp; ANZP</div>
    </div>
    """, unsafe_allow_html=True)

    if "_login_role" not in st.session_state:
        # ── Step 1: Role picker ───────────────────────────────────────────────
        st.markdown("<p style='text-align:center;color:#7D7D7D;font-size:10px;font-weight:500;margin-bottom:1.4rem;text-transform:uppercase;letter-spacing:0.15em;font-family:DM Mono,monospace'>Select your role to continue</p>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (rk, rm) in enumerate(role_meta.items()):
            with cols[i]:
                st.markdown(f"""
                <div class='role-card'>
                  <div style='width:48px;height:48px;border-radius:12px;
                       background:rgba(234,97,0,0.08);
                       border:1px solid rgba(234,97,0,0.2);
                       display:flex;align-items:center;justify-content:center;
                       margin:0 auto 12px;font-size:1.4rem'>{rm["icon"]}</div>
                  <div style='font-size:14px;font-weight:500;color:#3C3C3C;
                              margin-bottom:4px'>{rm["label"]}</div>
                  <div style='font-size:11px;color:#7D7D7D'>{rm["desc"]}</div>
                </div>""", unsafe_allow_html=True)
                if st.button(f"Continue →", key=f"role_{rk}",
                             use_container_width=True, type="primary"):
                    st.session_state["_login_role"] = rk
                    st.rerun()
        return False

    # ── Step 2: Credential form ───────────────────────────────────────────────
    sel_role = st.session_state["_login_role"]
    rm = role_meta[sel_role]

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown(f"""
        <div class='login-card'>
          <div style='display:flex;align-items:center;gap:10px;margin-bottom:20px'>
            <div style='width:40px;height:40px;border-radius:10px;
                 background:rgba(255,107,0,0.15);
                 border:1px solid rgba(255,107,0,0.3);
                 display:flex;align-items:center;justify-content:center;
                 font-size:1.2rem'>{rm["icon"]}</div>
            <div>
              <div style='font-size:14px;font-weight:500;color:#3C3C3C'>{rm["label"]} Login</div>
              <div style='font-size:11px;color:#7D7D7D'>{rm["desc"]}</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
        users_for_role = role_users[sel_role]
        if not users_for_role:
            st.error("No users configured for this role.")
        else:
            name_to_uname = {v["name"]: k for k, v in users_for_role.items()}
            sel_display = st.selectbox("Select user", list(name_to_uname.keys()),
                                       key="_login_sel_user")
            sel_uname = name_to_uname[sel_display]
            pwd = st.text_input("Password", type="password",
                                placeholder="Enter your password", key="_login_pwd")
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            col_btn, col_back = st.columns(2)
            with col_btn:
                if st.button("🔓 Sign In", type="primary", use_container_width=True,
                             key="_login_submit"):
                    stored = all_users[sel_uname]["password"]
                    if bcrypt.checkpw(pwd.encode(), stored.encode()):
                        st.session_state["authentication_status"] = True
                        st.session_state["name"]     = sel_display
                        st.session_state["username"] = sel_uname
                        st.session_state.pop("_login_role", None)
                        st.rerun()
                    else:
                        st.error("❌ Incorrect password")
            with col_back:
                if st.button("← Back", use_container_width=True, key="_login_back"):
                    st.session_state.pop("_login_role", None)
                    st.rerun()
    return False


auth_status = st.session_state.get("authentication_status")
name     = st.session_state.get("name", "")
username = st.session_state.get("username", "")

if not auth_status:
    _do_custom_login(config)
    st.stop()

# ── User info ─────────────────────────────────────────────────────────────────
user_info = config["credentials"]["usernames"].get(username, {})
role = user_info.get("role", "rsm")
user_country = user_info.get("country", "")
user_rsm = user_info.get("rsm_name", "")

# ── Data loading & classification ─────────────────────────────────────────────
# cache_resource = shared object reference, no serialisation/copy per rerun.
# df_raw & weekly_pivot are read-only so sharing is safe.
# master is .copy()-ed below before any mutation.
@st.cache_resource(show_spinner=False)
def get_master_data(decline_pct: float = 25.0, growth_pct: float = 15.0):
    import pickle
    from src.loader import BASEDATA_PATH, DISTI_PATH
    _cache_dir = Path(__file__).parent / ".datacache"
    _cache_dir.mkdir(exist_ok=True)
    try:
        _mtime = int(Path(BASEDATA_PATH).stat().st_mtime)
    except Exception:
        _mtime = 0
    _pkl = _cache_dir / f"master_{_mtime}_{int(decline_pct)}_{int(growth_pct)}.pkl"
    if _pkl.exists():
        try:
            with open(_pkl, "rb") as _f:
                return pickle.load(_f)
        except Exception:
            pass
    df = load_basedata()
    disti_df = load_disti()
    master, cur_q, all_5q, prior_4q, weekly_pivot = run_full_classification(
        df, decline_pct=decline_pct, growth_pct=growth_pct)
    master = attach_abc_xyz_per_segment(master, prior_4q, cur_q)
    tops = compute_top_distis(disti_df)
    master = master.merge(tops, on="join_key", how="left")
    for _c in ("Top_Disti_1", "Top_Disti_2"):
        if _c not in master.columns:
            master[_c] = ""
        master[_c] = master[_c].fillna("")
    # Pre-attach Region once here so it's pickled and never rebuilt on rerun
    if "Region" in df.columns and "Region" not in master.columns:
        _rmap = (df[["join_key", "Region"]].dropna(subset=["Region"])
                 .drop_duplicates("join_key").set_index("join_key")["Region"])
        master["Region"] = master["join_key"].map(_rmap).fillna("Unknown")
    result = df, master, cur_q, all_5q, prior_4q, weekly_pivot
    try:
        for _old in _cache_dir.glob("master_*.pkl"):
            if _old != _pkl:
                _old.unlink(missing_ok=True)
        with open(_pkl, "wb") as _f:
            pickle.dump(result, _f)
    except Exception:
        pass
    return result


_decline_pct = st.session_state.get("decline_pct", 25.0)
_growth_pct  = st.session_state.get("growth_pct",  15.0)

if "uploaded_df" in st.session_state:
    _df_uploaded = st.session_state["uploaded_df"]
    disti_df = st.session_state.get("uploaded_disti") or load_disti()
    # Key on object identity + thresholds — avoids re-classification on every rerun
    _classify_key = (id(_df_uploaded), id(disti_df), _decline_pct, _growth_pct)
    if st.session_state.get("_classify_cache_key") != _classify_key:
        with st.spinner("Classifying installer data…"):
            _master, cur_q, all_5q, prior_4q, weekly_pivot = run_full_classification(
                _df_uploaded, decline_pct=_decline_pct, growth_pct=_growth_pct)
            _master = attach_abc_xyz_per_segment(_master, prior_4q, cur_q)
            tops = compute_top_distis(disti_df)
            _master = _master.merge(tops, on="join_key", how="left")
            for _c in ("Top_Disti_1", "Top_Disti_2"):
                if _c not in _master.columns:
                    _master[_c] = ""
                _master[_c] = _master[_c].fillna("")
            st.session_state["_classify_cache_key"] = _classify_key
            st.session_state["_classify_cache"] = (
                _df_uploaded, _master, cur_q, all_5q, prior_4q, weekly_pivot)
    df_raw, _master_base, cur_q, all_5q, prior_4q, weekly_pivot = (
        st.session_state["_classify_cache"])
else:
    _cached = get_master_data(decline_pct=_decline_pct, growth_pct=_growth_pct)
    df_raw, _master_base, cur_q, all_5q, prior_4q, weekly_pivot = _cached

# ── Build override-applied master (cached in session_state by hash) ───────────────
overrides = get_overrides()
_ov_hash = hash(tuple(sorted((k, tuple(sorted(v.items()))) for k, v in overrides.items())))
if st.session_state.get("_master_ov_hash") != _ov_hash:
    # Only copy master when overrides actually changed (rare)
    master = _master_base.copy()
    for jk, fields in overrides.items():
        idx = master[master["join_key"] == jk].index
        for field, val in fields.items():
            if field in master.columns and len(idx) > 0:
                master.loc[idx, field] = val
    # Lost-Regained flag — vectorized
    last_lost = get_last_snapshot_lost()
    if last_lost:
        _reg_mask = master["join_key"].isin(last_lost) & (master["Installer_Category"] != "Lost")
        master["Lost_Regained"] = np.where(_reg_mask, "Yes", "No")
    else:
        master["Lost_Regained"] = "No"
    st.session_state["_master_ov_hash"] = _ov_hash
    st.session_state["_master_cached"] = master
else:
    master = st.session_state["_master_cached"]

# ── Quick role-scoped counts for sidebar (before full master_scoped is built) ──
if role == "country_manager" and user_country:
    _sidebar_master = master[master["Installer_Country"] == user_country]
elif role == "rsm" and user_rsm:
    _sidebar_master = master[master["RSMs"] == user_rsm]
else:
    _sidebar_master = master
# Apply region filter to count if a region is selected
# Read from widget key directly — avoids one-rerun lag vs sel_region copy
_sel_region_sidebar = st.session_state.get("sb_region_widget", "All")
if _sel_region_sidebar and _sel_region_sidebar != "All" and "Region" in _sidebar_master.columns:
    _sidebar_master = _sidebar_master[_sidebar_master["Region"] == _sel_region_sidebar]

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    role_label = role.replace("_", " ").title()
    _initials = "".join(w[0].upper() for w in name.split()[:2])
    _scope_tag = user_country or user_rsm or ""
    q_loaded = len(all_5q)
    _q_dot = "#34D399" if q_loaded >= 5 else "#FBBF24"
    st.markdown(f"""
    <div style='padding:16px 8px 0'>
      <!-- Brand -->
      <div style='display:flex;align-items:center;gap:8px;margin-bottom:20px;
                  padding-bottom:16px;border-bottom:1px solid #DCDCD6'>
        <div style='width:32px;height:32px;background:#EA6100;border-radius:8px;
             display:flex;align-items:center;justify-content:center;
             font-size:1rem;font-weight:700;color:#fff;flex-shrink:0'>E</div>
        <div>
          <div style='font-size:13px;font-weight:500;color:#3C3C3C;letter-spacing:-0.01em'>Installer Ecosystem</div>
          <div style='font-size:10px;color:#7D7D7D;letter-spacing:0.15em;font-family:"DM Mono",monospace;text-transform:uppercase'>ENPHASE ANALYTICS</div>
        </div>
      </div>
      <!-- User -->
      <div style='display:flex;align-items:center;gap:10px;margin-bottom:20px;
                  padding:10px;background:#F4F3F0;
                  border-radius:16px;border:1px solid #DCDCD6'>
        <div style='width:34px;height:34px;border-radius:8px;
             background:rgba(234,97,0,0.1);border:1px solid rgba(234,97,0,0.25);
             display:flex;align-items:center;justify-content:center;
             font-size:11px;font-weight:700;color:#EA6100;flex-shrink:0'>{_initials}</div>
        <div style='min-width:0;flex:1'>
          <div style='font-size:12px;font-weight:500;color:#3C3C3C;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{name}</div>
          <div style='font-size:10px;color:#7D7D7D;margin-top:1px'>{role_label}{(' · ' + _scope_tag) if _scope_tag else ''}</div>
        </div>
      </div>
      <!-- Stats grid -->
      <div style='font-size:9px;font-weight:500;color:#7D7D7D;
                  text-transform:uppercase;letter-spacing:0.15em;
                  font-family:"DM Mono",monospace;margin-bottom:8px'>Data Status</div>
      <div style='display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:16px'>
        <div style='background:#FFFFFF;border-radius:12px;padding:10px;border:1px solid #DCDCD6'>
          <div style='font-size:9px;color:#7D7D7D;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.12em;font-family:"DM Mono",monospace'>Quarter</div>
          <div style='font-size:11px;font-weight:400;color:#3C3C3C'>{("Q"+all_5q[0].split("-Q")[1]+"'"+all_5q[0].split("-")[0][2:]) + "–" + ("Q"+cur_q.split("-Q")[1]+"'"+cur_q.split("-")[0][2:]) if all_5q else cur_q}</div>
        </div>
        <div style='background:#FFFFFF;border-radius:12px;padding:10px;border:1px solid #DCDCD6'>
          <div style='font-size:9px;color:#7D7D7D;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.12em;font-family:"DM Mono",monospace'>Installers</div>
          <div style='font-size:13px;font-weight:400;color:#3C3C3C'>{len(_sidebar_master):,}</div>
        </div>
        <div style='background:#FFFFFF;border-radius:12px;padding:10px;border:1px solid #DCDCD6'>
          <div style='font-size:9px;color:#7D7D7D;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.12em;font-family:"DM Mono",monospace'>Countries</div>
          <div style='font-size:13px;font-weight:400;color:#3C3C3C'>{_sidebar_master['Installer_Country'].nunique()}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if "uploaded_df" in st.session_state:
        st.success("Using uploaded files")

    # ── Region filter (shown when data contains multiple regions) ────────────
    if "Region" in master.columns:
        _avail_regions = sorted(master["Region"].dropna().unique().tolist())
        if len(_avail_regions) > 1:
            _cur_region = st.session_state.get("sel_region", "All")
            _region_opts = ["All"] + _avail_regions
            _sel_region = st.selectbox(
                "🌍 Region",
                _region_opts,
                index=_region_opts.index(_cur_region) if _cur_region in _region_opts else 0,
                key="sb_region_widget",
            )
            st.session_state["sel_region"] = _sel_region
    st.divider()

    # Admin: data upload + settings
    if role == "admin":
        with st.expander("📂 Upload Data Files", expanded=False):
            st.markdown("**Activation Data** (basedata)")
            bd_files = st.file_uploader(
                "Upload 1–5 quarterly files",
                type=["xlsx"], accept_multiple_files=True, key="bd_upload"
            )
            st.markdown("**Disti Mapping**")
            disti_file = st.file_uploader(
                "Upload Installer disti mapping.xlsx",
                type=["xlsx"], accept_multiple_files=False, key="disti_upload"
            )
            if st.button("▶ Process & Apply", type="primary",
                         disabled=(not bd_files and not disti_file)):
                with st.spinner("Loading files…"):
                    if bd_files:
                        st.session_state["uploaded_df"] = load_basedata_from_bytes(bd_files)
                    if disti_file:
                        st.session_state["uploaded_disti"] = load_disti_from_bytes(disti_file)
                    st.cache_data.clear()
                st.success("Done — refreshing…")
                st.rerun()
            if "uploaded_df" in st.session_state or "uploaded_disti" in st.session_state:
                if st.button("🗑 Revert to disk files"):
                    st.session_state.pop("uploaded_df", None)
                    st.session_state.pop("uploaded_disti", None)
                    st.cache_data.clear()
                    st.rerun()

        with st.expander("⚙️ Classification Settings", expanded=False):
            new_decline = st.slider(
                "Declining threshold (%)",
                min_value=5, max_value=50,
                value=int(st.session_state.get("decline_pct", 25)),
                step=5,
                help="Run-rate must drop by this % vs prior 2Q avg to be Declining"
            )
            new_growth = st.slider(
                "Growing threshold (%)",
                min_value=5, max_value=50,
                value=int(st.session_state.get("growth_pct", 15)),
                step=5,
                help="Run-rate must rise by this % vs prior 2Q avg to be Growing"
            )
            if st.button("Apply Thresholds"):
                st.session_state["decline_pct"] = float(new_decline)
                st.session_state["growth_pct"]  = float(new_growth)
                st.cache_data.clear()
                st.rerun()
            st.caption(f"Current: Declining ≥{int(st.session_state.get('decline_pct',25))}% drop · "
                       f"Growing ≥{int(st.session_state.get('growth_pct',15))}% rise")

        if st.button("� Clear Data Cache", help="Force-reloads all data files from disk"):
            st.cache_data.clear()
            st.cache_resource.clear()
            for key in list(st.session_state.keys()):
                if key.startswith("_master"):
                    del st.session_state[key]
            st.rerun()

        if st.button("�📸 Save Quarter Snapshot"):
            save_snapshot(master, cur_q)
            st.success(f"Snapshot saved for {cur_q}")
        st.divider()

    # ── Glossary ────────────────────────────────────────────
    with st.expander("📖 Glossary & Guide", expanded=False):
        st.markdown("""
<style>
.gl-section {
    font-size:10px; font-weight:700; text-transform:uppercase;
    letter-spacing:0.08em; color:#FF6B00;
    margin:10px 0 5px; padding-bottom:4px;
    border-bottom:1px solid rgba(255,107,0,0.2);
}
.gl-row { display:flex; gap:6px; margin-bottom:6px; align-items:flex-start; }
.gl-badge {
    flex-shrink:0; font-size:9px; font-weight:700;
    padding:2px 7px; border-radius:20px; margin-top:1px;
    white-space:nowrap;
}
.gl-text { font-size:11px; color:#D1D5DB; line-height:1.4; }
.gl-sub  { font-size:10px; color:#6B7280; margin-top:1px; }
.gl-step { display:flex; gap:6px; margin-bottom:5px; align-items:flex-start; }
.gl-num  { flex-shrink:0; width:16px; height:16px; border-radius:50%;
           background:#FF6B00; color:#fff; font-size:9px; font-weight:700;
           display:flex; align-items:center; justify-content:center; margin-top:1px; }
</style>

<div class="gl-section">Tiers (by activation volume)</div>

<div class="gl-row">
  <span class="gl-badge" style="background:rgba(168,85,247,0.2);color:#A855F7">💎 Diamond</span>
  <div><div class="gl-text">Top 20 installers per country</div>
  <div class="gl-sub">Highest-value, priority engagement</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(100,116,139,0.2);color:#94A3B8">🥈 Platinum</span>
  <div><div class="gl-text">Next 50 per country</div>
  <div class="gl-sub">Strong, consistent performers</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(245,158,11,0.2);color:#F59E0B">🥇 Golden</span>
  <div><div class="gl-text">Next 100 per country</div>
  <div class="gl-sub">Moderate, regular activators</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(148,163,184,0.15);color:#94A3B8">🥈 Silver</span>
  <div><div class="gl-text">Remaining active (long tail)</div>
  <div class="gl-sub">Entry-tier, growth opportunity</div></div>
</div>

<div class="gl-section">Segments (by trend)</div>

<div class="gl-row">
  <span class="gl-badge" style="background:rgba(239,68,68,0.2);color:#EF4444">🔴 Lost</span>
  <div><div class="gl-text">Zero activations this quarter</div>
  <div class="gl-sub">Needs immediate re-engagement</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(249,115,22,0.2);color:#F97316">📉 Declining</span>
  <div><div class="gl-text">Run-rate dropped ≥25% vs prior 2Q avg</div>
  <div class="gl-sub">Threshold adjustable in Classification Settings</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(34,197,94,0.2);color:#22C55E">📈 Growing</span>
  <div><div class="gl-text">Run-rate rose ≥15% vs prior 2Q avg</div>
  <div class="gl-sub">Threshold adjustable in Classification Settings</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(59,130,246,0.2);color:#3B82F6">🆕 New</span>
  <div><div class="gl-text">First activation this quarter</div>
  <div class="gl-sub">No prior quarter history</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(148,163,184,0.15);color:#94A3B8">⚖️ Stable</span>
  <div><div class="gl-text">Active, steady run-rate</div>
  <div class="gl-sub">Not Declining, Growing, or New</div></div>
</div>

<div class="gl-section">Priority</div>

<div class="gl-row">
  <span class="gl-badge" style="background:rgba(99,102,241,0.2);color:#6366F1">P1</span>
  <div><div class="gl-text">Diamond or Platinum installers</div>
  <div class="gl-sub">Immediate attention — highest revenue impact</div></div>
</div>
<div class="gl-row">
  <span class="gl-badge" style="background:rgba(148,163,184,0.15);color:#94A3B8">P2</span>
  <div><div class="gl-text">Golden or Silver installers</div>
  <div class="gl-sub">Standard follow-up cadence</div></div>
</div>

<div class="gl-section">Classification Method</div>
<div class="gl-step"><div class="gl-num">1</div>
  <div class="gl-text">Rolling 5 quarters of activation data loaded</div></div>
<div class="gl-step"><div class="gl-num">2</div>
  <div class="gl-text">Current quarter run-rate vs prior 2Q average computed per installer</div></div>
<div class="gl-step"><div class="gl-num">3</div>
  <div class="gl-text">Segment assigned: Lost → New → Declining → Growing → Stable</div></div>
<div class="gl-step"><div class="gl-num">4</div>
  <div class="gl-text">Tier ranked by total devices activated in current quarter, per country</div></div>
<div class="gl-step"><div class="gl-num">5</div>
  <div class="gl-text">Priority = P1 if tier is Diamond/Platinum, else P2</div></div>

<div class="gl-section">Navigation Guide</div>
<div class="gl-text" style="margin-bottom:4px"><b>Insights</b> — Actionable priorities, heatmaps & focus list</div>
<div class="gl-text" style="margin-bottom:4px"><b>Dashboard</b> — KPI overview & country breakdown</div>
<div class="gl-text" style="margin-bottom:4px"><b>Summary</b> — Pivot tables by country & RSM with drill-down</div>
<div class="gl-text" style="margin-bottom:4px"><b>Installers List</b> — Full installer-level detail & export</div>
<div class="gl-text" style="margin-bottom:4px"><b>All Devices</b> — Microinverter, Storage & EVSE breakdown</div>
<div class="gl-text" style="margin-bottom:12px"><b>Inbox</b> — Action flags & follow-up items</div>
""", unsafe_allow_html=True)

    st.divider()
    if st.button("\U0001f6aa Logout", use_container_width=True, key="_logout_btn"):
        for k in ["authentication_status", "name", "username",
                  "uploaded_df", "uploaded_disti", "decline_pct", "growth_pct",
                  "sel_region", "sb_country", "sb_rsm", "sb_segment",
                  "sb_tier", "sb_priority"]:
            st.session_state.pop(k, None)
        st.rerun()

# ── Landing Dashboard ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def _kpi_counts(m: pd.DataFrame):
    """Cache all value_counts/len calls so dashboard rerenders are instant."""
    vc_seg  = m["Installer_Category"].value_counts().reset_index()
    vc_seg.columns = ["Segment", "Count"]
    vc_tier = m[m["Installer_Group"] != "Lost"]["Installer_Group"].value_counts().reset_index()
    vc_tier.columns = ["Tier", "Count"]
    vc_pri  = m["Priority"].value_counts().reset_index()
    vc_pri.columns = ["Priority", "Count"]
    grp_counts = m["Installer_Group"].value_counts()
    cat_counts = m["Installer_Category"].value_counts()
    return vc_seg, vc_tier, vc_pri, grp_counts, cat_counts


def _kpi_card(col, icon_label: str, value: str, tooltip: str):
    """Render a KPI card with a guaranteed visible ⓘ tooltip."""
    col.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #DCDCD6;border-radius:16px;
            padding:16px 20px;box-shadow:0 1px 3px rgba(60,60,60,0.08);
            transition:border-color 0.15s,box-shadow 0.15s;position:relative">
  <div style="display:flex;align-items:center;gap:4px;margin-bottom:6px">
    <span style="color:#7D7D7D;font-size:10px;text-transform:uppercase;
                 letter-spacing:0.15em;font-weight:500;
                 font-family:'DM Mono','IBM Plex Mono',monospace">{icon_label}</span>
    <span class="kpi-tip" data-tip="{tooltip}"
          style="width:15px;height:15px;border-radius:50%;border:1px solid #DCDCD6;
                 display:inline-flex;align-items:center;justify-content:center;
                 color:#7D7D7D;font-size:9px;font-weight:700;cursor:default;
                 flex-shrink:0;margin-left:2px;line-height:1">ⓘ</span>
  </div>
  <div style="color:#3C3C3C;font-weight:400;font-size:28px;line-height:1.1">{value}</div>
</div>""", unsafe_allow_html=True)


# ASP per quarter per device type (EURO region)
_ASP = {
    "2025-Q2": {"Microinverter": 166, "IQ Battery": 519},
    "2025-Q3": {"Microinverter": 161, "IQ Battery": 494},
    "2025-Q4": {"Microinverter": 167, "IQ Battery": 500},
    "2026-Q1": {"Microinverter": 168, "IQ Battery": 499},
    "2026-Q2": {"Microinverter": 177, "IQ Battery": 496},
}


@st.cache_data(show_spinner=False)
def _compute_dashboard_revenue(df_raw: pd.DataFrame, master: pd.DataFrame,
                               cq: str, lq: str) -> dict:
    """One-pass vectorised revenue for dashboard — cached until data changes."""
    results = {}
    for q, quarter_df in [(cq, df_raw[df_raw["Quarter"] == cq]),
                           (lq, df_raw[df_raw["Quarter"] == lq])]:
        asp_q = _ASP.get(q, {})
        if not asp_q:
            continue
        asp_df = pd.DataFrame([(d, a) for d, a in asp_q.items()],
                              columns=["Device Type", "_asp"])
        merged = quarter_df.merge(asp_df, on="Device Type", how="inner")
        merged["_rev"] = pd.to_numeric(merged["Number of devices"],
                                        errors="coerce").fillna(0) * merged["_asp"]
        rev_by_key = merged.groupby("join_key")["_rev"].sum()
        m2 = master[["join_key", "Installer_Group", "Installer_Category"]].copy()
        m2["_rev"] = m2["join_key"].map(rev_by_key).fillna(0)
        results[q] = m2
    return results


def _revenue_from_raw(df_raw: pd.DataFrame, join_keys, q_list: list) -> dict:
    """Compute revenue dict {quarter: dollars} for given installers."""
    df = df_raw[df_raw["join_key"].isin(join_keys) & df_raw["Quarter"].isin(q_list)]
    rev = {}
    for q in q_list:
        asp_q = _ASP.get(q, {})
        if not asp_q:
            rev[q] = 0
            continue
        df_q = df[df["Quarter"] == q]
        total = 0
        for dev, asp in asp_q.items():
            units = df_q[df_q["Device Type"] == dev]["Number of devices"].sum()
            total += units * asp
        rev[q] = total
    return rev


def render_kpi_dashboard(m: pd.DataFrame, label: str, q_list: list = None, df_raw: pd.DataFrame = None):
    _q_range = ""
    if q_list and len(q_list) >= 2:
        def _fmt_q(q):
            yr, qn = q.split("-Q")
            return f"Q{qn}'{yr[2:]}"
        _q_range = f" ({_fmt_q(q_list[0])}–{_fmt_q(q_list[-1])})"
    st.markdown(f"### {label} — Overview{_q_range}")
    st.markdown("""
<style>
.kpi-tip { position:relative; }
.kpi-tip::after {
    content: attr(data-tip);
    position:absolute; bottom:calc(100% + 8px); left:50%;
    transform:translateX(-50%);
    background:#1C2333; color:#E5E7EB;
    font-size:11px; font-weight:400; line-height:1.5;
    padding:8px 12px; border-radius:8px; white-space:normal;
    width:220px; text-align:left;
    border:1px solid rgba(255,255,255,0.12);
    box-shadow:0 8px 24px rgba(0,0,0,0.5);
    opacity:0; pointer-events:none;
    transition:opacity 0.15s; z-index:9999;
}
.kpi-tip:hover::after { opacity:1; }
.kpi-tip:hover { color:#FF6B00 !important; border-color:#FF6B00 !important; }
</style>""", unsafe_allow_html=True)

    vc_seg, vc_tier, vc_pri, grp_counts, cat_counts = _kpi_counts(m)
    dec_pct  = int(st.session_state.get('decline_pct', 25))
    grow_pct = int(st.session_state.get('growth_pct', 15))
    total    = len(m)
    lost_n   = cat_counts.get("Lost", 0)
    active_n = total - lost_n
    at_risk  = lost_n + cat_counts.get("Declining", 0)
    _cq_hero = (f"Q{q_list[-1].split('-Q')[1]}'{q_list[-1].split('-Q')[0][2:]}"
                if q_list else "current Q")

    # ── Hero row ──────────────────────────────────────────────────────────────
    h1, h2, h3 = st.columns(3)
    def _hero(col, label, value, sub, accent="#3C3C3C"):
        col.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #DCDCD6;border-radius:16px;
            padding:20px 24px;box-shadow:0 1px 3px rgba(60,60,60,0.06)">
  <div style="font-size:10px;font-weight:600;color:#7D7D7D;text-transform:uppercase;
              letter-spacing:0.15em;font-family:'DM Mono',monospace;margin-bottom:8px">{label}</div>
  <div style="font-size:36px;font-weight:300;color:{accent};line-height:1;margin-bottom:6px">{value}</div>
  <div style="font-size:11px;color:#7D7D7D">{sub}</div>
</div>""", unsafe_allow_html=True)

    _hero(h1, "Total Installers", f"{total:,}", "Rolling 5-quarter scope")
    _hero(h2, f"Active in {_cq_hero}", f"{active_n:,}",
          f"{active_n*100//total if total else 0}% of total \u00b7 activated in {_cq_hero}", "#22C55E")
    _hero(h3, "At Risk", f"{at_risk:,}",
          f"{at_risk*100//total if total else 0}% of total \u00b7 Lost + Declining", "#EF4444")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Tier + Segment compact panels ─────────────────────────────────────────
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #DCDCD6;border-radius:16px;padding:16px 20px">
  <div style="font-size:10px;font-weight:600;color:#7D7D7D;text-transform:uppercase;
              letter-spacing:0.15em;font-family:'DM Mono',monospace;margin-bottom:12px">Tier Breakdown</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div><div style="font-size:24px;font-weight:300;color:#A855F7">{grp_counts.get('Diamond',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F48E Diamond
           <span class="kpi-tip" data-tip="Top 20 installers per country ranked by total 5Q volume. Highest-value tier.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#64748B">{grp_counts.get('Platinum',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F948 Platinum
           <span class="kpi-tip" data-tip="Next 50 installers per country after Diamond, by 5Q volume. Strong, consistent performers.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#F59E0B">{grp_counts.get('Golden',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F947 Golden
           <span class="kpi-tip" data-tip="Next 100 installers per country after Platinum, by 5Q volume. Moderate but regular activators.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#94A3B8">{grp_counts.get('Silver',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F948 Silver
           <span class="kpi-tip" data-tip="Rank 171+ per country. Entry-tier long tail, growth opportunity.">&#9432;</span></div></div>
  </div>
</div>""", unsafe_allow_html=True)

    with sc2:
        st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #DCDCD6;border-radius:16px;padding:16px 20px">
  <div style="font-size:10px;font-weight:600;color:#7D7D7D;text-transform:uppercase;
              letter-spacing:0.15em;font-family:'DM Mono',monospace;margin-bottom:12px">Segment Breakdown</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
    <div><div style="font-size:24px;font-weight:300;color:#EF4444">{cat_counts.get('Lost',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F534 Lost
           <span class="kpi-tip" data-tip="Zero activations in the current quarter. Needs re-engagement.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#F97316">{cat_counts.get('Declining',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F4C9 Declining
           <span class="kpi-tip" data-tip="Run-rate dropped &ge;{dec_pct}% vs prior 2Q average. At risk of going Lost.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#22C55E">{cat_counts.get('Growing',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F4C8 Growing
           <span class="kpi-tip" data-tip="Run-rate rose &ge;{grow_pct}% vs prior 2Q average. Positive momentum.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#3B82F6">{cat_counts.get('New',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\U0001F195 New
           <span class="kpi-tip" data-tip="First-time activators — no orders in prior 4 quarters.">&#9432;</span></div></div>
    <div><div style="font-size:24px;font-weight:300;color:#94A3B8">{cat_counts.get('Stable',0):,}</div>
         <div style="font-size:11px;color:#7D7D7D;margin-top:2px">\u2696\uFE0F Stable
           <span class="kpi-tip" data-tip="Active but not Declining, Growing, or New. Steady baseline.">&#9432;</span></div></div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Revenue strip ─────────────────────────────────────────────────────────
    if df_raw is not None and q_list:
        _cq = q_list[-1]
        _lq = q_list[-2] if len(q_list) >= 2 else _cq
        _cq_label = f"Q{_cq.split('-Q')[1]}'{_cq.split('-Q')[0][2:]}"

        # Single cached pass over df_raw — avoids 6 separate 287K-row scans
        _rev_cache = _compute_dashboard_revenue(df_raw, m, _cq, _lq)

        def _grp_rev_fast(group_col, group_val, q=None):
            _q = q or _cq
            _tbl = _rev_cache.get(_q)
            if _tbl is None: return 0
            return float(_tbl[_tbl[group_col] == group_val]["_rev"].sum())

        def _fmt_m(v):
            if v >= 1_000_000: return f"${v/1_000_000:.1f}M"
            elif v >= 1_000:   return f"${v/1_000:.0f}K"
            return f"${v:,.0f}"

        _r = {g: _grp_rev_fast("Installer_Group", g) for g in ["Diamond","Platinum","Golden","Silver"]}
        _total_rev = sum(_r.values())
        st.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #DCDCD6;border-radius:16px;padding:16px 20px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
    <div style="font-size:10px;font-weight:600;color:#7D7D7D;text-transform:uppercase;
                letter-spacing:0.15em;font-family:'DM Mono',monospace">
      Revenue by Tier &nbsp;&middot;&nbsp; {_cq_label}
      <span style="font-weight:400;color:#AAAAAA">&nbsp;(units &times; ASP)</span>
    </div>
    <div style="font-size:20px;font-weight:300;color:#EA6100">{_fmt_m(_total_rev)}&nbsp;
      <span style="font-size:11px;color:#7D7D7D;font-weight:400">total</span>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px">
    <div style="border-left:3px solid #A855F7;padding-left:12px">
      <div style="font-size:20px;font-weight:300;color:#3C3C3C">{_fmt_m(_r['Diamond'])}</div>
      <div style="font-size:11px;color:#7D7D7D;margin-top:3px">\U0001F48E Diamond</div>
    </div>
    <div style="border-left:3px solid #64748B;padding-left:12px">
      <div style="font-size:20px;font-weight:300;color:#3C3C3C">{_fmt_m(_r['Platinum'])}</div>
      <div style="font-size:11px;color:#7D7D7D;margin-top:3px">\U0001F948 Platinum</div>
    </div>
    <div style="border-left:3px solid #F59E0B;padding-left:12px">
      <div style="font-size:20px;font-weight:300;color:#3C3C3C">{_fmt_m(_r['Golden'])}</div>
      <div style="font-size:11px;color:#7D7D7D;margin-top:3px">\U0001F947 Golden</div>
    </div>
    <div style="border-left:3px solid #94A3B8;padding-left:12px">
      <div style="font-size:20px;font-weight:300;color:#3C3C3C">{_fmt_m(_r['Silver'])}</div>
      <div style="font-size:11px;color:#7D7D7D;margin-top:3px">\U0001F948 Silver</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Revenue at Risk strip ──────────────────────────────────────────────
        _lq_label = f"Q{_lq.split('-Q')[1]}'{_lq.split('-Q')[0][2:]}"
        _lost_rev     = _grp_rev_fast("Installer_Category", "Lost", _lq)
        _declining_rev = _grp_rev_fast("Installer_Category", "Declining")
        _risk_total   = _lost_rev + _declining_rev
        st.markdown(f"""
<div style="background:#FFF5F5;border:1px solid #FECACA;border-radius:16px;padding:16px 20px;margin-top:10px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
    <div style="font-size:10px;font-weight:600;color:#EF4444;text-transform:uppercase;
                letter-spacing:0.15em;font-family:'DM Mono',monospace">
      \U0001F6A8 Revenue at Risk
      <span style="font-weight:400;color:#FCA5A5">&nbsp;(units &times; ASP)</span>
    </div>
    <div style="font-size:20px;font-weight:300;color:#EF4444">{_fmt_m(_risk_total)}&nbsp;
      <span style="font-size:11px;color:#7D7D7D;font-weight:400">total at risk</span>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div style="border-left:3px solid #EF4444;padding-left:12px">
      <div style="font-size:20px;font-weight:300;color:#EF4444">{_fmt_m(_lost_rev)}</div>
      <div style="font-size:11px;color:#7D7D7D;margin-top:3px">\U0001F534 Lost &nbsp;
        <span style="color:#AAAAAA">({_lq_label} baseline \u2014 last active quarter)</span></div>
    </div>
    <div style="border-left:3px solid #F97316;padding-left:12px">
      <div style="font-size:20px;font-weight:300;color:#F97316">{_fmt_m(_declining_rev)}</div>
      <div style="font-size:11px;color:#7D7D7D;margin-top:3px">\U0001F4C9 Declining &nbsp;
        <span style="color:#AAAAAA">({_cq_label} \u2014 at risk of further drop)</span></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    seg_colors  = {"Lost": "#EF4444", "Declining": "#F97316",
                   "Growing": "#22C55E", "New": "#3B82F6", "Stable": "#94A3B8"}
    tier_colors = {"Diamond": "#A855F7", "Platinum": "#64748B",
                   "Golden": "#F59E0B",  "Silver": "#94A3B8"}

    col_seg, col_tier = st.columns(2)
    with col_seg:
        fig = px.pie(vc_seg, names="Segment", values="Count",
                     color="Segment", color_discrete_map=seg_colors,
                     hole=0.55, title="Segment Mix", height=300)
        fig.update_layout(margin=dict(t=36, b=0, l=0, r=0),
                          paper_bgcolor="#FFFFFF",
                          title_font=dict(size=12, color="#3C3C3C"),
                          legend=dict(font=dict(size=11)))
        st.plotly_chart(fig, use_container_width=True)

    with col_tier:
        fig2 = px.bar(vc_tier, x="Tier", y="Count", color="Tier",
                      color_discrete_map=tier_colors, title="Tier Distribution", height=300)
        fig2.update_layout(showlegend=False, margin=dict(t=36, b=0, l=0, r=0),
                           paper_bgcolor="#FFFFFF", plot_bgcolor="#FAFAFA",
                           title_font=dict(size=12, color="#3C3C3C"),
                           xaxis=dict(tickfont=dict(size=11)),
                           yaxis=dict(tickfont=dict(size=11)))
        st.plotly_chart(fig2, use_container_width=True)


# ── Global filter defaults (no UI widgets — each tab has its own filters) ─────
sb_country  = user_country or "All"
sb_rsm      = user_rsm or "All"
sb_segment  = "All"
sb_tier     = "All"
sb_priority = "All"
sb_region   = st.session_state.get("sb_region_widget", "All")

# ── Scope master by role (no .copy() unless filtering is needed) ──────────────
if role == "country_manager" and user_country:
    master_scoped = master[master["Installer_Country"] == user_country]
    df_raw_scoped = df_raw[df_raw["Installer_Country"] == user_country]
elif role == "rsm" and user_rsm:
    master_scoped = master[master["RSMs"] == user_rsm]
    df_raw_scoped = df_raw[df_raw["join_key"].isin(master_scoped["join_key"])]
else:
    master_scoped = master
    df_raw_scoped = df_raw

# ── Apply sidebar global filters (single-pass mask) ───────────────────────────
_m_mask = pd.Series(True, index=master_scoped.index)
if sb_country and sb_country != "All":
    _m_mask &= master_scoped["Installer_Country"] == sb_country
if sb_rsm and sb_rsm != "All":
    _m_mask &= master_scoped["RSMs"] == sb_rsm
if sb_segment != "All":
    _m_mask &= master_scoped["Installer_Category"] == sb_segment
if sb_tier != "All":
    _m_mask &= master_scoped["Installer_Group"] == sb_tier
if sb_priority != "All":
    _m_mask &= master_scoped["Priority"] == sb_priority
if sb_region and sb_region != "All" and "Region" in master_scoped.columns:
    _m_mask &= master_scoped["Region"] == sb_region
if not _m_mask.all():
    master_scoped = master_scoped[_m_mask]
    df_raw_scoped = df_raw_scoped[df_raw_scoped["join_key"].isin(master_scoped["join_key"])]

# ── Active-filter context bar ───────────────────────────────────────────────────
_active_filters = []
if sb_country  != "All": _active_filters.append(f"\U0001f30d {sb_country}")
if sb_rsm      != "All": _active_filters.append(f"\U0001f464 {sb_rsm}")
if sb_segment  != "All": _active_filters.append(f"\U0001f4ca {sb_segment}")
if sb_tier     != "All": _active_filters.append(f"\U0001f48e {sb_tier}")
if sb_priority != "All": _active_filters.append(f"\u2b50 {sb_priority}")
if sb_region   != "All": _active_filters.append(f"\U0001f310 {sb_region}")
if _active_filters:
    st.info(
        "**Active Filters:** " + "  \u00b7  ".join(_active_filters)
        + f"  \u00b7  **{len(master_scoped):,} installers shown**"
    )

# ── Lazy navigation (replaces st.tabs — only active view renders) ────────────
_dash_label = "My Dashboard" if role == "rsm" else "Dashboard"
_NAV_TABS = [_dash_label, "Insights", "Summary", "Installers List", "All Devices", "Inbox"]

if "active_tab" not in st.session_state:
    st.session_state.active_tab = _dash_label
if st.session_state.active_tab not in _NAV_TABS:
    st.session_state.active_tab = _dash_label

st.markdown("""
<style>
div[data-testid="stHorizontalBlock"]:has(.nav-tab-btn) {
    gap: 2px !important;
    border-bottom: 1px solid #DCDCD6;
    padding-bottom: 0;
    margin-bottom: 16px;
}
div[data-testid="stHorizontalBlock"]:has(.nav-tab-btn) > div {
    flex: 1 1 0;
}
div[data-testid="stHorizontalBlock"]:has(.nav-tab-btn) button {
    width: 100% !important;
    border-radius: 0 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    color: #7D7D7D !important;
    font-size: 11px !important; font-weight: 500 !important;
    font-family: 'DM Mono','IBM Plex Mono',monospace !important;
    text-transform: uppercase !important; letter-spacing: 0.07em !important;
    padding: 10px 4px !important;
    transition: all 0.15s !important;
}
div[data-testid="stHorizontalBlock"]:has(.nav-tab-btn) button:hover {
    color: #3C3C3C !important;
    background: #F4F3F0 !important;
}
div.active-nav-tab button {
    color: #EA6100 !important;
    border-bottom: 2px solid #EA6100 !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

_nav_cols = st.columns(len(_NAV_TABS))
for _nc, _nt in zip(_nav_cols, _NAV_TABS):
    _is_active = st.session_state.active_tab == _nt
    with _nc:
        if _is_active:
            st.markdown("<div class='nav-tab-btn active-nav-tab'>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='nav-tab-btn'>", unsafe_allow_html=True)
        if st.button(_nt, key=f"nav_{_nt}", use_container_width=True):
            st.session_state.active_tab = _nt
        st.markdown("</div>", unsafe_allow_html=True)

_active_view = st.session_state.active_tab

if _active_view == "Insights":
    render_insights(master_scoped, df_raw_scoped, all_5q)

elif _active_view == _dash_label:
    # Data quality banner
    if len(all_5q) < 5:
        st.warning(
            f"Only **{len(all_5q)} quarter(s)** found in basedata ({', '.join(all_5q)}). "
            "Upload the full 5-quarter history (≈50 MB) for complete Segment/ABC/XYZ analysis."
        )

    _region_label = sb_region if sb_region and sb_region != "All" else "All Regions"
    scope_label = f"{user_country or user_rsm or _region_label}"
    render_kpi_dashboard(master_scoped, scope_label, all_5q, df_raw_scoped)

    if role == "admin":
        with st.expander("📝 Override Audit Log", expanded=False):
            audit = get_override_log()
            if audit:
                audit_df = pd.DataFrame(audit)
                audit_df["at"] = pd.to_datetime(audit_df["at"]).dt.strftime("%d %b %H:%M")
                audit_df = audit_df.rename(columns={
                    "join_key": "Installer", "field": "Field",
                    "old": "Old", "new": "New", "by": "By", "at": "When"
                })
                st.dataframe(audit_df[["Installer", "Field", "Old", "New", "By", "When"]],
                             use_container_width=True, hide_index=True)
            else:
                st.caption("No overrides recorded yet.")

elif _active_view == "Installers List":
    render_device_view(
        df_raw_scoped, master_scoped, weekly_pivot, all_5q,
        role, username, user_country, user_rsm
    )

elif _active_view == "All Devices":
    render_installer_list(
        master_scoped, weekly_pivot, df_raw_scoped, all_5q,
        role, username, user_country, user_rsm
    )

elif _active_view == "Summary":
    render_summary(df_raw_scoped, master_scoped, all_5q, role, user_country, user_rsm)

elif _active_view == "Inbox":
    render_inbox(master_scoped, role, username, user_rsm, user_country)

# ── Chatbot assistant (always visible at the bottom) ───────────────────────────
render_chatbot(master=master_scoped)


