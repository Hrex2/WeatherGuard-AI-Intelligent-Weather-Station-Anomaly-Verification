"""Interactive historical anomaly investigation workspace."""
from __future__ import annotations

from datetime import timedelta
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.evidence_service import observation_evidence
from services.investigation_service import (available_weather_variables,
                                           model_heatmap_data,
                                           variable_diagnostics)
from services.model_metadata import build_model_education
from services.temporal_service import temporal_verification
from ui.chart_theme import style_chart
from ui.station_map import render_station_map
from ui.theme import evidence_panel

FAMILIES = {
    "IsolationForest": "Isolation Forest",
    "LocalOutlierFactor": "Local Outlier Factor",
    "OneClassSVM": "One-Class SVM",
}


def _layout(fig, height=350):
    return style_chart(fig, height)


def _step_heading(number, title, description):
    st.markdown(
        "<div class='wg-workflow-step'>"
        f"<span class='wg-step-number'>{escape(str(number))}</span>"
        "<div class='wg-step-copy'>"
        f"<div class='wg-step-title'>{escape(str(title))}</div>"
        f"<div class='wg-step-caption'>{escape(str(description))}</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )


def _timestamp_from_selection(key):
    state = st.session_state.get(key)
    try:
        points = state.get("selection", {}).get("points", [])
        if points:
            return pd.Timestamp(points[0]["x"])
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return None


def _consume_chart_selection(keys, valid_times):
    changed = False
    for key in keys:
        selected = _timestamp_from_selection(key)
        marker_key = f"_{key}_last_consumed"
        if selected is None:
            continue
        marker = selected.isoformat()
        if marker != st.session_state.get(marker_key) and selected in valid_times:
            st.session_state["selected_observation"] = selected
            changed = True
        st.session_state[marker_key] = marker
    return changed


def _format_timestamp(value):
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M %Z")


def _prediction_agreement(predictions, timestamp):
    rows = predictions.loc[predictions.timestamp.eq(pd.Timestamp(timestamp))]
    available = int(rows.is_candidate.notna().sum())
    votes = int(rows.is_candidate.fillna(False).astype(bool).sum())
    pct = 100.0 * votes / available if available else np.nan
    return rows, votes, available, pct


def _draw_model_heatmap(prepared, full_agreement, families, selected):
    matrix = prepared["matrix"]
    if matrix.empty or len(matrix.columns) == 0:
        st.info("No saved model predictions match this date range and family selection.")
        return
    display_times = matrix.index
    total_configs = int(len(prepared["configurations"]))
    visible_names = []
    for cfg in prepared["configurations"]:
        prefix = cfg.split("_")[0]
        family_key = {"IF": "IsolationForest", "LOF": "LocalOutlierFactor", "SVM": "OneClassSVM"}.get(prefix, prefix)
        family = families.get(family_key, family_key)
        visible_names.append(f"{family} · {cfg}")
    labels = visible_names + ["8/12 consensus"]
    z_rows, hover_rows = [], []
    for name, config in zip(visible_names, prepared["configurations"]):
        values = matrix[config]
        z_rows.append(np.where(values.isna(), 2, values.fillna(0).astype(int)).tolist())
        hover_rows.append(["Unavailable" if pd.isna(value) else "Anomaly" if bool(value) else "Normal" for value in values])
    agreement = full_agreement.reindex(display_times)
    consensus_z, consensus_hover = [], []
    for _, row in agreement.iterrows():
        if pd.isna(row.get("available")) or int(row["available"]) != 12:
            consensus_z.append(2)
            consensus_hover.append("Unavailable: fewer than 12 saved configuration predictions")
        else:
            matched = int(row["votes"]) >= 8
            consensus_z.append(1 if matched else 0)
            consensus_hover.append(f"{int(row['votes'])}/12 configurations · {row['agreement_pct']:.1f}% agreement · {'8/12 threshold met' if matched else 'below 8/12 threshold'}")
    z_rows.append(consensus_z)
    hover_rows.append(consensus_hover)
    fig = go.Figure(go.Heatmap(
        z=z_rows, x=display_times, y=labels, customdata=hover_rows,
        zmin=0, zmax=2, colorscale=[[0, "#1d4e67"], [0.249, "#1d4e67"],
                                    [0.25, "#fbbf24"], [0.749, "#fbbf24"],
                                    [0.75, "#64748b"], [1, "#64748b"]],
        colorbar={"tickvals": [0, 1, 2], "ticktext": ["Normal", "Anomaly", "Unavailable"], "title": "Saved result"},
        hovertemplate="%{y}<br>%{x|%Y-%m-%d %H:%M}<br>%{customdata}<extra></extra>",
        xgap=1, ygap=1, hoverongaps=False,
    ))
    fig.update_layout(title="Saved prediction by model configuration and time",
                      xaxis_title="Historical timestamp", yaxis_title="Model configuration",
                      clickmode="event+select", yaxis={"autorange": "reversed"})
    if selected in display_times:
        fig.add_vline(x=selected, line_color="#f87171", line_width=2, line_dash="dash")
    st.plotly_chart(_layout(fig, max(380, min(660, 34 * len(labels)))), width="stretch",
                    key="model_anomaly_heatmap", on_select="rerun", selection_mode="points")
    if prepared["sampled_for_display"]:
        st.caption(f"This wide date range is sampled to {len(display_times):,} timestamps for readability. Hover or click a displayed cell; use the exact timestamp selector below to inspect any prediction in the selected date range.")
    else:
        st.caption("Gold cells are saved anomaly labels; blue cells are saved normal labels; grey cells mean the prediction is unavailable. The consensus row always uses all 12 configurations, even if rows are filtered by family.")


def _load_spatial_tables(root):
    result = {}
    for station in ("42099", "42101"):
        path = Path(root) / "phase03_model_revalidation" / f"spatial_comparison_{station}.csv"
        if path.is_file():
            try:
                result[station] = pd.read_csv(path, parse_dates=["candidate_time", "station_time"])
            except (OSError, ValueError, KeyError, pd.errors.ParserError):
                continue
    return result


def render_investigation_workspace(data, root):
    observations, predictions = data["observations"], data["predictions"]
    timestamps = pd.DatetimeIndex(predictions.timestamp.unique()).sort_values()
    variables = available_weather_variables(observations)
    if not len(timestamps):
        st.title("Investigate a Reading")
        st.warning("Saved prediction timestamps are unavailable.")
        return
    chart_selection_changed = _consume_chart_selection(("model_anomaly_heatmap", "investigation_variable_chart",
                                                         "isolation_forest_profile", "lof_profile", "oneclass_svm_profile"), timestamps)
    stored_selection = pd.Timestamp(st.session_state.get("selected_observation", timestamps[-1]))
    widget_value = st.session_state.get("investigation_timestamp_selector")
    last_selection = st.session_state.get("_last_investigation_selection")
    if chart_selection_changed:
        selected = stored_selection
    elif widget_value in timestamps and widget_value != last_selection:
        selected = pd.Timestamp(widget_value)
    elif stored_selection in timestamps and stored_selection != last_selection:
        selected = stored_selection
    elif widget_value in timestamps:
        selected = pd.Timestamp(widget_value)
    else:
        selected = stored_selection
    if selected not in timestamps:
        selected = timestamps[-1]
    tz = str(timestamps.tz)
    start_min, end_max = timestamps.min().date(), timestamps.max().date()
    default_start = max(start_min, (timestamps.max() - pd.Timedelta(days=13)).date())

    st.title("Investigate a Reading")
    st.caption("Choose a saved historical reading, compare model decisions, inspect the weather context, and see what evidence is still missing.")
    with st.container(border=True):
        st.subheader("Find an unusual observation")
        controls = st.columns([1.2, 1.0, 1.2])
        with controls[0]:
            date_range = st.date_input("Prediction date range", value=(default_start, end_max),
                                       min_value=start_min, max_value=end_max, key="investigation_heatmap_dates")
        with controls[1]:
            family_keys = list(FAMILIES)
            selected_families = st.multiselect("Model families", family_keys, default=family_keys,
                                               format_func=lambda key: FAMILIES[key], key="investigation_model_families")
        with controls[2]:
            variable_options = list(variables)
            if not variable_options:
                st.warning("No supported weather measurements are available in this dataset.")
                return
            variable = st.selectbox("Weather measurement", variable_options,
                                    format_func=lambda key: f"{variables[key][0]} ({variables[key][1]})",
                                    key="investigation_variable")
        if isinstance(date_range, tuple) and len(date_range) == 2:
            lo = pd.Timestamp(date_range[0]).tz_localize(tz)
            hi = (pd.Timestamp(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)).tz_localize(tz)
        else:
            lo = pd.Timestamp(date_range).tz_localize(tz)
            hi = (lo + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1))
        prepared = model_heatmap_data(predictions, lo, hi, selected_families,
                                      selected_timestamp=selected)
        in_range = prepared["all_timestamps"]
        if len(in_range) == 0:
            st.info("No saved model timestamps fall within this date range.")
            return
        if selected not in in_range:
            selected = in_range[-1]
        # Sync before rendering the widget so chart clicks, other pages, and the
        # selector all point to the same historical observation.
        st.session_state["selected_observation"] = selected
        st.session_state["_last_investigation_selection"] = selected
        if chart_selection_changed or st.session_state.get("investigation_timestamp_selector") not in in_range:
            st.session_state["investigation_timestamp_selector"] = selected
        st.markdown("#### Saved model outputs")
        st.caption("Select a point in the heatmap or use the exact timestamp control below.")
        _draw_model_heatmap(prepared, prepared["agreement"], FAMILIES, selected)
        if prepared["sampled_for_display"]:
            st.caption("The timestamp selector below contains every prediction timestamp in this interval, not only heatmap samples.")
        selected = st.selectbox("Exact timestamp to inspect", in_range,
                                format_func=_format_timestamp, key="investigation_timestamp_selector")
        st.session_state["selected_observation"] = selected
        selected_rows, votes, available, agreement_pct = _prediction_agreement(predictions, selected)
        obs_row = observations.loc[selected] if selected in observations.index else pd.Series(dtype=float)
        selected_value = pd.to_numeric(pd.Series([obs_row.get(variable, np.nan)]), errors="coerce").iloc[0]
        if available != 12:
            candidate_status = "Candidate status unavailable · incomplete model predictions"
        elif votes >= 8:
            candidate_status = "8/12 candidate · unusual model result, not a fault label"
        else:
            candidate_status = "Below the descriptive 8/12 candidate screen"
        _step_heading(1, "Selected observation", "The chosen time and measurement stay synchronized with the timeline and investigation charts.")
        with st.container(border=True, key="selected_observation_summary"):
            st.markdown(
                "<div class='wg-observation-banner'>"
                f"<div class='wg-observation-time'>{escape(_format_timestamp(selected))}</div>"
                f"<div class='wg-observation-status'>{escape(candidate_status)}</div></div>",
                unsafe_allow_html=True,
            )
            selected_summary = st.columns(3)
            selected_summary[0].metric("Selected measurement", f"{selected_value:g} {variables[variable][1]}" if pd.notna(selected_value) else "Unavailable")
            selected_summary[1].metric("Station record", "VILD0 · Ludhiana/Doraha")
            selected_summary[2].metric("Evidence interpretation", "Requires review")
            st.caption("Historical processed observation · station/provider lineage is incomplete · this is not a live reading.")

        _step_heading(2, "Model agreement", "Compare the saved vote count with the descriptive 8/12 screen; votes are not fault probabilities.")
        metrics = st.columns(4)
        metrics[0].metric("Configurations flagging", f"{votes}/{available}" if available else "Unavailable")
        metrics[1].metric("Model agreement", f"{agreement_pct:.1f}%" if available else "Unavailable",
                          help="Share of available saved configurations that flagged this reading. Not a probability.")
        metrics[2].metric("8/12 threshold", "Met" if available == 12 and votes >= 8 else "Not met" if available == 12 else "Unavailable")
        metrics[3].metric("Prediction coverage", f"{available}/12 available")
        st.caption("Model agreement is not probability of sensor failure. Grey heatmap cells and missing predictions are unavailable, not normal votes.")
        if len(selected_rows):
            family_votes = selected_rows.groupby("family").is_candidate.agg(
                flagged=lambda values: int(values.fillna(False).astype(bool).sum()),
                available=lambda values: int(values.notna().sum()),
            )
        else:
            family_votes = pd.DataFrame(columns=["flagged", "available"])
        family_columns = st.columns(3)
        for column, (family_key, family_label) in zip(family_columns, FAMILIES.items()):
            if family_key in family_votes.index:
                family_record = family_votes.loc[family_key]
                column.metric(f"{family_label} votes", f"{int(family_record.flagged)}/{int(family_record.available)}")
            else:
                column.metric(f"{family_label} votes", "Unavailable")
        st.caption("Family counts show each model family’s contribution to the saved vote total; the 8/12 screen is descriptive, not a calibrated optimum.")

    # Main observation visuals and right-side detail panel update from one selection.
    main, drawer = st.columns([2.1, 1], gap="large")
    diagnostic = variable_diagnostics(observations, variable, lo, hi)
    series_frame = diagnostic["series"]
    label, unit = variables[variable]
    with main:
        st.subheader(f"{label} through time")
        st.caption("The rolling line uses only preceding observations within the same saved segment.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=series_frame.index, y=series_frame.value, mode="lines",
                                 name=f"{label} ({unit})", line={"color": "#38BDF8", "width": 1.4}))
        if len(series_frame):
            fig.add_trace(go.Scatter(x=series_frame.index, y=series_frame.previous_rolling_mean, mode="lines",
                                     name="Previous six-observation mean", line={"color": "#2DD4BF", "dash": "dot"}))
        candidate_times = pd.DatetimeIndex(data["stability"].loc[data["stability"].configuration_votes.ge(8), "timestamp"])
        marker_times = candidate_times.intersection(series_frame.index)
        marker_values = series_frame.value.reindex(marker_times)
        fig.add_trace(go.Scatter(x=marker_times, y=marker_values, mode="markers", name="8/12 model candidate",
                                 marker={"color": "#FBBF24", "size": 8, "symbol": "diamond"}))
        if selected in series_frame.index and pd.notna(series_frame.loc[selected, "value"]):
            fig.add_trace(go.Scatter(x=[selected], y=[series_frame.loc[selected, "value"]], mode="markers",
                                     name="Selected reading", marker={"color": "#F87171", "size": 13, "symbol": "x"}))
        fig.update_layout(title=f"Historical {label.lower()} and model candidates", xaxis_title="Historical time",
                          yaxis_title=f"{label} ({unit})", clickmode="event+select")
        st.plotly_chart(_layout(fig, 390), width="stretch", key="investigation_variable_chart",
                        on_select="rerun", selection_mode="points")
        if diagnostic["count"]:
            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Values in range", f"{diagnostic['count']:,}")
            s2.metric("Missing values", f"{diagnostic['missing']:,}")
            s3.metric("Median", f"{diagnostic['median']:.2f} {unit}")
            s4.metric("Observed range", f"{diagnostic['minimum']:.2f} to {diagnostic['maximum']:.2f} {unit}")
        distribution_tab, temporal_tab, data_quality_tab = st.tabs(["Distribution", "Temporal context", "Data quality"])
        with distribution_tab:
            values = series_frame.value.dropna()
            if len(values):
                hcol, bcol = st.columns(2)
                with hcol:
                    hist = px.histogram(values, nbins=35, labels={"value": f"{label} ({unit})", "count": "Observations"},
                                        title=f"Distribution of {label.lower()}", color_discrete_sequence=["#38BDF8"])
                    st.plotly_chart(_layout(hist, 280), width="stretch")
                with bcol:
                    box = px.box(values, points="outliers", labels={"value": f"{label} ({unit})"},
                                 title=f"Spread of {label.lower()}", color_discrete_sequence=["#2DD4BF"])
                    st.plotly_chart(_layout(box, 280), width="stretch")
            else:
                st.info("No non-missing values in this interval.")
        with temporal_tab:
            context_start, context_end = selected - pd.Timedelta(hours=12), selected + pd.Timedelta(hours=12)
            context = variable_diagnostics(observations, variable, context_start, context_end)["series"]
            if len(context):
                temporal = go.Figure(go.Scatter(x=context.index, y=context.value, mode="lines+markers",
                                                name=f"{label} ({unit})", line={"color": "#38BDF8"}))
                temporal.add_vline(x=selected, line_dash="dash", line_color="#F87171")
                temporal.update_layout(title="Nearby observations around the selected time", xaxis_title="Historical time", yaxis_title=f"{label} ({unit})")
                st.plotly_chart(_layout(temporal, 300), width="stretch")
                change = context.loc[selected, "change_from_previous"] if selected in context.index else np.nan
                st.metric("Change from previous observation", f"{change:+.2f} {unit}" if pd.notna(change) else "Unavailable")
                st.caption("This is a descriptive change, not a validated sudden-change fault rule. E2 remains unavailable as independent evidence.")
            else:
                st.info("No nearby observations are available.")
        with data_quality_tab:
            missing_pct = 100 * diagnostic["missing"] / diagnostic["rows"] if diagnostic["rows"] else 0
            st.metric(f"Missing {label.lower()}", f"{diagnostic['missing']:,} / {diagnostic['rows']:,}", f"{missing_pct:.2f}% in the selected interval")
            st.caption("Missingness is reported as data availability and is not automatically treated as sensor-fault evidence.")
            with st.expander("View selected-range measurements"):
                st.dataframe(series_frame[["value", "change_from_previous", "previous_rolling_mean"]].rename(columns={
                    "value": f"{label} ({unit})", "change_from_previous": f"Change from previous ({unit})",
                    "previous_rolling_mean": f"Previous six-observation mean ({unit})"}), width="stretch")

    with drawer.container(border=True):
        st.subheader("Selected reading")
        st.caption("Detail panel · synchronized with the heatmap and timeline.")
        st.markdown(f"**{label}**  \n{_format_timestamp(selected)}")
        st.metric("Observed value", f"{selected_value:g} {unit}" if pd.notna(selected_value) else "Unavailable")
        st.markdown("**Station:** VILD0")
        st.caption("Station/provider provenance is incomplete.")
        render_station_map(root, "VILD0")
        st.markdown("#### Environmental context")
        context_rows = []
        for code, (display_name, display_unit) in variables.items():
            value = pd.to_numeric(pd.Series([obs_row.get(code, np.nan)]), errors="coerce").iloc[0]
            context_rows.append({"Measurement": display_name, "Value": f"{value:g} {display_unit}" if pd.notna(value) else "Unavailable"})
        st.dataframe(pd.DataFrame(context_rows), hide_index=True, width="stretch")
        with st.expander("Model configuration results for this reading"):
            model_rows = predictions.loc[predictions.timestamp.eq(selected)].copy()
            if len(model_rows):
                model_rows["family_label"] = model_rows.family.map(FAMILIES)
                st.dataframe(model_rows[["family_label", "configuration", "parameter", "parameter_value", "is_candidate"]], hide_index=True, width="stretch")
            else:
                st.info("No saved predictions exist at this timestamp.")

    _step_heading(3, "Evidence review", "Read each evidence source separately. Missing or ineligible evidence is not evidence that the station is healthy.")
    evidence_controls = st.columns([1.2, 1])
    with evidence_controls[0]:
        temporal_mode = st.radio("Temporal evidence view", ["real_time", "retrospective"], horizontal=True,
                                 format_func=lambda x: "Past observations only" if x == "real_time" else "Retrospective window",
                                 key="investigation_temporal_mode")
    with evidence_controls[1]:
        st.caption("Retrospective mode may inspect following timestamps; it is not a real-time result.")
    spatial = _load_spatial_tables(root)
    bundle = observation_evidence(selected, observations, predictions, data["stability"], data["episodes"], spatial,
                                  primary_variable=variable)
    temporal_result = temporal_verification(observations, selected, variable, mode=temporal_mode)
    temporal_state = {
        "SUPPORTING": "SUPPORTING_EVIDENCE",
        "CONFLICTING": "CONFLICTING_EVIDENCE",
        "NO_DETECTED_EVIDENCE": "NO_DETECTED_EVIDENCE",
        "UNAVAILABLE": "UNAVAILABLE",
    }.get(temporal_result["status"], "UNAVAILABLE")
    missing_values = int(pd.to_numeric(obs_row.reindex(list(variables)), errors="coerce").isna().sum()) if len(obs_row) else len(variables)
    quality_flags = bundle["quality_flags"]
    quality_flag_count = int(quality_flags.screening_flag.sum()) if len(quality_flags) and "screening_flag" in quality_flags else 0
    neighbor_ids = ", ".join(sorted(spatial)) if spatial else "none in the saved comparison files"
    evidence_items = [
        ("E1 · Model stability", bundle["evidence_states"]["E1"],
         f"{votes}/{available} saved configurations flagged this timestamp. This records configuration agreement, not fault probability or accuracy."),
        ("E2 · Temporal evidence", temporal_state,
         f"{temporal_result['reason']} Context is limited to the selected variable’s local history; it does not establish a regional event or diagnose a sensor."),
        ("E3 · Spatial evidence", "UNAVAILABLE",
         f"Saved comparison station IDs available: {neighbor_ids}. Independent provider lineage, exact sensor identity, and event-level adjudication are not verified, so spatial agreement is not decision-eligible."),
        ("E4 · Physical and data quality", bundle["evidence_states"]["E4"],
         f"{missing_values} of {len(variables)} selected-time measurements are missing; {quality_flag_count} broad screening flags. Missingness and broad checks do not confirm a hardware fault."),
    ]
    evidence_columns = st.columns(2)
    for index, (title, state, detail) in enumerate(evidence_items):
        with evidence_columns[index % 2].container(border=True):
            evidence_panel(title, state, detail)
    with st.expander("Supporting, conflicting, and unavailable details"):
        st.markdown("**Supporting** means a screen fired. **Conflicting** means the specified screens disagree. **No detected evidence** means a screen did not fire. **Unavailable** means required evidence could not be assessed.")
        st.json({key: value for key, value in temporal_result.items() if key != "timestamp"})
        if len(quality_flags):
            st.dataframe(quality_flags, hide_index=True, width="stretch")

    _step_heading(4, "Overall interpretation", "The summary describes what the available evidence can support and what remains unresolved.")
    with st.container(border=True, key="investigation_overall_interpretation"):
        st.markdown(
            "<div class='wg-interpretation'><b>Uncertain / insufficient evidence</b><br>"
            "A candidate reading is not a confirmed sensor fault. No combined E1–E4 fault decision is made here.</div>",
            unsafe_allow_html=True,
        )
        interpretation_columns = st.columns(3)
        interpretation_columns[0].markdown(f"**Model screen**  \n{votes}/{available} saved configuration votes; threshold {'met' if available == 12 and votes >= 8 else 'not met' if available == 12 else 'unavailable'}.")
        interpretation_columns[1].markdown(f"**Evidence on this reading**  \nE2: {temporal_result['status'].replace('_', ' ').title()} · E3: Unavailable · E4: {bundle['evidence_states']['E4'].replace('_', ' ').title()}.")
        interpretation_columns[2].markdown("**Still unknown**  \nIndependent station corroboration and adjudicated sensor-fault truth are not available.")
        st.caption("ANOMALY ≠ FAULT. This is a historical evidence review, not a live monitoring or maintenance decision.")

    st.subheader("How did each model family behave?")
    profiles = build_model_education(data)["profiles"]
    date_predictions = predictions.loc[predictions.timestamp.between(lo, hi)]
    observed_series = observations.loc[(observations.index >= lo) & (observations.index <= hi), variable]
    for family, label_family in FAMILIES.items():
        family_rows = date_predictions.loc[date_predictions.family.eq(family)]
        profile = profiles[family]
        with st.expander(f"{label_family} · {len(family_rows.configuration.unique())} configurations"):
            st.write(profile["simple"])
            st.caption(profile["difference"] + " " + profile["preprocessing"])
            config_summary = (family_rows.groupby("configuration").is_candidate.agg(
                anomaly_count=lambda s: int(s.fillna(False).astype(bool).sum()),
                available=lambda s: int(s.notna().sum())).reset_index())
            config_summary["normal_count"] = config_summary.available - config_summary.anomaly_count
            config_summary["anomaly_share_pct"] = np.where(config_summary.available.gt(0),
                                                             config_summary.anomaly_count / config_summary.available * 100, np.nan)
            st.dataframe(config_summary, hide_index=True, width="stretch")
            outcome_distribution = config_summary.melt(id_vars="configuration", value_vars=["normal_count", "anomaly_count"],
                                                       var_name="Saved label", value_name="Test timestamps")
            outcome_distribution["Saved label"] = outcome_distribution["Saved label"].replace({"normal_count": "Normal", "anomaly_count": "Anomaly"})
            distribution_fig = px.bar(outcome_distribution, x="configuration", y="Test timestamps", color="Saved label", barmode="group",
                                      title=f"{label_family}: normal and anomaly labels in selected period",
                                      color_discrete_map={"Normal": "#38BDF8", "Anomaly": "#FBBF24"})
            st.plotly_chart(_layout(distribution_fig, 260), width="stretch")
            settings = pd.DataFrame([{"Configuration": item["name"], "Varied parameter": item["parameter"],
                                      "Value": item["value"], "Anomaly count": item["anomalies"],
                                      "Anomaly rate (%)": item["anomaly_percentage"]}
                                     for item in profile["configs"]])
            st.dataframe(settings, hide_index=True, width="stretch")
            model_fig = go.Figure()
            model_fig.add_trace(go.Scatter(x=observed_series.index, y=observed_series, mode="lines",
                                           name=f"{variables[variable][0]} ({unit})", line={"color": "#38BDF8", "width": 1.2}))
            for config in [item["name"] for item in profile["configs"]]:
                hits = family_rows.loc[(family_rows.configuration.eq(config)) & family_rows.is_candidate.fillna(False).astype(bool), "timestamp"]
                hit_times = pd.DatetimeIndex(hits).intersection(observed_series.index)
                if len(hit_times):
                    model_fig.add_trace(go.Scatter(x=hit_times, y=observed_series.reindex(hit_times), mode="markers",
                                                   name=config, marker={"size": 7}, customdata=[config] * len(hit_times),
                                                   hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Configuration: %{customdata}<extra></extra>"))
            if selected in observed_series.index:
                model_fig.add_vline(x=selected, line_color="#F87171", line_dash="dash")
            model_fig.update_layout(title=f"{label_family}: saved anomaly labels", xaxis_title="Historical time", yaxis_title=f"{variables[variable][0]} ({unit})", clickmode="event+select")
            model_key = {"IsolationForest": "isolation_forest_profile", "LocalOutlierFactor": "lof_profile", "OneClassSVM": "oneclass_svm_profile"}[family]
            st.plotly_chart(_layout(model_fig, 300), width="stretch", key=model_key,
                            on_select="rerun", selection_mode="points")
            st.caption("Saved binary predictions only; no continuous anomaly scores or feature importance are available.")

