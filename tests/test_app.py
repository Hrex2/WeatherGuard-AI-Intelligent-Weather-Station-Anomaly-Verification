"""Application data-contract and Streamlit workspace smoke tests."""
from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from services.data_service import load_project_data, prediction_wide
from services.evidence_service import observation_evidence
from services.model_metadata import build_model_education


class TestWeatherGuardApplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.manifest, cls.hashes = load_project_data(ROOT)

    def test_dataset_artifacts_and_feature_contract(self):
        self.assertEqual(len(self.data["observations"]), 44879)
        self.assertEqual(len(self.data["train"]), 36434)
        self.assertEqual(len(self.data["test"]), 8415)
        self.assertEqual(self.data["train"].columns.tolist(), self.data["test"].columns.tolist())
        self.assertTrue(self.manifest["audit_passed"])
        self.assertEqual(set(self.hashes), {"observations", "train", "test"})

    def test_manifest_hash_mismatch_fails_closed_with_affected_filename(self):
        with patch("services.data_service.sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "SHA-256 verification failed for model_df.csv"):
                load_project_data(ROOT)

    def test_saved_predictions_are_complete_timestamp_aligned_grid(self):
        wide = prediction_wide(self.data["predictions"])
        self.assertEqual(wide.shape, (8415, 12))
        self.assertFalse(wide.isna().any().any())

    def test_unavailable_spatial_inputs_keep_uncertain_outcome(self):
        ts = self.data["observations"].index[-1]
        result = observation_evidence(ts, self.data["observations"], self.data["predictions"],
                                      self.data["stability"], self.data["episodes"], {})
        self.assertEqual(result["evidence_states"]["E3"], "UNAVAILABLE")
        self.assertEqual(result["outcome"], "UNCERTAIN_INSUFFICIENT_EVIDENCE")

    def test_subthreshold_votes_are_not_reported_as_conflicting_and_episodes_are_context(self):
        ts = self.data["stability"].iloc[0].timestamp
        predictions = self.data["predictions"].loc[self.data["predictions"].timestamp.eq(ts)].copy()
        predictions["is_candidate"] = False
        predictions.loc[predictions.index[:3], "is_candidate"] = True
        result = observation_evidence(ts, self.data["observations"], predictions,
                                      self.data["stability"], self.data["episodes"], {})
        self.assertEqual(result["vote_count"], 3)
        self.assertEqual(result["evidence_states"]["E1"], "NO_DETECTED_EVIDENCE")
        self.assertEqual(result["evidence_states"]["E2"], "UNAVAILABLE")

    def test_missing_values_alone_do_not_support_sensor_fault_evidence(self):
        ts = self.data["observations"].index[0]
        observations = self.data["observations"].copy()
        observations.loc[ts, ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"]] = float("nan")
        result = observation_evidence(ts, observations, self.data["predictions"],
                                      self.data["stability"], self.data["episodes"], {})
        self.assertEqual(result["evidence_states"]["E4"], "UNAVAILABLE")
        self.assertGreater(result["missing_quality_values"], 0)
        self.assertEqual(len(result["physical_screening_violations"]), 0)

    def test_saved_synthetic_campaign_separates_anywhere_and_unaffected_window_changes(self):
        results = pd.read_csv(ROOT / "outputs" / "synthetic_fault_campaign" / "event_level_results.csv")
        self.assertEqual(results.changed_configuration_predictions_anywhere.tolist(), [10, 15, 20, 21])
        self.assertEqual(results.unaffected_window_changed_configuration_predictions.tolist(), [0, 0, 0, 0])
        self.assertTrue(results.evaluation_window.str.contains("outside the injected observation").all())

    def test_model_education_uses_actual_configs_parameters_and_dataset_metadata(self):
        education = build_model_education(self.data)
        self.assertEqual(education["input_features"], 11)
        self.assertEqual(education["feature_order"], ["temp", "dwpt", "rhum", "prcp", "wspd", "pres", "temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h", "month_sin", "month_cos"])
        self.assertEqual(education["train_rows"], 36434)
        self.assertEqual(education["test_rows"], 8415)
        profiles = education["profiles"]
        self.assertEqual(sum(len(profile["configs"]) for profile in profiles.values()), 12)
        self.assertEqual([x["value"] for x in profiles["IsolationForest"]["configs"]], [0.01, 0.02, 0.03, 0.05])
        self.assertEqual(profiles["IsolationForest"]["configs"][0]["parameters"]["n_estimators"], 200)
        self.assertEqual(profiles["IsolationForest"]["configs"][0]["parameters"]["n_jobs"], -1)
        self.assertEqual(profiles["IsolationForest"]["configs"][0]["parameters"]["random_state"], 42)
        self.assertIn("unscaled", profiles["IsolationForest"]["preprocessing"])
        self.assertEqual([x["value"] for x in profiles["LocalOutlierFactor"]["configs"]], [10, 20, 30, 50])
        self.assertTrue(profiles["LocalOutlierFactor"]["configs"][0]["parameters"]["novelty"])
        self.assertEqual(profiles["LocalOutlierFactor"]["configs"][0]["parameters"]["contamination"], 0.02)
        self.assertIn("training rows only", profiles["LocalOutlierFactor"]["preprocessing"])
        self.assertEqual(profiles["OneClassSVM"]["configs"][0]["parameters"]["kernel"], "rbf")
        self.assertEqual(profiles["OneClassSVM"]["configs"][0]["parameters"]["gamma"], "scale")
        self.assertEqual([x["value"] for x in profiles["OneClassSVM"]["configs"]], [0.01, 0.02, 0.03, 0.05])

    def test_streamlit_workspaces_start_without_page_errors(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
        self.assertEqual([title.value for title in app.title], ["Home"])
        self.assertEqual(app.radio[0].options, ["Home", "Weather Data", "Investigate a Reading", "Model Evaluation", "Experiment Lab", "Research"])
        for workspace in ("Weather Data", "Investigate a Reading", "Experiment Lab", "Research", "Model Evaluation"):
            app.radio[0].set_value(workspace).run()
            self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
            if workspace == "Weather Data":
                self.assertGreater(len(app.get("plotly_chart")), 0)
            if workspace == "Model Evaluation":
                self.assertEqual([tab.label for tab in app.tabs], ["A. Experiments & Results", "B. How the Models Work"])
                self.assertGreater(len(app.get("plotly_chart")), 0)
                self.assertNotIn("new_predictions", app.session_state)
                for family in ("IsolationForest", "LocalOutlierFactor", "OneClassSVM"):
                    app.selectbox(key="model_profile_family").set_value(family).run()
                    self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])


if __name__ == "__main__":
    unittest.main()
