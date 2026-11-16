"""Application data-contract and Streamlit workspace smoke tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from services.data_service import load_project_data, prediction_wide
from services.evidence_service import observation_evidence


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

    def test_streamlit_workspaces_start_without_page_errors(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
        self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])
        self.assertEqual([title.value for title in app.title], ["Command Center"])
        for workspace in ("Research Studio", "Investigation Studio", "Experiment Lab", "Model Evaluation"):
            app.radio[0].set_value(workspace).run()
            self.assertEqual(len(app.exception), 0, [error.message for error in app.exception])


if __name__ == "__main__":
    unittest.main()
