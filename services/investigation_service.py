"""Data preparation helpers for the interactive historical investigation view."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from weather_research.models import default_model_configs

WEATHER_VARIABLES = {
    "temp": ("Air temperature", "°C"),
    "dwpt": ("Dew point", "°C"),
    "rhum": ("Relative humidity", "%"),
    "prcp": ("Precipitation", "mm"),
    "wspd": ("Wind speed", "km/h"),
    "wdir": ("Wind direction", "°"),
    "wpgt": ("Wind gust", "km/h"),
    "pres": ("Air pressure", "hPa"),
    "snow": ("Snow depth", "mm"),
    "tsun": ("Sunshine duration", "minutes"),
}


def available_weather_variables(observations: pd.DataFrame):
    """Return only recognized weather measurements genuinely in the dataset."""
    return {key: WEATHER_VARIABLES[key] for key in WEATHER_VARIABLES if key in observations.columns}


def model_heatmap_data(predictions: pd.DataFrame, start, end, families=None,
                       max_timestamps=900, selected_timestamp=None):
    """Build actual model-by-time labels, all-model agreement, and readable sample.

    Predictions outside the filtered interval are not included. For long ranges,
    the matrix is sampled only for display; agreement retains every timestamp and
    the timestamp selector can still inspect any available row.
    """
    required = {"timestamp", "configuration", "family", "is_candidate"}
    if not required.issubset(predictions.columns):
        raise KeyError(f"prediction table requires {sorted(required)}")
    if predictions.duplicated(["timestamp", "configuration"]).any():
        raise ValueError("predictions contain duplicate timestamp/configuration pairs")
    pred = predictions.copy()
    pred["timestamp"] = pd.to_datetime(pred["timestamp"])
    if pred["is_candidate"].isna().any():
        # Keep missing configuration predictions visible as unavailable cells.
        pred["is_candidate"] = pred["is_candidate"].astype("boolean")
    tz = pred["timestamp"].dt.tz
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    if tz is not None:
        lo = lo.tz_localize(tz) if lo.tzinfo is None else lo.tz_convert(tz)
        hi = hi.tz_localize(tz) if hi.tzinfo is None else hi.tz_convert(tz)
    elif lo.tzinfo is not None:
        lo, hi = lo.tz_localize(None), hi.tz_localize(None)
    if lo > hi:
        raise ValueError("start timestamp must not be after end timestamp")
    filtered = pred.loc[pred.timestamp.between(lo, hi)].copy()
    if families is not None:
        model_rows = filtered.loc[filtered.family.isin(families)].copy()
    else:
        model_rows = filtered.copy()

    config_order = [cfg["name"] for cfg in default_model_configs()]
    present = set(model_rows.configuration.dropna().astype(str))
    ordered_configs = [name for name in config_order if name in present]
    ordered_configs.extend(sorted(present - set(ordered_configs)))
    if model_rows.empty:
        full_matrix = pd.DataFrame(index=pd.DatetimeIndex([], tz=tz), columns=ordered_configs, dtype="float64")
    else:
        full_matrix = model_rows.pivot(index="timestamp", columns="configuration", values="is_candidate")
        full_matrix = full_matrix.reindex(columns=ordered_configs).sort_index()
        full_matrix = full_matrix.astype("Float64").astype(float)

    if filtered.empty:
        agreement = pd.DataFrame(columns=["votes", "available", "agreement_pct", "consensus_8_of_12"])
        agreement.index = pd.DatetimeIndex([], tz=tz, name="timestamp")
    else:
        grouped = filtered.groupby("timestamp").is_candidate.agg(votes=lambda s: int(s.fillna(False).astype(bool).sum()),
                                                                  available=lambda s: int(s.notna().sum()))
        total_configurations = int(predictions.configuration.nunique())
        grouped["agreement_pct"] = np.where(grouped.available.gt(0), grouped.votes / grouped.available * 100.0, np.nan)
        consensus = pd.Series(pd.NA, index=grouped.index, dtype="boolean")
        # The 8-of-12 threshold is meaningful only for the documented full
        # protocol. Partial grids still get an agreement percentage above.
        complete = grouped.available.eq(total_configurations) & (total_configurations == 12)
        consensus.loc[complete] = grouped.loc[complete, "votes"].ge(8)
        grouped["consensus_8_of_12"] = consensus
        agreement = grouped

    display_matrix = full_matrix
    sampled = False
    if len(full_matrix) > max_timestamps:
        stride = math.ceil(len(full_matrix) / max_timestamps)
        display_matrix = full_matrix.iloc[::stride].copy()
        if selected_timestamp is not None:
            selected = pd.Timestamp(selected_timestamp)
            if selected in full_matrix.index and selected not in display_matrix.index:
                display_matrix = pd.concat([display_matrix, full_matrix.loc[[selected]]]).sort_index()
        sampled = True
    return {
        "matrix": display_matrix,
        "full_matrix": full_matrix,
        "agreement": agreement,
        "configurations": ordered_configs,
        "sampled_for_display": sampled,
        "displayed_timestamps": display_matrix.index,
        "all_timestamps": full_matrix.index,
    }


def variable_diagnostics(observations: pd.DataFrame, variable: str, start=None, end=None,
                         rolling_observations=6):
    """Return ordered values, prior-only rolling mean and descriptive checks."""
    if variable not in available_weather_variables(observations):
        raise KeyError(f"Weather variable is not available: {variable}")
    if not isinstance(observations.index, pd.DatetimeIndex) or observations.index.has_duplicates:
        raise ValueError("observations require a unique timestamp index")
    source = observations.sort_index()
    segment_col = "segment_id" if "segment_id" in source else None
    raw = pd.to_numeric(source[variable], errors="coerce")
    if segment_col:
        groups = source[segment_col]
        previous = raw.groupby(groups, sort=False, dropna=True).shift(1)
        rolling = raw.groupby(groups, sort=False, dropna=True).transform(
            lambda s: s.shift(1).rolling(rolling_observations, min_periods=1).mean())
    else:
        previous = raw.shift(1)
        rolling = raw.shift(1).rolling(rolling_observations, min_periods=1).mean()
    diagnostics = pd.DataFrame({"value": raw, "previous_observation": previous,
                                "change_from_previous": raw - previous,
                                "previous_rolling_mean": rolling})
    if start is not None:
        diagnostics = diagnostics.loc[diagnostics.index >= pd.Timestamp(start)]
    if end is not None:
        diagnostics = diagnostics.loc[diagnostics.index <= pd.Timestamp(end)]
    nonmissing = diagnostics.value.dropna()
    return {
        "series": diagnostics,
        "rows": len(diagnostics),
        "missing": int(diagnostics.value.isna().sum()),
        "count": int(nonmissing.count()),
        "mean": float(nonmissing.mean()) if len(nonmissing) else np.nan,
        "median": float(nonmissing.median()) if len(nonmissing) else np.nan,
        "std": float(nonmissing.std()) if len(nonmissing) > 1 else np.nan,
        "minimum": float(nonmissing.min()) if len(nonmissing) else np.nan,
        "maximum": float(nonmissing.max()) if len(nonmissing) else np.nan,
    }


def verified_station_location(root: Path, station_id="VILD0"):
    """Return coordinates only when the supplied station manifest actually has valid values."""
    manifest_path = Path(root) / "outputs" / "station_provenance" / "station_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False, "reason": "Station metadata manifest unavailable.", "station_id": station_id}
    station = next((item for item in manifest.get("stations", []) if str(item.get("station_id")) == str(station_id)), None)
    if station is None:
        return {"available": False, "reason": "Station metadata unavailable.", "station_id": station_id}
    coordinates = station.get("coordinates") or {}
    lat, lon = coordinates.get("latitude"), coordinates.get("longitude")
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"available": False, "reason": "Station coordinates unavailable.", "station_id": station_id,
                "reported_location": station.get("reported_location")}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {"available": False, "reason": "Station coordinates are invalid and will not be mapped.", "station_id": station_id}
    return {"available": True, "station_id": station_id, "latitude": lat, "longitude": lon,
            "reported_location": station.get("reported_location"), "role": station.get("role")}
