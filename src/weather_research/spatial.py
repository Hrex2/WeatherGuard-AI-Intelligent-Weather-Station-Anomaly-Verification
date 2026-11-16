"""Exact-time neighboring-station availability and observed values."""
from __future__ import annotations

import pandas as pd


def _availability(ts, frame, variable):
    if frame is None or frame.empty:
        return "NO_OBSERVED_DATA", None
    if ts in frame.index:
        if variable not in frame.columns or pd.isna(frame.at[ts, variable]):
            return "VARIABLE_UNAVAILABLE", None
        return "OBSERVED_TIMESTAMP", frame.at[ts, variable]
    if ts < frame.index.min():
        return "BEFORE_OBSERVATION_PERIOD", None
    if ts > frame.index.max():
        return "AFTER_OBSERVATION_PERIOD", None
    return "INTERNAL_TIMESTAMP_GAP", None


def spatial_evidence(candidate_times, station_frames: dict, variable: str):
    rows=[]
    for ts in pd.DatetimeIndex(candidate_times):
        observed=[]
        for station, frame in station_frames.items():
            if not isinstance(frame.index, pd.DatetimeIndex):
                raise TypeError(f"{station} index must be DatetimeIndex")
            status, value = _availability(ts, frame, variable)
            rows.append({"timestamp":ts,"station_id":station,"variable":variable,
                         "availability":status,"observed_value":value})
            if status == "OBSERVED_TIMESTAMP": observed.append(value)
    return pd.DataFrame(rows)


def compare_spatial_values(primary_values: pd.Series, neighbor_table: pd.DataFrame,
                           tolerance: float):
    """Compare exact-time observed values using a caller-declared physical tolerance."""
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    required={"timestamp","station_id","availability","observed_value"}
    if not required.issubset(neighbor_table.columns):
        raise KeyError(f"neighbor table needs {sorted(required)}")
    out=neighbor_table.copy()
    out["primary_value"] = out["timestamp"].map(primary_values)
    valid=(out["availability"].eq("OBSERVED_TIMESTAMP") & out["primary_value"].notna()
           & out["observed_value"].notna())
    out["absolute_difference"] = pd.NA
    out.loc[valid,"absolute_difference"] = (out.loc[valid,"observed_value"].astype(float)-
                                              out.loc[valid,"primary_value"].astype(float)).abs()
    out["comparison"] = "UNAVAILABLE"
    out.loc[valid & out["absolute_difference"].le(tolerance),"comparison"]="SUPPORTS_WITHIN_DECLARED_TOLERANCE"
    out.loc[valid & out["absolute_difference"].gt(tolerance),"comparison"]="DIFFERS_BEYOND_DECLARED_TOLERANCE"
    return out
