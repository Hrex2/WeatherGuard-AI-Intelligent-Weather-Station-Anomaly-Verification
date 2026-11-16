"""WeatherGuard dark scientific observatory theme."""
import streamlit as st
from html import escape


def apply_theme():
    st.markdown("""
    <style>
    :root { --wg-bg:#0B1220; --wg-surface:#111C2E; --wg-raised:#172438;
            --wg-cyan:#38BDF8; --wg-teal:#2DD4BF; --wg-amber:#FBBF24;
            --wg-red:#F87171; --wg-text:#E5EDF7; --wg-muted:#94A3B8; }
    .stApp { background: radial-gradient(ellipse at 88% 0%, #16263b 0%, #0B1220 45%); color:var(--wg-text); }
    [data-testid="stSidebar"] { background:#0c1727; border-right:1px solid #24354c; }
    [data-testid="stHeader"] { background:rgba(11,18,32,.72); }
    h1,h2,h3 { letter-spacing:-.025em; color:#f1f6fd; }
    .wg-eyebrow { color:#67d7df; font-size:.72rem; text-transform:uppercase; letter-spacing:.17em; font-weight:700; }
    .wg-subtitle { color:#9fb1c8; font-size:1.03rem; margin-top:-.45rem; }
    .wg-card { background:linear-gradient(145deg,#172438,#111c2e); border:1px solid #263b55; border-radius:14px; padding:18px 20px; min-height:112px; box-shadow:0 8px 28px rgba(0,0,0,.16); }
    .wg-card-label { color:#91a4bc; font-size:.78rem; text-transform:uppercase; letter-spacing:.09em; }
    .wg-card-value { color:#edf7ff; font-size:1.8rem; line-height:1.35; font-weight:700; font-variant-numeric:tabular-nums; }
    .wg-card-note { color:#88a0b9; font-size:.76rem; }
    .wg-pill { display:inline-block; border:1px solid #31516a; border-radius:99px; padding:4px 10px; color:#b8dbea; background:#10293a; font-size:.76rem; }
    .wg-panel { background:#111c2e; border:1px solid #283a51; border-left:4px solid #475569; border-radius:12px; padding:15px 18px; margin:.5rem 0 .8rem 0; }
    .wg-panel.support { border-left-color:#2dd4bf; }
    .wg-panel.conflict { border-left-color:#fbbf24; }
    .wg-panel.unavailable { border-left-color:#64748b; }
    .wg-panel.none { border-left-color:#38bdf8; }
    .wg-muted { color:#94a3b8; }
    div[data-testid="stMetric"] { background:linear-gradient(145deg,#172438,#111c2e); border:1px solid #263b55; border-radius:14px; padding:12px 16px; }
    div[data-testid="stMetricValue"] { font-variant-numeric:tabular-nums; }
    .stButton > button { border-radius:9px; border:1px solid #287b91; background:#103145; color:#d7f4ff; }
    .stButton > button:hover { border-color:#38bdf8; color:white; }
    [data-testid="stDataFrame"] { border:1px solid #263b55; border-radius:10px; overflow:hidden; }
    hr { border-color:#26384e; }
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, note=""):
    st.markdown(f"<div class='wg-card'><div class='wg-card-label'>{escape(str(label))}</div><div class='wg-card-value'>{escape(str(value))}</div><div class='wg-card-note'>{escape(str(note))}</div></div>", unsafe_allow_html=True)


def evidence_panel(title, state, details):
    kind = ("support" if state == "SUPPORTING_EVIDENCE" else
            "conflict" if state == "CONFLICTING_EVIDENCE" else
            "none" if state == "NO_DETECTED_EVIDENCE" else "unavailable")
    label = state.replace("_", " ").title()
    st.markdown(f"<div class='wg-panel {kind}'><b>{escape(str(title))}</b><br><span class='wg-pill'>{escape(label)}</span><p class='wg-muted' style='margin:.65rem 0 0'>{escape(str(details))}</p></div>", unsafe_allow_html=True)
