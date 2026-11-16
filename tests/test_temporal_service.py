"""Tests for independent causal and retrospective temporal verification."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from services.temporal_service import temporal_verification


class TestTemporalVerification(unittest.TestCase):
    def frame(self, values, times=None):
        index = times or pd.date_range("2025-01-01", periods=len(values), freq="h", tz="Asia/Kolkata")
        return pd.DataFrame({"temp": values}, index=index)

    def test_realtime_spike_is_causal_and_does_not_read_future(self):
        values = [10.0] * 8 + [30.0] + [10.0] * 8
        frame = self.frame(values)
        ts = frame.index[8]
        result = temporal_verification(frame, ts, "temp", window_hours=6, mode="real_time")
        self.assertEqual(result["status"], "SUPPORTING")
        self.assertEqual(result["future_count"], 0)
        changed_future = frame.copy()
        changed_future.loc[ts + pd.Timedelta(hours=1):, "temp"] = 500
        after = temporal_verification(changed_future, ts, "temp", window_hours=6, mode="real_time")
        self.assertEqual(result["robust_deviation"], after["robust_deviation"])

    def test_retrospective_persistence_and_return_to_baseline(self):
        ts = pd.date_range("2025-01-01", periods=18, freq="h", tz="Asia/Kolkata")[8]
        persistent = self.frame([10.0] * 8 + [30.0] * 10)
        isolated = self.frame([10.0] * 8 + [30.0] + [10.0] * 9)
        self.assertEqual(temporal_verification(persistent, ts, "temp", mode="retrospective")["status"], "SUPPORTING")
        self.assertEqual(temporal_verification(isolated, ts, "temp", mode="retrospective")["status"], "CONFLICTING")

    def test_gradual_and_stable_series_have_no_robust_departure(self):
        stable = self.frame([10.0] * 18)
        gradual = self.frame(np.linspace(10, 12, 18).tolist())
        for frame in (stable, gradual):
            result = temporal_verification(frame, frame.index[12], "temp")
            self.assertEqual(result["status"], "NO_DETECTED_EVIDENCE")

    def test_stuck_sensor_pattern_is_reported_without_fault_diagnosis(self):
        frame = self.frame([10, 11, 12, 13, 14, 15, 15, 15, 15, 15, 15, 15])
        result = temporal_verification(frame, frame.index[-1], "temp", window_hours=8)
        self.assertGreaterEqual(result["stuck_run_length"], 4)
        self.assertTrue(result["stuck_pattern"])
        self.assertIn(result["status"], {"SUPPORTING", "NO_DETECTED_EVIDENCE"})

    def test_missing_current_value_and_insufficient_history_are_unavailable(self):
        frame = self.frame([10.0, 10.0, np.nan, 10.0, 11.0])
        self.assertEqual(temporal_verification(frame, frame.index[2], "temp")["status"], "UNAVAILABLE")
        self.assertEqual(temporal_verification(frame, frame.index[0], "temp")["status"], "UNAVAILABLE")

    def test_irregular_time_and_long_gaps_do_not_bridge_segments(self):
        times = list(pd.date_range("2025-01-01", periods=5, freq="h", tz="Asia/Kolkata"))
        times += list(pd.date_range("2025-01-04", periods=5, freq="h", tz="Asia/Kolkata"))
        frame = self.frame([10, 10, 10, 10, 10, 50, 50, 50, 50, 50], times)
        result = temporal_verification(frame, frame.index[5], "temp", window_hours=72)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["prior_count"], 0)

    def test_retrospective_insufficient_following_data_is_unavailable(self):
        frame = self.frame([10.0] * 7 + [30.0])
        result = temporal_verification(frame, frame.index[-1], "temp", mode="retrospective")
        self.assertEqual(result["status"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
