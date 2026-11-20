import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from weather_research.metar_pilot import (
    PILOT_SPEC, PilotBlockedError, analyze_station_frame, build_run_manifest,
    compare_common_timestamps, dry_run_payload, execute_pilot,
    provider_window_supported, sha256_file, unique_run_directory,
    validate_spec, verify_run_manifest, write_immutable_dataframe,
    write_retrieval_failure,
)
from scripts.run_phase1c_metar_pilot import main as pilot_cli_main


class MetarPilotConfigTests(unittest.TestCase):
    def test_correct_station_selection(self):
        self.assertEqual(PILOT_SPEC["stations"], ["VILD0", "42105"])

    def test_correct_five_parameters(self):
        self.assertEqual(PILOT_SPEC["parameters"], ["temp", "rhum", "wspd", "wdir", "pres"])

    def test_exact_date_boundaries(self):
        self.assertEqual(PILOT_SPEC["start_date_inclusive"], "2025-09-01")
        self.assertEqual(PILOT_SPEC["end_date_inclusive"], "2025-09-30")
        self.assertEqual(PILOT_SPEC["end_boundary_exclusive"], "2025-10-01")
        validate_spec(PILOT_SPEC)

    def test_end_boundary_is_exclusive_next_day(self):
        spec = dict(PILOT_SPEC)
        spec["end_boundary_exclusive"] = "2025-09-30"
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_metar_provider_is_enforced(self):
        spec = dict(PILOT_SPEC)
        spec["provider"] = "HOURLY"
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_model_fill_is_disabled(self):
        self.assertIs(PILOT_SPEC["model_fill"], False)
        self.assertFalse(dry_run_payload()["model_fill"])

    def test_unknown_provider_is_rejected(self):
        spec = dict(PILOT_SPEC)
        spec["provider"] = "UNKNOWN_PROVIDER"
        with self.assertRaises(ValueError):
            validate_spec(spec)

    def test_provider_runtime_window_blocks_requested_pilot(self):
        self.assertFalse(provider_window_supported(
            provider_start=date(2026, 11, 16),
            requested_start=date(2025, 9, 1),
            requested_end_exclusive=date(2025, 10, 1),
            now_utc=datetime(2026, 11, 17, tzinfo=timezone.utc),
            max_lookback_hours=24,
        ))

    def test_provider_window_rejects_duration_longer_than_lookback(self):
        self.assertFalse(provider_window_supported(
            provider_start=date(2020, 1, 1),
            requested_start=date(2026, 11, 16),
            requested_end_exclusive=date(2026, 11, 17),
            now_utc=datetime(2026, 11, 17, 12, tzinfo=timezone.utc),
            max_lookback_hours=24,
        ))

    def test_dry_run_reports_no_network_or_download(self):
        report = dry_run_payload()
        self.assertFalse(report["network_request_performed"])
        self.assertFalse(report["observation_rows_downloaded"])
        self.assertEqual(report["approval_status"], "PENDING_USER_APPROVAL")


class MetarPilotApprovalTests(unittest.TestCase):
    def test_cli_dry_run_never_calls_execution(self):
        with patch("scripts.run_phase1c_metar_pilot.execute_pilot") as execute:
            self.assertEqual(pilot_cli_main([]), 0)
            execute.assert_not_called()

    def test_execution_refused_without_both_confirmation_flags(self):
        called = []
        def fake_retrieve(station, spec):
            called.append(station)
            raise AssertionError("retriever should not be called")
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PermissionError):
                execute_pilot(spec=PILOT_SPEC, execute=True, confirm=False,
                              output_root=Path(temp_dir), retriever=fake_retrieve)
        self.assertEqual(called, [])

    def test_current_provider_window_refuses_before_retriever_or_output(self):
        called = []
        def fake_retrieve(station, spec):
            called.append(station)
            return pd.DataFrame(), "mock"
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PilotBlockedError):
                execute_pilot(spec=PILOT_SPEC, execute=True, confirm=True,
                              output_root=Path(temp_dir), retriever=fake_retrieve,
                              provider_start=date(2026, 11, 16),
                              now_utc=datetime(2026, 11, 17, tzinfo=timezone.utc))
            self.assertEqual(list(Path(temp_dir).iterdir()), [])
        self.assertEqual(called, [])


class MetarPilotQualityTests(unittest.TestCase):
    @staticmethod
    def sample_frame(index, *, values=None, sources=True):
        values = values or {"temp": [20.0] * len(index), "rhum": [50.0] * len(index),
                            "wspd": [10.0] * len(index), "wdir": [180.0] * len(index),
                            "pres": [1000.0] * len(index)}
        frame = pd.DataFrame(values, index=index)
        if sources:
            for parameter in PILOT_SPEC["parameters"]:
                frame[f"{parameter}_source"] = "metar"
        return frame

    def test_missing_source_indicators_are_unknown(self):
        frame = self.sample_frame(pd.date_range("2025-09-01", periods=2, freq="h"), sources=False)
        row = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T02:00:00Z")[0]
        self.assertEqual(row["unknown_source_rows"], 2)
        self.assertEqual(row["source_values"], [])

    def test_duplicate_timestamp_detection(self):
        index = pd.DatetimeIndex(["2025-09-01T00:00Z", "2025-09-01T00:00Z"])
        frame = self.sample_frame(index)
        row = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T02:00:00Z")[0]
        self.assertEqual(row["duplicate_timestamp_count"], 1)
        self.assertEqual(row["completeness_percent"], 50.0)

    def test_missing_values_are_separate_from_missing_hourly_timestamps(self):
        index = pd.DatetimeIndex(["2025-09-01T00:00Z", "2025-09-01T01:00Z"])
        frame = self.sample_frame(index)
        frame.loc[index[0], "temp"] = float("nan")
        row = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T02:00:00Z")[0]
        self.assertEqual(row["missing_value_count"], 1)
        self.assertEqual(row["missing_expected_count"], 1)
        self.assertEqual(row["completeness_percent"], 50.0)

    def test_missing_hour_detection(self):
        index = pd.DatetimeIndex(["2025-09-01T00:00Z", "2025-09-01T02:00Z"])
        frame = self.sample_frame(index)
        row = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T03:00:00Z")[0]
        self.assertEqual(row["missing_expected_count"], 1)
        self.assertEqual(row["non_hour_intervals"], 1)

    def test_utc_normalization_of_naive_timestamps(self):
        frame = self.sample_frame(pd.DatetimeIndex(["2025-09-01 00:00", "2025-09-01 01:00"]))
        row = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T02:00:00Z")[0]
        self.assertTrue(row["first_valid_timestamp_utc"].endswith("+00:00"))

    def test_variable_completeness_uses_expected_hourly_grid(self):
        frame = self.sample_frame(pd.DatetimeIndex(["2025-09-01T00:00Z", "2025-09-01T02:00Z"]))
        rows = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T03:00:00Z")
        self.assertEqual(rows[0]["completeness_percent"], 66.667)

    def test_actual_common_timestamp_intersection(self):
        a = self.sample_frame(pd.DatetimeIndex(["2025-09-01T00:00Z", "2025-09-01T01:00Z"]))
        b = self.sample_frame(pd.DatetimeIndex(["2025-09-01T01:00Z", "2025-09-01T02:00Z"]))
        summary, pairs = compare_common_timestamps(a, b)
        self.assertEqual(summary[0]["shared_timestamps"], 1)
        self.assertEqual(summary[0]["a_only_timestamps"], 1)
        self.assertEqual(summary[0]["b_only_timestamps"], 1)
        self.assertEqual(len(pairs), 5)

    def test_unusual_values_are_flagged_but_retained(self):
        frame = self.sample_frame(pd.DatetimeIndex(["2025-09-01T00:00Z"]), values={"temp": [69.0], "rhum": [55.0], "wspd": [7.0], "wdir": [10.0], "pres": [1002.0]})
        result = analyze_station_frame(frame, station_id="VILD0", start_date="2025-09-01", end_exclusive="2025-09-01T01:00:00Z")
        self.assertEqual(result[0]["suspicious_value_count_retained"], 0)
        self.assertEqual(frame.iloc[0]["temp"], 69.0)


class MetarPilotStorageTests(unittest.TestCase):
    def test_unique_run_directory_generation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = unique_run_directory(Path(temp_dir), "run-1")
            self.assertTrue((first / "raw").is_dir())
            with self.assertRaises(FileExistsError):
                unique_run_directory(Path(temp_dir), "run-1")

    def test_immutable_raw_export_and_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "raw.csv"
            frame = pd.DataFrame({"temp": [12.5]}, index=pd.DatetimeIndex(["2025-09-01T00:00Z"], name="time"))
            digest = write_immutable_dataframe(frame, path)
            self.assertEqual(digest, sha256_file(path))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_immutable_dataframe(frame, path)
            self.assertEqual(path.read_bytes(), before)

    def test_retrieval_failure_has_no_success_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = unique_run_directory(Path(temp_dir), "failed-run")
            failure = write_retrieval_failure(run_dir, station_id="VILD0", error=RuntimeError("mock failure"), observation_rows_downloaded=False)
            record = json.loads(failure.read_text(encoding="utf-8"))
            self.assertFalse(record["successful_run_manifest_created"])
            self.assertFalse((run_dir / "metadata" / "pilot_run_manifest.json").exists())

    def test_manifest_hash_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = unique_run_directory(Path(temp_dir), "manifest-run")
            raw_path = run_dir / "raw" / "VILD0.csv"
            digest = write_immutable_dataframe(pd.DataFrame({"temp": [1.0]}), raw_path)
            manifest = build_run_manifest(run_dir=run_dir, stations=["VILD0", "42105"],
                                          files=[{"path": "raw/VILD0.csv", "sha256": digest,
                                                  "size_bytes": raw_path.stat().st_size, "station_id": "VILD0"}],
                                          retrieval_timestamp_utc="2026-11-17T00:00:00+00:00", package_version="2.2.3")
            self.assertTrue(verify_run_manifest(run_dir, manifest))
            raw_path.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_run_manifest(run_dir, manifest)


if __name__ == "__main__":
    unittest.main()
