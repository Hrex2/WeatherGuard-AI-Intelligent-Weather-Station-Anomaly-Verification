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
from ui.theme import apply_theme, metric_card, evidence_panel

st.set_page_config(page_title="WeatherGuard AI", page_icon="🌦️", layout="wide", initial_sidebar_state="expanded")
apply_theme()


@st.cache_data(show_spinner="Loading verified research artifacts…", ttl=600)
def _load_data(root_text):
    return load_project_data(Path(root_text))


def _plot_layout(fig, height=350):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#cad8e8", "family": "Inter, Segoe UI, sans-serif"},
        margin={"l": 14, "r": 14, "t": 30, "b": 12},
        xaxis={"gridcolor": "#26384e", "zerolinecolor": "#26384e"},
        yaxis={"gridcolor": "#26384e", "zerolinecolor": "#26384e"},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    return fig


def _fmt_ts(ts):
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M %Z")


def _source_note():
    st.caption("Historical processed research snapshot • not a live feed • timezone Asia/Kolkata")


def render_header(kicker, title, subtitle):
    st.markdown(f"<div class='wg-eyebrow'>{kicker}</div>", unsafe_allow_html=True)
    st.title(title)
    st.markdown(f"<div class='wg-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")


def render_command(data, manifest, hashes):
    obs = data["observations"]
    stability = data["stability"].set_index("timestamp").sort_index()
    predictions = data["predictions"]
    candidate = stability.loc[stability.configuration_votes.ge(8)]
    render_header("WeatherGuard AI  /  overview", "Command Center", "A station anomaly is a prompt for investigation, not a sensor-fault verdict.")
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
    st.divider()
    metrics = st.columns(6)
    with metrics[0]: metric_card("Processed rows", f"{len(obs):,}", "model_df snapshot; not raw acquisition")
    with metrics[1]: metric_card("Feature-ready rows", f"{len(data['train']) + len(data['test']):,}", "saved train + test matrices")
    with metrics[2]: metric_card("8/12 candidates", f"{len(candidate):,}", "verified saved stability table")
    with metrics[3]: metric_card("Episodes · 1h", f"{len(data['episodes']):,}", "saved episode profiles")
    with metrics[4]: metric_card("Regional outcomes", "Not evaluated", "integrated evidence pipeline pending")
    with metrics[5]: metric_card("Station-specific outcomes", "Not evaluated", "no verified fault labels")
    st.write("")
    left, right = st.columns([1.55, 1])
    with left:
        st.subheader("Observation timeline")
        variable = st.selectbox("Weather variable", ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"], key="command_variable")
        series = obs[variable].dropna()
        if len(series) > 6000:
            series = series.iloc[:: max(1, len(series) // 6000)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=variable, line={"color":"#38BDF8","width":1.5}))
        if len(candidate):
            candidate_times = candidate.index.intersection(obs.index)
            fig.add_trace(go.Scatter(x=candidate_times, y=obs.loc[candidate_times, variable], mode="markers", name="8/12 candidate", marker={"color":"#FBBF24","size":7,"symbol":"diamond"}))
        st.plotly_chart(_plot_layout(fig, 390), width="stretch")
    with right:
        st.subheader("Configuration sensitivity")
        counts = data["configuration_results"].sort_values("anomalies")
        fig = px.bar(counts, x="anomalies", y="configuration", orientation="h", color="family",
                     color_discrete_sequence=["#38BDF8", "#2DD4BF", "#A78BFA"])
        st.plotly_chart(_plot_layout(fig, 390), width="stretch")
    st.subheader("Recent consensus candidates")
    recent = candidate.tail(12).reset_index().rename(columns={"index":"timestamp"})
    if len(recent):
        display_cols = [c for c in ["timestamp", "configuration_votes", "family_balanced_agreement"] if c in recent]
        st.dataframe(recent[display_cols].sort_values("timestamp", ascending=False), hide_index=True, width="stretch")
    else:
        st.info("No saved rows meet the 8/12 candidate threshold.")
    with st.expander("Dataset and prediction fingerprints"):
        st.json({"phase01_manifest_audit_passed": manifest.get("audit_passed"), "sha256": hashes,
                 "saved_prediction_rows": len(predictions), "unique_timestamps": predictions.timestamp.nunique(),
                 "configurations": predictions.configuration.nunique()})


def render_research(data):
    render_header("WeatherGuard AI  /  research studio", "Research Studio", "A verified research narrative with published literature separated from project findings.")
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
    render_header("WeatherGuard AI  /  investigation studio", "Investigation Studio", "Explore the historical series, saved model votes, temporal context, spatial coverage, and screening flags.")
    obs = data["observations"]
    stab = data["stability"].set_index("timestamp").sort_index()
    start_date, end_date = obs.index.min().date(), obs.index.max().date()
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        dates = st.date_input("Observation date range", value=(max(start_date, end_date.replace(year=end_date.year-1)), end_date), min_value=start_date, max_value=end_date, key="explorer_dates")
    with col2:
        variable = st.selectbox("Variable", ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"], key="explorer_variable")
    with col3:
        view = st.selectbox("Rows", ["All observations", "8/12 candidates only", "Below 8/12 candidate threshold"], key="explorer_candidates")
    if isinstance(dates, tuple) and len(dates) == 2:
        lo = pd.Timestamp(dates[0]).tz_localize(str(obs.index.tz))
        hi = (pd.Timestamp(dates[1]) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)).tz_localize(str(obs.index.tz))
        frame = obs.loc[(obs.index >= lo) & (obs.index <= hi)]
    else:
        frame = obs
    candidates = stab.loc[stab.configuration_votes.ge(8)]
    if view == "8/12 candidates only":
        frame = frame.loc[frame.index.isin(candidates.index)]
    elif view == "Below 8/12 candidate threshold":
        frame = frame.loc[~frame.index.isin(candidates.index)]
    chart = frame[[variable]].dropna()
    if len(chart) > 8000:
        chart = chart.iloc[:: max(1, len(chart) // 8000)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=chart.index, y=chart[variable], mode="lines", name=variable, line={"color":"#38BDF8","width":1.3}))
    event_idx = chart.index.intersection(candidates.index)
    if len(event_idx):
        fig.add_trace(go.Scatter(x=event_idx, y=chart.loc[event_idx, variable], mode="markers", name="8/12 model candidate", marker={"color":"#FBBF24","size":8,"symbol":"diamond"}))
    st.plotly_chart(_plot_layout(fig, 420), width="stretch")
    st.caption(f"Rows in selected window: {len(frame):,}. Dataset timestamps are shown in {obs.index.tz}.")
    choices = frame.index
    if not len(choices):
        st.info("No observations match these filters.")
        return
    preferred = candidates.index.intersection(choices)
    default_ts = st.session_state.get("selected_observation")
    if default_ts is None or pd.Timestamp(default_ts) not in choices:
        default_ts = preferred[-1] if len(preferred) else choices[-1]
    selectables = choices
    if len(selectables) > 12000:
        selectables = selectables[:: max(1, len(selectables)//12000)]
        if default_ts not in selectables:
            selectables = selectables.append(pd.DatetimeIndex([default_ts])).sort_values()
    index = list(selectables).index(default_ts)
    selected = st.selectbox("Selected observation (shared across workspaces)", selectables, index=index,
                            format_func=_fmt_ts, key="selected_observation_widget")
    st.session_state["selected_observation"] = selected
    selected_values = obs.loc[selected]
    st.subheader("Observation details")
    st.dataframe(selected_values.rename("value").to_frame(), width="stretch")

    spatial_tables = {}
    for station in ("42099", "42101"):
        path = root / "phase03_model_revalidation" / f"spatial_comparison_{station}.csv"
        if path.is_file():
            spatial_tables[station] = pd.read_csv(path, parse_dates=["candidate_time", "station_time"])
    bundle = observation_evidence(selected, obs, data["predictions"], data["stability"], data["episodes"], spatial_tables)
    a, b, c, d = st.columns(4)
    details = {
        "E1 · Model stability": (bundle["evidence_states"]["E1"], f"Configuration votes: {bundle['vote_count'] if bundle['vote_count'] is not None else 'unavailable'} / 12. Agreement is not an anomaly probability."),
        "E2 · Temporal consistency": (bundle["evidence_states"]["E2"], f"Saved one-hour candidate episodes matching this timestamp: {len(bundle['episodes'])}. No episode means no detected evidence under the saved 8/12 candidate definition."),
        "E3 · Spatial corroboration": (bundle["evidence_states"]["E3"], "Exploratory candidate comparisons may be shown below, but raw neighbor series/provenance and a validated residual threshold are unavailable."),
        "E4 · Physical screening": (bundle["evidence_states"]["E4"], f"Broad screening flags at this timestamp: {int(bundle['quality_flags'].screening_flag.sum()) if len(bundle['quality_flags']) else 'unavailable'}. A screening flag is not a sensor-fault label."),
    }
    for slot, key in zip((a,b,c,d), details):
        with slot:
            evidence_panel(key, *details[key])
    st.markdown("### Current interpretation")
    st.info(bundle["outcome"] + " — " + bundle["outcome_reason"])
    st.markdown("**Outcome evidence:** model votes and available screening flags are displayed above. **Missing:** a validated integrated rule, complete neighbor series, and independent source provenance. **Conflict:** cannot be reliably adjudicated with current artifacts.")
    st.subheader("Twelve model configuration predictions")
    if len(bundle["model_rows"]):
        st.dataframe(bundle["model_rows"][["configuration", "family", "parameter", "parameter_value", "is_candidate"]], hide_index=True, width="stretch")
    else:
        st.info("No saved prediction row exists for the selected timestamp.")
    if len(bundle["spatial_rows"]):
        st.subheader("Exploratory neighboring-station comparison")
        st.dataframe(bundle["spatial_rows"], hide_index=True, width="stretch")


def render_experiments(root, data, phase01_hashes):
    render_header("WeatherGuard AI  /  experiment lab", "Experiment Lab", "Run controlled, explicitly simulated injections on held-out observations.")
    st.warning("SIMULATED DATA — NOT A REAL-WORLD SENSOR FAULT. This initial lab supports temperature point-spike dose tests only; other fault groups remain unimplemented.")
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
    st.dataframe(pd.DataFrame([{"Fault type":"Point temperature spike", "Status":"Implemented and executed", "Notes":"Controlled same timestamp; four supported magnitudes; 12 existing configurations"},
                               {"Fault type":"Other variable point faults", "Status":"Pending", "Notes":"Not exposed as runnable options"},
                               {"Fault type":"Step, drift, stuck, noise, dropout", "Status":"Pending", "Notes":"Backend primitives/tests exist in part; campaign evaluation not wired"}]), hide_index=True, width="stretch")


def render_evaluation(data, root):
    render_header("WeatherGuard AI  /  model evaluation", "Model Evaluation", "Inspect saved model configuration behavior and synthetic-only results without implying real-world accuracy.")
    tabs = st.tabs(["Configuration comparison", "Stability", "Synthetic fault evaluation", "Ablation"])
    st.markdown("#### Optional model execution")
    st.caption("No fitted model objects are included in this archive. This control explicitly refits the established 12 configurations on the saved training matrix and predicts the saved test matrix; it is not run on page load.")
    if st.button("Run the saved 12-model protocol", key="run_saved_protocol", type="primary"):
        try:
            with st.spinner("Fitting 12 configurations on 36k training rows and predicting the held-out matrix…"):
                new_predictions, metadata = run_saved_protocol(data["train"], data["test"])
            st.session_state["new_predictions"] = new_predictions
            st.session_state["new_prediction_metadata"] = metadata
        except (ValueError, KeyError) as exc:
            st.error(f"Local model execution failed: {exc}")
    if "new_predictions" in st.session_state:
        meta = st.session_state["new_prediction_metadata"]
        st.success(f"New local execution completed at {meta['executed_at_utc']} · {len(st.session_state['new_predictions']):,} prediction rows")
        st.json(meta)
        st.caption("This execution is separate from the saved historical predictions. Model-output parity is reported here rather than assumed.")
        new_long = st.session_state["new_predictions"].reset_index()
        saved_long = data["predictions"][["timestamp", "configuration", "is_candidate"]]
        paired = new_long.merge(saved_long, on=["timestamp", "configuration"], how="left", suffixes=("_new", "_saved"), validate="one_to_one")
        if paired.is_candidate_saved.isna().any():
            st.warning("Prediction grid differs from the saved historical artifact.")
        else:
            mismatch = paired.is_candidate_new.astype(bool) != paired.is_candidate_saved.astype(bool)
            st.metric("Saved-label mismatches", f"{int(mismatch.sum()):,} / {len(paired):,}")
            st.dataframe(new_long.head(100), hide_index=True, width="stretch")
    with tabs[0]:
        cfg = data["configuration_results"].sort_values("anomaly_percentage", ascending=False)
        st.caption("Anomaly counts describe model output frequency, not ground-truth performance.")
        fig = px.bar(cfg.sort_values("anomalies"), x="anomalies", y="configuration", orientation="h", color="family",
                     color_discrete_sequence=["#38BDF8", "#2DD4BF", "#A78BFA"], hover_data=["parameter_value", "anomaly_percentage"])
        st.plotly_chart(_plot_layout(fig, 460), width="stretch")
        st.dataframe(cfg, hide_index=True, width="stretch")
    with tabs[1]:
        stability = data["stability"]
        fig = px.histogram(stability, x="configuration_votes", nbins=13, color_discrete_sequence=["#38BDF8"])
        st.plotly_chart(_plot_layout(fig, 320), width="stretch")
        st.caption("Votes are configuration agreement, not calibrated anomaly probability.")
        st.dataframe(stability.configuration_votes.value_counts().sort_index().rename_axis("votes").rename("timestamps").reset_index(), hide_index=True, width="stretch")
        st.info("Saved Phase 03 predictions are historical artifacts. A local refit differs at 42 of 100,980 labels; see the parity report before interpreting refit comparisons.")
    with tabs[2]:
        summary_path = root / "outputs" / "synthetic_fault_campaign" / "observation_level_results.csv"
        if summary_path.is_file():
            results = pd.read_csv(summary_path)
            st.warning("Synthetic labels only. These detection rates do not measure accuracy on real weather observations.")
            st.dataframe(results, hide_index=True, width="stretch")
            fig = px.line(results, x="magnitude", y="synthetic_detection_rate", markers=True,
                          labels={"synthetic_detection_rate":"Target detected by ≥1 configuration", "magnitude":"Injected temperature change (°C)"},
                          color_discrete_sequence=["#2DD4BF"])
            st.plotly_chart(_plot_layout(fig, 330), width="stretch")
        else:
            st.info("Not evaluated. No synthetic campaign output is available.")
    with tabs[3]:
        st.info("Not evaluated. The integrated E1–E4 ablation runner and validated evidence inputs are not available yet.")
        st.caption("No synthetic or original-observation ablation metrics are displayed until an executable, reviewable comparison exists.")


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

with st.sidebar:
    st.markdown("<div class='wg-eyebrow'>WeatherGuard AI</div>", unsafe_allow_html=True)
    st.markdown("### Observatory")
    st.caption("Research dataset mode")
    workspace = st.radio("Workspace", ["Command Center", "Research Studio", "Investigation Studio", "Experiment Lab", "Model Evaluation"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Dataset** · VILD0 processed snapshot")
    st.caption(f"{len(data['observations']):,} rows · {data['predictions'].configuration.nunique()} saved configurations")
    st.caption("Not a live feed · source provenance incomplete")
    st.divider()
    st.caption("Working title: Uncertainty-Aware Event-Level Verification of Weather Station Anomalies")

if workspace == "Command Center":
    render_command(data, manifest, hashes)
elif workspace == "Research Studio":
    render_research(data)
elif workspace == "Investigation Studio":
    render_investigation(data, ROOT)
elif workspace == "Experiment Lab":
    render_experiments(ROOT, data, hashes)
else:
    render_evaluation(data, ROOT)
