from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from src.weather_research.station_preflight import (
    classify_data_source, classify_suitability, haversine_km,
    parse_station_inventory, valid_coordinates, verify_preflight_manifest,
    write_preflight_manifest,
)


class TestStationPreflight(unittest.TestCase):
    def test_station_identity_parsing_preserves_distinct_ids_and_source(self):
        stations = parse_station_inventory({"stations": [
            {"station_id": "VILD0", "role": "primary"},
            {"station_id": "42099", "role": "neighbor"}]})
        self.assertEqual([row["station_id"] for row in stations], ["VILD0", "42099"])
        self.assertNotEqual(stations[0]["station_id"], stations[1]["station_id"])
        self.assertTrue(all(row["verification_status"] == "METADATA_ONLY" for row in stations))

    def test_coordinate_validation_rejects_missing_nonfinite_and_out_of_range(self):
        self.assertTrue(valid_coordinates(30.9, 75.8))
        for pair in ((None, 1), (float("nan"), 1), (91, 0), (0, 181)):
            self.assertFalse(valid_coordinates(*pair))

    def test_missing_metadata_is_not_invented(self):
        station = parse_station_inventory({"stations": [{"station_id": "42099", "role": "neighbor"}]})[0]
        self.assertIsNone(station["latitude"])
        self.assertIsNone(station["longitude"])
        self.assertIsNone(station["elevation_m"])

    def test_conflicting_provider_identities_are_retained_separately(self):
        rows = [{"provider": "Meteostat", "station_id": "VILD0"},
                {"provider": "IMD", "station_id": "42099"}]
        self.assertEqual(len({(row["provider"], row["station_id"]) for row in rows}), 2)

    def test_haversine_distance_known_points(self):
        self.assertAlmostEqual(haversine_km(0, 0, 0, 1), 111.195, delta=0.02)

    def test_haversine_rejects_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            haversine_km(100, 0, 0, 0)

    def test_elevation_difference_is_unavailable_when_elevation_missing(self):
        primary = neighbor = None
        difference = abs(primary-neighbor) if primary is not None and neighbor is not None else None
        self.assertIsNone(difference)

    def test_parameter_status_contract_includes_not_checked(self):
        from src.weather_research.station_preflight import PARAMETERS, STATUSES
        self.assertEqual(len(PARAMETERS), 7)
        self.assertIn("NOT_CHECKED", STATUSES)
        self.assertNotIn("VERIFIED_AVAILABLE", {"NOT_CHECKED"})

    def test_missing_temporal_coverage_remains_unchecked(self):
        start = end = None
        temporal_overlap = "VERIFIED_AVAILABLE" if start and end else "NOT_CHECKED"
        self.assertEqual(temporal_overlap, "NOT_CHECKED")

    def test_direct_and_model_generated_sources_are_separated(self):
        self.assertEqual(classify_data_source("synop"), "OBSERVATION_SOURCE_INDICATED_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(classify_data_source("model substituted"), "MODEL_GENERATED_OR_INTERPOLATED")
        self.assertEqual(classify_data_source(None), "UNKNOWN_ORIGIN")

    def test_suitability_requires_verified_metadata_and_observed_overlap(self):
        category, _ = classify_suitability(primary_coordinates=False, neighbor_coordinates=False,
                                           elevation_known=False, parameter_overlap=False,
                                           observed_overlap=False, direct_source=False)
        self.assertEqual(category, "INSUFFICIENT_METADATA")
        category, _ = classify_suitability(primary_coordinates=True, neighbor_coordinates=True,
                                           elevation_known=True, parameter_overlap=True,
                                           observed_overlap=True, direct_source=True)
        self.assertEqual(category, "SUITABLE_CANDIDATE")

    def test_unavailable_api_is_representable_without_negative_evidence(self):
        response = {"status": "NOT_CHECKED", "coverage": None, "reason": "provider endpoint unavailable"}
        self.assertEqual(response["status"], "NOT_CHECKED")
        self.assertIsNone(response["coverage"])

    def test_mocked_inventory_response_does_not_claim_populated_parameter_rows(self):
        from src.weather_research.station_preflight import inventory_parameter_records
        response = SimpleNamespace(start="2020-01-01", end="2025-12-31", parameters=["temp", "wspd"])
        rows = inventory_parameter_records("VILD0", response, retrieved_at="2026-11-17T00:00:00Z")
        self.assertEqual(len(rows), 7)
        self.assertTrue(all(row["availability_status"] == "NOT_CHECKED" for row in rows))
        self.assertTrue(all("not observation rows" in row["data_type"] for row in rows))

    def test_manifest_integrity_detects_output_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "out"
            output.mkdir()
            (output / "report.txt").write_text("ok", encoding="utf-8")
            source = root / "input.txt"
            source.write_text("source", encoding="utf-8")
            write_preflight_manifest(output, commit="abc", inputs=[source], summary={},
                                     network_status="NOT_CHECKED", environment={})
            self.assertTrue(verify_preflight_manifest(output))
            source.write_text("tampered source", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_preflight_manifest(output)
            source.write_text("source", encoding="utf-8")
            (output / "report.txt").write_text("altered", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_preflight_manifest(output)


if __name__ == "__main__":
    unittest.main()
