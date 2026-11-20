"""Map-first historical dashboard backed only by saved observations and predictions."""
from __future__ import annotations

import math
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from ui.integrated_evidence_panel import build_dashboard_assessment, render_integrated_evidence_panel

MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
VARIABLES = {
    "temp": ("Temperature", "°C"),
    "dwpt": ("Dew point", "°C"),
    "rhum": ("Relative humidity", "%"),
    "prcp": ("Precipitation", "mm"),
    "wspd": ("Wind speed", "km/h"),
    "pres": ("Pressure", "hPa"),
}
STATION_INFO = {
    "VILD0": ("Ludhiana / Doraha record", "Primary processed series"),
    "42099": ("Ludhiana (WMO 42099)", "Neighbor source records"),
    "42101": ("Patiala (WMO 42101)", "Neighbor source records"),
}
SOURCE_FILES = {
    "VILD0": "outputs/phase06_controlled_e3_validation/raw_station_data/VILD0_hourly_source_level.csv",
    "42099": "outputs/phase04_provenance_aware_collection/raw_station_data/42099_hourly_source_level.csv",
    "42101": "outputs/phase04_provenance_aware_collection/raw_station_data/42101_hourly_source_level.csv",
}


@st.cache_data(show_spinner=False)
def _load_station_records(root_text: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Load only saved, georeferenced station records and source rows."""
    root = Path(root_text)
    path = root / "outputs/phase06_controlled_e3_validation/station_zone_assignment.csv"
    if not path.is_file():
        return pd.DataFrame(columns=["station_id", "latitude", "longitude"]), {}
    records = pd.read_csv(path)
    records = records.loc[records.station_id.astype(str).isin(STATION_INFO)].copy()
    records = records.dropna(subset=["latitude", "longitude"])
    records["station_id"] = records.station_id.astype(str)
    sources: dict[str, pd.DataFrame] = {}
    for station_id, relative_path in SOURCE_FILES.items():
        source_path = root / relative_path
        if not source_path.is_file():
            continue
        frame = pd.read_csv(source_path)
        if "time" not in frame:
            continue
        frame["time"] = pd.to_datetime(frame.time, utc=True, errors="coerce")
        frame = frame.dropna(subset=["time"]).set_index("time").sort_index()
        sources[station_id] = frame
    return records, sources


def _timestamp_votes(stability: pd.DataFrame, selected: pd.Timestamp) -> tuple[int | None, int]:
    rows = stability.loc[stability.timestamp.eq(selected)]
    if rows.empty:
        return None, 0
    row = rows.iloc[0]
    available = int(row.get("available_configurations", 12))
    return int(row.get("configuration_votes", 0)), available


def _source_values(source: pd.DataFrame | None, selected_utc: pd.Timestamp) -> tuple[pd.Series, str]:
    if source is None or selected_utc not in source.index:
        return pd.Series(dtype=object), "No exact source row at this timestamp"
    rows = source.loc[[selected_utc]] if isinstance(source.loc[selected_utc], pd.Series) else source.loc[[selected_utc]]
    row = rows.iloc[0] if len(rows) == 1 else rows.iloc[0]
    source_name = str(row.get("source", "source-level record"))
    return row, f"Exact source-level timestamp · {source_name} · {len(rows)} row(s)"


def _selected_value(row: pd.Series, source_rows: pd.DataFrame | None, source_code: str,
                    key: str, selected_utc: pd.Timestamp) -> str:
    if source_code == "VILD0":
        value = pd.to_numeric(pd.Series([row.get(key)]), errors="coerce").iloc[0]
        return "Unavailable" if pd.isna(value) else f"{value:g} {VARIABLES[key][1]}"
    if source_rows is None or selected_utc not in source_rows.index:
        return "Unavailable at this exact timestamp"
    rows = source_rows.loc[[selected_utc]]
    values = pd.to_numeric(rows.get(key), errors="coerce").dropna().unique() if key in rows else []
    if len(values) == 0:
        return "Unavailable in source record"
    if len(values) > 1:
        return f"Multiple source values ({len(values)})"
    return f"{values[0]:g} {VARIABLES[key][1]}"


def _selected_station_status(station_id: str, votes: int | None, available: int) -> tuple[str, list[int]]:
    if station_id != "VILD0" or votes is None or available != 12:
        return "Unknown · model status unavailable", [148, 163, 184, 220]
    if votes >= 8:
        return f"E1 candidate · {votes}/12 (not a fault label)", [239, 68, 68, 235]
    return f"No 8/12 E1 candidate · {votes}/12", [56, 189, 248, 230]


def _plot_style(fig: go.Figure, height: int = 220) -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#CBD5E1", "family": "Inter, Segoe UI, sans-serif", "size": 11},
        margin={"l": 8, "r": 8, "t": 34, "b": 8},
        xaxis={"gridcolor": "#26384E", "zerolinecolor": "#26384E"},
        yaxis={"gridcolor": "#26384E", "zerolinecolor": "#26384E"},
        legend={"orientation": "h", "y": 1.1, "x": 0},
    )
    return fig


def _playback_seconds(start: pd.Timestamp, end: pd.Timestamp) -> float:
    days = max(1.0, (end.normalize() - start.normalize()).total_seconds() / 86400 + 1)
    if days <= 366:
        return 10.0
    return min(120.0, 10.0 * days / 365.0)


def _set_station_details_open(open_state: bool) -> None:
    st.session_state["home_details_open"] = open_state


@st.fragment(run_every=0.8)
def render_home_dashboard(data: dict, root_text: str) -> None:
    obs = data["observations"]
    predictions = data["predictions"]
    stability = data["stability"].copy()
    if stability["timestamp"].dt.tz is None:
        stability["timestamp"] = pd.to_datetime(stability.timestamp, utc=True).dt.tz_convert(obs.index.tz)
    else:
        stability["timestamp"] = stability.timestamp.dt.tz_convert(obs.index.tz)
    records, source_frames = _load_station_records(root_text)

    latest = obs.index.max()
    tz = obs.index.tz
    min_date, max_date = obs.index.min().date(), latest.date()
    default_start = max(min_date, (latest - pd.Timedelta(days=29)).date())
    date_selection = st.date_input(
        "Historical period · year / month / day", value=(default_start, max_date), min_value=min_date,
        max_value=max_date, key="home_date_range",
        help="Filter actual saved historical timestamps. This is not a live data feed.",
    )
    if isinstance(date_selection, tuple) and len(date_selection) == 2:
        start_date, end_date = date_selection
    else:
        start_date = end_date = date_selection
    start_ts = pd.Timestamp(start_date).tz_localize(tz)
    end_ts = (pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)).tz_localize(tz)
    timeline = obs.index[(obs.index >= start_ts) & (obs.index <= end_ts)]
    if timeline.empty:
        st.info("No saved timestamps fall within this date range.")
        return

    signature = (str(start_date), str(end_date))
    if st.session_state.get("_home_range_signature") != signature:
        st.session_state["_home_range_signature"] = signature
        st.session_state["home_playing"] = False
        st.session_state["home_timeline_slider"] = len(timeline) - 1
    if "home_timeline_slider" not in st.session_state:
        st.session_state["home_timeline_slider"] = len(timeline) - 1
    frame_index = max(0, min(int(st.session_state["home_timeline_slider"]), len(timeline) - 1))

    if st.session_state.get("home_playing"):
        started_at = st.session_state.get("home_play_started_at", time.monotonic())
        origin = int(st.session_state.get("home_play_origin", frame_index))
        speed = float(st.session_state.get("home_play_speed", 1.0))
        remain = max(0, len(timeline) - 1 - origin)
        duration = _playback_seconds(timeline[origin], timeline[-1])
        elapsed = max(0.0, time.monotonic() - started_at)
        frame_index = min(len(timeline) - 1, origin + int(math.floor(remain * elapsed * speed / duration)))
        st.session_state["home_timeline_slider"] = frame_index
        if frame_index >= len(timeline) - 1:
            st.session_state["home_playing"] = False

    selected_ts = timeline[frame_index]
    st.session_state["selected_observation"] = selected_ts
    # The detail selector is the source of truth after a user chooses a station.
    # Map picks update this key before the selector is rendered below.
    selected_station = st.session_state.get(
        "home_detail_station_select", st.session_state.get("home_station_id", "VILD0")
    )
    details_open = st.session_state.get("home_details_open", True)

    st.markdown(
        "<div class='wg-eyebrow'>HISTORICAL WEATHER INTELLIGENCE · ASIA/KOLKATA</div>"
        "<h1 class='wg-home-title'>Station overview</h1>"
        "<div class='wg-subtitle'>Explore saved observations and model candidates in their historical context.</div>",
        unsafe_allow_html=True,
    )
    st.caption("Processed research snapshot · not a live feed · a model candidate is not a confirmed fault.")

    layout = st.columns([0.92, 2.15, 1.02], gap="small")

    # Left analytics panel: data and candidate context respond to both station and date range.
    with layout[0]:
        with st.expander("Analytics", expanded=True):
            st.caption("Selected station · selected period")
            variable = st.selectbox(
                "Measurement", list(VARIABLES),
                format_func=lambda code: f"{VARIABLES[code][0]} ({VARIABLES[code][1]})",
                key="home_analytics_variable",
            )
            names = {sid: STATION_INFO[sid][0] for sid in STATION_INFO if sid in set(records.station_id) if len(records)}
            if not names:
                names = {"VILD0": STATION_INFO["VILD0"][0]}
            if selected_station not in names:
                selected_station = "VILD0" if "VILD0" in names else next(iter(names))
                st.session_state["home_station_id"] = selected_station
            st.caption(f"{names.get(selected_station, selected_station)}")

            if selected_station == "VILD0":
                chart_series = obs.loc[(obs.index >= start_ts) & (obs.index <= end_ts), variable].dropna()
            else:
                src = source_frames.get(selected_station)
                chart_series = (src.loc[(src.index >= start_ts.tz_convert('UTC')) & (src.index <= end_ts.tz_convert('UTC')), variable].dropna()
                                if src is not None and variable in src.columns else pd.Series(dtype=float))
            if len(chart_series) > 900:
                chart_series = chart_series.iloc[::max(1, math.ceil(len(chart_series) / 900))]
            if len(chart_series):
                trend = go.Figure(go.Scatter(
                    x=chart_series.index, y=chart_series.values, mode="lines",
                    line={"color": "#38BDF8", "width": 1.4}, name=VARIABLES[variable][0],
                ))
                if selected_station == "VILD0":
                    cand = stability.loc[
                        stability.configuration_votes.ge(8)
                        & stability.timestamp.between(start_ts, end_ts), "timestamp"
                    ]
                    cand = pd.DatetimeIndex(cand).intersection(chart_series.index)
                    if len(cand):
                        trend.add_trace(go.Scatter(
                            x=cand, y=chart_series.reindex(cand), mode="markers", name="8/12 E1 candidate",
                            marker={"color": "#EF4444", "size": 6, "symbol": "diamond"},
                        ))
                trend.update_layout(title=f"{VARIABLES[variable][0]} trend", xaxis_title="Historical time", yaxis_title=VARIABLES[variable][1])
                st.plotly_chart(_plot_style(trend, 230), width="stretch", key="home_analytics_trend")
                st.caption("Red diamonds mark saved E1 candidates; they do not confirm faults.")
            else:
                st.info("No values for this measurement in the selected period.")

            votes, available = _timestamp_votes(stability, selected_ts)
            st.metric("Configurations flagging", f"{votes}/{available}" if votes is not None else "Unavailable")
            st.caption(f"{len(timeline):,} saved timestamps in this timeline window.")

    # Central map: station record coordinates only. No synthetic locations or regional labels.
    with layout[1]:
        with st.container(border=True):
            map_header, map_hint = st.columns([1.3, 1])
            with map_header:
                st.markdown("### Station map")
            with map_hint:
                st.caption("Select a marker to inspect its record")
            votes, available = _timestamp_votes(stability, selected_ts)
            points = records.copy()
            if points.empty:
                st.info("Saved station-record coordinates are unavailable; no markers were placed.")
            else:
                marker_data = []
                for row in points.itertuples(index=False):
                    station_id = str(row.station_id)
                    status, color = _selected_station_status(station_id, votes, available)
                    marker_data.append({
                        "station_id": station_id, "name": STATION_INFO[station_id][0],
                        "latitude": float(row.latitude), "longitude": float(row.longitude),
                        "status": status, "color": color,
                    })
                marker_frame = pd.DataFrame(marker_data)
                phase = (time.monotonic() % 1.8) / 1.8
                pulse_radius = 900 + int(1700 * phase)
                pulse_frame = marker_frame.copy()
                pulse_frame["pulse_color"] = pulse_frame.color.map(lambda color: [color[0], color[1], color[2], max(12, int(48 * (1 - phase)))])
                pulse_layer = pdk.Layer(
                    "ScatterplotLayer", pulse_frame, id="station-ripples", pickable=False,
                    get_position="[longitude, latitude]", get_radius=pulse_radius,
                    radius_units="meters", radius_min_pixels=13, radius_max_pixels=38,
                    get_fill_color="pulse_color", stroked=False,
                )
                point_layer = pdk.Layer(
                    "ScatterplotLayer", marker_frame, id="station-points", pickable=True,
                    auto_highlight=True, get_position="[longitude, latitude]", get_radius=1050,
                    radius_units="meters", radius_min_pixels=8, radius_max_pixels=16,
                    get_fill_color="color", get_line_color=[226, 232, 240, 230],
                    line_width_min_pixels=1, stroked=True,
                )
                center_lat = float(marker_frame.latitude.mean())
                center_lon = float(marker_frame.longitude.mean())
                deck = pdk.Deck(
                    layers=[pulse_layer, point_layer],
                    initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=7.1, pitch=0, bearing=0),
                    map_style=MAP_STYLE,
                    tooltip={"html": "<b>{name}</b><br/>{status}<br/>Record coordinates · sensor point unconfirmed",
                             "style": {"backgroundColor": "#111c2e", "color": "#f1f5f9"}},
                )
                map_event = st.pydeck_chart(deck, width="stretch", height=535,
                                           on_select="rerun", selection_mode="single-object", key="home_station_map")
                try:
                    clicked = map_event.selection.objects.get("station-points", [])
                    if clicked:
                        clicked_id = str(clicked[-1].get("station_id", ""))
                        if clicked_id in STATION_INFO:
                            st.session_state["home_station_id"] = clicked_id
                            st.session_state["home_detail_station_select"] = clicked_id
                            selected_station = clicked_id
                            st.session_state["home_details_open"] = True
                            details_open = True
                except (AttributeError, KeyError, TypeError):
                    pass
                st.caption("Map points show station-record coordinates. Exact sensor locations and independent E3 corroboration are unverified.")
                legend = st.columns(3)
                legend[0].markdown("🔵 **No 8/12 candidate**")
                legend[1].markdown("🔴 **E1 candidate**")
                legend[2].markdown("⚪ **Unknown / unavailable**")
                st.caption("Orange regional status is intentionally unassigned: E3 has insufficient independent evidence. No marker color means a confirmed fault.")

    # Right-side station details panel; exact timestamp values come from saved observations/exports.
    with layout[2]:
        if details_open:
            with st.container(border=True):
                top, close = st.columns([1, 0.2])
                with top:
                    st.markdown("### Station details")
                with close:
                    st.button(
                        "×", key="close_station_details", help="Close station details",
                        on_click=_set_station_details_open, args=(False,),
                    )
                available_ids = [sid for sid in STATION_INFO if sid in set(records.station_id)] if len(records) else ["VILD0"]
                if not available_ids:
                    available_ids = ["VILD0"]
                if selected_station not in available_ids:
                    selected_station = available_ids[0]
                selected_station = st.selectbox(
                    "Station record", available_ids,
                    index=available_ids.index(selected_station),
                    format_func=lambda sid: f"{sid} · {STATION_INFO[sid][0]}",
                    key="home_detail_station_select",
                )
                st.session_state["home_station_id"] = selected_station
                meta = records.loc[records.station_id.eq(selected_station)] if len(records) else pd.DataFrame()
                station_row = obs.loc[selected_ts] if selected_station == "VILD0" else pd.Series(dtype=float)
                source = source_frames.get(selected_station)
                source_match = None
                source_note = "Processed historical snapshot"
                if selected_station != "VILD0":
                    source_match, source_note = _source_values(source, selected_ts.tz_convert("UTC"))
                votes, available = _timestamp_votes(stability, selected_ts)
                status, _ = _selected_station_status(selected_station, votes, available)
                st.markdown(f"**{status}**")
                st.caption(f"Selected time · {selected_ts.strftime('%Y-%m-%d %H:%M %Z')}")
                if len(meta):
                    record = meta.iloc[0]
                    st.caption(f"{float(record.latitude):.5f}, {float(record.longitude):.5f} · station-record point")
                st.caption(source_note)
                if selected_station == "VILD0" and votes is not None and votes >= 8:
                    st.markdown("<div class='wg-candidate-note'>Unusual model candidate · not a confirmed sensor fault</div>", unsafe_allow_html=True)
                for key, (label, unit) in VARIABLES.items():
                    value = _selected_value(station_row, source, selected_station, key, selected_ts.tz_convert("UTC"))
                    is_available_value = value != "Unavailable" and "Unavailable" not in value and "Multiple source values" not in value
                    color = "#EF4444" if selected_station == "VILD0" and votes is not None and votes >= 8 and is_available_value else "#F1F5F9"
                    st.markdown(f"<div class='wg-reading-row'><span>{label}</span><strong style='color:{color}'>{value}</strong></div>", unsafe_allow_html=True)
                st.markdown("#### Integrated evidence")
                assessment_key = (selected_station, selected_ts.isoformat(), variable)
                if st.session_state.get("_home_assessment_key") != assessment_key:
                    st.session_state["_home_assessment_key"] = assessment_key
                    st.session_state["_home_assessment_result"] = build_dashboard_assessment(
                        data, root_text, selected_ts, selected_station, variable,
                    )
                with st.expander("View E1–E4 assessment", expanded=False):
                    render_integrated_evidence_panel(st.session_state["_home_assessment_result"])
                if selected_station != "VILD0":
                    st.caption("Neighbor source rows are available only for some dates. They are context, not independent validation.")
                st.button(
                    "Open station details", key="open_station_details",
                    on_click=_set_station_details_open, args=(True,),
                )
        else:
            with st.container(border=True):
                st.markdown("### Station details hidden")
                st.button(
                    "Open station details", key="open_station_details_hidden",
                    on_click=_set_station_details_open, args=(True,),
                )

    # Supporting histories use only the selected station's saved rows and the active date range.
    with st.container(border=True):
        st.markdown("### Historical context")
        st.caption("Charts update with the selected station and date range. Gaps stay missing; no measurements are interpolated.")
        source = source_frames.get(selected_station) if selected_station != "VILD0" else None
        if selected_station == "VILD0":
            history = obs.loc[(obs.index >= start_ts) & (obs.index <= end_ts)]
        elif source is not None:
            history = source.loc[(source.index >= start_ts.tz_convert("UTC")) & (source.index <= end_ts.tz_convert("UTC"))]
        else:
            history = pd.DataFrame()
        history_columns = st.columns(2)
        for index, (variable_code, (label, unit)) in enumerate(
            (item for item in VARIABLES.items() if item[0] in {"temp", "rhum", "wspd", "pres"})
        ):
            with history_columns[index % 2]:
                st.markdown(f"**{label} · {unit}**")
                if variable_code not in history.columns or history.empty:
                    st.info(f"{label} history is unavailable for this station and period.")
                    continue
                values = pd.to_numeric(history[variable_code], errors="coerce")
                valid = values.dropna()
                if valid.empty:
                    st.info(f"No recorded {label.lower()} values in this period.")
                    continue
                if len(valid) > 900:
                    valid = valid.iloc[::max(1, math.ceil(len(valid) / 900))]
                history_fig = go.Figure(go.Scatter(
                    x=valid.index, y=valid.values, mode="lines",
                    line={"color": "#38BDF8", "width": 1.3}, name=label,
                ))
                if selected_ts in valid.index:
                    history_fig.add_vline(x=selected_ts, line_color="#F59E0B", line_dash="dash", line_width=1)
                history_fig.update_layout(title=label, xaxis_title="Historical time", yaxis_title=unit, showlegend=False)
                st.plotly_chart(_plot_style(history_fig, 185), width="stretch", key=f"home_history_{selected_station}_{variable_code}")
                st.caption(f"{len(valid):,} plotted valid values · {int(values.isna().sum()):,} missing in source rows")

        candidates = stability.loc[
            stability.configuration_votes.ge(8) & stability.timestamp.between(start_ts, end_ts),
            "timestamp",
        ]
        if len(candidates):
            monthly = candidates.dt.strftime("%Y-%m").value_counts().sort_index().rename_axis("month").rename("timestamps").reset_index()
            frequency = px.bar(monthly, x="month", y="timestamps", labels={"month": "Month", "timestamps": "Saved 8/12 candidates"},
                               title="Candidate frequency by month", color_discrete_sequence=["#F59E0B"])
            st.plotly_chart(_plot_style(frequency, 230), width="stretch", key="home_candidate_frequency")
        else:
            st.info("No saved 8/12 candidate timestamps fall within this selected period.")
        st.caption("Candidate frequency is descriptive and does not estimate fault prevalence. Candidate counts are available for the primary held-out station only.")

    # Persistent timeline and real-data replay controls.
    with st.container(border=True):
        controls = st.columns([.72, .72, .72, .72, .8, .72, 2.0])
        if "home_playing" not in st.session_state:
            st.session_state["home_playing"] = False
        if controls[0].button("◀ Prev", key="home_prev_button"):
            st.session_state["home_playing"] = False
            st.session_state["home_timeline_slider"] = max(0, frame_index - 1)
            frame_index = st.session_state["home_timeline_slider"]
        if controls[1].button("▶ Play" if not st.session_state["home_playing"] else "▶ Playing", key="home_play_button", disabled=st.session_state["home_playing"]):
            st.session_state["home_play_origin"] = frame_index
            st.session_state["home_play_started_at"] = time.monotonic()
            st.session_state["home_play_speed"] = float(st.session_state.get("home_play_speed_selector", "1x")[:-1])
            st.session_state["home_playing"] = True
        if controls[2].button("Ⅱ Pause", key="home_pause_button", disabled=not st.session_state["home_playing"]):
            st.session_state["home_playing"] = False
        if controls[3].button("↺ Reset", key="home_reset_button"):
            st.session_state["home_playing"] = False
            st.session_state["home_timeline_slider"] = 0
            frame_index = 0
        with controls[4]:
            speed_label = st.selectbox("Speed", ["1x", "1.5x", "2x"], key="home_play_speed_selector", label_visibility="collapsed")
        if controls[5].button("Next ▶", key="home_next_button"):
            st.session_state["home_playing"] = False
            st.session_state["home_timeline_slider"] = min(len(timeline) - 1, frame_index + 1)
            frame_index = st.session_state["home_timeline_slider"]
        if st.session_state.get("home_playing"):
            speed = float(speed_label[:-1])
            if speed != st.session_state.get("home_play_speed", 1.0):
                st.session_state["home_play_speed"] = speed
                st.session_state["home_play_started_at"] = time.monotonic()
                st.session_state["home_play_origin"] = frame_index
        slider_index = st.slider(
            "Historical timestamp", min_value=0, max_value=max(0, len(timeline) - 1),
            step=1, key="home_timeline_slider", label_visibility="collapsed",
        )
        if not st.session_state.get("home_playing"):
            frame_index = int(slider_index)
            selected_ts = timeline[frame_index]
            st.session_state["selected_observation"] = selected_ts
        duration = _playback_seconds(timeline[0], timeline[-1])
        st.caption(f"{selected_ts.strftime('%Y-%m-%d %H:%M %Z')} · frame {frame_index + 1:,} of {len(timeline):,} · replay duration {duration:.0f}s at 1× (all timestamps are saved historical records)")
