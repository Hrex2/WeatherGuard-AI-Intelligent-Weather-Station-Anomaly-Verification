"""Broad physical screening rules; flags are not sensor-fault labels."""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_SCREENING_BOUNDS = {
    "temp": (-90.0, 60.0), "dwpt": (-100.0, 45.0),
    "rhum": (0.0, 100.0), "prcp": (0.0, 1000.0),
    "wspd": (0.0, 150.0), "pres": (800.0, 1100.0),
}


def physical_quality_flags(frame: pd.DataFrame, bounds=None) -> pd.DataFrame:
    bounds = bounds or DEFAULT_SCREENING_BOUNDS
    rows=[]
    for variable, (low, high) in bounds.items():
        if variable not in frame:
            continue
        numeric = pd.to_numeric(frame[variable], errors="coerce")
        for position, (ts, raw_value, value) in enumerate(zip(frame.index, frame[variable].to_numpy(), numeric.to_numpy())):
            missing = bool(pd.isna(raw_value))
            nonnumeric = bool(not missing and pd.isna(value))
            infinite = bool(pd.notna(value) and not np.isfinite(value))
            below = bool(pd.notna(value) and np.isfinite(value) and value < low)
            above = bool(pd.notna(value) and np.isfinite(value) and value > high)
            rows.append({"timestamp": ts, "row_position": position, "variable": variable,
                         "raw_value": raw_value, "missing": missing,
                         "nonnumeric": nonnumeric, "infinite": infinite,
                         "below_screening_range": below, "above_screening_range": above,
                         "cross_variable_inconsistency": False,
                         "screening_flag": bool(missing or nonnumeric or infinite or below or above),
                         "rule_type": "broad screening rule; not station calibration or a fault label"})
    out=pd.DataFrame(rows)
    if {"temp", "dwpt"}.issubset(frame.columns):
        temp=pd.to_numeric(frame["temp"], errors="coerce")
        dew=pd.to_numeric(frame["dwpt"], errors="coerce")
        conflicts=dew.gt(temp)
        positions=np.flatnonzero(conflicts.to_numpy())
        extra=pd.DataFrame({"timestamp": frame.index[conflicts], "row_position": positions,
                            "variable": "dwpt_vs_temp",
                            "raw_value": (dew-temp)[conflicts].values,
                            "missing": False,"nonnumeric": False,"infinite": False,
                            "below_screening_range": False,"above_screening_range": False,
                            "cross_variable_inconsistency": True,"screening_flag": True,
                            "rule_type": "cross-variable screening inconsistency; not a sensor-fault label"})
        out=pd.concat([out,extra],ignore_index=True)
    return out
