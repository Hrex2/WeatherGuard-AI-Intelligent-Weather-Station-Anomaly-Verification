"""Input and index checks. These checks do not decide whether weather is anomalous."""
from __future__ import annotations

import pandas as pd

BASE_VARIABLES = ("temp", "dwpt", "rhum", "prcp", "wspd", "pres")


def validate_observations(frame: pd.DataFrame, required=BASE_VARIABLES) -> dict:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("observations require a DatetimeIndex")
    if frame.index.hasnans:
        raise ValueError("timestamp index contains NaT")
    if frame.index.has_duplicates:
        raise ValueError("duplicate timestamps must be resolved explicitly")
    if not frame.index.is_monotonic_increasing:
        raise ValueError("timestamps must be sorted in increasing order")
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise KeyError(f"missing required variables: {missing}")
    return {
        "rows": len(frame),
        "first_timestamp": frame.index.min(),
        "last_timestamp": frame.index.max(),
        "timezone": str(frame.index.tz),
        "missing_by_variable": frame[list(required)].isna().sum().to_dict(),
        "duplicate_timestamps": int(frame.index.duplicated().sum()),
    }


def cadence_report(index: pd.DatetimeIndex) -> dict:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("index must be a DatetimeIndex")
    gaps = index.to_series().diff().dropna()
    return {
        "n_intervals": len(gaps),
        "median_interval": gaps.median() if len(gaps) else pd.NaT,
        "maximum_interval": gaps.max() if len(gaps) else pd.NaT,
        "intervals_over_one_hour": int((gaps > pd.Timedelta(hours=1)).sum()),
    }
