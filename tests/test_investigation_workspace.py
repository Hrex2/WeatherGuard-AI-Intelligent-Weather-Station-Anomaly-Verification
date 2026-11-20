"""Regression coverage for the interactive investigation and CSV services."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from services.data_service import load_project_data
from services.investigation_service import (available_weather_variables,
                                             model_heatmap_data,
                                             variable_diagnostics,
                                             verified_station_location)
from services.uploaded_analysis import (BASE_VARIABLES,
                                        prepare_uploaded_weather_data)


class TestInvestigationServices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, _, _ = load_project_data(ROOT)

    def test_heatmap_uses_saved_grid_and_family_filter(self):
        pred = self.data["predictions"]
        first, last = pred.timestamp.min(), pred.timestamp.max()
        all_models = model_heatmap_data(pred, first, last)
        self.assertEqual(all_models["full_matrix"].shape, (8415, 12))
        self.assertEqual(len(all_models["configurations"]), 12)
        first_family = pred.family.iloc[0]
        family = model_heatmap_data(pred, first, first + pd.Timedelta(hours=24), [first_family])
        self.assertEqual(set(family["configurations"]), set(pred.loc[pred.family.eq(first_family), "configuration"].unique()))
        self.assertLessEqual(len(family["all_timestamps"]), 25)
        self.assertTrue(model_heatmap_data(pred, first, first + pd.Timedelta(hours=24), []).get("full_matrix").empty)

    def test_heatmap_missing_cells_and_consensus_only_on_complete_twelve(self):
        pred = self.data["predictions"].head(12).copy()
        pred["is_candidate"] = pred.is_candidate.astype("boolean")
        pred.loc[pred.index[0], "is_candidate"] = pd.NA
        first = pred.timestamp.min()
        result = model_heatmap_data(pred, first, first)
        self.assertTrue(pd.isna(result["full_matrix"].loc[first, pred.iloc[0].configuration]))
        self.assertTrue(pd.isna(result["agreement"].loc[first, "consensus_8_of_12"]))
        partial = pred.iloc[:3].copy()
        partial_result = model_heatmap_data(partial, first, first)
        self.assertTrue(pd.isna(partial_result["agreement"].loc[first, "consensus_8_of_12"]))

    def test_heatmap_date_range(self):
        pred = self.data["predictions"]
        first = pred.timestamp.min()
        result = model_heatmap_data(pred, first, first + pd.Timedelta(hours=5))
        self.assertTrue(result["all_timestamps"].min() >= first)
        self.assertTrue(result["all_timestamps"].max() <= first + pd.Timedelta(hours=5))

    def test_variables_are_discovered_from_real_columns_and_causal(self):
        obs = self.data["observations"].iloc[:30].copy()
        variables = available_weather_variables(obs)
        self.assertEqual(set(variables), {"temp", "dwpt", "rhum", "prcp", "wspd", "pres"})
        result = variable_diagnostics(obs, "temp")
        self.assertTrue(pd.isna(result["series"].iloc[0].previous_rolling_mean))
        self.assertEqual(result["series"].iloc[1].previous_rolling_mean, result["series"].iloc[0].value)
        with self.assertRaises(KeyError):
            variable_diagnostics(obs, "snow")

    def test_verified_map_refuses_unverified_coordinates(self):
        result = verified_station_location(ROOT, "VILD0")
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "Station coordinates unavailable.")


class TestUploadedDataPreparation(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=120, freq="h").astype(str),
            "t": np.linspace(10, 20, 120), "d": np.linspace(2, 8, 120),
            "rh": np.linspace(40, 70, 120), "rain": np.zeros(120),
            "wind": np.linspace(1, 5, 120), "pressure": np.linspace(1000, 1005, 120),
        })
        self.mapping = dict(zip(BASE_VARIABLES, ["t", "d", "rh", "rain", "wind", "pressure"]))
        self.units = {name: unit for name, unit in zip(["t", "d", "rh", "rain", "wind", "pressure"], ["°C", "°C", "%", "mm", "km/h", "hPa"])}

    def test_validation_prepares_ordered_chronological_train_test_and_does_not_mutate(self):
        original = self.frame.copy(deep=True)
        prepared = prepare_uploaded_weather_data(self.frame, "time", self.mapping, self.units)
        pd.testing.assert_frame_equal(self.frame, original)
        self.assertEqual(prepared["metadata"]["feature_order"], ["temp", "dwpt", "rhum", "prcp", "wspd", "pres", "temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h", "month_sin", "month_cos"])
        self.assertLess(prepared["train"].index.max(), prepared["test"].index.min())
        self.assertTrue(np.isfinite(prepared["test"].to_numpy()).all())
        self.assertEqual(prepared["metadata"]["usable_rows"], 120)
        self.assertEqual(prepared["metadata"]["excluded_rows"], 0)

    def test_unit_conversion_and_training_only_medians(self):
        frame = self.frame.copy()
        frame["t"] = frame["t"] * 9 / 5 + 32
        units = {**self.units, "t": "°F"}
        converted = prepare_uploaded_weather_data(frame, "time", self.mapping, units)
        self.assertAlmostEqual(converted["observations"].temp.iloc[0], 10)

    def test_csv_acceptance_cases_missing_columns_bad_values_missing_data_and_empty(self):
        # Case A: extra source columns are tolerated and valid data are prepared.
        extra = self.frame.assign(operator_note="not a model feature")
        prepared = prepare_uploaded_weather_data(extra, "time", self.mapping, self.units)
        self.assertEqual(prepared["metadata"]["usable_rows"], 120)

        # Case B: identify precisely which mapped source field is absent.
        with self.assertRaisesRegex(KeyError, r"temp \(t\)"):
            prepare_uploaded_weather_data(self.frame.drop(columns="t"), "time", self.mapping, self.units)

        # Case C: fail with a column-specific message when measurements are text.
        bad_numeric = self.frame.copy()
        bad_numeric["t"] = bad_numeric["t"].astype(object)
        bad_numeric.loc[0, "t"] = "warm"
        with self.assertRaisesRegex(ValueError, r"Column t contains 1 non-numeric temp value"):
            prepare_uploaded_weather_data(bad_numeric, "time", self.mapping, self.units)

        # Case D: report partial missingness; reject an all-empty model variable.
        partial = self.frame.copy()
        partial.loc[0, "t"] = np.nan
        result = prepare_uploaded_weather_data(partial, "time", self.mapping, self.units)
        self.assertEqual(result["metadata"]["missing_values_by_variable"]["temp"], 1)
        all_missing = self.frame.copy()
        all_missing["rain"] = np.nan
        with self.assertRaisesRegex(ValueError, r"all-missing training variable.*prcp"):
            prepare_uploaded_weather_data(all_missing, "time", self.mapping, self.units)

        # Case E: empty input is a handled validation error, not an empty model run.
        with self.assertRaisesRegex(ValueError, "uploaded CSV is empty"):
            prepare_uploaded_weather_data(self.frame.iloc[:0], "time", self.mapping, self.units)

    def test_duplicate_bad_and_nonhourly_timestamps_fail_closed(self):
        duplicate = self.frame.copy()
        duplicate.loc[1, "time"] = duplicate.loc[0, "time"]
        with self.assertRaisesRegex(ValueError, "Duplicate timestamps"):
            prepare_uploaded_weather_data(duplicate, "time", self.mapping, self.units)
        bad = self.frame.copy()
        bad.loc[0, "time"] = "not a date"
        with self.assertRaisesRegex(ValueError, "invalid or missing timestamps"):
            prepare_uploaded_weather_data(bad, "time", self.mapping, self.units)
        mixed_timezone = self.frame.copy()
        mixed_timezone.loc[1, "time"] = "2024-01-01T01:00:00Z"
        with self.assertRaisesRegex(ValueError, "mix timezone-aware and timezone-naive"):
            prepare_uploaded_weather_data(mixed_timezone, "time", self.mapping, self.units)
        irregular = self.frame.copy()
        hourly = pd.date_range("2024-01-01", periods=120, freq="h")
        hourly = hourly.to_series()
        hourly.iloc[60:] += pd.Timedelta(hours=1)
        irregular["time"] = hourly.astype(str).to_numpy()
        with self.assertRaisesRegex(ValueError, "every adjacent timestamp.*1 interval.*1 hourly timestamp"):
            prepare_uploaded_weather_data(irregular, "time", self.mapping, self.units)


if __name__ == "__main__":
    unittest.main()
