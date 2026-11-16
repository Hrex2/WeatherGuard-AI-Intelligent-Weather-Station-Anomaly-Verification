"""Validated, isolated analysis runs for user supplied station CSV files."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from services.model_service import FEATURE_ORDER, run_saved_protocol
from weather_research.features import add_segments, engineer_features
from weather_research.models import stability_summary

BASE_VARIABLES = ("temp", "dwpt", "rhum", "prcp", "wspd", "pres")
BASE_FEATURES = FEATURE_ORDER[:9]
CANONICAL_UNITS = {"temp": "°C", "dwpt": "°C", "rhum": "%", "prcp": "mm",
                   "wspd": "km/h", "pres": "hPa"}
UNIT_CONVERSIONS = {
    "temp": {"°C": lambda s: s, "°F": lambda s: (s - 32) * 5 / 9, "K": lambda s: s - 273.15},
    "dwpt": {"°C": lambda s: s, "°F": lambda s: (s - 32) * 5 / 9, "K": lambda s: s - 273.15},
    "rhum": {"%": lambda s: s, "fraction (0–1)": lambda s: s * 100},
    "prcp": {"mm": lambda s: s, "inches": lambda s: s * 25.4, "metres": lambda s: s * 1000},
    "wspd": {"km/h": lambda s: s, "m/s": lambda s: s * 3.6, "mph": lambda s: s * 1.609344},
    "pres": {"hPa": lambda s: s, "Pa": lambda s: s / 100, "kPa": lambda s: s * 10},
}


def prepare_uploaded_weather_data(frame: pd.DataFrame, timestamp_column: str,
                                  column_mapping: dict[str, str], source_units: dict[str, str],
                                  timezone_name="Asia/Kolkata"):
    """Validate a six-variable hourly CSV and prepare causal 11-feature matrices.

    The input frame is never modified. The existing model protocol is explicitly
    hourly, so non-hourly series that cannot produce its one-hour feature are
    rejected with a useful message instead of silently changing the feature set.
    """
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("The uploaded CSV is empty or could not be parsed")
    if timestamp_column not in frame.columns:
        raise KeyError(f"Timestamp column is missing: {timestamp_column}")
    missing_variables = set(BASE_VARIABLES) - set(column_mapping)
    if missing_variables:
        raise ValueError(f"Map all six required weather variables: {sorted(missing_variables)}")
    mapped_columns = [column_mapping[name] for name in BASE_VARIABLES]
    if any(column not in frame.columns for column in mapped_columns):
        raise KeyError("One or more mapped weather columns are missing from the CSV")
    if len(set(mapped_columns)) != len(mapped_columns):
        raise ValueError("Each required weather variable must map to a different CSV column")
    if timestamp_column in mapped_columns:
        raise ValueError("The timestamp column cannot also be used as a weather measurement")
    if not timezone_name or not isinstance(timezone_name, str):
        raise ValueError("Enter a valid timezone name for timestamps without timezone information")

    copied = frame.copy(deep=True)
    parsed_items = []
    timezone_awareness = set()
    for value in copied[timestamp_column]:
        try:
            item = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            item = pd.NaT
        parsed_items.append(item)
        if pd.notna(item):
            timezone_awareness.add(item.tzinfo is not None)
    if len(timezone_awareness) > 1:
        raise ValueError("Timestamp values mix timezone-aware and timezone-naive values; normalize them to one consistent timezone first")
    all_timezone_aware = timezone_awareness == {True}
    parsed = pd.to_datetime(pd.Series(parsed_items, index=copied.index), errors="coerce",
                            utc=all_timezone_aware)
    if parsed.isna().any():
        raise ValueError(f"{int(parsed.isna().sum())} row(s) have invalid or missing timestamps")
    try:
        if parsed.dt.tz is None:
            parsed = parsed.dt.tz_localize(timezone_name, ambiguous="raise", nonexistent="raise")
        else:
            parsed = parsed.dt.tz_convert(timezone_name)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not interpret timestamps in timezone {timezone_name}: {exc}") from exc

    out = pd.DataFrame(index=pd.DatetimeIndex(parsed, name="timestamp"))
    unit_summary = {}
    source_missing = {}
    for variable in BASE_VARIABLES:
        column = column_mapping[variable]
        if column not in source_units or source_units[column] not in UNIT_CONVERSIONS[variable]:
            raise ValueError(f"Select a supported source unit for {variable} ({column})")
        raw = copied[column]
        numeric = pd.to_numeric(raw, errors="coerce")
        bad = raw.notna() & numeric.isna()
        if bad.any():
            raise ValueError(f"Column {column} contains {int(bad.sum())} non-numeric {variable} value(s)")
        if variable == "rhum" and source_units[column] == "fraction (0–1)":
            if ((numeric.dropna() < 0) | (numeric.dropna() > 1)).any():
                raise ValueError("Relative humidity declared as a fraction must be between 0 and 1")
        converted = UNIT_CONVERSIONS[variable][source_units[column]](numeric.astype(float))
        out[variable] = converted.to_numpy()
        source_missing[variable] = int(converted.isna().sum())
        unit_summary[variable] = {"source_column": column, "source_unit": source_units[column],
                                  "canonical_unit": CANONICAL_UNITS[variable]}
    if out.index.has_duplicates:
        duplicate_count = int(out.index.duplicated(keep=False).sum())
        raise ValueError(f"Duplicate timestamps found ({duplicate_count} rows). Resolve them before analysis.")
    out = out.sort_index()
    intervals = out.index.to_series().diff().dropna()
    if not len(intervals):
        raise ValueError("At least two timestamped observations are required")
    cadence = intervals.median()
    expected_interval = pd.Timedelta(hours=1)
    irregular_intervals = intervals.ne(expected_interval)
    implied_missing_hours = int(sum(max(int(interval / expected_interval) - 1, 0)
                                    for interval in intervals if interval > expected_interval
                                    and interval % expected_interval == pd.Timedelta(0)))
    if irregular_intervals.any():
        raise ValueError(
            "This model protocol requires every adjacent timestamp to be exactly one elapsed hour; "
            f"median interval is {cadence}, {int(irregular_intervals.sum())} interval(s) are irregular, "
            f"and {implied_missing_hours} hourly timestamp(s) are implied missing. "
            "No observations were resampled or interpolated; split or correct the source data before analysis."
        )

    segmented = add_segments(out, max_gap="1h")
    engineered = engineer_features(segmented, rolling_observations=6, expected_interval="1h")
    engineered = engineered.rename(columns={"temp_rolling_mean_6obs": "temp_rolling_mean_6h",
                                            "temp_deviation_6obs": "temp_deviation_6h"})
    feature_ready = engineered.dropna(subset=list(BASE_FEATURES[6:])).loc[:, list(BASE_FEATURES)].copy()
    if len(feature_ready) < 60:
        raise ValueError(f"Only {len(feature_ready)} rows have the required causal hourly features; at least 60 are needed to split and fit the 12-config protocol.")
    split_at = int(len(feature_ready) * 0.8)
    train_raw, test_raw = feature_ready.iloc[:split_at].copy(), feature_ready.iloc[split_at:].copy()
    if len(train_raw) <= 50 or test_raw.empty:
        raise ValueError("The chronological split must contain more than 50 training rows and at least one test row")
    medians = train_raw.median(numeric_only=True)
    all_missing = medians[medians.isna()].index.tolist()
    if all_missing:
        raise ValueError(f"Cannot fit using all-missing training variable(s): {all_missing}")
    train = train_raw.replace([np.inf, -np.inf], np.nan).fillna(medians)
    test = test_raw.replace([np.inf, -np.inf], np.nan).fillna(medians)
    if not np.isfinite(train.to_numpy(dtype=float)).all() or not np.isfinite(test.to_numpy(dtype=float)).all():
        raise ValueError("Non-finite values remain after training-only median imputation")
    metadata = {
        "timezone": timezone_name,
        "source_rows": int(len(copied)),
        "timestamp_start": str(out.index.min()), "timestamp_end": str(out.index.max()),
        "median_cadence": str(cadence), "duplicates": 0,
        "hourly_interval_count": int(len(intervals)), "irregular_interval_count": 0,
        "implied_missing_hour_count": 0, "usable_rows": int(len(out)), "excluded_rows": 0,
        "missing_values_by_variable": source_missing,
        "unit_mapping": unit_summary,
        "feature_ready_rows": int(len(feature_ready)),
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_start": str(train.index.min()), "train_end": str(train.index.max()),
        "test_start": str(test.index.min()), "test_end": str(test.index.max()),
        "feature_order": list(FEATURE_ORDER),
        "imputation": "Per-column median fitted on chronological training rows only; applied to train and test.",
        "feature_engineering": "Causal previous-observation difference, previous six-observation mean, six-observation deviation; hourly gaps start a new segment.",
    }
    return {"observations": out, "engineered": engineered, "features": feature_ready,
            "train": train, "test": test, "metadata": metadata}


def run_uploaded_weather_analysis(prepared: dict, original_bytes: bytes, filename: str,
                                  station_id: str, output_root: Path):
    """Explicitly train a new local 12-config model version and save isolated outputs."""
    if not station_id.strip():
        raise ValueError("Enter a user-declared station ID or label")
    run_id = "upload_" + uuid.uuid4().hex[:12]
    output_dir = Path(output_root) / "outputs" / "uploaded_analyses" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    predictions, protocol = run_saved_protocol(prepared["train"], prepared["test"])
    stability, jaccard = stability_summary(predictions)
    results = predictions.reset_index().groupby(["family", "configuration"], as_index=False).agg(
        anomalies=("is_candidate", "sum"), test_observations=("is_candidate", "size"))
    results["anomaly_percentage"] = results.anomalies / results.test_observations * 100.0
    uploaded_hash = hashlib.sha256(original_bytes).hexdigest()
    metadata = {**prepared["metadata"], **protocol,
                "run_id": run_id, "run_type": "NEW_USER_UPLOADED_DATA_MODEL_FIT",
                "input_filename": Path(filename).name, "input_sha256": uploaded_hash,
                "station_id_user_declared_unverified": station_id.strip(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "saved_estimator_objects": False,
                "source_data_persisted": False,
                "prediction_rows": int(len(predictions)),
                "model_agreement_warning": "Votes are not probabilities; no verified fault labels are available."}
    predictions.reset_index().to_csv(output_dir / "heldout_predictions.csv", index=False)
    results.to_csv(output_dir / "configuration_results.csv", index=False)
    stability.to_csv(output_dir / "heldout_stability.csv")
    jaccard.to_csv(output_dir / "jaccard_similarity.csv")
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    return {"predictions": predictions, "stability": stability, "jaccard": jaccard,
            "configuration_results": results, "metadata": metadata, "output_dir": output_dir}
