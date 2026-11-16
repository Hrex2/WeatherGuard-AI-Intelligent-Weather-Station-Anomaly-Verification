"""Pre-fit validation for the additional reusable synthetic fault matrix."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from scripts.run_synthetic_fault_matrix import (SCENARIOS, normalize_metric_table,
                                                validate_scenarios)
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


if __name__ == "__main__":
    unittest.main()
