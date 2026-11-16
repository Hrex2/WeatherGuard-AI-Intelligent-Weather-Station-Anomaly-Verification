"""Independent, segment-aware temporal screening from measured weather series.

This service does not read model votes or consensus-derived episodes. Its
statuses describe temporal behavior only and are not calibrated fault labels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def temporal_verification(observations: pd.DataFrame, timestamp, variable: str,
                          window_hours=6, mode="real_time", lookahead_hours=6,
                          min_context=3, robust_z_threshold=3.5,
                          stuck_min_run=4):
    """Assess local temporal behavior without crossing a detected sampling gap.

    ``real_time`` references only prior observations plus the selected reading.
    ``retrospective`` may inspect following measurements and labels that result
    as retrospective investigation; it cannot be used for live detection.
    Cadence is the median positive interval in the selected look-back window
    (plus the requested look-ahead only in retrospective mode), falling back to
    the series median when needed. Gaps >1.5×cadence and explicit segment-ID
    changes break context. A stuck run also stops at missing values and any
    interval differing from local cadence by more than 10% (minimum tolerance
    one minute). Thresholds are screening defaults, not validated domain rules.
    """
    if variable not in observations.columns:
        raise KeyError(f"Weather variable is not available: {variable}")
    if not isinstance(observations.index, pd.DatetimeIndex):
        raise TypeError("observations require a DatetimeIndex")
    if observations.index.has_duplicates or not observations.index.is_monotonic_increasing:
        raise ValueError("observations require unique, chronologically ordered timestamps")
    if mode not in {"real_time", "retrospective"}:
        raise ValueError("mode must be 'real_time' or 'retrospective'")
    if window_hours <= 0 or lookahead_hours < 0 or min_context < 2 or robust_z_threshold <= 0 or stuck_min_run < 2:
        raise ValueError("window, context, or threshold settings are invalid")
    ts = pd.Timestamp(timestamp)
    if observations.index.tz is not None:
        ts = ts.tz_localize(observations.index.tz) if ts.tzinfo is None else ts.tz_convert(observations.index.tz)
    elif ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    if ts not in observations.index:
        return _unavailable(ts, variable, mode, "Selected timestamp is not present in the observation series.")

    values = pd.to_numeric(observations[variable], errors="coerce")
    diffs = observations.index.to_series().diff().dropna()
    cadence_window_start = ts - pd.Timedelta(hours=window_hours)
    cadence_window_end = ts + pd.Timedelta(hours=lookahead_hours if mode == "retrospective" else 0)
    local_diffs = diffs.loc[(diffs.index > cadence_window_start) & (diffs.index <= cadence_window_end)]
    local_diffs = local_diffs[local_diffs > pd.Timedelta(0)]
    cadence = local_diffs.median() if len(local_diffs) else (diffs[diffs > pd.Timedelta(0)].median() if len(diffs) else pd.NaT)
    if pd.isna(cadence):
        return _unavailable(ts, variable, mode, "Sampling cadence cannot be estimated from the available observations.")
    gap_limit = cadence * 1.5
    interval_breaks = observations.index.to_series().diff().gt(gap_limit)
    if "segment_id" in observations.columns:
        segment_ids = observations["segment_id"]
        segment_changes = segment_ids.ne(segment_ids.shift())
        segment_changes &= ~(segment_ids.isna() & segment_ids.shift().isna())
        interval_breaks |= segment_changes
    segment = interval_breaks.cumsum()
    same_segment = segment.eq(segment.loc[ts])
    in_segment = observations.index[same_segment.to_numpy()]
    prior_times = in_segment[(in_segment < ts) & (in_segment >= ts - pd.Timedelta(hours=window_hours))]
    future_times = (in_segment[(in_segment > ts) & (in_segment <= ts + pd.Timedelta(hours=lookahead_hours))]
                    if mode == "retrospective" else in_segment[:0])
    current = values.loc[ts]
    prior = values.reindex(prior_times).dropna()
    future = values.reindex(future_times).dropna()
    result = {"timestamp": ts, "variable": variable, "mode": mode, "status": "UNAVAILABLE",
              "value": float(current) if pd.notna(current) else np.nan,
              "cadence": str(cadence), "prior_count": int(len(prior)),
              "future_count": int(len(future)), "window_hours": float(window_hours),
              "lookahead_hours": float(lookahead_hours) if mode == "retrospective" else 0.0,
              "reference_median": np.nan, "reference_mad": np.nan,
              "robust_deviation": np.nan, "sudden_change": False,
              "persistent_unusual_state": None, "stuck_run_length": 1,
              "stuck_pattern": False,
              "reason": ""}
    if pd.isna(current):
        return {**result, "reason": "Selected measurement is missing; temporal behavior is unavailable."}
    if len(prior) < min_context:
        return {**result, "reason": f"Only {len(prior)} prior non-missing observations in the same segment; {min_context} required."}

    reference = float(prior.median())
    mad = float((prior - reference).abs().median())
    robust_scale = 1.4826 * mad
    if robust_scale == 0:
        robust_scale = float(prior.std(ddof=1))
    deviation = float(current - reference)
    robust_z = deviation / robust_scale if robust_scale > 0 else (0.0 if deviation == 0 else np.inf)
    previous = float(prior.iloc[-1])
    change = float(current - previous)
    sudden = abs(robust_z) >= robust_z_threshold

    # Count in the original ordered series. A missing value or irregular interval
    # breaks the run; dropping missing values here would incorrectly bridge it.
    run = 1
    selected_position = observations.index.get_loc(ts)
    expected_tolerance = max(pd.Timedelta(minutes=1), cadence * 0.1)
    for position in range(selected_position - 1, -1, -1):
        interval = observations.index[position + 1] - observations.index[position]
        if segment.iloc[position] != segment.iloc[selected_position] or abs(interval - cadence) > expected_tolerance:
            break
        previous_value = values.iloc[position]
        if pd.isna(previous_value) or not np.isclose(float(previous_value), float(current), rtol=0.0, atol=1e-12):
            break
        run += 1
    stuck = run >= stuck_min_run and prior.nunique() > 1
    result.update(reference_median=reference, reference_mad=mad,
                  robust_deviation=float(robust_z), sudden_change=bool(sudden),
                  stuck_run_length=run, stuck_pattern=bool(stuck))

    if mode == "real_time":
        # A causal screen can identify a sudden departure, but cannot claim
        # persistence or inspect later values.
        result.update(status="SUPPORTING" if sudden or stuck else "NO_DETECTED_EVIDENCE",
                      persistent_unusual_state=None,
                      reason=("Current value departs robustly from prior local history; this is a temporal screening flag."
                              if sudden else "A repeated-value run follows changing local measurements; this is a stuck-pattern screen, not a hardware diagnosis."
                              if stuck else "No robust departure or stuck pattern was detected in prior local history."))
    else:
        if len(future) < min_context:
            result["reason"] = f"Only {len(future)} following non-missing observations in the same segment; {min_context} required for retrospective review."
            return result
        future_median = float(future.median())
        future_deviation = future_median - reference
        future_z = future_deviation / robust_scale if robust_scale > 0 else (0.0 if future_deviation == 0 else np.inf)
        persists = abs(future_z) >= robust_z_threshold
        result["persistent_unusual_state"] = bool(persists)
        if stuck:
            result.update(status="SUPPORTING", reason="A repeated-value run follows changing local measurements; this retrospective stuck-pattern screen is not a hardware diagnosis.")
        elif sudden and persists:
            result.update(status="SUPPORTING", reason="The selected departure and following local median remain unusual relative to prior history; retrospective screening only.")
        elif sudden and not persists:
            result.update(status="CONFLICTING", reason="The selected value departs from prior history, while following values return toward its prior local median; this conflicts with persistence, not proof of sensor fault.")
        else:
            result.update(status="NO_DETECTED_EVIDENCE", reason="No robust departure or persistent unusual state was detected in the requested retrospective window.")
        result["following_median"] = future_median
        result["following_robust_deviation"] = float(future_z)
    result["status"] = "UNAVAILABLE" if result["status"] == "UNAVAILABLE" else result["status"]
    return result


def _unavailable(timestamp, variable, mode, reason):
    return {"timestamp": timestamp, "variable": variable, "mode": mode,
            "status": "UNAVAILABLE", "value": np.nan, "reason": reason}
