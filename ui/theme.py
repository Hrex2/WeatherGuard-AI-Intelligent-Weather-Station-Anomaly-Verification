"""WeatherGuard dark scientific observatory theme."""
import streamlit as st
from html import escape


def apply_theme():
    st.markdown("""
    <style>
    :root { --wg-bg:#101827; --wg-surface:#172235; --wg-raised:#1E293B;
            --wg-cyan:#38BDF8; --wg-teal:#2DD4BF; --wg-amber:#FBBF24;
            --wg-red:#F87171; --wg-text:#E5EDF7; --wg-muted:#94A3B8; }
    .stApp { background:radial-gradient(ellipse at 84% -10%, #1b2b42 0%, #101827 48%); color:var(--wg-text); }
    [data-testid="stSidebar"] { background:#111c2e; border-right:1px solid #26384e; }
    [data-testid="stHeader"] { background:rgba(16,24,39,.78); }
    [data-testid="stAppViewContainer"] > .main .block-container { max-width:1800px; padding-top:1.15rem; padding-bottom:5.5rem; }
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
    .wg-brand { display:flex; align-items:center; gap:10px; color:#f1f5f9; font-weight:800; font-size:1.05rem; letter-spacing:-.02em; padding:.35rem 0; }
    .wg-brand-mark { display:inline-flex; width:31px; height:31px; align-items:center; justify-content:center; border-radius:10px; color:#082f49; background:#38bdf8; font-size:1.1rem; box-shadow:0 0 18px rgba(56,189,248,.2); }
    .wg-home-title { margin:.12rem 0 .1rem 0; font-size:2rem; letter-spacing:-.04em; }
    .wg-reading-row { display:flex; flex-direction:column; gap:1px; border-bottom:1px solid #29384d; padding:8px 0; }
    .wg-reading-row span { color:#94a3b8; font-size:.75rem; text-transform:uppercase; letter-spacing:.06em; }
    .wg-reading-row strong { font-size:.95rem; font-variant-numeric:tabular-nums; }
    .wg-candidate-note { background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.35); color:#fecaca; padding:8px 10px; border-radius:9px; font-size:.8rem; margin:.25rem 0 .45rem; }
    .wg-upload-nudge { position:fixed; bottom:0; left:0; right:0; z-index:700; pointer-events:none; display:flex; justify-content:center; padding:7px 12px; background:linear-gradient(180deg,rgba(16,24,39,0),rgba(16,24,39,.96) 35%); }
    .wg-upload-nudge span { pointer-events:auto; border:1px solid #31516a; border-radius:999px; padding:7px 15px; color:#dbeafe; background:#172438; box-shadow:0 8px 28px rgba(0,0,0,.3); font-size:.78rem; }
    div[data-testid="stRadio"] > label { display:none; }
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap:.35rem; flex-wrap:wrap; }
    div[data-testid="stRadio"] > div[role="radiogroup"] label { border:1px solid #2a3b51; border-radius:9px; padding:.32rem .72rem; background:#172235; color:#cbd5e1; transition:all .16s ease; }
    div[data-testid="stRadio"] > div[role="radiogroup"] label:has(input:checked) { border-color:#38bdf8; background:#123047; color:#f0f9ff; }
    div.st-key-wg_persistent_upload_action { position:fixed; bottom:1.1rem; right:1.2rem; z-index:800; width:auto; }
    div.st-key-wg_persistent_upload_action button { border-radius:999px; box-shadow:0 8px 28px rgba(0,0,0,.35); background:#0e7490; color:white; border:1px solid #38bdf8; padding:.58rem 1rem; }
    div.st-key-wg_persistent_upload_action button:hover { background:#155e75; border-color:#7dd3fc; }
    @media (max-width:1100px) { .wg-reading-row strong { font-size:.88rem; } }
    @media (max-width:760px) {
      [data-testid="stAppViewContainer"] > .main .block-container { padding-left:.75rem; padding-right:.75rem; padding-top:.7rem; }
      .wg-home-title { font-size:1.6rem; }
      div[data-testid="stRadio"] > div[role="radiogroup"] { justify-content:center; }
      div.st-key-wg_persistent_upload_action { right:.65rem; bottom:.65rem; }
    }
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
