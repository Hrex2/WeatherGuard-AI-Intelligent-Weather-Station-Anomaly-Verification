"""Small, reproducible analysis helpers for the Phase 09 E3 study."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PHASE03_EVENT_RULES = (
    ("rapid_temp_rise", "temp_change_1h", "max", "temp"),
    ("rapid_temp_drop", "temp_change_1h", "min", "temp"),
    ("max_candidate_temperature", "temp", "max", "temp"),
    ("min_candidate_temperature", "temp", "min", "temp"),
    ("min_candidate_rh", "rhum", "min", "rhum"),
    ("max_candidate_rh", "rhum", "max", "rhum"),
    ("max_candidate_wind_speed", "wspd", "max", "wspd"),
    ("min_candidate_pressure", "pres", "min", "pres"),
)


def select_phase03_events(candidates: pd.DataFrame) -> pd.DataFrame:
    """Reproduce Phase 07's full-table mechanical extrema without neighbor data."""
    rows: list[pd.Series] = []
    for event_type, selector, direction, variable in PHASE03_EVENT_RULES:
        if selector not in candidates or variable not in candidates:
            raise ValueError(f"candidate table missing selection column: {selector}/{variable}")
        values = pd.to_numeric(candidates[selector], errors="coerce")
        if values.notna().sum() == 0:
            raise ValueError(f"no valid candidate values for selection metric {selector}")
        index = values.idxmax() if direction == "max" else values.idxmin()
        row = candidates.loc[index].copy()
        row["event_type"] = event_type
        row["event_variable"] = variable
        row["selection_metric"] = selector
        row["selection_direction"] = direction
        rows.append(row)
    selected = pd.DataFrame(rows).drop_duplicates("timestamp", keep="first").copy()
    selected["candidate_timestamp_local"] = selected.timestamp.astype(str)
    selected["candidate_timestamp_utc"] = pd.to_datetime(selected.timestamp, utc=True, errors="coerce")
    if selected.candidate_timestamp_utc.isna().any():
        raise ValueError("selected candidate timestamps could not be parsed")
    return selected.sort_values(["candidate_timestamp_utc", "event_type"], kind="stable").reset_index(drop=True)


def select_candidate_events(events: pd.DataFrame) -> pd.DataFrame:
    """Return every mechanically selected event in stable UTC order."""
    required = {"event_id", "candidate_timestamp_utc", "event_type", "comparison_variable"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"candidate event table is missing columns: {sorted(missing)}")
    result = events.copy(deep=True)
    if result.event_id.isna().any() or result.event_id.duplicated().any():
        raise ValueError("candidate event identifiers must be present and unique")
    result["candidate_timestamp_utc"] = pd.to_datetime(
        result.candidate_timestamp_utc, utc=True, errors="coerce")
    if result.candidate_timestamp_utc.isna().any():
        raise ValueError("candidate timestamps must parse as timezone-aware UTC values")
    return result.sort_values(["candidate_timestamp_utc", "event_id"], kind="stable").reset_index(drop=True)


def compute_descriptive_metrics(variable: str, pairs: pd.DataFrame, *,
                                minimum_pairs: int = 30,
                                minimum_distinct_dates: int = 10) -> dict[str, Any]:
    """Summarize valid paired values; withhold unstable metrics below Phase 05 minima.

    ``reference_value - primary_value`` is the signed bias convention. Wind
    direction uses circular errors and deliberately has no Pearson correlation.
    This function does not classify agreement or event support.
    """
    if minimum_pairs < 1 or minimum_distinct_dates < 1:
        raise ValueError("sample-size minima must be positive")
    required = {"primary_value", "reference_value", "primary_time"}
    if required - set(pairs.columns):
        raise ValueError(f"paired data is missing columns: {sorted(required - set(pairs.columns))}")
    frame = pairs.copy()
    frame["primary_time"] = pd.to_datetime(frame.primary_time, utc=True, errors="coerce")
    frame["primary_value"] = pd.to_numeric(frame.primary_value, errors="coerce")
    frame["reference_value"] = pd.to_numeric(frame.reference_value, errors="coerce")
    valid = frame.dropna(subset=["primary_time", "primary_value", "reference_value"])
    valid = valid[np.isfinite(valid.primary_value) & np.isfinite(valid.reference_value)]
    n = len(valid)
    dates = int(valid.primary_time.dt.date.nunique())
    result = {"variable": variable, "n_valid_pairs": n, "n_distinct_dates": dates,
              "minimum_pairs": minimum_pairs, "minimum_distinct_dates": minimum_distinct_dates,
              "metrics_status": "METRICS_REPORTED" if n >= minimum_pairs and dates >= minimum_distinct_dates
              else "COUNTS_ONLY_BELOW_PRAGMATIC_MINIMUM",
              "bias_reference_minus_primary": None, "mae": None, "rmse": None,
              "median_absolute_error": None, "correlation": None,
              "correlation_method": "NOT_APPROPRIATE_FOR_CIRCULAR_VARIABLE" if variable == "wind_direction" else "PEARSON"}
    if result["metrics_status"] != "METRICS_REPORTED":
        return result
    a, b = valid.primary_value.to_numpy(float), valid.reference_value.to_numpy(float)
    if variable == "wind_direction":
        signed = (b - a + 180.0) % 360.0 - 180.0
        absolute = np.abs(signed)
        result["bias_reference_minus_primary"] = float(np.rad2deg(np.angle(np.mean(np.exp(1j * np.deg2rad(signed))))))
        result["mae"] = float(absolute.mean())
        result["rmse"] = float(np.sqrt(np.mean(signed ** 2)))
        result["median_absolute_error"] = float(np.median(absolute))
    else:
        difference = b - a
        result["bias_reference_minus_primary"] = float(difference.mean())
        result["mae"] = float(np.abs(difference).mean())
        result["rmse"] = float(np.sqrt(np.mean(difference ** 2)))
        result["median_absolute_error"] = float(np.median(np.abs(difference)))
        result["correlation"] = (float(np.corrcoef(a, b)[0, 1])
                                 if np.std(a) > 0 and np.std(b) > 0 else None)
    return result


def summarize_tolerance_sensitivity(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare pair-count sensitivity across exact and tolerance windows."""
    keys = ("source_pair", "variable")
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for row in comparisons:
        groups.setdefault(tuple(row.get(key) for key in keys), []).append(dict(row))
    output: list[dict[str, Any]] = []
    for (source_pair, variable), rows in sorted(groups.items(), key=lambda item: str(item[0])):
        baseline = next((int(row["n_value_pairs"]) for row in rows
                         if int(row["tolerance_minutes"]) == 0), 0)
        for row in sorted(rows, key=lambda item: int(item["tolerance_minutes"])):
            n = int(row["n_value_pairs"])
            output.append({"source_pair": source_pair, "variable": variable,
                           "tolerance_minutes": int(row["tolerance_minutes"]),
                           "n_value_pairs": n, "exact_pair_count": baseline,
                           "pair_count_change_vs_exact": n - baseline,
                           "interpretation":"Availability sensitivity only; widened windows can add temporally offset reports."})
    return output


def verify_phase09_manifest(manifest_path: str | Path, root: str | Path) -> dict[str, Any]:
    """Verify all recorded input/output file hashes in a Phase 09 manifest."""
    manifest_path, root = Path(manifest_path), Path(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked = 0
    missing: list[str] = []
    mismatched: list[str] = []
    for group in ("input_files", "generated_artifacts"):
        entries = manifest.get(group, {})
        if isinstance(entries, list):
            entries = {item["path"]: item for item in entries}
        for relative, item in entries.items():
            path = root / relative
            if not path.is_file():
                missing.append(relative)
                continue
            checked += 1
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != item.get("sha256"):
                mismatched.append(relative)
    return {"valid": not missing and not mismatched, "checked_files": checked,
            "missing_files": missing, "hash_mismatches": mismatched}
