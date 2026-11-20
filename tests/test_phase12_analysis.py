import unittest
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from services.phase12_analysis import binary_contingency, evidence_profile, timestamp_offset_minutes, sha256_file
from services.ablation_service import apply_component_subset, assessment_change_count
from services.evidence_integration import component_record, integrate_evidence


class Phase12AnalysisTests(unittest.TestCase):
    def test_binary_contingency_counts_and_empty_jaccard(self):
        result = binary_contingency([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual((result["both_positive"], result["left_only"], result["right_only"], result["both_negative"]), (1, 1, 1, 1))
        self.assertEqual(result["agreement_pct"], 50)
        self.assertEqual(result["jaccard_positive"], 1 / 3)
        empty = binary_contingency([0, 0], [0, 0])
        self.assertIsNone(empty["jaccard_positive"])
        self.assertIsNone(empty["phi"])

    def test_evidence_profile_does_not_turn_missing_into_negative(self):
        profile = evidence_profile(
            {"E1": "AVAILABLE", "E2": "INSUFFICIENT_DATA", "E3": "DESCRIPTIVE_ONLY", "E4": "AVAILABLE"},
            {"E1": "SUPPORTING_EVIDENCE", "E2": "UNAVAILABLE", "E3": "DESCRIPTIVE_ONLY", "E4": "NO_DETECTED_EVIDENCE"},
            ("E1", "E2", "E3", "E4"),
        )
        self.assertEqual(profile["supporting_evidence_count"], 1)
        self.assertEqual(profile["missing_evidence_count"], 1)
        self.assertEqual(profile["descriptive_only_count"], 1)
        self.assertEqual(profile["contradictory_evidence_count"], 0)
        e2_e4 = binary_contingency([True, False, True], [False, False, True])
        self.assertEqual(e2_e4["both_positive"], 1)
        self.assertEqual(e2_e4["left_only"], 1)
        self.assertEqual(e2_e4["right_only"], 0)

    def test_e3_offset_signed_and_exact(self):
        self.assertEqual(timestamp_offset_minutes("2025-01-01T00:00:00Z", "2025-01-01T00:15:00Z"), 15)
        self.assertEqual(timestamp_offset_minutes("2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z"), 0)
        self.assertIsNone(timestamp_offset_minutes(None, "2025-01-01T00:00:00Z"))

    def test_subset_preserves_baseline_and_e3_stays_decision_ineligible(self):
        ts = "2025-01-01T00:00:00+00:00"
        baseline = {"execution_status": "AVAILABLE", "station_id": "VILD0",
                    "configuration_votes": 9, "configuration_count": 12, "candidate_8_of_12": True}
        components = {
            "E1": component_record("E1", "AVAILABLE", "SUPPORTING_EVIDENCE", "8/12", "same saved votes", ts, {}, []),
            "E2": component_record("E2", "AVAILABLE", "NO_DETECTED_EVIDENCE", "clear", "temporal screen", ts, {}, []),
            "E3": component_record("E3", "DESCRIPTIVE_ONLY", "DESCRIPTIVE_ONLY", "context", "descriptive", ts, {}, [], False),
            "E4": component_record("E4", "AVAILABLE", "SUPPORTING_EVIDENCE", "flag", "broad range", ts, {}, []),
        }
        full = integrate_evidence(baseline, components, ts)
        masked = apply_component_subset(full, ("E2", "E4"), "Phase 12 test")
        self.assertEqual(masked["baseline_prediction"], baseline)
        self.assertEqual(masked["integrated_assessment"]["category"], "SUSPICIOUS")
        self.assertEqual(masked["components"]["E1"]["execution_status"], "NOT_APPLICABLE")
        self.assertFalse(masked["components"]["E3"]["decision_eligible"])
        same = integrate_evidence(baseline, components, ts)
        self.assertEqual(assessment_change_count([full], [same]), 0)
        other = integrate_evidence(baseline, components, "2025-01-01T01:00:00+00:00")
        with self.assertRaises(ValueError):
            assessment_change_count([full], [other])

    def test_historical_research_input_is_not_mutated_by_analysis_helpers(self):
        source = Path(__file__).resolve().parents[1] / "verified_phase01" / "model_df.csv"
        self.assertTrue(source.is_file())
        before = sha256_file(source)
        binary_contingency([True, False], [False, True])
        evidence_profile({"E2":"AVAILABLE"},{"E2":"SUPPORTING_EVIDENCE"},("E2",))
        after = sha256_file(source)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
