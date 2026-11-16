"""Canonical segment-aware, causal feature engineering."""
from __future__ import annotations

import pandas as pd
import numpy as np
from .validation import BASE_VARIABLES


def add_segments(frame: pd.DataFrame, max_gap="1h", segment_col="segment_id") -> pd.DataFrame:
    """Return a copy with contiguous-observation segments; a gap starts a new segment."""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("frame must have a DatetimeIndex")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("timestamps must be unique and sorted before segmentation")
    out = frame.copy(deep=True)
    gap = out.index.to_series().diff()
    out[segment_col] = gap.gt(pd.Timedelta(max_gap)).cumsum().astype("int64")
    return out


def engineer_features(
    frame: pd.DataFrame,
    segment_col="segment_id",
    rolling_observations=6,
    expected_interval="1h",
) -> pd.DataFrame:
    """Add canonical features without mutating input.

    ``temp_change_row`` preserves the historic grouped previous-row difference.
    ``temp_change_1h`` is the strict elapsed-time version and is null unless the
    preceding row is exactly one hour earlier. The rolling mean is the historic
    previous-six-observation mean (shift(1)); missing segment IDs follow pandas
    groupby(dropna=True) semantics and therefore yield null engineered features.
    """
    missing = set(BASE_VARIABLES + (segment_col,)) - set(frame.columns)
    if missing:
        raise KeyError(f"missing feature inputs: {sorted(missing)}")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("feature engineering requires a DatetimeIndex")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("feature engineering requires unique sorted timestamps")
    if rolling_observations < 1:
        raise ValueError("rolling_observations must be positive")
    out = frame.copy(deep=True)
    numeric_temp=pd.to_numeric(out["temp"],errors="coerce")
    bad=out["temp"].notna() & numeric_temp.isna()
    if bad.any(): raise ValueError(f"temp contains nonnumeric values at {int(bad.sum())} rows")
    out["temp_change_row"] = numeric_temp.groupby(out[segment_col],sort=False,dropna=True).diff()
    prior_mean = numeric_temp.groupby(out[segment_col],sort=False,dropna=True).transform(
        lambda values: values.shift(1).rolling(
            window=rolling_observations, min_periods=rolling_observations
        ).mean()
    )
    out[f"temp_rolling_mean_{rolling_observations}obs"] = prior_mean
    out[f"temp_deviation_{rolling_observations}obs"] = numeric_temp - prior_mean
    elapsed = out.index.to_series().diff()
    same_segment = out[segment_col].notna() & out[segment_col].eq(out[segment_col].shift())
    out["temp_change_1h"] = out["temp_change_row"].where(
        same_segment & elapsed.eq(pd.Timedelta(expected_interval))
    )
    return out


def add_month_cycle(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the original month/12 sine-cosine terms without fitting parameters."""
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("month-cycle features require a DatetimeIndex")
    out=frame.copy(deep=True)
    month=out.index.month
    out["month_sin"]=np.sin(2*np.pi*month/12)
    out["month_cos"]=np.cos(2*np.pi*month/12)
    return out
