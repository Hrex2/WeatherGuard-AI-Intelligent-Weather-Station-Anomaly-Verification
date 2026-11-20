"""Small, explicit provenance-aware collection helpers for Phase 04."""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


VERIFIED_STATION_IDS = {"42099", "42101"}
REQUIRED_VARIABLES = ("temp", "dwpt", "rhum", "prcp", "wspd", "pres")


def eligible_for_retrieval(station_id: str, verification_status: str) -> bool:
    """Only stations with an approved independent identity record are eligible."""
    return station_id in VERIFIED_STATION_IDS and verification_status == "VERIFIED_IDENTITY_AND_HISTORIC_SITE_METADATA"


def fetch_observation_sources(ms, station_id: str, start, end, timezone: str,
                              parameters: Iterable, expected_version: str = "2.2.3"):
    """Fetch unsquashed source-level rows, with model exclusion explicitly enabled.

    Meteostat 2.x has no `Hourly(model=False, flags=True)` constructor. The 2.2.3
    API uses `config.include_model_data=False`, and `TimeSeries.fetch` keeps the
    source as an index level when `squash=False`; `sources=True` is still passed
    explicitly for the API contract and future-compatible metadata retention.
    """
    version = getattr(ms, "__version__", None)
    if version != expected_version:
        raise RuntimeError(f"Expected Meteostat {expected_version}, found {version!r}")
    if "providers" not in inspect.signature(ms.hourly).parameters:
        raise RuntimeError("Installed Meteostat hourly API lacks explicit provider selection")
    config = ms.config
    if not hasattr(config, "include_model_data"):
        raise RuntimeError("Installed Meteostat config cannot explicitly exclude model data")
    old_model_setting = config.include_model_data
    old_cache_setting = getattr(config, "cache_enable", None)
    config.include_model_data = False
    if old_cache_setting is not None:
        config.cache_enable = False
    try:
        series = ms.hourly(
            station_id, start, end, timezone=timezone,
            parameters=list(parameters), providers=[ms.Provider.HOURLY],
        )
        frame = series.fetch(
            squash=False, fill=False, sources=True, location=False,
            clean=False, humanize=False,
        )
        if frame is not None and isinstance(frame.index, pd.MultiIndex):
            if "source" not in frame.index.names:
                raise RuntimeError("Meteostat output omitted the source index despite unsquashed retrieval")
        return frame, {
            "meteostat_version": version,
            "model_setting": False,
            "model_setting_mechanism": "meteostat.config.include_model_data=False (restored after fetch)",
            "flags_setting": "NOT_SUPPORTED; equivalent provider source identifiers retained via sources=True and unsquashed source index",
            "source_setting": True,
            "source_setting_mechanism": "fetch(sources=True, squash=False); source provider retained as index level",
            "fill_setting": False,
            "clean_setting": False,
            "cache_setting_during_fetch": False if old_cache_setting is not None else "UNAVAILABLE",
            "timezone": timezone,
            "provider": "hourly",
        }
    finally:
        config.include_model_data = old_model_setting
        if old_cache_setting is not None:
            config.cache_enable = old_cache_setting


def source_provider_grade_map(ms) -> dict[str, str]:
    """Return provider IDs and declared grades from the installed registry."""
    from meteostat.core.providers import provider_service

    return {str(provider.id.value if hasattr(provider.id, "value") else provider.id):
            (str(provider.grade.value) if provider.grade is not None and hasattr(provider.grade, "value")
             else str(provider.grade) if provider.grade is not None else "UNSPECIFIED")
            for provider in provider_service.providers}


def time_index(frame: pd.DataFrame) -> pd.DatetimeIndex:
    if isinstance(frame.index, pd.MultiIndex) and "time" in frame.index.names:
        return pd.DatetimeIndex(frame.index.get_level_values("time"))
    if isinstance(frame.index, pd.DatetimeIndex):
        return frame.index
    if "time" in frame.columns:
        return pd.DatetimeIndex(pd.to_datetime(frame["time"], utc=True))
    raise TypeError("frame must have a DatetimeIndex or a MultiIndex containing time")


def source_index(frame: pd.DataFrame) -> pd.Index:
    if isinstance(frame.index, pd.MultiIndex) and "source" in frame.index.names:
        return frame.index.get_level_values("source")
    if "source" in frame.columns:
        return pd.Index(frame.source)
    return pd.Index(["UNKNOWN"] * len(frame))


def coverage_metrics(frame: pd.DataFrame, start, end, variables=REQUIRED_VARIABLES) -> dict:
    times = time_index(frame)
    unique_times = pd.DatetimeIndex(times.unique()).sort_values()
    expected = pd.date_range(start=start, end=end, freq="h")
    matched = expected.intersection(unique_times)
    duplicate_mask = times.duplicated(keep=False)
    result = {
        "source_time_rows": int(len(frame)),
        "unique_timestamps": int(len(unique_times)),
        "duplicate_source_time_rows": int(duplicate_mask.sum()),
        "timestamps_with_multiple_source_rows": int(pd.Series(times).value_counts().gt(1).sum()),
        "first_timestamp": str(unique_times.min()) if len(unique_times) else None,
        "last_timestamp": str(unique_times.max()) if len(unique_times) else None,
        "expected_hourly_timestamps": int(len(expected)),
        "available_expected_timestamps": int(len(matched)),
        "missing_expected_timestamps": int(len(expected.difference(unique_times))),
        "unexpected_timestamps_outside_requested_grid": int(len(unique_times.difference(expected))),
        "timezone": str(unique_times.tz) if len(unique_times) else None,
        "variable_summary": {},
    }
    for variable in variables:
        if variable not in frame.columns:
            result["variable_summary"][variable] = {
                "source_level_valid_values": 0, "unique_timestamps_with_value": 0,
                "missing_expected_timestamps": int(len(expected)), "status": "VARIABLE_NOT_RETURNED",
            }
            continue
        values = pd.to_numeric(frame[variable], errors="coerce")
        valid_mask = values.notna()
        valid_times = pd.DatetimeIndex(times[valid_mask].unique())
        result["variable_summary"][variable] = {
            "source_level_valid_values": int(valid_mask.sum()),
            "unique_timestamps_with_value": int(len(valid_times)),
            "missing_expected_timestamps": int(len(expected.difference(valid_times))),
            "status": "AVAILABLE" if valid_mask.any() else "NO_VALID_VALUES",
        }
    return result


def write_raw_frame(frame: pd.DataFrame, destination: Path) -> str:
    """Write a raw package-returned frame once and return its SHA-256."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"Refusing to replace existing raw data: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=True, date_format="%Y-%m-%dT%H:%M:%S%z")
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return digest


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def missingness_rows(station_id: str, frame: pd.DataFrame, start, end,
                     variables=REQUIRED_VARIABLES) -> list[dict]:
    summary = coverage_metrics(frame, start, end, variables)
    return [{"station_id": station_id, "variable": variable,
             "source_level_valid_values": values["source_level_valid_values"],
             "unique_timestamps_with_value": values["unique_timestamps_with_value"],
             "expected_hourly_timestamps": summary["expected_hourly_timestamps"],
             "missing_expected_timestamps": values["missing_expected_timestamps"],
             "status": values["status"],
             "interpretation": "Missingness indicates unavailable data, not disagreement."}
            for variable, values in summary["variable_summary"].items()]


def source_series(frame: pd.DataFrame, variable: str) -> dict[str, pd.Series]:
    """Return one non-null, timestamp-indexed series per provider source."""
    if variable not in frame.columns:
        return {}
    times = time_index(frame)
    sources = source_index(frame).astype(str)
    values = pd.to_numeric(frame[variable], errors="coerce")
    result = {}
    for source in sources.unique():
        mask = (sources == source) & values.notna()
        series = pd.Series(values[mask].to_numpy(), index=pd.DatetimeIndex(times[mask])).sort_index()
        result[source] = series[~series.index.duplicated(keep="first")]
    return result
