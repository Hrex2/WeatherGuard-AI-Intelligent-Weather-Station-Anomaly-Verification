"""Tests for controlled ablation masks over identical saved observation results."""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.ablation_service import (
    ABLATION_CONFIGURATIONS, ablate, assessment_change_count,
)
from services.evidence_integration import component_record, integrate_evidence


class TestAblationService(unittest.TestCase):
    def setUp(self):
        self.timestamp = "2025-05-01T12:00:00+05:30"
        outputs = {
            "E1": component_record("E1", "AVAILABLE", "SUPPORTING_EVIDENCE", "8/12",
                "Saved baseline screen", self.timestamp, {"artifact": "saved predictions"}, [], True),
            "E2": component_record("E2", "AVAILABLE", "NO_DETECTED_EVIDENCE", "No screen",
                "Temporal screen", self.timestamp, {"implementation": "temporal service"}, []),
            "E3": component_record("E3", "INSUFFICIENT_DATA", "UNAVAILABLE", "No independent data",
                "Spatial evidence missing", self.timestamp, {"source": "spatial tables"}, [], False),
            "E4": component_record("E4", "AVAILABLE", "NO_DETECTED_EVIDENCE", "No broad flag",
                "Physical screen", self.timestamp, {"implementation": "quality screen"}, []),
        }
        self.full = integrate_evidence({
            "execution_status": "AVAILABLE", "station_id": "VILD0",
            "source": "saved Phase 03 predictions", "configuration_votes": 8,
            "configuration_count": 12, "candidate_8_of_12": True,
            "model_rows": [{"configuration": "C1", "is_candidate": True}],
        }, outputs, self.timestamp)

    def test_all_requested_configurations_share_identical_observation(self):
        results = [ablate(self.full, config_id) for config_id in ABLATION_CONFIGURATIONS]
        self.assertEqual({row["timestamp"] for row in results}, {self.timestamp})
        self.assertEqual(len(results), len(ABLATION_CONFIGURATIONS))

    def test_baseline_prediction_is_preserved_in_every_configuration(self):
        for config_id in ABLATION_CONFIGURATIONS:
            self.assertEqual(ablate(self.full, config_id)["baseline_prediction"], self.full["baseline_prediction"])

    def test_disabled_components_are_not_treated_as_negative_evidence(self):
        result = ablate(self.full, "A0")
        for component in result["components"].values():
            self.assertEqual(component["execution_status"], "NOT_APPLICABLE")
            self.assertEqual(component["evidence_result"], "NOT_APPLICABLE")
            self.assertIn("not interpreted as negative", component["explanation"])

    def test_e3_contextual_ablation_does_not_change_assessment(self):
        without_e3 = ablate(self.full, "A5")
        with_e3 = ablate(self.full, "A6")
        self.assertEqual(without_e3["integrated_assessment"]["category"], with_e3["integrated_assessment"]["category"])
        self.assertEqual(with_e3["components"]["E3"]["execution_status"], "INSUFFICIENT_DATA")
        self.assertFalse(with_e3["components"]["E3"]["decision_eligible"])

    def test_missing_evidence_is_not_converted_to_normal(self):
        baseline_only = ablate(self.full, "A0")
        self.assertEqual(baseline_only["integrated_assessment"]["category"], "SUSPICIOUS")
        self.assertNotEqual(baseline_only["integrated_assessment"]["category"], "NORMAL")
        self.assertIn("ANOMALY ≠ FAULT", baseline_only["research_boundary"])

    def test_results_are_reproducible_for_same_inputs(self):
        first = [ablate(self.full, config_id) for config_id in ABLATION_CONFIGURATIONS]
        second = [ablate(self.full, config_id) for config_id in ABLATION_CONFIGURATIONS]
        self.assertEqual(first, second)

    def test_unknown_configuration_fails_explicitly(self):
        with self.assertRaisesRegex(KeyError, "unknown ablation"):
            ablate(self.full, "A99")

    def test_assessment_comparison_requires_same_timestamps(self):
        first = [ablate(self.full, "A5")]
        second = [ablate(self.full, "A6")]
        self.assertEqual(assessment_change_count(first, second), 0)
        second[0]["timestamp"] = "2025-05-02T12:00:00+05:30"
        with self.assertRaisesRegex(ValueError, "identical ordered timestamps"):
            assessment_change_count(first, second)


if __name__ == "__main__":
    unittest.main()
