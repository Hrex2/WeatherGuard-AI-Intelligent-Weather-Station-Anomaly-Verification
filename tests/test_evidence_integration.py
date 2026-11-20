"""Contract, failure-isolation, and research-boundary tests for E1–E4 orchestration."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services import evidence_integration as integration


class TestEvidenceIntegration(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2025-01-01", periods=8, freq="h", tz="Asia/Kolkata")
        self.ts = self.index[-1]
        self.observations = pd.DataFrame({
            "temp": [10.0] * 7 + [30.0], "dwpt": [5.0] * 8, "rhum": [50.0] * 8,
            "prcp": [0.0] * 8, "wspd": [5.0] * 8, "pres": [1000.0] * 8,
        }, index=self.index)
        self.predictions = pd.DataFrame({
            "timestamp": [self.ts] * 12, "configuration": [f"config-{i}" for i in range(12)],
            "family": ["test"] * 12, "is_candidate": [i < 8 for i in range(12)],
            "anomaly_score": [0.1] * 12,
        })
        self.stability = pd.DataFrame({"timestamp": [self.ts], "configuration_votes": [8]})
        self.episodes = pd.DataFrame(columns=["start", "end"])
        self.spatial = {"42099": pd.DataFrame({
            "candidate_time": [self.ts], "station_time": [self.ts], "temp_difference": [0.3],
        })}
        self.sources = ["phase03_model_revalidation/spatial_comparison_42099.csv"]

    def _run(self, spatial=None):
        return integration.run_integrated_assessment(
            self.ts, "VILD0", self.observations, self.predictions, self.stability,
            self.episodes, self.spatial if spatial is None else spatial, self.sources,
        )

    @staticmethod
    def _record(component_id, status="AVAILABLE", result="NO_DETECTED_EVIDENCE", eligible=False):
        return integration.component_record(
            component_id, status, result, "test result", "test explanation",
            "2025-01-01T00:00:00+00:00", {"source": "test"}, ["test limitation"], eligible,
        )

    def test_all_four_adapters_connect_to_existing_implementations(self):
        result = self._run()
        self.assertEqual(set(result["components"]), set(integration.COMPONENT_IDS))
        self.assertEqual(result["components"]["E1"]["execution_status"], "AVAILABLE")
        self.assertEqual(result["components"]["E1"]["evidence_result"], "SUPPORTING_EVIDENCE")
        self.assertEqual(result["components"]["E2"]["execution_status"], "AVAILABLE")
        self.assertEqual(result["components"]["E3"]["execution_status"], "DESCRIPTIVE_ONLY")
        self.assertEqual(result["components"]["E4"]["execution_status"], "AVAILABLE")

    def test_e3_is_descriptive_only_and_not_decision_eligible(self):
        result = self._run()
        e3 = result["components"]["E3"]
        self.assertEqual(e3["evidence_result"], "DESCRIPTIVE_ONLY")
        self.assertFalse(e3["decision_eligible"])
        self.assertIn("E3", result["integrated_assessment"]["restricted_descriptive_evidence"])

    def test_e3_without_exact_time_rows_is_insufficient_not_normal(self):
        result = self._run(spatial={})
        self.assertEqual(result["components"]["E3"]["execution_status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["components"]["E3"]["evidence_result"], "UNAVAILABLE")
        self.assertIn("E3", result["integrated_assessment"]["unavailable_evidence"])

    def test_one_unavailable_component_is_preserved(self):
        components = {cid: self._record(cid) for cid in integration.COMPONENT_IDS}
        components["E2"] = self._record("E2", "INSUFFICIENT_DATA", "UNAVAILABLE")
        result = integration.integrate_evidence({"execution_status": "AVAILABLE", "candidate_8_of_12": False}, components, self.ts)
        self.assertEqual(result["components"]["E2"]["execution_status"], "INSUFFICIENT_DATA")
        self.assertEqual(result["integrated_assessment"]["category"], "INSUFFICIENT_EVIDENCE")

    def test_multiple_unavailable_components_are_reported(self):
        components = {cid: self._record(cid) for cid in integration.COMPONENT_IDS}
        components["E2"] = self._record("E2", "INSUFFICIENT_DATA", "UNAVAILABLE")
        components["E3"] = self._record("E3", "UNAVAILABLE", "UNAVAILABLE")
        result = integration.integrate_evidence({"execution_status": "AVAILABLE", "candidate_8_of_12": False}, components, self.ts)
        self.assertEqual(set(result["integrated_assessment"]["unavailable_evidence"]), {"E2", "E3"})

    def test_conflicting_temporal_evidence_is_separate_from_baseline(self):
        components = {cid: self._record(cid) for cid in integration.COMPONENT_IDS}
        components["E2"] = self._record("E2", result="CONFLICTING_EVIDENCE")
        result = integration.integrate_evidence({"execution_status": "AVAILABLE", "candidate_8_of_12": True}, components, self.ts)
        self.assertEqual(result["integrated_assessment"]["contradictory_evidence"], ["E2"])
        self.assertEqual(result["integrated_assessment"]["category"], "SUSPICIOUS")

    def test_invalid_component_output_becomes_visible_error(self):
        components = {cid: self._record(cid) for cid in integration.COMPONENT_IDS}
        components["E2"] = {"component_id": "E2", "execution_status": "NORMAL"}
        result = integration.integrate_evidence({"execution_status": "AVAILABLE", "candidate_8_of_12": False}, components, self.ts)
        self.assertEqual(result["components"]["E2"]["execution_status"], "ERROR")
        self.assertIn("E2", result["integrated_assessment"]["unavailable_evidence"])

    def test_adapter_execution_failure_does_not_abort_other_components(self):
        with patch.object(integration, "_e2", side_effect=RuntimeError("screen unavailable")):
            result = self._run()
        self.assertEqual(result["components"]["E2"]["execution_status"], "ERROR")
        self.assertIn("RuntimeError", result["components"]["E2"]["explanation"])
        self.assertEqual(result["components"]["E1"]["execution_status"], "AVAILABLE")
        self.assertEqual(result["components"]["E3"]["execution_status"], "DESCRIPTIVE_ONLY")

    def test_non_candidate_without_validated_rule_is_insufficient_not_normal(self):
        predictions = self.predictions.copy()
        predictions["is_candidate"] = False
        result = integration.run_integrated_assessment(
            self.ts, "VILD0", self.observations, predictions, self.stability,
            self.episodes, {}, [],
        )
        self.assertEqual(result["integrated_assessment"]["category"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["integrated_assessment"]["is_validated_combined_classifier"])

    def test_original_baseline_prediction_is_preserved(self):
        result = self._run()
        baseline = result["baseline_prediction"]
        self.assertEqual(baseline["source"], "saved Phase 03 predictions; no new model fit")
        self.assertEqual(baseline["configuration_votes"], 8)
        self.assertEqual(baseline["configuration_count"], 12)
        self.assertEqual(len(baseline["model_rows"]), 12)

    def test_e3_cannot_change_final_assessment(self):
        baseline = {"execution_status": "AVAILABLE", "candidate_8_of_12": False}
        components = {cid: self._record(cid) for cid in integration.COMPONENT_IDS}
        components["E3"] = self._record("E3", "DESCRIPTIVE_ONLY", "DESCRIPTIVE_ONLY", eligible=False)
        first = integration.integrate_evidence(baseline, components, self.ts)
        components["E3"]["details"] = [{"strong_spatial_support": True}]
        second = integration.integrate_evidence(baseline, components, self.ts)
        self.assertEqual(first["integrated_assessment"]["category"], second["integrated_assessment"]["category"])
        self.assertFalse(second["components"]["E3"]["decision_eligible"])

    def test_dashboard_response_has_required_explainable_structure(self):
        result = self._run()
        self.assertTrue({"timestamp", "station_id", "baseline_prediction", "components",
                         "integrated_assessment", "research_boundary"}.issubset(result))
        for component_id in integration.COMPONENT_IDS:
            integration.validate_component_record(result["components"][component_id], component_id)
        self.assertIn(result["integrated_assessment"]["category"], integration.ASSESSMENTS)
        self.assertIn("ANOMALY ≠ FAULT", result["research_boundary"])


if __name__ == "__main__":
    unittest.main()
