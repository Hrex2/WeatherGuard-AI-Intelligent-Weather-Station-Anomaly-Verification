import unittest
from unittest.mock import patch

from weather_research.station_identity import classify_identity, same_identifier
from weather_research.provider_availability import (
    PARAMETERS, build_retrieval_proposal, classify_meteostat_source,
    classify_provider_response, frequencies_compatible, intersect_windows,
    parameter_inventory_records, require_approval,
)
from scripts.run_phase1b_station_readiness import main as phase1b_main


class StationIdentityTests(unittest.TestCase):
    def test_duplicate_provider_identifiers(self):
        self.assertTrue(same_identifier(" 42099 ", "42099"))

    def test_same_station_alias_requires_independent_evidence(self):
        a={"coordinates":(30.0,75.0),"elevation_m":250}; b={"coordinates":(30.0,75.001),"elevation_m":251}
        self.assertEqual(classify_identity(a,b,shared_official_id=True),"POSSIBLE_ALIAS")
        self.assertEqual(classify_identity(a,b,shared_official_id=True,independent_evidence=True),"SAME_PHYSICAL_STATION_CONFIRMED")

    def test_distinct_nearby_stations(self):
        a={"coordinates":(30.0,75.0),"elevation_m":250}; b={"coordinates":(30.02,75.0),"elevation_m":251}
        self.assertEqual(classify_identity(a,b),"IDENTITY_UNRESOLVED")
        self.assertEqual(classify_identity(a,b,independent_evidence=True,history_evidence=True),"DISTINCT_STATIONS_CONFIRMED")

    def test_conflicting_coordinates_and_elevations(self):
        a={"coordinates":(30.0,75.0),"elevation_m":100}; b={"coordinates":(30.0001,75.0),"elevation_m":300}
        self.assertEqual(classify_identity(a,b),"CONFLICTING_METADATA")

    def test_relocation_requires_history_evidence(self):
        a={"coordinates":(30.0,75.0)}; b={"coordinates":(30.1,75.0)}
        self.assertEqual(classify_identity(a,b,shared_official_id=True),"IDENTITY_UNRESOLVED")
        self.assertEqual(classify_identity(a,b,shared_official_id=True,history_evidence=True),"POSSIBLE_RELOCATION")


class ProviderAvailabilityTests(unittest.TestCase):
    def test_parameter_inventory_results_are_inventory_only(self):
        records=parameter_inventory_records("x","Meteostat",{"parameters":["temperature"],"start_date":"2021-01-01","end_date":"2021-12-31"})
        self.assertEqual(len(records),len(PARAMETERS))
        self.assertEqual(records[0]["verification_status"],"INVENTORY_ONLY")
        self.assertEqual(records[1]["verification_status"],"NOT_CHECKED")

    def test_observation_source_is_not_directness_proof(self):
        self.assertEqual(classify_meteostat_source("METAR"),"OBSERVATION_SOURCE_INDICATED_NOT_INDEPENDENTLY_VERIFIED")

    def test_unknown_numeric_source(self):
        self.assertEqual(classify_meteostat_source(3),"SOURCE_UNKNOWN")

    def test_missing_source_indicator(self):
        self.assertEqual(classify_meteostat_source(None),"SOURCE_UNKNOWN")

    def test_provider_endpoint_unavailable(self):
        self.assertEqual(classify_provider_response(404),"UNAVAILABLE")

    def test_rate_limit_and_auth_errors(self):
        self.assertEqual(classify_provider_response(429),"ACCESS_RESTRICTED")
        self.assertEqual(classify_provider_response(401),"ACCESS_RESTRICTED")

    def test_timeout_does_not_imply_access_restriction(self):
        self.assertEqual(classify_provider_response(None,exception="Read timeout"),"NOT_CHECKED")

    def test_preflight_cli_has_no_bulk_download_even_with_approval_flag(self):
        with patch("sys.argv", ["run_phase1b_station_readiness.py", "--approve-raw-download"]):
            with self.assertRaises(SystemExit) as error:
                phase1b_main()
        self.assertEqual(error.exception.code, 2)

    def test_common_window_intersection(self):
        self.assertEqual(intersect_windows([("2021-01-01","2025-01-01"),("2022-01-01","2024-01-01")]),("2022-01-01","2024-01-01"))

    def test_sampling_frequency_compatibility(self):
        self.assertTrue(frequencies_compatible(["hourly","hourly"]))
        self.assertFalse(frequencies_compatible(["hourly","daily"]))

    def test_proposal_does_not_invent_size_or_counts(self):
        p=build_retrieval_proposal(stations=["VILD0"],variables=["temperature"],start_date="2021-01-01",end_date="2021-02-01",providers=["Meteostat"],frequency="hourly",availability_verified=False)
        self.assertIsNone(p["expected_record_count"])
        self.assertIsNone(p["expected_file_size"])
        self.assertFalse(p["retrieval_authorized"])

    def test_approval_gate_fails_closed(self):
        with self.assertRaises(PermissionError):
            require_approval(approved=False,stations=["x"],variables=["t"],start_date="2021-01-01",end_date="2021-02-01",providers=["p"])
        with self.assertRaises(PermissionError):
            require_approval(approved=True,stations=["x"],variables=["t"],start_date=None,end_date="2021-02-01",providers=["p"])


if __name__ == "__main__":
    unittest.main()
