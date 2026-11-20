"""Explicit validation and isolated 12-configuration analysis for new CSV data."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from services.uploaded_analysis import (BASE_VARIABLES, CANONICAL_UNITS,
                                        UNIT_CONVERSIONS,
                                        prepare_uploaded_weather_data,
                                        run_uploaded_weather_analysis)

VARIABLE_NAMES = {"temp": "Air temperature", "dwpt": "Dew point", "rhum": "Relative humidity",
                  "prcp": "Precipitation", "wspd": "Wind speed", "pres": "Air pressure"}


def _show_uploaded_results(result):
    metadata = result["metadata"]
    st.success(f"New local model run completed · {metadata['run_id']}")
    st.caption(f"User-declared station label: {metadata['station_id_user_declared_unverified']} · source file: {metadata['input_filename']} · SHA-256: {metadata['input_sha256']}")
    st.warning("This run trained new models on the uploaded file's earlier 80% and evaluated the later 20%. No fitted estimators were saved. This is not real-world fault validation.")
    config_results = result["configuration_results"]
    chart_data = result["predictions"].reset_index()
    agreement = result["stability"]
    high = agreement.index[agreement.configuration_votes.ge(8)]
    all_times = agreement.index
    default_time = high[-1] if len(high) else all_times[-1]
    selected = st.selectbox("Choose a held-out reading from this upload", all_times,
                            index=all_times.get_loc(default_time), key="uploaded_analysis_timestamp",
                            format_func=lambda ts: pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M %Z"))
    row = result["observations"].loc[selected]
    votes = chart_data.loc[chart_data.timestamp.eq(selected), "is_candidate"].astype(bool)
    n_votes, n_available = int(votes.sum()), len(votes)
    detail, other = st.columns([1.3, 1])
    with detail.container(border=True):
        st.subheader("Selected uploaded reading")
        st.markdown(f"**{pd.Timestamp(selected).strftime('%Y-%m-%d %H:%M %Z')}** · station label {metadata['station_id_user_declared_unverified']} (user-declared, unverified)")
        st.metric("Model agreement", f"{n_votes}/{n_available} configurations", help="Agreement among this new local fit; not a fault probability.")
        st.metric("Interpretation", "Uncertain / insufficient evidence")
        st.caption("This uploaded-file run has model results, but no verified neighboring-station evidence or real fault labels. An anomaly flag alone cannot confirm a sensor problem.")
        env = pd.DataFrame([{"Measurement": VARIABLE_NAMES[name], "Value": "Unavailable" if pd.isna(row[name]) else f"{row[name]:g} {CANONICAL_UNITS[name]}"} for name in BASE_VARIABLES])
        st.dataframe(env, hide_index=True, width="stretch")
    with other:
        st.subheader("Saved configuration results")
        st.dataframe(config_results, hide_index=True, width="stretch")
        st.metric("8/12 candidate timestamps", f"{int(agreement.configuration_votes.ge(8).sum()):,}")
    st.caption(f"Run outputs are isolated at `{Path(result['output_dir']).as_posix()}`. Uploaded source rows were not written to disk.")
    with st.expander("Run provenance and preprocessing"):
        st.json(metadata)


def render_new_csv_analysis(root):
    st.subheader("Analyze a new station CSV")
    st.caption("Uploads are processed as a separate analysis run. They are never appended to or used to overwrite the verified historical snapshots.")
    mode = st.radio(
        "Choose an isolated upload workflow",
        ["Existing model inference", "Retraining / refitting"],
        horizontal=True,
        key="uploaded_analysis_mode",
        help="Inference would require saved fitted estimators. Retraining fits a separate new local model version only after explicit confirmation.",
    )
    if mode == "Existing model inference":
        st.warning("Inference is unavailable: this repository contains saved historical predictions but no persisted fitted estimator objects or compatible inference bundle. No model will be fit in this mode.")
    else:
        st.info("This separate workflow validates the upload first, then fits a new 12-configuration model only after you explicitly run it. Existing research artifacts are not overwritten.")
    upload = st.file_uploader("Choose a weather-station CSV", type=["csv"], key="new_station_csv")
    if upload is None:
        return
    content = upload.getvalue()
    if len(content) > 25 * 1024 * 1024:
        st.error("This interface supports CSV files up to 25 MB.")
        return
    file_hash = sha256(content).hexdigest()
    try:
        raw = pd.read_csv(BytesIO(content))
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
        st.error(f"Could not read the uploaded CSV: {exc}")
        return
    if raw.empty:
        st.error("The uploaded CSV has no data rows.")
        return
    st.caption(f"{len(raw):,} rows · {len(raw.columns)} columns · SHA-256 {file_hash}")
    schema = pd.DataFrame({
        "Column": raw.columns.astype(str),
        "Detected type": [str(dtype) for dtype in raw.dtypes],
        "Missing values": [int(raw[column].isna().sum()) for column in raw.columns],
    })
    st.caption("Schema compatibility: manual mapping is required for a timestamp and the six model weather variables; units and hourly cadence are validated before analysis.")
    st.dataframe(schema, hide_index=True, width="stretch")
    with st.expander("Preview uploaded columns and first rows"):
        st.dataframe(raw.head(20), hide_index=True, width="stretch")
    with st.form("new_csv_mapping_form"):
        timestamp_column = st.selectbox("Timestamp column", list(raw.columns), key="upload_timestamp_column")
        station_id = st.text_input("Station label (user-declared; not verified metadata)", value="Uploaded station", key="upload_station_label")
        timezone_name = st.text_input("Timezone for timezone-naive timestamps", value="Asia/Kolkata", key="upload_timezone")
        st.markdown("**Map the six weather variables used by this model protocol and declare each source unit.**")
        mapping, units = {}, {}
        for variable in BASE_VARIABLES:
            col, unit_col = st.columns([1.1, 1])
            with col:
                default = raw.columns.get_loc(variable) + 1 if variable in raw.columns else 0
                mapping[variable] = st.selectbox(f"{VARIABLE_NAMES[variable]} column", ["— Select —", *raw.columns], index=default, key=f"upload_map_{variable}")
            with unit_col:
                available_units = list(UNIT_CONVERSIONS[variable])
                default_unit = available_units.index(CANONICAL_UNITS[variable])
                units[variable] = st.selectbox(f"Source unit for {variable}", available_units, index=default_unit, key=f"upload_unit_{variable}")
        validate = st.form_submit_button("Validate mapping and prepare a separate run")
    signature = (file_hash, timestamp_column, tuple(sorted(mapping.items())), tuple(sorted(units.items())), timezone_name, station_id)
    previous_signature = st.session_state.get("uploaded_analysis_signature")
    if previous_signature is not None and previous_signature != signature:
        st.session_state.pop("uploaded_analysis_prepared", None)
        st.session_state.pop("uploaded_analysis_result", None)
    if validate:
        if "— Select —" in mapping.values():
            st.error("Choose a CSV column for each of the six required weather variables.")
        else:
            source_unit_map = {mapping[name]: units[name] for name in BASE_VARIABLES}
            try:
                prepared = prepare_uploaded_weather_data(raw, timestamp_column, mapping, source_unit_map, timezone_name)
                prepared["source_sha256"] = file_hash
                prepared["filename"] = upload.name
                prepared["station_id"] = station_id
                st.session_state["uploaded_analysis_prepared"] = prepared
                st.session_state["uploaded_analysis_signature"] = signature
                st.session_state.pop("uploaded_analysis_result", None)
            except (ValueError, KeyError, TypeError) as exc:
                st.error(f"Validation stopped; no model was trained. {exc}")
    prepared = st.session_state.get("uploaded_analysis_prepared")
    if prepared and st.session_state.get("uploaded_analysis_signature") == signature:
        st.success("Validation passed. The uploaded file is prepared as a separate hourly analysis; no historical archive data were changed.")
        meta = prepared["metadata"]
        cards = st.columns(4)
        cards[0].metric("Feature-ready rows", f"{meta['feature_ready_rows']:,}")
        cards[1].metric("Training rows", f"{meta['train_rows']:,}")
        cards[2].metric("Held-out rows", f"{meta['test_rows']:,}")
        cards[3].metric("Missing source values", f"{sum(meta['missing_values_by_variable'].values()):,}")
        st.caption(f"Chronological split: train {meta['train_start']}–{meta['train_end']}; test {meta['test_start']}–{meta['test_end']}. All imputations use training medians only. The model protocol requires hourly timestamps and the same 11 features.")
        if mode == "Existing model inference":
            st.info("The CSV passed preprocessing validation, but results cannot be produced with existing model inference because no fitted model artifacts are saved.")
        elif st.button("Train a new local 12-configuration model and analyze held-out rows", type="primary", key="run_uploaded_analysis"):
            with st.spinner("Fitting the explicitly requested new local model version on uploaded training rows…"):
                try:
                    result = run_uploaded_weather_analysis(prepared, content, upload.name, station_id, Path(root))
                    result["observations"] = prepared["observations"]
                    st.session_state["uploaded_analysis_result"] = result
                except (ValueError, KeyError, FileNotFoundError, RuntimeError) as exc:
                    st.error(f"Uploaded analysis did not complete: {exc}")
        result = st.session_state.get("uploaded_analysis_result")
        if mode == "Retraining / refitting" and result and result["metadata"].get("input_sha256") == file_hash:
            _show_uploaded_results(result)

