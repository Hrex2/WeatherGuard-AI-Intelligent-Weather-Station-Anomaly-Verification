"""Pre-fit validation for the additional reusable synthetic fault matrix."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from scripts.run_synthetic_fault_matrix import SCENARIOS, validate_scenarios
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


if __name__ == "__main__":
    unittest.main()
