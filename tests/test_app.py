"""Application data-contract and Streamlit workspace smoke tests."""
from __future__ import annotations

import sys
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from services.data_service import (load_project_data, prediction_wide,
                                  verify_phase03_integrity, write_phase03_integrity_manifest)
from services.evidence_service import observation_evidence
from services.model_metadata import build_model_education
from ui.home_dashboard import _load_station_records, _selected_station_status, _playback_seconds


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
        self.assertTrue({"observations", "train", "test"}.issubset(self.hashes))
        self.assertTrue(any(name.startswith("phase03:") for name in self.hashes))

    def test_dashboard_uses_saved_station_record_coordinates_and_cautious_marker_states(self):
        records, sources = _load_station_records(str(ROOT))
        self.assertTrue({"station_id", "latitude", "longitude"}.issubset(records.columns))
        self.assertTrue(records.latitude.between(-90, 90).all())
        self.assertTrue(records.longitude.between(-180, 180).all())
        self.assertIn("42099", sources)
        self.assertEqual(_selected_station_status("VILD0", 9, 12)[0], "E1 candidate · 9/12 (not a fault label)")
        self.assertIn("Unknown", _selected_station_status("42099", 9, 12)[0])
        from pandas import Timestamp
        self.assertEqual(_playback_seconds(Timestamp("2025-01-01"), Timestamp("2025-02-01")), 10.0)

    def test_manifest_hash_mismatch_fails_closed_with_affected_filename(self):
        with patch("services.data_service.sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "SHA-256 verification failed for model_df.csv"):
                load_project_data(ROOT)

    def test_saved_predictions_are_complete_timestamp_aligned_grid(self):
        wide = prediction_wide(self.data["predictions"])
        self.assertEqual(wide.shape, (8415, 12))
        self.assertFalse(wide.isna().any().any())

    def test_phase03_integrity_manifest_records_hashes_without_provenance_claim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            pd.DataFrame({"timestamp": ["2025-01-01", "2025-01-02"],
                          "configuration": ["A", "B"], "label": [0, 1]}).to_csv(folder / "predictions.csv", index=False)
            refs = {"observations": "a", "train": "b", "test": "c"}
            write_phase03_integrity_manifest(folder, refs, manifest_created_revision="base-commit")
            manifest = verify_phase03_integrity(folder, refs)
            self.assertEqual(manifest["audit_status"], "HASHED_INTEGRITY_ONLY_HISTORICAL_PROVENANCE_UNKNOWN")
            self.assertIsNone(manifest["artifact_generation_revision"])
            self.assertEqual(manifest["artifacts"][0]["unique_timestamp_count"], 2)
            pd.DataFrame({"timestamp": ["2025-01-01"], "configuration": ["A"], "label": [1]}).to_csv(folder / "predictions.csv", index=False)
            with self.assertRaisesRegex(ValueError, "SHA-256 verification failed"):
                verify_phase03_integrity(folder, refs)
            (folder / "predictions.csv").unlink()
            with self.assertRaisesRegex(ValueError, "missing: predictions.csv"):
                verify_phase03_integrity(folder, refs)

    def test_unavailable_spatial_inputs_keep_uncertain_outcome(self):
        ts = self.data["observations"].index[-1]
        result = observation_evidence(ts, self.data["observations"], self.data["predictions"],
                                      self.data["stability"], self.data["episodes"], {})
        self.assertEqual(result["evidence_states"]["E3"], "UNAVAILABLE")
        self.assertEqual(result["outcome"], "UNCERTAIN_INSUFFICIENT_EVIDENCE")

    def test_subthreshold_votes_are_not_conflicting_and_e2_does_not_use_consensus_episodes(self):
        ts = self.data["stability"].iloc[0].timestamp
        predictions = self.data["predictions"].loc[self.data["predictions"].timestamp.eq(ts)].copy()
        predictions["is_candidate"] = False
        predictions.loc[predictions.index[:3], "is_candidate"] = True
        result = observation_evidence(ts, self.data["observations"], predictions,
                                      self.data["stability"], self.data["episodes"], {})
        self.assertEqual(result["vote_count"], 3)
        self.assertEqual(result["evidence_states"]["E1"], "NO_DETECTED_EVIDENCE")
        self.assertEqual(result["evidence_states"]["E2"], result["temporal_result"]["status"])
        without_episodes = observation_evidence(ts, self.data["observations"], predictions,
                                               self.data["stability"], pd.DataFrame(columns=["start", "end"]), {})
        self.assertEqual(result["evidence_states"]["E2"], without_episodes["evidence_states"]["E2"])

    def test_shared_evidence_service_uses_selected_variable_and_explains_scope(self):
        ts = self.data["predictions"].timestamp.iloc[100]
        result = observation_evidence(ts, self.data["observations"], self.data["predictions"],
            self.data["stability"], self.data["episodes"], {}, primary_variable="dwpt")
        self.assertEqual(result["temporal_result"]["variable"], "dwpt")
        self.assertIn("does not identify a regional weather event", result["evidence_meanings"]["E2"])

    def test_missing_values_alone_do_not_support_sensor_fault_evidence(self):
        ts = self.data["observations"].index[0]
        observations = self.data["observations"].copy()
        observations.loc[ts, ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"]] = float("nan")
        result = observation_evidence(ts, observations, self.data["predictions"],
                                      self.data["stability"], self.data["episodes"], {})
        self.assertEqual(result["evidence_states"]["E4"], "UNAVAILABLE")
        self.assertGreater(result["missing_quality_values"], 0)
        self.assertEqual(len(result["physical_screening_violations"]), 0)

    def test_missing_selected_observation_is_unavailable_through_integrated_evidence(self):
        ts = self.data["predictions"].timestamp.iloc[100]
        observations = self.data["observations"].copy()
        observations.loc[ts, "temp"] = float("nan")
        result = observation_evidence(ts, observations, self.data["predictions"],
            self.data["stability"], self.data["episodes"], {}, primary_variable="temp")
        self.assertEqual(result["temporal_result"]["status"], "UNAVAILABLE")
        self.assertFalse(result["temporal_result"]["stuck_pattern"])
        self.assertEqual(result["evidence_states"]["E2"], "UNAVAILABLE")
        self.assertEqual(result["evidence_states"]["E3"], "UNAVAILABLE")
        self.assertEqual(result["evidence_states"]["E4"], "UNAVAILABLE")
        self.assertEqual(len(result["physical_screening_violations"]), 0)
        self.assertEqual(result["evidence_available_count"], 1)
        self.assertFalse(result["evidence_complete"])
        self.assertEqual(result["outcome"], "UNCERTAIN_INSUFFICIENT_EVIDENCE")

        no_history = observations.copy()
        position = no_history.index.get_loc(ts)
        no_history.iloc[position - 6:position, no_history.columns.get_loc("temp")] = float("nan")
        no_history.loc[ts, "temp"] = self.data["observations"].loc[ts, "temp"]
        unavailable = observation_evidence(ts, no_history, self.data["predictions"],
            self.data["stability"], self.data["episodes"], {}, primary_variable="temp")
        self.assertEqual(unavailable["temporal_result"]["status"], "UNAVAILABLE")
        self.assertFalse(unavailable["temporal_result"]["stuck_pattern"])

    def test_missing_value_inside_repeated_sequence_does_not_bridge_stuck_pattern(self):
        ts = pd.date_range("2025-01-01", periods=9, freq="h", tz="UTC")[-1]
        observations = pd.DataFrame({"temp": [10, 11, 12, 15, 15, float("nan"), 15, 15, 15]},
                                    index=pd.date_range("2025-01-01", periods=9, freq="h", tz="UTC"))
        predictions = pd.DataFrame({"timestamp": [ts], "is_candidate": [True]})
        stability = pd.DataFrame({"timestamp": [ts]})
        episodes = pd.DataFrame(columns=["start", "end"])
        result = observation_evidence(ts, observations, predictions, stability, episodes, {}, primary_variable="temp")
        self.assertEqual(result["temporal_result"]["stuck_run_length"], 3)
        self.assertFalse(result["temporal_result"]["stuck_pattern"])
        self.assertNotEqual(result["evidence_states"]["E2"], "SUPPORTING")

    def test_sampling_gap_at_selected_boundary_is_unavailable_and_not_stuck(self):
        base = pd.Timestamp("2025-01-01", tz="UTC")
        index = pd.DatetimeIndex([base, base + pd.Timedelta(hours=1),
                                  base + pd.Timedelta(hours=2), base + pd.Timedelta(hours=27)])
        ts = index[-1]
        observations = pd.DataFrame({"temp": [10, 11, 12, 12]}, index=index)
        predictions = pd.DataFrame(columns=["timestamp", "is_candidate"])
        stability = pd.DataFrame(columns=["timestamp"])
        episodes = pd.DataFrame(columns=["start", "end"])
        result = observation_evidence(ts, observations, predictions, stability, episodes, {}, primary_variable="temp")
        self.assertEqual(result["temporal_result"]["status"], "UNAVAILABLE")
        self.assertEqual(result["temporal_result"]["prior_count"], 0)
        self.assertFalse(result["temporal_result"]["stuck_pattern"])
        self.assertEqual(result["evidence_states"]["E3"], "UNAVAILABLE")
        self.assertEqual(result["outcome"], "UNCERTAIN_INSUFFICIENT_EVIDENCE")

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
        self.assertEqual(app.radio(key="primary_navigation").options, ["Home", "Model", "Research", "Experiments", "About"])
        self.assertTrue(any("Station overview" in str(x.value) for x in app.markdown))
        self.assertTrue(any("Integrated evidence" in str(x.value) for x in app.markdown))
        self.assertIsNotNone(app.slider(key="home_timeline_slider"))
        self.assertIsNotNone(app.button(key="home_play_button"))
        self.assertIsNotNone(app.button(key="home_next_button"))
        # Exercise synchronized timeline controls against saved observations.
        app.slider(key="home_timeline_slider").set_value(0).run()
        app.button(key="home_next_button").click().run()
        self.assertEqual(app.slider(key="home_timeline_slider").value, 1)
        app.button(key="home_play_button").click().run()
        self.assertTrue(app.session_state["home_playing"])
        app.button(key="home_pause_button").click().run()
        self.assertFalse(app.session_state["home_playing"])
        app.selectbox(key="home_detail_station_select").set_value("42099").run()
        self.assertEqual(app.session_state["home_station_id"], "42099")
        self.assertTrue(any("Unknown · model status unavailable" in str(x.value) for x in app.markdown))
        app.button(key="close_station_details").click().run()
        self.assertIsNotNone(app.button(key="open_station_details_hidden"))
        app.button(key="open_station_details_hidden").click().run()
        self.assertIsNotNone(app.selectbox(key="home_detail_station_select"))
        # Visit the tabbed workspace before workspaces with their own tab sets;
        # AppTest retains inactive tab elements in a single shared test object.
        for workspace in ("Weather Data", "Experiments", "Model", "Investigate a Reading", "Research", "About"):
            if workspace in ("Weather Data", "Investigate a Reading"):
                app.radio(key="primary_navigation").set_value("Home").run()
                app.radio(key="quick_workspace").set_value(workspace).run()
            else:
                app.radio(key="primary_navigation").set_value(workspace).run()
            self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
            if workspace == "Weather Data":
                self.assertGreater(len(app.get("plotly_chart")), 0)
                self.assertTrue(any("Analyze a new station CSV" in str(x.value) for x in app.get("subheader")))
            if workspace == "Investigate a Reading":
                self.assertGreaterEqual(len(app.get("plotly_chart")), 4)
                self.assertTrue(any("Find an unusual observation" in str(x.value) for x in app.get("subheader")))
                self.assertIsNotNone(app.selectbox(key="investigation_variable"))
            if workspace == "Model":
                self.assertEqual(app.radio(key="model_section_navigation").options,
                                 ["Introduction", "Data Acquisition", "Preprocessing", "Model Selection", "Model Training", "Model Evaluation", "Results", "Conclusion"])
                app.radio(key="model_section_navigation").set_value("Model Selection").run()
                self.assertIsNotNone(app.selectbox(key="model_workspace_family"))
                for family in ("IsolationForest", "LocalOutlierFactor", "OneClassSVM"):
                    app.selectbox(key="model_workspace_family").set_value(family).run()
                    self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
                for section in ("Data Acquisition", "Preprocessing", "Model Training", "Model Evaluation", "Conclusion"):
                    app.radio(key="model_section_navigation").set_value(section).run()
                    self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
                app.radio(key="model_section_navigation").set_value("Results").run()
                self.assertEqual([tab.label for tab in app.tabs], ["A. Experiments & Results", "B. How the Models Work"])
                self.assertGreater(len(app.get("plotly_chart")), 0)
                self.assertNotIn("new_predictions", app.session_state)
            if workspace == "Experiments":
                self.assertEqual(app.radio(key="experiment_section_navigation").options,
                                 ["E1 · Model Stability", "E2 · Temporal Consistency", "E3 · Spatial Evidence", "E4 · Physical Plausibility", "Phase 12 · Contribution and Ablation", "Phase 13 · Research Synthesis", "Phase 14 · IEEE Paper", "Synthetic Campaigns"])
                app.radio(key="experiment_section_navigation").set_value("E3 · Spatial Evidence").run()
                self.assertTrue(any("Decision-ineligible" in str(x.value) for x in app.get("error")))
                app.radio(key="experiment_section_navigation").set_value("Phase 12 · Contribution and Ablation").run()
                self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
                for section in ("E2 · Temporal Consistency", "E4 · Physical Plausibility", "Phase 13 · Research Synthesis", "Phase 14 · IEEE Paper"):
                    app.radio(key="experiment_section_navigation").set_value(section).run()
                    self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
                app.radio(key="experiment_section_navigation").set_value("Synthetic Campaigns").run()
                self.assertTrue(any("Saved eight-scenario fault matrix" in str(x.value) for x in app.get("subheader")))
                self.assertTrue(any("Five-context synthetic fault study" in str(x.value) for x in app.get("subheader")))
                self.assertTrue(any("Independent temporal-screen comparison" in str(x.value) for x in app.get("markdown")))
                self.assertTrue(any("Synthetic baseline response and setting sensitivity" in str(x.value) for x in app.get("markdown")))
                self.assertTrue(any("Coverage does not measure interpretive benefit" in str(x.value) for x in app.get("caption")))
            if workspace == "Research":
                self.assertEqual(app.radio(key="research_section_navigation").options[0], "Abstract")
                app.radio(key="research_section_navigation").set_value("Experimental Results").run()
                self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
                for section in app.radio(key="research_section_navigation").options:
                    app.radio(key="research_section_navigation").set_value(section).run()
                    self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])

    def test_upload_inference_and_retraining_are_separate(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        app.button(key="persistent_dataset_cta").click().run()
        mode = app.radio(key="uploaded_analysis_mode")
        self.assertEqual(mode.options, ["Existing model inference", "Retraining / refitting"])
        self.assertTrue(any("Inference is unavailable" in str(item.value) for item in app.get("warning")))
        self.assertFalse(any(button.key == "run_uploaded_analysis" for button in app.button))
        mode.set_value("Retraining / refitting").run()
        self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])


if __name__ == "__main__":
    unittest.main()
