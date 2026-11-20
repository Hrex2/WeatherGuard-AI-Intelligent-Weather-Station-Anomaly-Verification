from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from weather_research.e3_spatial import DEFAULT_ZONES, assign_distance_zone, nearest_timestamp_pairs
from weather_research.phase04_collection import (
    coverage_metrics,
    eligible_for_retrieval,
    fetch_observation_sources,
    missingness_rows,
    sha256_file,
    source_series,
    write_raw_frame,
)


def source_frame():
    idx = pd.MultiIndex.from_tuples([
        (pd.Timestamp("2025-03-28T00:00:00Z"), "isd_lite"),
        (pd.Timestamp("2025-03-28T00:00:00Z"), "ghcnh"),
        (pd.Timestamp("2025-03-28T01:00:00Z"), "isd_lite"),
    ], names=["time", "source"])
    return pd.DataFrame({"temp": [10.0, 11.0, None], "dwpt": [2.0, None, None],
                         "rhum": [45.0, None, None], "prcp": [0.0, None, None],
                         "wspd": [3.0, None, None], "pres": [1000.0, None, None]}, index=idx)


def test_explicit_model_exclusion_and_source_metadata_restoration():
    observed = {}
    frame = source_frame()

    class Config:
        include_model_data = True
        cache_enable = True

    class Series:
        def fetch(self, **kwargs):
            observed["fetch_kwargs"] = kwargs
            observed["model_during_fetch"] = config.include_model_data
            observed["cache_during_fetch"] = config.cache_enable
            return frame

    def hourly(station, start, end, *, timezone, parameters, providers):
        observed.update({"station": station, "timezone": timezone, "parameters": parameters, "providers": providers})
        return Series()

    config = Config()
    ms = SimpleNamespace(__version__="2.2.3", config=config, hourly=hourly, Provider=SimpleNamespace(HOURLY="hourly"))
    result, settings = fetch_observation_sources(ms, "42099", datetime(2025, 3, 28), datetime(2025, 3, 29), "UTC", ["temp"])
    assert result.equals(frame)
    assert observed["model_during_fetch"] is False
    assert observed["cache_during_fetch"] is False
    assert config.include_model_data is True
    assert config.cache_enable is True
    assert observed["fetch_kwargs"] == {"squash": False, "fill": False, "sources": True,
                                        "location": False, "clean": False, "humanize": False}
    assert settings["source_setting"] is True and settings["model_setting"] is False
    assert "source" in result.index.names


def test_model_setting_restored_after_fetch_failure():
    class Config:
        include_model_data = True
        cache_enable = True

    class Series:
        def fetch(self, **kwargs):
            raise RuntimeError("network unavailable")

    config = Config()
    def hourly(station, start, end, *, timezone, parameters, providers):
        return Series()
    ms = SimpleNamespace(__version__="2.2.3", config=config,
                         hourly=hourly, Provider=SimpleNamespace(HOURLY="hourly"))
    with pytest.raises(RuntimeError, match="network unavailable"):
        fetch_observation_sources(ms, "42099", datetime(2025, 1, 1), datetime(2025, 1, 2), "UTC", ["temp"])
    assert config.include_model_data is True
    assert config.cache_enable is True


def test_duplicate_timestamps_and_timezone_and_missingness_are_explicit():
    frame = source_frame()
    result = coverage_metrics(frame, pd.Timestamp("2025-03-28T00:00:00Z"),
                              pd.Timestamp("2025-03-28T02:00:00Z"))
    assert result["source_time_rows"] == 3
    assert result["unique_timestamps"] == 2
    assert result["duplicate_source_time_rows"] == 2
    assert result["timestamps_with_multiple_source_rows"] == 1
    assert result["timezone"] == "UTC"
    assert result["missing_expected_timestamps"] == 1
    miss = missingness_rows("42099", frame, pd.Timestamp("2025-03-28T00:00:00Z"),
                             pd.Timestamp("2025-03-28T02:00:00Z"))
    temp = next(row for row in miss if row["variable"] == "temp")
    assert temp["unique_timestamps_with_value"] == 1
    assert temp["missing_expected_timestamps"] == 2
    assert "not disagreement" in temp["interpretation"]


def test_exact_and_tolerance_pairs_remain_separate():
    primary = pd.Series([1.0, 2.0], index=pd.DatetimeIndex(["2025-01-01T00:00Z", "2025-01-01T01:00Z"]))
    neighbor = pd.Series([1.2, 2.3], index=pd.DatetimeIndex(["2025-01-01T00:00Z", "2025-01-01T01:15Z"]))
    assert nearest_timestamp_pairs(primary, neighbor, 0).match_type.tolist() == ["EXACT", "NO_MATCH"]
    assert nearest_timestamp_pairs(primary, neighbor, 15).match_type.tolist() == ["EXACT", "TOLERANCE_MATCH"]


def test_unverified_stations_are_excluded_from_retrieval():
    verified = "VERIFIED_IDENTITY_AND_HISTORIC_SITE_METADATA"
    assert eligible_for_retrieval("42099", verified)
    assert eligible_for_retrieval("42101", verified)
    assert not eligible_for_retrieval("VILD0", verified)
    assert not eligible_for_retrieval("42105", "UNVERIFIED")


def test_provisional_zone_boundaries_and_unknown_zone_rejection():
    assert [assign_distance_zone(d) for d in [0, 10, 50, 100, 250, 251]] == ["A", "B", "C", "D", "E", "E"]
    assert [zone.name for zone in DEFAULT_ZONES] == list("ABCDE")
    with pytest.raises(ValueError):
        assign_distance_zone(float("nan"))


def test_raw_export_is_preserved_and_hash_is_reproducible(tmp_path: Path):
    destination = tmp_path / "raw" / "42099.csv"
    frame = source_frame()
    first_hash = write_raw_frame(frame, destination)
    assert first_hash == sha256_file(destination)
    raw = pd.read_csv(destination)
    assert "source" in raw.columns
    assert set(raw.source) == {"isd_lite", "ghcnh"}
    with pytest.raises(FileExistsError):
        write_raw_frame(frame, destination)
    assert sha256_file(destination) == first_hash


def test_source_series_preserves_per_source_values():
    series = source_series(source_frame(), "temp")
    assert list(series) == ["isd_lite", "ghcnh"]
    assert series["isd_lite"].iloc[0] == 10
    assert series["ghcnh"].iloc[0] == 11

