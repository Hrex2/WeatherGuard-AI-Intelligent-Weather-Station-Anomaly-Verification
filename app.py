"""WeatherGuard AI: research dataset, investigation, experiments, and literature."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.data_service import load_project_data
from services.model_service import run_saved_protocol
from services.evidence_service import observation_evidence
from services.model_metadata import build_model_education
from services.research_artifact_integrity import multicontext_artifact_state
from ui.investigation_workspace import render_investigation_workspace
from ui.new_csv_analysis import render_new_csv_analysis
from ui.home_dashboard import render_home_dashboard
from ui.station_map import render_station_map
from ui.theme import apply_theme, metric_card, evidence_panel
from ui.model_workspace import render_model_workspace
from ui.research_workspace import render_research_workspace
from ui.experiment_workspace import render_experiment_workspace
from ui.chart_theme import style_chart

st.set_page_config(page_title="WeatherGuard AI", page_icon="🌦️", layout="wide", initial_sidebar_state="auto")
apply_theme()


@st.cache_data(show_spinner="Loading verified research artifacts…", ttl=600)
def _load_data(root_text):
    return load_project_data(Path(root_text))


def _plot_layout(fig, height=350):
    return style_chart(fig, height)


def _fmt_ts(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M %Z")


def _source_note():
    st.caption("Historical processed research snapshot • not a live feed • timezone Asia/Kolkata")


def render_header(kicker, title, subtitle):
    st.markdown(f"<div class='wg-eyebrow'>{kicker}</div>", unsafe_allow_html=True)
    st.title(title)
    st.markdown(f"<div class='wg-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")


@st.dialog("Experiment with your data", width="large")
def render_upload_dialog(root):
    render_new_csv_analysis(root)


def render_about():
    render_header("WeatherGuard AI / project", "About", "A research prototype for reviewing unusual historical weather-station readings.")
    st.markdown("""
    WeatherGuard AI combines saved model outputs with temporal, spatial, and physical evidence to help people investigate unusual weather observations.

    **Research boundary:** model agreement identifies candidates; it does not confirm sensor failure. The project’s E3 spatial evidence remains descriptive because independent station lineage and event adjudication are insufficient.
    """)
    st.info("This application is a historical research prototype, not a live monitoring or maintenance system.")
    st.caption("Project team and contact information are not specified in the repository.")


def render_home(data, manifest, hashes):
    obs = data["observations"]
    stability = data["stability"].set_index("timestamp").sort_index()
    predictions = data["predictions"]
    candidate = stability.loc[stability.configuration_votes.ge(8)]
    render_header("WeatherGuard AI", "Home", "Understand unusual historical readings and the evidence available to investigate them.")
    st.markdown("WeatherGuard AI examines historical weather-station readings, identifies unusual observations and gathers available evidence to help investigate whether a reading represents unusual weather or a possible measurement problem.")
    _source_note()
    meta = st.columns([1.4, 1, 1, 1])
    with meta[0]:
        st.markdown("### VILD0 · Ludhiana/Doraha")
        st.caption("Punjab, India · primary station · source acquisition provenance not bundled")
    with meta[1]:
        st.markdown("**Analysis period**")
        st.caption(f"{_fmt_ts(obs.index.min())} → {_fmt_ts(obs.index.max())}")
    with meta[2]:
        st.markdown("**Prediction provenance**")
        st.caption("Saved Phase 03 historical predictions")
    with meta[3]:
        st.markdown("**Dataset integrity**")
        st.caption("Manifest hashes match · processed snapshot")
    st.caption("Measurements available: air temperature, dew point, relative humidity, precipitation, wind speed and air pressure.")
    st.divider()
    metrics = st.columns(4)
    with metrics[0]: st.metric("Historical readings", f"{len(obs):,}", help="Processed observations in the saved historical snapshot.")
    with metrics[1]: st.metric("Model configurations", f"{data['predictions'].configuration.nunique()}", help="Four settings each for three unsupervised model families.")
    with metrics[2]: st.metric("Readings flagged by 8/12 or more", f"{len(candidate):,}", help="This is a configured consensus threshold, not a fault probability.")
    with metrics[3]: st.metric("Research status", "Prototype", help="Real fault labels and a validated combined evidence rule are not available.")
    st.info("A model flag means ‘unusual compared with patterns the model learned.’ It does not confirm a broken sensor or explain the weather event.")
    st.write("")
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Explore a weather measurement")
        st.caption("Processed station observations, with 8/12 consensus candidates marked. Explore other variables and dates in Weather Data.")
        variable_labels = {"temp": "Air temperature (°C)", "dwpt": "Dew point (°C)", "rhum": "Relative humidity (%)", "prcp": "Precipitation (mm)", "wspd": "Wind speed (km/h)", "pres": "Air pressure (hPa)"}
        variable = st.selectbox("Weather measurement", list(variable_labels), format_func=lambda key: variable_labels[key], key="command_variable")
        series = obs[variable].dropna()
        if len(series) > 6000:
            series = series.iloc[:: max(1, len(series) // 6000)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=variable, line={"color":"#38BDF8","width":1.5}))
        if len(candidate):
            candidate_times = candidate.index.intersection(obs.index)
            fig.add_trace(go.Scatter(x=candidate_times, y=obs.loc[candidate_times, variable], mode="markers", name="8/12 candidate", marker={"color":"#FBBF24","size":7,"symbol":"diamond"}))
        fig.update_layout(title=variable_labels[variable], xaxis_title="Historical time", yaxis_title=variable_labels[variable])
        st.plotly_chart(_plot_layout(fig, 390), width="stretch")
    with right:
        st.subheader("How often did configurations flag readings?")
        counts = data["configuration_results"].sort_values("anomalies")
        fig = px.bar(counts, x="anomalies", y="configuration", orientation="h", color="family",
                     color_discrete_sequence=["#38BDF8", "#2DD4BF", "#A78BFA"])
        st.plotly_chart(_plot_layout(fig, 390), width="stretch")
    st.subheader("Recent unusual readings for investigation")
    recent = candidate.tail(12).reset_index().rename(columns={"index":"timestamp"})
    if len(recent):
        recent = recent[["timestamp", "configuration_votes"]].rename(columns={"timestamp": "Historical time", "configuration_votes": "Configurations agreeing (of 12)"})
        st.dataframe(recent.sort_values("Historical time", ascending=False), hide_index=True, width="stretch")
    else:
        st.info("No saved rows meet the 8/12 candidate threshold.")
    with st.expander("Station geography"):
        render_station_map(ROOT, "VILD0")
    with st.expander("Dataset and prediction verification details"):
        st.json({"phase01_manifest_audit_passed": manifest.get("audit_passed"), "sha256": hashes,
                 "saved_prediction_rows": len(predictions), "unique_timestamps": predictions.timestamp.nunique(),
                 "configurations": predictions.configuration.nunique()})


def render_weather_data(data):
    obs = data["observations"]
    stability = data["stability"].set_index("timestamp").sort_index()
    render_header("WeatherGuard AI / historical data", "Weather Data", "Explore the measurements behind the saved analysis.")
    st.info("This is a historical processed research snapshot, not a live sensor feed. Times are shown in Asia/Kolkata.")
    labels = {"temp": ("Air temperature", "°C"), "dwpt": ("Dew point", "°C"),
              "rhum": ("Relative humidity", "%"), "prcp": ("Rainfall / precipitation", "mm"),
              "wspd": ("Wind speed", "km/h"), "pres": ("Air pressure", "hPa")}
    controls = st.columns([1.2, 1])
    with controls[0]:
        variable = st.selectbox("Weather measurement", list(labels), format_func=lambda key: labels[key][0], key="weather_data_variable")
    start, end = obs.index.min().date(), obs.index.max().date()
    with controls[1]:
        dates = st.date_input("Date range", value=(max(start, end.replace(year=end.year - 1)), end), min_value=start, max_value=end, key="weather_data_dates")
    if isinstance(dates, tuple) and len(dates) == 2:
        lo = pd.Timestamp(dates[0]).tz_localize(str(obs.index.tz))
        hi = (pd.Timestamp(dates[1]) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)).tz_localize(str(obs.index.tz))
        view = obs.loc[(obs.index >= lo) & (obs.index <= hi)]
    else:
        view = obs
    series = view[variable].dropna()
    if len(series) > 9000:
        series = series.iloc[::max(1, len(series) // 9000)]
    selected = st.session_state.get("selected_observation")
    if isinstance(dates, tuple) and len(dates) == 2:
        candidate_index = stability.index[(stability.index >= lo) & (stability.index <= hi)
                                          & stability.configuration_votes.ge(8)]
    else:
        candidate_index = stability.index[stability.configuration_votes.ge(8)]
    candidate_times = candidate_index.intersection(series.index)
    summary = st.columns(3)
    summary[0].metric("Historical rows in range", f"{len(view):,}")
    summary[1].metric("8/12 candidates in range", f"{len(candidate_times):,}",
                      help="Saved model agreement is a review marker, not a fault label.")
    selected_value = series.get(pd.Timestamp(selected)) if selected is not None and pd.Timestamp(selected) in series.index else None
    summary[2].metric("Selected reading", f"{selected_value:.2f} {labels[variable][1]}" if selected_value is not None else "Outside range / unavailable",
                      help="The selected timestamp is shared with Home and Investigate a Reading.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=labels[variable][0],
                             line={"color": "#38BDF8", "width": 1.4},
                             hovertemplate="%{x|%Y-%m-%d %H:%M}<br>%{y:.2f} " + labels[variable][1] + "<extra></extra>"))
    if len(candidate_times):
        fig.add_trace(go.Scatter(x=candidate_times, y=series.loc[candidate_times], mode="markers", name="8/12 model agreement",
                                 marker={"color": "#FBBF24", "size": 7, "symbol": "diamond"}))
    if selected is not None and pd.Timestamp(selected) in series.index:
        selected = pd.Timestamp(selected)
        fig.add_trace(go.Scatter(x=[selected], y=[series.loc[selected]], mode="markers", name="Selected reading",
                                 marker={"color": "#F87171", "size": 11, "symbol": "x"}))
    fig.update_layout(title=f"{labels[variable][0]} over time", xaxis_title="Historical time", yaxis_title=f"{labels[variable][0]} ({labels[variable][1]})")
    if series.empty:
        st.info("No non-missing measurements are available for this variable and date range.")
    st.plotly_chart(_plot_layout(fig, 430), width="stretch")
    st.caption(f"Showing {len(view):,} historical rows; {int(view[variable].isna().sum()):,} missing values for {labels[variable][0].lower()} in this range. Gold markers indicate model agreement, not confirmed faults.")
    with st.expander("View measurement rows"):
        st.dataframe(view[[variable]].rename(columns={variable: f"{labels[variable][0]} ({labels[variable][1]})"}), width="stretch")
    with st.expander("New Data Analysis · validate and analyze a station CSV"):
        render_new_csv_analysis(ROOT)


def render_research(data):
    render_header("WeatherGuard AI / research", "Research", "Explore the research question, methods, evidence, findings and limitations behind the prototype.")
    tabs = st.tabs(["Overview", "Literature review", "Research gap & contribution", "Method & results", "References"])
    with tabs[0]:
        st.subheader("Uncertainty-aware event-level verification")
        st.write("Unsupervised models can flag observations that differ from learned patterns. That alone cannot establish whether a reading represents unusual weather, a station-specific observation problem, or insufficient evidence. WeatherGuard preserves these possibilities and separates model flags from interpretation.")
        st.markdown("**Research question**  \nCan model-configuration stability, temporal event consistency, neighboring-station observations, and physical sensor-quality checks help distinguish unusual regional weather from suspicious station observations while explicitly representing missing or conflicting evidence?")
        st.markdown("**Working interpretation**")
        st.markdown("1. Regionally supported unusual event  \n2. Station-specific suspicious observation  \n3. Uncertain or insufficient evidence")
        st.warning("No verified real-observation fault labels are included. The three-way system is a research target; current saved candidates are not adjudicated outcomes.")
        st.subheader("Research objectives")
        st.markdown("- Preserve a reproducible 11-feature chronological baseline and examine stability across 12 model configurations.\n- Group consensus timestamps into segment-aware temporal episodes.\n- Compare candidates with available neighboring-station observations while retaining coverage limits.\n- Combine model, temporal, spatial, and physical screening evidence without converting missingness into negative evidence.")
    with tabs[1]:
        papers = json.loads((ROOT / "research_content" / "literature.json").read_text(encoding="utf-8"))
        for paper in papers:
            with st.expander(f"{paper['year']} · {paper['title']}", expanded=False):
                st.markdown(f"**Authors:** {paper['authors']}  \n**Publication:** {paper['venue']}  \n**DOI:** [{paper['doi']}]({paper['url']})")
                st.markdown(f"**Objective.** {paper['objective']}  \n**Data and method.** {paper['data_and_method']}  \n**Reported contribution.** {paper['findings']}  \n**Limitations.** {paper['limitations']}  \n**Relevance here.** {paper['relevance']}")
        matrix = pd.DataFrame([{"Study": str(p["year"]) + " · " + p["authors"].split(",")[0], **p["matrix"]} for p in papers])
        st.subheader("Literature comparison matrix")
        st.caption("A check indicates the article addresses the topic described in its verified scope; it does not mean the methods or outcomes match this project.")
        st.dataframe(matrix, hide_index=True, width="stretch")
    with tabs[2]:
        st.subheader("Evidence-grounded research gap")
        st.write("The cited meteorological QA literature establishes range, persistence, temporal, internal, spatial, metadata, and workflow checks. The literature review also includes a weather-station information-quality model using certainty factors. These studies have distinct goals and settings; they do not establish that the current project is novel or superior.")
        st.write("The project-specific question is narrower: how to present an unsupervised model flag alongside temporal, spatial, and physical evidence when no real fault labels exist and some evidence is unavailable. The current implementation is incomplete, so this is a research direction rather than a demonstrated contribution.")
        st.markdown("**Implemented in the repository:** saved 12-configuration predictions; 8/12 consensus table; one-hour episode profiles; exploratory spatial comparison tables; broad physical screening; a controlled temperature point-spike campaign.  \n**Still proposed or incomplete:** full E1–E4 evidence states, verified neighbor provenance, other synthetic fault groups, ablation, and calibrated or validated outcome logic.")
    with tabs[3]:
        steps = [
            ("Data and integrity", "Processed Phase 01 snapshots; hashes checked against the included manifest.", "verified_phase01 / audit.py"),
            ("Feature pipeline", "Historical grouped previous-row difference and shifted previous-six-observation rolling features.", "features.py / audit.py"),
            ("Seasonal model matrix", "Six weather variables, three temperature history features, month sine and cosine.", "11 ordered features"),
            ("Model stability", "Four Isolation Forest, four LOF, and four One-Class SVM configurations.", "models.py / Phase 03 outputs"),
            ("Temporal episodes", "One-hour primary candidate gap; continuous segment membership.", "temporal.py / 81 saved episodes"),
            ("Spatial and physical evidence", "Descriptive neighbor comparisons and broad screening; coverage/provenance incomplete.", "spatial.py / quality.py"),
            ("Interpretation", "Abstaining three-way scaffold; not calibrated or end-to-end validated.", "evidence.py"),
        ]
        for title, body, code in steps:
            with st.expander(title):
                st.write(body)
                st.code(code, language="text")
        st.subheader("Saved project results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Prediction cells", f"{len(data['predictions']):,}")
        c2.metric("8/12 candidates", f"{int(data['stability'].configuration_votes.ge(8).sum()):,}")
        c3.metric("One-hour episodes", f"{len(data['episodes']):,}")
        st.info("These are saved historical project artifacts. They were not regenerated by opening this page.")
    with tabs[4]:
        papers = json.loads((ROOT / "research_content" / "literature.json").read_text(encoding="utf-8"))
        for p in papers:
            st.markdown(f"- {p['authors']} ({p['year']}). *{p['title']}*. {p['venue']}. [DOI: {p['doi']}]({p['url']})")
        st.caption("Bibliographic metadata and summaries were checked against publisher pages or institutional research records. Full-text access was not available for every paper during this build.")


def render_investigation(data, root):
    render_investigation_workspace(data, root)


def render_synthetic_experiments(root, data, phase01_hashes):
    render_header("WeatherGuard AI  /  experiments", "Synthetic Campaigns", "Review saved controlled injection results and their limits.")
    st.warning("SIMULATED DATA — NOT REAL-WORLD FAULT VALIDATION. Synthetic results test detector behavior on declared injections; they do not estimate field accuracy or diagnose hardware.")
    matrix_dir = root / "research_results" / "fault_matrix_02bd147f5cce"
    matrix_manifest_path = matrix_dir / "run_metadata.json"
    if matrix_manifest_path.is_file():
        try:
            matrix_manifest = json.loads(matrix_manifest_path.read_text(encoding="utf-8"))
            matrix_hashes = matrix_manifest.get("dataset_hashes", {})
            matrix_verified = (
                matrix_manifest.get("phase01_audit_passed") is True
                and matrix_hashes.get("model_df") == phase01_hashes.get("observations")
                and matrix_hashes.get("X_train_multi") == phase01_hashes.get("train")
                and matrix_hashes.get("X_test_multi") == phase01_hashes.get("test")
            )
        except (OSError, json.JSONDecodeError):
            matrix_verified = False
            matrix_manifest = {}
        st.subheader("Saved eight-scenario fault matrix · one held-out context")
        if matrix_verified:
            summary_path = matrix_dir / "scenario_summary.csv"
            family_path = matrix_dir / "family_scenario_summary.csv"
            if summary_path.is_file():
                st.dataframe(pd.read_csv(summary_path), hide_index=True, width="stretch")
            if family_path.is_file():
                with st.expander("Model-family response"):
                    st.dataframe(pd.read_csv(family_path), hide_index=True, width="stretch")
            with st.expander("Injection values and experiment provenance"):
                registry_path = matrix_dir / "injection_registry.csv"
                if registry_path.is_file():
                    st.dataframe(pd.read_csv(registry_path), hide_index=True, width="stretch")
                st.json(matrix_manifest)
            st.caption("The original campaign remains in a separate section below. The matrix is a single-context synthetic study; VILD0 is an unverified inherited dataset label.")
        else:
            st.warning("The saved fault matrix is unavailable or its dataset hashes do not match the verified Phase 01 snapshots.")
    else:
        st.info("The eight-scenario matrix has not been added to this checkout.")
    multicontext_dir = root / "research_results" / "fault_matrix_multicontext_46ae5d119d"
    multicontext_manifest_path = multicontext_dir / "campaign_manifest.json"
    if multicontext_manifest_path.is_file():
        artifact_state = multicontext_artifact_state(root, phase01_hashes)
        st.subheader("Five-context synthetic fault study")
        if artifact_state["verified"]:
            bundle = artifact_state["bundle"]
            multicontext_manifest = bundle["campaign"]
            e2_manifest = bundle["e2_manifest"]
            e2_outputs = bundle["e2_outputs"]
            baseline_outputs = bundle["baseline_outputs"]
            st.dataframe(bundle["context_summary"], hide_index=True, width="stretch")
            with st.expander("Model-family response by context"):
                st.dataframe(bundle["family_context_summary"], hide_index=True, width="stretch")
            st.caption("Five preselected synthetic contexts share the same fitted models. Metrics describe responses to known injections; they are not field accuracy or sensor-fault diagnoses.")
            st.markdown("**Independent temporal-screen comparison · exploratory synthetic E2**")
            paired = e2_outputs["e2_multicontext_fault_paired.csv"]
            e2_by_fault = paired.groupby("experiment_id").agg(
                comparisons=("pair_id", "size"),
                status_changes=("status_changed_by_injection", "sum"),
                supporting_faulted=("synthetic_faulted", lambda s: int((s == "SUPPORTING").sum())),
                supporting_same_time=("clean_same_timestamp", lambda s: int((s == "SUPPORTING").sum())),
            ).reset_index()
            e2_by_fault["status_change_rate"] = e2_by_fault.status_changes / e2_by_fault.comparisons
            st.dataframe(e2_by_fault, hide_index=True, width="stretch")
            detail = e2_outputs["e2_multicontext_fault_detail.csv"]
            e2_status_counts = detail.groupby(["condition", "status"]).size().rename("count").reset_index()
            with st.expander("Temporal screen status counts, including matched controls"):
                st.dataframe(e2_status_counts, hide_index=True, width="stretch")
            with st.expander("Verified raw E2 paired and detail records"):
                st.dataframe(paired, hide_index=True, width="stretch")
                st.dataframe(detail, hide_index=True, width="stretch")

            st.markdown("**Synthetic baseline response and setting sensitivity**")
            baseline_summary = baseline_outputs["synthetic_baseline_response_summary.csv"]
            consensus = baseline_summary[baseline_summary.baseline.eq("E1_consensus")]
            st.dataframe(consensus, hide_index=True, width="stretch")
            with st.expander("Context response ranges, model-family and E4 responses"):
                st.dataframe(baseline_outputs["synthetic_baseline_context_summary.csv"], hide_index=True, width="stretch")
                other_baselines = baseline_summary[~baseline_summary.baseline.eq("E1_consensus")]
                st.dataframe(other_baselines, hide_index=True, width="stretch")
            with st.expander("E2 temporal-screen setting sensitivity"):
                st.dataframe(baseline_outputs["synthetic_e2_setting_sensitivity.csv"], hide_index=True, width="stretch")
            with st.expander("Evidence coverage ablation (not an outcome ablation)"):
                st.dataframe(baseline_outputs["evidence_coverage_ablation_summary.csv"], hide_index=True, width="stretch")
                st.caption("E3-dependent combinations are blocked because verified neighboring-station evidence is unavailable. Coverage does not measure interpretive benefit.")
            with st.expander("Verified raw synthetic response and coverage records"):
                st.dataframe(baseline_outputs["synthetic_baseline_response_detail.csv"], hide_index=True, width="stretch")
                st.dataframe(baseline_outputs["evidence_coverage_ablation.csv"], hide_index=True, width="stretch")
            st.caption("Fractions describe response to declared synthetic injection labels. They are not field accuracy, and unmodified observations are not verified negatives.")
            st.caption(
                f"{e2_manifest.get('evaluated_rows', 0):,} screen evaluations; "
                f"{e2_manifest.get('controls_selected', 0)} matched unmodified controls. "
                "SUPPORTING means temporal departures only; controls are not independently adjudicated clean. "
                "UNAVAILABLE values remain unavailable and do not count as evidence."
            )
            with st.expander("Campaign provenance"):
                st.json(multicontext_manifest)
        else:
            st.warning(artifact_state["warning"])
    else:
        st.subheader("Five-context synthetic fault study")
        st.warning("Research results are hidden because the five-context campaign manifest is missing.")
    saved_dir = root / "outputs" / "synthetic_fault_campaign"
    saved_summary = saved_dir / "experiment_summary.csv"
    campaign_manifest_path = saved_dir / "synthetic_campaign_manifest.json"
    saved_campaign_verified = False
    if campaign_manifest_path.is_file():
        try:
            campaign_manifest = json.loads(campaign_manifest_path.read_text(encoding="utf-8"))
            expected_campaign_hashes = campaign_manifest.get("dataset_hashes", {})
            saved_campaign_verified = (
                campaign_manifest.get("phase01_manifest_audit_passed") is True
                and expected_campaign_hashes.get("model_df") == phase01_hashes.get("observations")
                and expected_campaign_hashes.get("X_train_multi") == phase01_hashes.get("train")
                and expected_campaign_hashes.get("X_test_multi") == phase01_hashes.get("test")
            )
        except (OSError, json.JSONDecodeError):
            saved_campaign_verified = False
    if saved_summary.is_file() and saved_campaign_verified:
        summary = pd.read_csv(saved_summary)
        st.subheader("Most recent saved controlled campaign")
        st.dataframe(summary, hide_index=True, width="stretch")
        event_path = saved_dir / "event_level_results.csv"
        event_results = pd.read_csv(event_path) if event_path.is_file() else pd.DataFrame()
        if len(event_results):
            st.caption("The affected feature window includes the injected row and up to six following hourly rows. ‘Outside’ changes exclude that window.")
            st.dataframe(event_results[["experiment_id", "unaffected_window_changed_configuration_predictions",
                                        "changed_configuration_predictions_anywhere"]], hide_index=True, width="stretch")
        dose_options = ["Clean baseline", *summary.magnitude.tolist()]
        dose_choice = st.selectbox("Saved dose to visualize", dose_options,
                                   index=3 if len(dose_options) > 3 else 0,
                                   format_func=lambda value: value if isinstance(value, str) else f"+{value:g} °C",
                                   key="saved_experiment_dose")
        is_clean = dose_choice == "Clean baseline"
        dose = 0.0 if is_clean else float(dose_choice)
        selected_run = summary.iloc[0] if is_clean else summary.loc[summary.magnitude.eq(dose)].iloc[0]
        target = pd.Timestamp("2025-09-02 07:30:00+05:30")
        obs = data["observations"]
        window = obs.loc[(obs.index >= target - pd.Timedelta(hours=12)) &
                         (obs.index <= target + pd.Timedelta(hours=12)), "temp"]
        if len(window):
            injected = window.copy()
            if not is_clean and target in injected.index:
                injected.loc[target] += float(dose)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=window.index, y=window, mode="lines+markers", name="Historical baseline", line={"color":"#38BDF8"}))
            if not is_clean:
                fig.add_trace(go.Scatter(x=injected.index, y=injected, mode="lines+markers", name="Synthetic injected series", line={"color":"#F59E0B"}))
                fig.add_vline(x=target, line_dash="dash", line_color="#FBBF24")
            fig.update_layout(yaxis_title="Temperature (°C)", xaxis_title="Historical timestamp")
            st.plotly_chart(_plot_layout(fig, 340), width="stretch")
            st.caption(("Clean historical baseline." if is_clean else
                        f"Synthetic dose +{dose:g} °C at {target.strftime('%Y-%m-%d %H:%M %Z')}. Historical observations remain unchanged."))
        votes = pd.DataFrame([{"Condition": "Clean baseline", "Configuration votes": int(selected_run.clean_votes)}] if is_clean else
                             [{"Condition": "Clean baseline", "Configuration votes": int(selected_run.clean_votes)},
                              {"Condition": f"+{dose:g} °C synthetic spike", "Configuration votes": int(selected_run.faulted_votes)}])
        st.dataframe(votes, hide_index=True, width="stretch")
        st.caption("Configuration votes are counts, not probabilities. The campaign’s target-any-model and 8/12 consensus outcomes are separate questions.")
        for f in ("observation_level_results.csv", "event_level_results.csv", "clean_baseline_reproduction.csv"):
            path = saved_dir / f
            if path.is_file():
                with st.expander(f.replace(".csv", "").replace("_", " ").title()):
                    st.dataframe(pd.read_csv(path), hide_index=True, width="stretch")
    elif saved_summary.is_file():
        st.warning("Saved synthetic results do not match the loaded Phase 01 snapshot manifest; they are not shown as verified.")
    with st.form("run_synthetic_campaign"):
        magnitude = st.selectbox("Temperature point-spike magnitude (°C)", [2.0, 5.0, 10.0, 15.0], index=2)
        timestamp = st.text_input("Held-out timestamp", "2025-09-02 07:30:00+05:30")
        submitted = st.form_submit_button("Run controlled model experiment", type="primary")
    if submitted:
        try:
            from weather_research.synthetic_campaign import run_temperature_spike_campaign
            run_id = datetime.now().strftime("run_%Y%m%dT%H%M%S")
            run_dir = saved_dir / "runs" / run_id
            with st.spinner("Fitting the established 12 model configurations on the training matrix and evaluating the held-out injection…"):
                run_temperature_spike_campaign(root, output_dir=run_dir, timestamp=timestamp, magnitudes=(magnitude,))
            st.success("Experiment complete. Original data and training rows were retained unchanged.")
            st.session_state["latest_experiment_dir"] = str(run_dir)
        except (ValueError, KeyError, FileNotFoundError, RuntimeError) as exc:
            st.error(f"Experiment could not run: {exc}")
    run_dir = Path(st.session_state.get("latest_experiment_dir", "")) if st.session_state.get("latest_experiment_dir") else None
    if run_dir and (run_dir / "experiment_summary.csv").is_file():
        st.subheader("New experiment from this session")
        st.dataframe(pd.read_csv(run_dir / "experiment_summary.csv"), hide_index=True, width="stretch")
        st.caption(f"Run artifacts: {run_dir.relative_to(root)} · SIMULATED · saved baseline predictions are unchanged")
        for label, filename in (("Per-configuration target results", "configuration_detection_results.csv"),
                                ("Per-configuration prediction changes", "prediction_changes.csv"),
                                ("Feature propagation", "feature_propagation.csv"),
                                ("Outside-window checks", "unaffected_window_checks.csv"),
                                ("Reproducibility metadata", "synthetic_campaign_manifest.json")):
            path = run_dir / filename
            if path.is_file():
                with st.expander(label):
                    if path.suffix == ".json":
                        st.json(json.loads(path.read_text(encoding="utf-8")))
                    else:
                        table = pd.read_csv(path)
                        st.dataframe(table, hide_index=True, width="stretch")
    st.markdown("#### Implemented injection coverage")
    st.dataframe(pd.DataFrame([{"Fault type":"Point temperature spike", "Status":"Saved campaign and interactive dose runner", "Notes":"Separate from the eight-scenario matrix above"},
                               {"Fault type":"Spike, drop, offset, stuck, drift, missing block, noise, dew-point inconsistency", "Status":"Saved synthetic matrix; one held-out context", "Notes":"No multi-context validation or field-performance claim"}]), hide_index=True, width="stretch")


def _campaign_is_verified(root, hashes):
    folder = root / "outputs" / "synthetic_fault_campaign"
    manifest_path = folder / "synthetic_campaign_manifest.json"
    if not (folder / "observation_level_results.csv").is_file() or not (folder / "event_level_results.csv").is_file():
        return False
    try:
        campaign = json.loads(manifest_path.read_text(encoding="utf-8"))
        recorded = campaign.get("dataset_hashes", {})
        return (campaign.get("phase01_manifest_audit_passed") is True
                and recorded.get("model_df") == hashes.get("observations")
                and recorded.get("X_train_multi") == hashes.get("train")
                and recorded.get("X_test_multi") == hashes.get("test"))
    except (OSError, json.JSONDecodeError):
        return False


def render_evaluation(data, root, hashes):
    render_header("Learn about the saved analysis", "Model Evaluation", "See what the project tested, what the results show, and how each model works.")
    try:
        education = build_model_education(data)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        st.error("Model education details could not be assembled from the saved configuration and dataset metadata.")
        st.caption(str(exc))
        return
    st.caption("Two sections: saved experiments and results, then a plain-language model guide with technical detail on demand.")
    experiments_tab, models_tab = st.tabs(["A. Experiments & Results", "B. How the Models Work"])

    with experiments_tab:
        st.subheader("A1. Compare the tested configurations")
        st.write("The saved analysis compared four settings for each of three unsupervised algorithms. The bars show how often each configuration flagged a held-out reading as unusual.")
        cfg = data["configuration_results"].copy()
        parameter_names = pd.DataFrame(education["configurations"])[["name", "parameter"]].rename(columns={"name": "configuration"})
        cfg = cfg.merge(parameter_names, on="configuration", how="left", validate="one_to_one")
        cfg["family"] = cfg["family"].replace({"IsolationForest": "Isolation Forest", "LocalOutlierFactor": "Local Outlier Factor", "OneClassSVM": "One-Class SVM"})
        fig = px.bar(cfg.sort_values("anomalies"), x="anomalies", y="configuration", color="family", orientation="h",
                     hover_data={"parameter": True, "parameter_value": True, "anomaly_percentage": ":.2f", "test_observations": True},
                     labels={"anomalies": "Readings flagged", "configuration": "Saved configuration", "family": "Algorithm"},
                     color_discrete_sequence=["#38BDF8", "#2DD4BF", "#A78BFA"], title="Saved flags by model configuration")
        fig.update_layout(xaxis_title="Held-out readings flagged (not accuracy)", yaxis_title="Configuration")
        st.plotly_chart(_plot_layout(fig, 450), width="stretch")
        st.caption("These are model output counts. No verified real fault labels exist, so accuracy, precision, recall and F1 are not available.")
        with st.expander("All 12 configurations and saved counts"):
            st.dataframe(data["configuration_results"].sort_values(["family", "configuration"]), hide_index=True, width="stretch")

        st.subheader("A2. Do the models agree? (model stability)")
        stability = data["stability"]
        candidate_count = int(stability.configuration_votes.ge(8).sum())
        c1, c2 = st.columns(2)
        c1.metric("8/12 consensus candidates", f"{candidate_count:,}", help="A configured two-thirds vote threshold, not an anomaly probability.")
        c2.metric("Test timestamps", f"{len(stability):,}", help="Saved historical timestamps evaluated by all 12 configurations.")
        st.write("More configurations flagging the same observation means stronger agreement among these tested settings. It does not say how likely a sensor fault is.")
        vote_counts = stability.configuration_votes.value_counts().sort_index().rename_axis("votes").rename("timestamps").reset_index()
        vote_fig = px.bar(vote_counts, x="votes", y="timestamps", labels={"votes":"Configurations flagging the reading (of 12)", "timestamps":"Number of timestamps"},
                          title="How many configurations flagged each timestamp", color_discrete_sequence=["#38BDF8"])
        st.plotly_chart(_plot_layout(vote_fig, 330), width="stretch")
        family_columns = {"Isolation Forest": "IsolationForest_votes", "Local Outlier Factor": "LocalOutlierFactor_votes", "One-Class SVM": "OneClassSVM_votes"}
        family_votes = stability[list(family_columns.values())].rename(columns={v:k for k,v in family_columns.items()}).melt(var_name="Algorithm family", value_name="Configurations flagging")
        family_fig = px.histogram(family_votes, x="Configurations flagging", color="Algorithm family", barmode="group", histnorm="probability",
                                  labels={"Configurations flagging":"Flags within this family (of 4)", "probability":"Share of timestamps"},
                                  title="Family-level voting patterns", color_discrete_sequence=["#38BDF8", "#2DD4BF", "#A78BFA"])
        st.plotly_chart(_plot_layout(family_fig, 330), width="stretch")
        jac_path = root / "phase03_model_revalidation" / "jaccard_similarity_verified.csv"
        if jac_path.is_file():
            try:
                jac = pd.read_csv(jac_path, index_col=0).apply(pd.to_numeric, errors="coerce")
                if jac.empty or jac.isna().all().all():
                    raise ValueError("Saved similarity matrix contains no usable numeric values")
                heat = px.imshow(jac, text_auto=".2f", zmin=0, zmax=1, aspect="auto", color_continuous_scale="Tealgrn",
                                 labels={"x":"Model configuration", "y":"Model configuration", "color":"Jaccard similarity"},
                                 title="How similarly did each pair flag readings? (Jaccard similarity)")
                st.plotly_chart(_plot_layout(heat, 520), width="stretch")
                st.caption("Jaccard similarity compares the overlap of flagged timestamp sets. Lower overlap indicates disagreement; it is not model accuracy.")
            except (OSError, ValueError, KeyError, pd.errors.ParserError) as exc:
                st.warning(f"Saved configuration similarity is unavailable: {exc}")
        else:
            st.info("Saved configuration similarity matrix is unavailable.")
        with st.expander("Technical definition of the similarity measure"):
            st.write("Jaccard similarity is the number of timestamps flagged by both configurations divided by the number flagged by either one. It compares decisions, not correctness.")

        st.subheader("A3. Controlled temperature experiment")
        if _campaign_is_verified(root, hashes):
            dose_results = pd.read_csv(root / "outputs" / "synthetic_fault_campaign" / "observation_level_results.csv")
            event_results = pd.read_csv(root / "outputs" / "synthetic_fault_campaign" / "event_level_results.csv")
            doses = dose_results[["magnitude", "configuration_votes_faulted", "detected_injected_observations", "injected_observations"]].copy()
            doses["any_model_detected"] = doses.detected_injected_observations.gt(0)
            doses["8_of_12_consensus"] = doses.configuration_votes_faulted.ge(8)
            clean_row = pd.DataFrame([{"magnitude": 0.0, "configuration_votes_faulted": int(dose_results.configuration_votes_clean.iloc[0]),
                                       "detected_injected_observations": 0, "injected_observations": 1,
                                       "any_model_detected": False, "8_of_12_consensus": False}])
            doses = pd.concat([clean_row, doses], ignore_index=True).sort_values("magnitude")
            votes_fig = px.line(doses, x="magnitude", y="configuration_votes_faulted", markers=True,
                                hover_data={"any_model_detected": True, "8_of_12_consensus": True},
                                labels={"magnitude":"Synthetic temperature change (°C)", "configuration_votes_faulted":"Configurations flagging target (of 12)"},
                                title="Synthetic dose versus model votes", color_discrete_sequence=["#F59E0B"])
            votes_fig.update_layout(xaxis_title="Injected temperature change (°C)", yaxis_title="Target votes (of 12)")
            st.plotly_chart(_plot_layout(votes_fig, 340), width="stretch")
            st.dataframe(doses.rename(columns={"magnitude":"Dose (°C)", "configuration_votes_faulted":"Target votes (of 12)", "any_model_detected":"At least one model flagged", "8_of_12_consensus":"Met 8/12 cutoff"}), hide_index=True, width="stretch")
            st.warning("Synthetic controlled results only; not real-world sensor-fault accuracy. ‘Any model’ and ‘8/12 consensus’ are different detection criteria.")
            st.caption("The injected timestamp was 2025-09-02 07:30 IST. The expected feature-propagation window is the injected row plus up to six following hourly rows.")
            st.dataframe(event_results[["experiment_id", "changed_configuration_predictions_anywhere", "unaffected_window_changed_configuration_predictions"]].rename(columns={"changed_configuration_predictions_anywhere":"Changed predictions anywhere", "unaffected_window_changed_configuration_predictions":"Changes beyond expected feature window"}), hide_index=True, width="stretch")
            with st.expander("Saved experiment protocol and limitations"):
                st.json(json.loads((root / "outputs" / "synthetic_fault_campaign" / "synthetic_campaign_manifest.json").read_text(encoding="utf-8")))
                st.write("The injected observation and recomputed features are synthetic copies. Historical observations and saved Phase 03 predictions are not overwritten.")
        else:
            st.info("Verified saved controlled experiment results are unavailable for the loaded dataset.")

        st.subheader("A4. Configuration sensitivity")
        st.write("Each family varies a predefined setting while holding its other explicit protocol settings fixed. This is a configuration comparison, not automated or exhaustive hyperparameter optimization.")
        sensitivity = cfg.copy()
        sensitivity["family"] = sensitivity["family"].replace({"IsolationForest": "Isolation Forest", "LocalOutlierFactor": "Local Outlier Factor", "OneClassSVM": "One-Class SVM"})
        sens_fig = px.line(sensitivity.sort_values("parameter_value"), x="parameter_value", y="anomalies", facet_col="family", markers=True,
                           hover_data=["configuration", "parameter", "anomaly_percentage"],
                           labels={"parameter_value":"Varied value", "anomalies":"Saved readings flagged", "family":"Algorithm family"},
                           title="Flag counts across the tested parameter settings", color_discrete_sequence=["#2DD4BF"])
        sens_fig.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.replace("family=", "")))
        st.plotly_chart(_plot_layout(sens_fig, 350), width="stretch")
        st.caption("Each panel has its own x-axis because the families vary different parameters: contamination, neighborhood size, or nu.")

        st.subheader("A5. Contribution tests (ablation)")
        st.info("Not evaluated yet. There is no validated integrated E1–E4 runner and no suitable evidence inputs for an ablation comparison.")

    with models_tab:
        st.subheader("Choose an algorithm to learn about")
        family = st.selectbox("Model profile", list(education["profiles"]),
                              format_func=lambda key: education["profiles"][key]["name"], key="model_profile_family")
        profile = education["profiles"][family]
        st.markdown("### What does this algorithm do?")
        st.info(profile["simple"])
        st.caption("Illustration of the idea only; this is not the fitted model's decision boundary.")
        if family == "IsolationForest":
            diagram = st.columns([1, 1, 1])
            diagram[0].markdown("**Weather reading**\n\nA point among many measurements")
            diagram[1].markdown("**Random questions**\n\nSplit values into smaller groups")
            diagram[2].markdown("**Isolation depth**\n\nFewer splits can indicate unusualness")
        elif family == "LocalOutlierFactor":
            diagram = st.columns([1, 1, 1])
            diagram[0].markdown("**Reading A**\n\nCompare nearby learned points")
            diagram[1].markdown("**Local density**\n\nEstimate neighborhood crowding")
            diagram[2].markdown("**Relative density**\n\nA sparse pocket may be unusual")
        else:
            diagram = st.columns([1, 1, 1])
            diagram[0].markdown("**Training observations**\n\nLearn the typical data region")
            diagram[1].markdown("**Flexible boundary**\n\nRBF kernel shapes a curved edge")
            diagram[2].markdown("**New reading**\n\nOutside the learned region may be flagged")
        with st.expander("Technical explanation"):
            st.write(profile["technical"])

        st.subheader("Why include it?")
        st.write(profile["why"])
        st.caption(profile["difference"])

        st.subheader("What data did it learn from?")
        facts = st.columns(4)
        facts[0].metric("Training observations", f"{education['train_rows']:,}")
        facts[1].metric("Test observations", f"{education['test_rows']:,}")
        facts[2].metric("Input features", str(education["input_features"]))
        facts[3].metric("Estimator objects saved", "No")
        timeline = pd.DataFrame([
            {"Split": "Training", "Start": education["training_start"], "End": education["training_end"], "Rows": education["train_rows"]},
            {"Split": "Testing", "Start": education["testing_start"], "End": education["testing_end"], "Rows": education["test_rows"]},
        ])
        timeline_fig = px.timeline(timeline, x_start="Start", x_end="End", y="Split", color="Split", text="Rows",
                                   hover_data={"Rows": True}, title="Chronological training and testing periods",
                                   color_discrete_sequence=["#38BDF8", "#F59E0B"])
        timeline_fig.update_layout(xaxis_title="Historical timestamp", yaxis_title="Saved data split", showlegend=False)
        st.plotly_chart(_plot_layout(timeline_fig, 250), width="stretch")
        st.caption(f"Train: {education['train_rows']:,} rows, { _fmt_ts(education['training_start']) } to { _fmt_ts(education['training_end']) }. Test: {education['test_rows']:,} rows, {_fmt_ts(education['testing_start'])} to {_fmt_ts(education['testing_end'])}.")
        st.write("Each configured model is fitted on the earlier training period, then evaluated on the later held-out test period. Test observations are not used to fit the model or scaler.")
        st.markdown("**Preprocessing used:** " + profile["preprocessing"])
        if family == "IsolationForest":
            st.caption("Its inputs are unscaled in this protocol. LOF and One-Class SVM use a StandardScaler fitted on training rows only.")
        else:
            st.caption("The scaler is fitted to training observations only, then applied to both training and test rows to avoid test-data leakage.")

        st.subheader("What information goes into each reading?")
        feature_rows = []
        for group, features in education["feature_groups"].items():
            for feature in features:
                label, unit = education["feature_labels"][feature]
                feature_rows.append({"Feature group": group, "Input name": feature, "Meaning": label, "Unit": unit})
        feature_frame = pd.DataFrame(feature_rows)
        group_counts = feature_frame.groupby("Feature group", sort=False).size().rename("Features").reset_index()
        feature_fig = px.bar(group_counts, x="Features", y="Feature group", orientation="h", text="Features",
                             title="Feature groups used by the models", color_discrete_sequence=["#2DD4BF"])
        st.plotly_chart(_plot_layout(feature_fig, 230), width="stretch")
        with st.expander("Show all 11 feature names and meanings"):
            st.dataframe(feature_frame, hide_index=True, width="stretch")
        st.caption("Six current weather measurements, three recent-temperature features, and two seasonal month encodings. These are model inputs, not explanations of an individual prediction.")

        st.subheader("How was the model configured?")
        configs = pd.DataFrame(profile["configs"])
        first_parameters = profile["configs"][0]["parameters"]
        parameter_table = pd.DataFrame([{"Parameter": name,
                                         "scikit-learn default": str(profile["defaults"].get(name, "not applicable")),
                                         "Protocol setting": str(first_parameters[name]),
                                         "What varied?": "Varied across configurations" if len({str(item["parameters"][name]) for item in profile["configs"]}) > 1 else "Held fixed"}
                                        for name in profile["configs"][0]["parameters"]
                                        if name in {"n_estimators", "contamination", "random_state", "n_jobs", "n_neighbors", "novelty", "kernel", "gamma", "nu"}])
        st.dataframe(parameter_table, hide_index=True, width="stretch")
        st.write(profile["parameter_explanation"])
        param_fig = px.bar(configs, x="value", y="anomalies", color="name", hover_data=["parameter", "anomaly_percentage"],
                           labels={"value": profile["configs"][0]["parameter"], "anomalies":"Saved readings flagged", "name":"Configuration"},
                           title=f"Saved results for {profile['name']} settings", color_discrete_sequence=px.colors.sequential.Teal)
        st.plotly_chart(_plot_layout(param_fig, 300), width="stretch")
        with st.expander("All four tested settings"):
            st.dataframe(configs[["name", "parameter", "value", "anomalies", "anomaly_percentage"]].rename(columns={"name":"Configuration", "parameter":"Varied parameter", "value":"Value", "anomalies":"Saved flags", "anomaly_percentage":"Flagged (%)"}), hide_index=True, width="stretch")
        with st.expander("Estimator defaults from this installed scikit-learn version"):
            st.caption(f"scikit-learn {__import__('sklearn').__version__}. Values below come from the installed estimator constructor; explicit project overrides are shown above.")
            defaults = pd.DataFrame([{"Parameter": name, "scikit-learn default": str(value)} for name, value in profile["defaults"].items()])
            st.dataframe(defaults, hide_index=True, width="stretch")

        st.subheader("How does a prediction happen?")
        st.markdown("**For an explicitly run protocol:** historical reading → same 11-feature preparation → preprocessing used by this family → fitted estimator → normal or unusual label")
        st.caption("The application explores archived historical test predictions; it is not a live predictor for newly arriving readings. Fitted estimator objects are not stored, and opening this page does not fit models.")
        st.markdown("**In principle:** " + profile["detects_well"])
        st.markdown("**May miss or misread:** " + profile["may_miss"])
        st.warning("An unusual label is not proof of a sensor fault. Configuration votes are not probabilities, and real-world fault accuracy has not been measured.")

        with st.expander("Optional: run a new local refit (advanced; takes time)"):
            st.caption("This refits the established 12 configurations on the verified train matrix. It is separate from the archived predictions and is not run automatically.")
            if st.button("Run a new 12-configuration refit", key="run_saved_protocol", type="primary"):
                try:
                    with st.spinner("Fitting 12 configurations on the saved training rows…"):
                        new_predictions, metadata = run_saved_protocol(data["train"], data["test"])
                    st.session_state["new_predictions"] = new_predictions
                    st.session_state["new_prediction_metadata"] = metadata
                except (ValueError, KeyError) as exc:
                    st.error(f"Local model execution failed: {exc}")
            if "new_predictions" in st.session_state:
                meta = st.session_state["new_prediction_metadata"]
                st.success(f"New local refit completed at {meta['executed_at_utc']} · {len(st.session_state['new_predictions']):,} rows")
                saved = data["predictions"][["timestamp", "configuration", "is_candidate"]]
                fresh = st.session_state["new_predictions"].reset_index()
                paired = fresh.merge(saved, on=["timestamp", "configuration"], how="left", suffixes=("_new", "_saved"), validate="one_to_one")
                if paired.is_candidate_saved.isna().any():
                    st.warning("The new prediction grid does not align with the archived grid.")
                else:
                    mismatch = paired.is_candidate_new.astype(bool) != paired.is_candidate_saved.astype(bool)
                    st.metric("Labels differing from archived results", f"{int(mismatch.sum()):,} / {len(paired):,}")
                    st.caption("The known saved/local discrepancy is 42 of 100,980 cells; it remains unresolved.")


try:
    data, manifest, hashes = _load_data(str(ROOT))
except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
    st.error("WeatherGuard could not load the verified research artifacts.")
    st.code(str(exc))
    st.info("Check that verified_phase01/ and phase03_model_revalidation/ are present next to app.py.")
    st.stop()

if "selected_observation" not in st.session_state:
    high = data["stability"].loc[data["stability"].configuration_votes.ge(8), "timestamp"]
    st.session_state["selected_observation"] = high.iloc[-1] if len(high) else data["observations"].index[-1]

with st.container(border=True, key="primary_header"):
    brand, nav = st.columns([1.25, 4.4], vertical_alignment="center")
    with brand:
        st.markdown("<div class='wg-brand'><span class='wg-brand-mark'>⌁</span><span>WEATHERGUARD <span style='color:#38bdf8'>AI</span></span></div>", unsafe_allow_html=True)
    with nav:
        primary_page = st.radio(
            "Main navigation",
            ["Home", "Weather Data", "Investigate a Reading", "Model Evaluation",
             "Experiment Lab", "Research", "About"],
            horizontal=True, label_visibility="collapsed", key="primary_navigation",
        )

with st.sidebar:
    st.markdown("<div class='wg-eyebrow'>PROJECT WORKSPACE</div>", unsafe_allow_html=True)
    st.markdown("### Dataset context")
    st.markdown("**VILD0 · primary processed series**")
    st.caption("Ludhiana / Doraha record · historical snapshot")
    st.caption(f"{len(data['observations']):,} rows · {data['predictions'].configuration.nunique()} saved configurations")
    st.success("Saved artifact integrity verified")
    st.divider()
    st.caption("Historical data only · provider and sensor provenance remain incomplete.")

if primary_page == "Weather Data":
    render_weather_data(data)
elif primary_page == "Investigate a Reading":
    render_investigation(data, ROOT)
elif primary_page == "Home":
    render_home_dashboard(data, str(ROOT))
elif primary_page == "Model Evaluation":
    render_model_workspace(data, ROOT, hashes, render_evaluation)
elif primary_page == "Experiment Lab":
    render_experiment_workspace(ROOT, data, hashes, render_synthetic_experiments)
elif primary_page == "Research":
    render_research_workspace(ROOT, data)
elif primary_page == "About":
    render_about()

with st.container(key="wg_persistent_upload_action"):
    if st.button("＋  Experiment with your data", key="persistent_dataset_cta", type="primary"):
        render_upload_dialog(ROOT)
