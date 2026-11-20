"""Approval-gated METAR pilot specification and quality helpers.

This module deliberately does not perform retrieval by itself. The currently
inspected Meteostat 2.2.3 METAR adapter cannot serve the requested 2025 period;
the CLI checks that limitation before it can reach the provider call.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

PILOT_SPEC: dict[str, Any] = {
    "schema_version": 1,
    "stations": ["VILD0", "42105"],
    "primary_station": "VILD0",
    "neighbour_candidate": "42105",
    "provider": "METAR",
    "parameters": ["temp", "rhum", "wspd", "wdir", "pres"],
    "start_date_inclusive": "2025-09-01",
    "end_date_inclusive": "2025-09-30",
    "end_boundary_exclusive": "2025-10-01",
    "frequency": "hourly",
    "source_timezone": "UTC (Meteostat-naive timestamps are UTC)",
    "comparison_timezone": "UTC",
    "model_fill": False,
    "approval_status": "PENDING_USER_APPROVAL",
    "expected_output_directory": "research_results/phase1c_metar_pilot/runs/<unique_run_id>/",
    "package_version": "2.2.3",
    "provider_interface_status": "BLOCKED_FOR_REQUESTED_HISTORICAL_WINDOW",
}

PARAMETER_LABELS = {
    "temp": "Air temperature",
    "rhum": "Relative humidity (derived in Meteostat from temp and dew point)",
    "wspd": "Wind speed",
    "wdir": "Wind direction",
    "pres": "Atmospheric pressure",
}
METRIC_UNITS = {"temp": "degC", "rhum": "%", "wspd": "km/h", "wdir": "degrees", "pres": "hPa"}
SUSPICIOUS_RANGES = {
    "temp": (-100.0, 70.0),
    "rhum": (0.0, 100.0),
    "wspd": (0.0, 200.0),
    "wdir": (0.0, 360.0),
    "pres": (800.0, 1100.0),
}


class PilotBlockedError(RuntimeError):
    """Raised when the configured provider cannot safely serve the pilot window."""


class PilotRetrievalError(RuntimeError):
    """Raised for a failed or incomplete pilot retrieval."""


def validate_spec(spec: dict[str, Any]) -> None:
    expected = PILOT_SPEC
    for key in ("stations", "primary_station", "neighbour_candidate", "provider", "parameters",
                "start_date_inclusive", "end_date_inclusive", "end_boundary_exclusive", "frequency", "model_fill"):
        if spec.get(key) != expected[key]:
            raise ValueError(f"Pilot specification mismatch for {key}")
    start = date.fromisoformat(spec["start_date_inclusive"])
    inclusive_end = date.fromisoformat(spec["end_date_inclusive"])
    exclusive_end = date.fromisoformat(spec["end_boundary_exclusive"])
    if exclusive_end != inclusive_end + timedelta(days=1) or start >= exclusive_end:
        raise ValueError("Pilot end date must be inclusive with the next date as the exclusive boundary")
    if spec.get("approval_status") != "PENDING_USER_APPROVAL":
        raise ValueError("Preparation artifact approval state must remain PENDING_USER_APPROVAL")


def dry_run_payload(spec: dict[str, Any] | None = None) -> dict[str, Any]:
    current = dict(PILOT_SPEC if spec is None else spec)
    validate_spec(current)
    return {
        "mode": "DRY_RUN",
        "stations": current["stations"],
        "provider": current["provider"],
        "parameters": current["parameters"],
        "start_inclusive": current["start_date_inclusive"],
        "end_inclusive": current["end_date_inclusive"],
        "end_exclusive": current["end_boundary_exclusive"],
        "frequency": current["frequency"],
        "timezone": current["comparison_timezone"],
        "model_fill": current["model_fill"],
        "approval_status": current["approval_status"],
        "package_requirement": f"meteostat=={current['package_version']} (isolated environment)",
        "credential_requirement": "No RapidAPI key for the Python dataset interface; METAR adapter requires MS_AVIATIONWEATHER_USER_AGENT.",
        "output_directory": current["expected_output_directory"],
        "provider_preflight": "BLOCKED: Meteostat 2.2.3 METAR adapter requests only hours=24 and runtime provider metadata starts 2026-11-16; requested 2025-09 window is unsupported.",
        "network_request_performed": False,
        "observation_rows_downloaded": False,
    }


def provider_window_supported(*, provider_start: date, requested_start: date, requested_end_exclusive: date,
                              now_utc: datetime, max_lookback_hours: int) -> bool:
    """Fail closed when provider runtime metadata or request horizon excludes the pilot."""
    if now_utc.tzinfo is None or now_utc.utcoffset() is None:
        raise ValueError("now_utc must be timezone-aware")
    now = now_utc.astimezone(timezone.utc)
    request_start = datetime.combine(requested_start, time.min, tzinfo=timezone.utc)
    request_end = datetime.combine(requested_end_exclusive, time.min, tzinfo=timezone.utc)
    earliest = now - timedelta(hours=max_lookback_hours)
    return (requested_start >= provider_start
            and request_start >= earliest
            and request_end <= now + timedelta(microseconds=1)
            and request_end - request_start <= timedelta(hours=max_lookback_hours))


def _utc_index(frame: pd.DataFrame) -> pd.DatetimeIndex:
    if "time" in frame.index.names:
        values = frame.index.get_level_values("time")
    elif isinstance(frame.index, pd.DatetimeIndex):
        values = frame.index
    elif "time" in frame.columns:
        values = frame["time"]
    else:
        raise ValueError("DataFrame must contain a time index or time column")
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True, errors="raise"))


def _source_values(frame: pd.DataFrame, field: str, valid: pd.Series) -> list[str]:
    source_col = f"{field}_source"
    if source_col not in frame.columns:
        return ["UNKNOWN"] * int(valid.sum())
    values = frame.loc[valid, source_col]
    return [str(v).strip() if pd.notna(v) and str(v).strip() else "UNKNOWN" for v in values]


def analyze_station_frame(frame: pd.DataFrame, *, station_id: str,
                          start_date: str = PILOT_SPEC["start_date_inclusive"],
                          end_exclusive: str = PILOT_SPEC["end_boundary_exclusive"]) -> list[dict[str, Any]]:
    """Summarize coverage and quality without dropping or altering raw values."""
    start = pd.Timestamp(start_date, tz="UTC")
    end = pd.Timestamp(end_exclusive, tz="UTC")
    expected = pd.date_range(start, end, freq="h", inclusive="left")
    times = _utc_index(frame)
    within = (times >= start) & (times < end)
    inside_times = times[within]
    monotonic = inside_times.is_monotonic_increasing
    duplicate_count = int(inside_times.duplicated().sum())
    records: list[dict[str, Any]] = []
    for field in PILOT_SPEC["parameters"]:
        if field not in frame.columns:
            values = pd.Series([float("nan")] * len(frame), index=frame.index, dtype="float64")
        else:
            values = pd.to_numeric(frame[field], errors="coerce")
        valid = values.notna() & pd.Series(within, index=frame.index)
        valid_times = pd.DatetimeIndex(times[valid.to_numpy()])
        valid_unique = valid_times.unique().sort_values()
        expected_missing = expected.difference(valid_unique)
        unexpected = valid_unique.difference(expected)
        intervals = valid_unique.to_series().diff().dropna()
        expected_step = pd.Timedelta(hours=1)
        source_vals = _source_values(frame, field, valid)
        unknown_sources = sum(value == "UNKNOWN" for value in source_vals)
        known_sources = sorted(set(value for value in source_vals if value != "UNKNOWN"))
        if field == "rhum" and known_sources:
            source_note = "Provider returns RHUM derived from METAR temperature and dew point in Meteostat 2.2.3."
        else:
            source_note = "Source values are retained from the returned per-parameter source columns; source label alone is not independent instrument verification."
        low, high = SUSPICIOUS_RANGES[field]
        in_window_values = values[valid]
        suspicious = int(((in_window_values < low) | (in_window_values > high)).sum())
        records.append({
            "station_id": station_id,
            "parameter": field,
            "unit": METRIC_UNITS[field],
            "row_count": int(len(inside_times)),
            "non_null_count": int(valid.sum()),
            "missing_value_count": int(len(inside_times) - int(valid.sum())),
            "missing_expected_count": int(len(expected_missing)),
            "completeness_percent": round(100 * len(valid_unique) / len(expected), 3) if len(expected) else None,
            "first_valid_timestamp_utc": valid_unique[0].isoformat() if len(valid_unique) else "",
            "last_valid_timestamp_utc": valid_unique[-1].isoformat() if len(valid_unique) else "",
            "duplicate_timestamp_count": duplicate_count,
            "timestamps_monotonic": bool(monotonic),
            "unexpected_timestamp_count": int(len(unexpected)),
            "non_hour_intervals": int((intervals != expected_step).sum()),
            "source_values": known_sources,
            "unknown_source_rows": int(unknown_sources),
            "suspicious_value_count_retained": suspicious,
            "source_note": source_note,
        })
    return records


def compare_common_timestamps(frame_a: pd.DataFrame, frame_b: pd.DataFrame,
                              *, station_a: str = "VILD0", station_b: str = "42105") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return per-variable timestamp counts and shared non-null values; never interpolate."""
    time_a, time_b = _utc_index(frame_a), _utc_index(frame_b)
    summary: list[dict[str, Any]] = []
    pairs: list[dict[str, Any]] = []
    for field in PILOT_SPEC["parameters"]:
        start = pd.Timestamp(PILOT_SPEC["start_date_inclusive"], tz="UTC")
        end = pd.Timestamp(PILOT_SPEC["end_boundary_exclusive"], tz="UTC")
        if field not in frame_a.columns or field not in frame_b.columns:
            valid_a, valid_b = set(), set()
        else:
            va = pd.to_numeric(frame_a[field], errors="coerce").notna().to_numpy()
            vb = pd.to_numeric(frame_b[field], errors="coerce").notna().to_numpy()
            valid_a = set(time_a[va & (time_a >= start) & (time_a < end)])
            valid_b = set(time_b[vb & (time_b >= start) & (time_b < end)])
        shared = valid_a & valid_b
        summary.append({"parameter": field, "station_a": station_a, "station_b": station_b,
                        "station_a_valid_timestamps": len(valid_a), "station_b_valid_timestamps": len(valid_b),
                        "shared_timestamps": len(shared), "a_only_timestamps": len(valid_a-shared),
                        "b_only_timestamps": len(valid_b-shared), "shared_valid_values_both_stations": len(shared)})
        if field in frame_a.columns and field in frame_b.columns:
            for timestamp in sorted(shared):
                idx_a = next(i for i, t in enumerate(time_a) if t == timestamp and pd.notna(frame_a[field].iloc[i]))
                idx_b = next(i for i, t in enumerate(time_b) if t == timestamp and pd.notna(frame_b[field].iloc[i]))
                pairs.append({"parameter": field, "timestamp_utc": timestamp.isoformat(),
                              "station_a": station_a, "station_a_value": frame_a[field].iloc[idx_a],
                              "station_a_source": frame_a.get(f"{field}_source", pd.Series(index=frame_a.index, dtype=object)).iloc[idx_a],
                              "station_b": station_b, "station_b_value": frame_b[field].iloc[idx_b],
                              "station_b_source": frame_b.get(f"{field}_source", pd.Series(index=frame_b.index, dtype=object)).iloc[idx_b]})
    return summary, pairs


def unique_run_directory(output_root: Path, run_id: str | None = None) -> Path:
    run_id = run_id or f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    run_dir = Path(output_root) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    for name in ("raw", "processed", "quality", "metadata", "reports"):
        (run_dir / name).mkdir()
    return run_dir


def write_immutable_dataframe(frame: pd.DataFrame, path: Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        frame.to_csv(stream, index=True, lineterminator="\n")
    return sha256_file(path)


def write_retrieval_failure(run_dir: Path, *, station_id: str, error: Exception,
                            observation_rows_downloaded: bool) -> Path:
    report = {"status": "FAILED", "station_id": station_id,
              "error_type": type(error).__name__, "message": str(error),
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "observation_rows_downloaded": observation_rows_downloaded,
              "successful_run_manifest_created": False}
    path = Path(run_dir) / "reports" / "retrieval_failure.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_run_manifest(*, run_dir: Path, stations: list[str], files: list[dict[str, Any]],
                       retrieval_timestamp_utc: str, package_version: str) -> dict[str, Any]:
    if not files:
        raise ValueError("A successful run manifest requires at least one retrieved observation artifact")
    return {"schema_version": 1, "run_id": Path(run_dir).name,
            "retrieval_timestamp_utc": retrieval_timestamp_utc, "stations": stations,
            "provider": "METAR", "parameters": PILOT_SPEC["parameters"],
            "start_date_inclusive": PILOT_SPEC["start_date_inclusive"],
            "end_date_inclusive": PILOT_SPEC["end_date_inclusive"],
            "end_boundary_exclusive": PILOT_SPEC["end_boundary_exclusive"],
            "frequency": "hourly", "source_timezone": "UTC (naive package timestamps)",
            "package_version": package_version,
            "artifact_type": "Meteostat Python TimeSeries DataFrame export; not original HTTP response bytes",
            "approval_state": "APPROVED_AT_EXECUTION", "files": files,
            "raw_observation_download_started": True}


def verify_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> bool:
    root = Path(run_dir).resolve()
    for record in manifest["files"]:
        path = (root / record["path"]).resolve()
        if root not in path.parents or not path.is_file() or sha256_file(path) != record["sha256"]:
            raise ValueError(f"Run artifact integrity check failed: {record['path']}")
    return True


def retrieve_station_meteostat(station_id: str, *, spec: dict[str, Any]) -> tuple[pd.DataFrame, str]:
    """Future-only provider adapter. It fails before a request for the current 2025 pilot window."""
    import importlib.metadata
    import importlib.util
    import meteostat as ms

    version = importlib.metadata.version("meteostat")
    if version != spec["package_version"]:
        raise PilotBlockedError(f"Expected Meteostat {spec['package_version']}; found {version}.")
    if ms.Provider.METAR.value != "metar":
        raise PilotBlockedError("Installed package does not expose the verified METAR provider enum.")
    if ms.config.include_model_data is not False:
        ms.config.include_model_data = False

    # Version 2.2.3 exposes provider start metadata through its request filter.
    # Inspect that local metadata before calling the public retrieval function.
    globals_ = ms.hourly.__globals__
    data_service = globals_.get("data_service")
    fetch_method = getattr(type(data_service), "_fetch_provider_data", None)
    provider_service = getattr(fetch_method, "__globals__", {}).get("provider_service")
    provider_record = provider_service.get_provider(ms.Provider.METAR) if provider_service else None
    if provider_record is None:
        raise PilotBlockedError("Could not verify the current METAR provider's supported time window.")
    provider_start = provider_record.start
    now = datetime.now(timezone.utc)
    if not provider_window_supported(
        provider_start=provider_start,
        requested_start=date.fromisoformat(spec["start_date_inclusive"]),
        requested_end_exclusive=date.fromisoformat(spec["end_boundary_exclusive"]),
        now_utc=now,
        max_lookback_hours=24,
    ):
        raise PilotBlockedError(
            f"Meteostat {version} METAR adapter's runtime window (provider start {provider_start}, "
            "endpoint hours=24) does not include the 2025-09 pilot. No observation request was made."
        )

    endpoint = ms.config.aviationweather_endpoint
    if "aviationweather.gov/api/data/metar" not in endpoint or "hours=24" not in endpoint:
        raise PilotBlockedError("The configured METAR endpoint differs from the inspected 24-hour Aviation Weather Center adapter.")
    user_agent = os.environ.get("MS_AVIATIONWEATHER_USER_AGENT", "").strip()
    if not user_agent:
        raise PilotBlockedError("Set MS_AVIATIONWEATHER_USER_AGENT before an approved Aviation Weather Center request.")
    ms.config.aviationweather_user_agent = user_agent
    if importlib.util.find_spec("metar") is None:
        raise PilotBlockedError("Meteostat's METAR parser dependency 'metar' is not installed in this environment.")

    parameters = [getattr(ms.Parameter, field.upper()) for field in spec["parameters"]]
    series = ms.hourly(
        station_id,
        date.fromisoformat(spec["start_date_inclusive"]),
        date.fromisoformat(spec["end_date_inclusive"]),
        timezone=None,
        parameters=parameters,
        providers=[ms.Provider.METAR],
    )
    actual_sources = set(getattr(series, "providers", []))
    if actual_sources and actual_sources != {"metar"}:
        raise PilotBlockedError(f"Provider source mismatch; received {sorted(actual_sources)}.")
    table = series.fetch(squash=True, fill=False, sources=True, clean=False,
                         humanize=False, units=ms.UnitSystem.METRIC)
    if table is None:
        raise PilotRetrievalError(f"Meteostat returned no DataFrame for station {station_id}.")
    return table, version


def execute_pilot(*, spec: dict[str, Any], execute: bool, confirm: bool,
                  output_root: Path,
                  retriever: Callable[[str, dict[str, Any]], tuple[pd.DataFrame, str]] | None = None,
                  provider_start: date | None = None,
                  now_utc: datetime | None = None) -> Path:
    """Execute only after explicit flags and provider-window preflight succeed."""
    validate_spec(spec)
    if not execute or not confirm:
        raise PermissionError("Retrieval requires both --execute and --confirm-pilot-retrieval.")
    if spec["approval_status"] != "PENDING_USER_APPROVAL":
        raise PermissionError("Approval state must be explicitly represented as pending before the user authorizes execution.")
    now = now_utc or datetime.now(timezone.utc)
    if retriever is None and provider_start is None:
        provider_start = runtime_meteostat_provider_start(spec["package_version"])
    if provider_start is not None and not provider_window_supported(
        provider_start=provider_start,
        requested_start=date.fromisoformat(spec["start_date_inclusive"]),
        requested_end_exclusive=date.fromisoformat(spec["end_boundary_exclusive"]),
        now_utc=now,
        max_lookback_hours=24,
    ):
        raise PilotBlockedError(f"METAR provider start {provider_start} and 24-hour endpoint cannot serve the requested 2025-09 window.")
    if retriever is None:
        def retriever(station: str, config: dict[str, Any]) -> tuple[pd.DataFrame, str]:
            return retrieve_station_meteostat(station, spec=config)
    # Never create a run directory until the interface preflight has succeeded.
    run_dir = unique_run_directory(output_root)
    retrieved_files: list[dict[str, Any]] = []
    frames: dict[str, pd.DataFrame] = {}
    version = spec["package_version"]
    retrieved_at = now.astimezone(timezone.utc).isoformat()
    for station in spec["stations"]:
        try:
            frame, version = retriever(station, spec)
            if frame is None or frame.empty:
                raise PilotRetrievalError(f"No observations returned for {station}.")
            source_cols = [f"{p}_source" for p in spec["parameters"] if f"{p}_source" in frame.columns]
            for column in source_cols:
                values = set(str(x).strip().lower() for x in frame[column].dropna() if str(x).strip())
                if values - {"metar"}:
                    raise PilotBlockedError(f"Non-METAR source returned in {column}: {sorted(values)}")
            path = run_dir / "raw" / f"{station}_meteostat_metar_dataframe.csv"
            digest = write_immutable_dataframe(frame, path)
            retrieved_files.append({"path": path.relative_to(run_dir).as_posix(), "sha256": digest,
                                    "size_bytes": path.stat().st_size, "station_id": station})
            frames[station] = frame
        except Exception as exc:
            write_retrieval_failure(run_dir, station_id=station, error=exc,
                                    observation_rows_downloaded=bool(retrieved_files))
            raise PilotRetrievalError(str(exc)) from exc
    if set(frames) != set(spec["stations"]):
        raise PilotRetrievalError("Both requested stations must be retrieved; substitutions are prohibited.")
    (run_dir / "metadata" / "quality_by_station.json").write_text(
        json.dumps({station: analyze_station_frame(frame, station_id=station) for station, frame in frames.items()}, indent=2)+"\n", encoding="utf-8")
    summary, pairs = compare_common_timestamps(frames["VILD0"], frames["42105"])
    (run_dir / "quality" / "common_timestamp_summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    if pairs:
        pd.DataFrame(pairs).to_csv(run_dir / "processed" / "common_timestamp_values.csv", index=False)
    manifest = build_run_manifest(run_dir=run_dir, stations=spec["stations"], files=retrieved_files,
                                  retrieval_timestamp_utc=retrieved_at, package_version=version)
    for relative in ("metadata/quality_by_station.json", "quality/common_timestamp_summary.json"):
        path = run_dir / relative
        manifest["files"].append({"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    for relative in ("processed/common_timestamp_values.csv",):
        path = run_dir / relative
        if path.exists():
            manifest["files"].append({"path": relative, "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    (run_dir / "metadata" / "pilot_run_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    verify_run_manifest(run_dir, manifest)
    return run_dir


def runtime_meteostat_provider_start(required_version: str) -> date:
    """Inspect the pinned provider registry without invoking the timeseries request."""
    import importlib.metadata
    try:
        import meteostat as ms
    except ImportError as exc:
        raise PilotBlockedError(f"Meteostat {required_version} is not installed in this environment.") from exc

    version = importlib.metadata.version("meteostat")
    if version != required_version:
        raise PilotBlockedError(f"Expected Meteostat {required_version}; found {version}.")
    fetch_method = getattr(type(ms.hourly.__globals__["data_service"]), "_fetch_provider_data", None)
    provider_service = getattr(fetch_method, "__globals__", {}).get("provider_service")
    provider = provider_service.get_provider(ms.Provider.METAR) if provider_service else None
    if provider is None or not isinstance(provider.start, date):
        raise PilotBlockedError("Could not inspect a supported METAR provider start date; refusing retrieval.")
    return provider.start
