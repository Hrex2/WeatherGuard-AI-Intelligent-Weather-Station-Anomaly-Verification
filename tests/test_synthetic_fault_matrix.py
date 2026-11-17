"""Pre-fit validation for the additional reusable synthetic fault matrix."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from scripts.run_synthetic_fault_matrix import (SCENARIOS, normalize_metric_table,
                                                validate_scenarios, write_scenario_summary)
from scripts.run_multicontext_fault_matrix import select_heldout_contexts
from scripts.evaluate_e2_multicontext_faults import build_paired_e2_table, select_matched_controls
from weather_research.synthetic_campaign import load_verified_snapshots


class TestSyntheticFaultMatrix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots, _, _ = load_verified_snapshots(ROOT)

    def test_all_synthetic_scenarios_validate_before_any_model_fit(self):
        raw = self.snapshots["model_df"]
        before = raw.copy(deep=True)
        valid = validate_scenarios(self.snapshots["model_df"], self.snapshots["X_train_multi"],
                                   self.snapshots["X_test_multi"],
                                   pd.Timestamp("2025-09-02 07:30:00+05:30"))
        self.assertTrue(valid)
        self.assertEqual(len(SCENARIOS), 8)
        self.assertEqual({scenario["kind"] for scenario in SCENARIOS},
                         {"spike", "point_negative_offset", "positive_offset", "stuck", "drift", "dropout", "noise_burst"})
        self.assertTrue(raw.equals(before))

    def test_metrics_do_not_label_unmodified_observations_as_verified_negatives(self):
        source = pd.DataFrame({"tp": [2], "fp": [3], "fn": [1], "tn": [9],
            "synthetic_point_recall": [2 / 3], "clean_false_positive_rate": [0.25],
            "recall_wilson_95pct_ci": ["not used"], "false_positive_rate_wilson_95pct_ci": ["not used"]})
        result = normalize_metric_table(source)
        self.assertIn("unmodified_observation_flags", result)
        self.assertIn("unmodified_observation_flag_rate", result)
        self.assertNotIn("false_positive_rate_wilson_95pct_ci", result)
        self.assertNotIn("fp", result)

    def test_multicontext_selector_uses_preinjection_strata_and_separation(self):
        contexts = select_heldout_contexts(ROOT)
        self.assertEqual(len(contexts), 5)
        self.assertEqual(contexts.timestamp.nunique(), 5)
        ordered = pd.DatetimeIndex(contexts.timestamp.sort_values())
        self.assertTrue((ordered.to_series().diff().dropna() >= pd.Timedelta(days=14)).all())
        self.assertTrue(contexts.timestamp.isin(self.snapshots["X_test_multi"].index).all())
        self.assertTrue((contexts.selection_rule.str.contains("no detector outputs used")).all())
        self.assertTrue(contexts.attrs["selection_thresholds"]["temperature_median_24h_q25"]
                        <= contexts.attrs["selection_thresholds"]["temperature_median_24h_q75"])
        self.assertEqual(set(contexts.context_id), {"TEMP_LOW_VAR_LOW", "TEMP_LOW_VAR_HIGH",
            "TEMP_HIGH_VAR_LOW", "TEMP_HIGH_VAR_HIGH", "TEMP_MIDLEVEL_MIDVAR"})

    def test_scenario_summary_preserves_outside_propagation_metrics(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            pd.DataFrame([{"experiment_id": "TEST", "kind": "spike", "variable": "temp",
                "magnitude": 1, "duration_observations": 1, "name": "IF_0.01",
                "family": "IsolationForest", "injected_and_flagged_count": 1,
                "unmodified_observation_flags": 2, "injected_not_flagged_count": 0,
                "unmodified_observation_unflagged": 10, "changed_predictions": 3,
                "new_flags_outside_injected_labels": 1,
                "changed_config_predictions_outside_expected_feature_window": 0,
                "withdrawn_clean_flags": 2}]).to_csv(run_dir / "configuration_metrics.csv", index=False)
            summary, family = write_scenario_summary(run_dir)
            self.assertEqual(summary.iloc[0].changed_outside_expected_feature_window, 0)
            self.assertIn("changed_outside_expected_feature_window", family.columns)

    def test_e2_controls_match_quarter_time_and_do_not_overlap_fault_contexts(self):
        contexts = select_heldout_contexts(ROOT).to_dict("records")
        controls = select_matched_controls(self.snapshots["model_df"],
            self.snapshots["X_test_multi"], contexts, controls_per_context=2)
        self.assertEqual(len(controls), 10)
        for row in controls.to_dict("records"):
            timestamp = row["timestamp"]
            matched = next(context for context in contexts if context["context_id"] == row["matched_context_id"])
            target = matched["timestamp"]
            self.assertEqual(timestamp.quarter, target.quarter)
            self.assertEqual((timestamp.hour, timestamp.minute), (target.hour, target.minute))
            self.assertTrue(timestamp in self.snapshots["X_test_multi"].index)
            self.assertTrue(all(abs(timestamp - context["timestamp"]) >= pd.Timedelta(days=14)
                                for context in contexts))

    def test_e2_pair_builder_requires_one_unlabeled_clean_and_one_labeled_fault_row(self):
        common = {"pair_id": "ctx:scenario:time:temp", "context_id": "ctx",
                  "experiment_id": "scenario", "timestamp": pd.Timestamp("2025-01-01", tz="UTC"),
                  "variable": "temp", "mode": "real_time", "window_hours": 6,
                  "robust_z_threshold": 3.5}
        detail = pd.DataFrame([
            {**common, "condition": "clean_same_timestamp", "status": "NO_DETECTED_EVIDENCE", "synthetic_label": False},
            {**common, "condition": "synthetic_faulted", "status": "SUPPORTING", "synthetic_label": True},
        ])
        paired = build_paired_e2_table(detail)
        self.assertEqual(len(paired), 1)
        self.assertTrue(paired.status_changed_by_injection.iloc[0])

    def test_e2_pair_builder_rejects_duplicates_missing_sides_and_fault_labeled_clean_rows(self):
        common = {"pair_id": "ctx:scenario:time:temp", "context_id": "ctx",
                  "experiment_id": "scenario", "timestamp": pd.Timestamp("2025-01-01", tz="UTC"),
                  "variable": "temp", "mode": "real_time", "window_hours": 6,
                  "robust_z_threshold": 3.5}
        clean = {**common, "condition": "clean_same_timestamp", "status": "NO_DETECTED_EVIDENCE", "synthetic_label": False}
        faulted = {**common, "condition": "synthetic_faulted", "status": "SUPPORTING", "synthetic_label": True}
        with self.assertRaisesRegex(ValueError, "Duplicate E2 paired condition"):
            build_paired_e2_table(pd.DataFrame([clean, clean, faulted]))
        with self.assertRaisesRegex(ValueError, "incomplete clean/faulted pairs"):
            build_paired_e2_table(pd.DataFrame([clean]))
        with self.assertRaisesRegex(ValueError, "must not carry fault labels"):
            build_paired_e2_table(pd.DataFrame([{**clean, "synthetic_label": True}, faulted]))


if __name__ == "__main__":
    unittest.main()
