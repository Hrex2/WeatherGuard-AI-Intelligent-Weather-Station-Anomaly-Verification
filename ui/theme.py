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
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color:#e5edf7 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color:#b8c7d9 !important; }
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
    .wg-reading-title { font-family: Georgia, 'Times New Roman', serif; font-size:1.14rem; line-height:1.8; color:#dce7f3; }
    .wg-section-nav { position:sticky; top:1rem; }
    .wg-reading-row { display:flex; flex-direction:column; gap:1px; border-bottom:1px solid #29384d; padding:8px 0; }
    .wg-reading-row span { color:#94a3b8; font-size:.75rem; text-transform:uppercase; letter-spacing:.06em; }
    .wg-reading-row strong { font-size:.95rem; font-variant-numeric:tabular-nums; }
    .wg-candidate-note { background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.35); color:#fecaca; padding:8px 10px; border-radius:9px; font-size:.8rem; margin:.25rem 0 .45rem; }
    .wg-workflow-step { display:flex; gap:.8rem; align-items:flex-start; margin:.15rem 0 .55rem; }
    .wg-step-number { flex:0 0 2rem; height:2rem; display:flex; align-items:center; justify-content:center; border-radius:10px; background:#123047; border:1px solid #287b91; color:#a5f3fc; font-weight:800; font-size:.88rem; }
    .wg-step-copy { min-width:0; }
    .wg-step-title { color:#f1f6fd; font-size:1.08rem; font-weight:700; line-height:1.3; }
    .wg-step-caption { color:#94a3b8; font-size:.83rem; margin-top:.2rem; }
    .wg-observation-banner { border:1px solid #31516a; border-radius:12px; background:linear-gradient(110deg,#14283d,#111c2e); padding:14px 16px; margin:.5rem 0 .8rem; }
    .wg-observation-time { color:#f1f6fd; font-size:1.24rem; font-weight:750; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }
    .wg-observation-status { color:#fbbf24; font-size:.82rem; font-weight:700; margin-top:.35rem; }
    .wg-interpretation { border:1px solid #3b5268; border-left:5px solid #fbbf24; border-radius:12px; background:#121f30; padding:16px 18px; margin:.5rem 0 .8rem; }
    .wg-upload-nudge { position:fixed; bottom:0; left:0; right:0; z-index:700; pointer-events:none; display:flex; justify-content:center; padding:7px 12px; background:linear-gradient(180deg,rgba(16,24,39,0),rgba(16,24,39,.96) 35%); }
    .wg-upload-nudge span { pointer-events:auto; border:1px solid #31516a; border-radius:999px; padding:7px 15px; color:#dbeafe; background:#172438; box-shadow:0 8px 28px rgba(0,0,0,.3); font-size:.78rem; }
    div[data-testid="stRadio"] > label { display:none; }
    div[data-testid="stRadio"] > div[role="radiogroup"] { gap:.35rem; flex-wrap:wrap; }
    div[data-testid="stRadio"] > div[role="radiogroup"] label { border:1px solid #2a3b51; border-radius:9px; padding:.32rem .72rem; background:#172235; color:#dbe7f3 !important; transition:all .16s ease; }
    div[data-testid="stRadio"] > div[role="radiogroup"] label p { color:#dbe7f3 !important; opacity:1 !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] label:has(input:checked) { border-color:#38bdf8; background:#123047; color:#f0f9ff !important; }
    div[data-testid="stRadio"] > div[role="radiogroup"] label:has(input:checked) p { color:#f0f9ff !important; }
    :where(button, a, input, select, textarea, [role="button"], [role="radio"], [role="tab"], [role="slider"], [tabindex]):focus-visible {
      outline:3px solid #67e8f9 !important; outline-offset:3px !important; box-shadow:0 0 0 2px #101827 !important;
    }
    div[data-testid="stRadio"] label:has(input:focus-visible) {
      outline:3px solid #67e8f9 !important; outline-offset:2px !important; border-color:#67e8f9 !important;
    }
    div.st-key-model_section_navigation div[role="radiogroup"],
    div.st-key-research_section_navigation div[role="radiogroup"],
    div.st-key-experiment_section_navigation div[role="radiogroup"] { flex-direction:column; flex-wrap:nowrap; align-items:stretch; }
    div.st-key-model_section_navigation div[role="radiogroup"] label,
    div.st-key-research_section_navigation div[role="radiogroup"] label,
    div.st-key-experiment_section_navigation div[role="radiogroup"] label { width:100%; justify-content:flex-start; margin:0; }
    div.st-key-model_section_navigation div[role="radiogroup"] label p,
    div.st-key-research_section_navigation div[role="radiogroup"] label p,
    div.st-key-experiment_section_navigation div[role="radiogroup"] label p { font-size:.83rem; }
    div.st-key-wg_persistent_upload_action { position:fixed; bottom:1.1rem; right:1.2rem; z-index:800; width:auto; }
    div.st-key-wg_persistent_upload_action button { border-radius:999px; box-shadow:0 8px 28px rgba(0,0,0,.35); background:#0e7490; color:white; border:1px solid #38bdf8; padding:.58rem 1rem; }
    div.st-key-wg_persistent_upload_action button:hover { background:#155e75; border-color:#7dd3fc; }
    .stApp [data-testid="stCaptionContainer"] p { color:#a9bbcf !important; }
    .stApp [data-testid="stWidgetLabel"] p { color:#b8c7d9 !important; }
    .stApp [data-testid="stMetricLabel"] p { color:#a9bbcf !important; }
    .stApp [data-testid="stMetricValue"] div { color:#f1f5f9 !important; }
    .stApp [data-testid="stMetricDelta"] { color:#cbd5e1 !important; }
    .stApp [data-testid="stAlertContentInfo"] p { color:#dbeafe !important; }
    .stApp [data-testid="stAlertContentWarning"] p { color:#fde68a !important; }
    .stApp [data-testid="stAlertContentError"] p { color:#fecaca !important; }
    .stApp [data-testid="stAlertContentSuccess"] p { color:#bbf7d0 !important; }
    .stApp [data-testid="stAlertContainer"] { border:1px solid #31465e; border-radius:10px; }
    .stApp [data-testid="stExpander"] summary { background:#172235 !important; border:1px solid #2a3b51 !important; border-radius:9px; color:#dbe7f3 !important; }
    .stApp [data-testid="stExpander"] summary p { color:#dbe7f3 !important; }
    .stApp [data-testid="stDateInput"] input,
    .stApp [data-testid="stTextInput"] input,
    .stApp [data-testid="stNumberInput"] input { background:#172235 !important; border-color:#38516b !important; color:#e5edf7 !important; }
    .stApp [data-baseweb="select"] > div { background:#172235 !important; border-color:#38516b !important; color:#e5edf7 !important; }
    .stApp [data-baseweb="select"] input { color:#e5edf7 !important; }
    .stApp [data-baseweb="tag"] { background:#123047 !important; border:1px solid #31516a !important; color:#e5edf7 !important; }
    @media (max-width:1100px) {
      .wg-reading-row strong { font-size:.88rem; }
      [data-testid="stHorizontalBlock"] { flex-direction:column !important; align-items:stretch; }
      [data-testid="stColumn"] { width:100% !important; flex:1 1 100% !important; }
      div.st-key-wg_persistent_upload_action { position:static; width:100%; display:flex; justify-content:flex-end; margin-top:.5rem; }
      div.st-key-wg_persistent_upload_action button { box-shadow:none; }
    }
    @media (max-width:760px) {
      [data-testid="stAppViewContainer"] > .main .block-container { padding-left:.75rem; padding-right:.75rem; padding-top:.7rem; }
      .wg-home-title { font-size:1.6rem; }
      div[data-testid="stRadio"] > div[role="radiogroup"] { justify-content:center; }
      .wg-section-nav { position:static; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { scroll-behavior:auto !important; animation-duration:.01ms !important; animation-iteration-count:1 !important; transition-duration:.01ms !important; }
    }
    div[data-testid="stMetric"] { background:linear-gradient(145deg,#172438,#111c2e); border:1px solid #263b55; border-radius:14px; padding:12px 16px; }
    div[data-testid="stMetricValue"] { font-variant-numeric:tabular-nums; }
    .stApp [data-testid="stButton"] button { border-radius:9px !important; border:1px solid #287b91 !important; background:#103145 !important; color:#d7f4ff !important; }
    .stApp [data-testid="stButton"] button:hover { border-color:#38bdf8 !important; color:white !important; }
    [data-testid="stDataFrame"] { border:1px solid #263b55; border-radius:10px; overflow:hidden; }
    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] { min-width:0; max-width:100%; }
    hr { border-color:#26384e; }
    </style>
    """, unsafe_allow_html=True)


def metric_card(label, value, note=""):
    st.markdown(f"<div class='wg-card'><div class='wg-card-label'>{escape(str(label))}</div><div class='wg-card-value'>{escape(str(value))}</div><div class='wg-card-note'>{escape(str(note))}</div></div>", unsafe_allow_html=True)


def evidence_panel(title, state, details):
    kind = ("support" if state == "SUPPORTING_EVIDENCE" else
            "conflict" if state == "CONFLICTING_EVIDENCE" else
            "none" if state == "NO_DETECTED_EVIDENCE" else "unavailable")
    label = {
        "SUPPORTING_EVIDENCE": "Supporting",
        "CONFLICTING_EVIDENCE": "Conflicting",
        "NO_DETECTED_EVIDENCE": "No detected evidence",
        "UNAVAILABLE": "Unavailable",
    }.get(state, state.replace("_", " ").title())
    st.markdown(f"<div class='wg-panel {kind}'><b>{escape(str(title))}</b><br><span class='wg-pill'>{escape(label)}</span><p class='wg-muted' style='margin:.65rem 0 0'>{escape(str(details))}</p></div>", unsafe_allow_html=True)
