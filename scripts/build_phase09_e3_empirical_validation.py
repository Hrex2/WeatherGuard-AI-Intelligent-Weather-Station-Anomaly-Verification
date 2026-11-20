"""Build Phase 09 descriptive E3 validation outputs from preserved observations."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from weather_research.e3_evidence_policy import (
    INDEPENDENT, NOT_COMPARABLE, UNKNOWN, evaluate_evidence_record,
)
from weather_research.e3_spatial import haversine_km, nearest_timestamp_pairs
from weather_research.phase09_validation import (
    compute_descriptive_metrics, select_phase03_events, summarize_tolerance_sensitivity,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase09_e3_empirical_validation"
PH04 = ROOT / "outputs" / "phase04_provenance_aware_collection"
PH05 = ROOT / "outputs" / "phase05_primary_station_verification"
PH06 = ROOT / "outputs" / "phase06_controlled_e3_validation"
PH07 = ROOT / "outputs" / "phase07_independent_evidence"
PH08 = ROOT / "outputs" / "phase08_e3_evidence_policy"
NATIVE = PH07 / "external_reference_data"
TOLERANCES_MIN = (0, 15, 30, 60)
MIN_PAIRS = 30
MIN_DATES = 10
DISTANCE_ZONES = {"A": "0-10 km", "B": "10-50 km", "C": "50-100 km",
                  "D": "100-250 km", "E": ">250 km"}

SOURCE_INPUTS = [
    "PROJECT_STATUS.md",
    "phase03_model_revalidation/candidate_observations_8of12.csv",
    "outputs/phase04_provenance_aware_collection/PHASE04_AUDIT_REPORT.md",
    "outputs/phase04_provenance_aware_collection/retrieval_manifest.json",
    "outputs/phase04_provenance_aware_collection/raw_station_data/42099_hourly_source_level.csv",
    "outputs/phase04_provenance_aware_collection/raw_station_data/42101_hourly_source_level.csv",
    "outputs/phase05_primary_station_verification/PHASE05_PRIMARY_IDENTITY_REPORT.md",
    "outputs/phase05_primary_station_verification/vild0_identity_crosswalk.csv",
    "outputs/phase05_primary_station_verification/variable_comparison_protocol.md",
    "outputs/phase06_controlled_e3_validation/PHASE06_RESEARCH_REPORT.md",
    "outputs/phase06_controlled_e3_validation/primary_retrieval_manifest.json",
    "outputs/phase06_controlled_e3_validation/raw_station_data/VILD0_hourly_source_level.csv",
    "outputs/phase07_independent_evidence/PHASE07_RESEARCH_REPORT.md",
    "outputs/phase07_independent_evidence/external_reference_manifest.json",
    "outputs/phase07_independent_evidence/candidate_event_register.csv",
    "outputs/phase07_independent_evidence/event_level_comparison.csv",
    "outputs/phase07_independent_evidence/source_lineage_register.csv",
    "outputs/phase07_independent_evidence/source_dependence_assessment.csv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INI0000VILD_2025.psv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INI0000VILD_2026.psv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INM00042101_2025.psv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INM00042101_2026.psv",
    "outputs/phase08_e3_evidence_policy/PHASE08_E3_EVIDENCE_POLICY.md",
    "outputs/phase08_e3_evidence_policy/E3_READINESS_GATES.json",
    "outputs/phase08_e3_evidence_policy/E3_POLICY_DECISION.json",
    "outputs/phase08_e3_evidence_policy/E3_VALIDATION_TEST_MATRIX.csv",
    "src/weather_research/e3_evidence_policy.py",
    "src/weather_research/e3_spatial.py",
    "src/weather_research/phase09_validation.py",
    "tests/test_e3_evidence_policy.py",
    "scripts/build_phase09_e3_empirical_validation.py",
    "tests/test_phase09_validation.py",
]

VARIABLE_FIELDS = {
    "temperature": {"vild": "temperature", "patiala": "temperature", "unit": "degC"},
    "dewpoint": {"vild": "dew_point_temperature", "patiala": "dew_point_temperature", "unit": "degC"},
    "relative_humidity": {"vild": "relative_humidity", "patiala": "relative_humidity", "unit": "%"},
    "wind_speed": {"vild": "wind_speed", "patiala": "wind_speed", "unit": "m/s"},
    "wind_direction": {"vild": "wind_direction", "patiala": "wind_direction", "unit": "degree"},
    "pressure": {"vild": "altimeter", "patiala": "sea_level_pressure", "unit": "hPa"},
    "precipitation": {"vild": "precipitation", "patiala": "precipitation", "unit": "mm"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    if not rows:
        path.write_text("status\nNO_ROWS\n", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(name: str, value: dict[str, Any]) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def read_native(station: str) -> pd.DataFrame:
    if station == "VILD":
        pattern = "GHCNh_INI0000VILD_*.psv"
        expected_id, expected_report, physical_id = "ICAO-VILD", "FM15", "GHCNh-INI0000VILD"
    else:
        pattern = "GHCNh_INM00042101_*.psv"
        expected_id, expected_report, physical_id = "WMO-42101", "FM12", "GHCNh-INM00042101"
    files = sorted(NATIVE.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no preserved NOAA station-year data for {station}")
    frame = pd.concat([pd.read_csv(file, sep="|", low_memory=False) for file in files], ignore_index=True)
    frame = frame.copy()  # Compact the wide NOAA frame before adding analysis columns.
    frame["time"] = pd.to_datetime(frame["DATE"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["time"]).sort_values("time", kind="stable")
    if frame.time.duplicated().any():
        raise ValueError(f"duplicate timestamps in NOAA station-year source for {station}")
    frame["_expected_source_id"] = expected_id
    frame["_expected_report_type"] = expected_report
    frame["_physical_site_id"] = physical_id
    return frame.reset_index(drop=True)


def get_variable_frame(frame: pd.DataFrame, variable: str, station: str) -> pd.DataFrame:
    field = VARIABLE_FIELDS[variable]["vild" if station == "VILD" else "patiala"]
    required_suffixes = ("Quality_Code", "Measurement_Code", "Report_Type", "Source_Code", "Source_Station_ID")
    cols = ["time", "_expected_source_id", "_expected_report_type", "_physical_site_id", field]
    cols += [f"{field}_{suffix}" for suffix in required_suffixes]
    existing = [column for column in cols if column in frame.columns]
    result = frame[existing].copy()
    result["value"] = pd.to_numeric(result[field], errors="coerce")
    result["qc_code"] = result.get(f"{field}_Quality_Code")
    result["measurement_code"] = result.get(f"{field}_Measurement_Code")
    result["report_type"] = result.get(f"{field}_Report_Type")
    result["source_code"] = result.get(f"{field}_Source_Code")
    result["source_station_id"] = result.get(f"{field}_Source_Station_ID")
    report_mask = result.report_type.astype(str).eq(result._expected_report_type)
    source_mask = result.source_station_id.astype(str).eq(result._expected_source_id)
    result["metadata_identity_valid"] = report_mask & source_mask
    return result.sort_values("time", kind="stable").reset_index(drop=True)


def qc_status(code: Any) -> str:
    if pd.isna(code) or str(code).strip() == "":
        return "NOT_REPORTED"
    value = str(code).strip()
    try:
        number = float(value)
        if number.is_integer():
            value = str(int(number))
    except (TypeError, ValueError):
        pass
    return {"1": "GOOD", "2": "SUSPECT", "3": "ERRONEOUS",
            "4": "CALCULATED", "5": "REMOVED"}.get(value, f"FLAG_{value}")


def report_key(row: pd.Series) -> str:
    """Construct a stable source-row key; this is not a provider-issued report ID."""
    return f"{row.get('source_station_id')}|{pd.Timestamp(row.time).tz_convert('UTC').isoformat()}|{row.get('report_type')}"


def policy_record(primary: pd.Series, reference: pd.Series, *, variable: str,
                  distance_km: float, tolerance_minutes: int,
                  primary_value: Any, reference_value: Any,
                  primary_unit: str, reference_unit: str) -> dict[str, Any]:
    return {
        "source_id": "NOAA_GHCNH_NATIVE_REPORT_PAIR",
        "station_id": str(reference.source_station_id),
        "primary_station_id": str(primary.source_station_id),
        "primary_physical_site_id": str(primary["_physical_site_id"]),
        "physical_site_id": str(reference["_physical_site_id"]),
        "primary_report_id": report_key(primary), "original_report_id": report_key(reference),
        "primary_report_system": str(primary.report_type), "report_system": str(reference.report_type),
        "lineage_classification": INDEPENDENT,
        "station_identity_verified": True, "primary_station_identity_verified": True,
        "physical_sites_distinct_verified": True, "report_systems_distinct_verified": True,
        "coordinates_verified": True, "distance_km": distance_km,
        "variable": variable, "primary_value": primary_value, "primary_unit": primary_unit,
        "reference_value": reference_value, "reference_unit": reference_unit,
        "candidate_timestamp": primary.time, "reference_timestamp": reference.time,
        "qc_status": qc_status(primary.qc_code) if qc_status(primary.qc_code) == qc_status(reference.qc_code)
                     else ("GOOD" if qc_status(primary.qc_code) == "GOOD" and qc_status(reference.qc_code) == "GOOD"
                           else f"PAIR_QC:{qc_status(primary.qc_code)}|{qc_status(reference.qc_code)}"),
        "is_imputed": (str(primary.get("measurement_code")) == "E"
                        or str(reference.get("measurement_code")) == "E"),
        "tolerance_minutes": tolerance_minutes,
    }


def main() -> None:
    if OUT.exists() and any((OUT / name).exists() for name in (
        "PHASE09_EMPIRICAL_VALIDATION_REPORT.md", "PHASE09_DATASET_REGISTER.csv",
        "PHASE09_EVENT_REGISTER.csv", "PHASE09_ELIGIBILITY_AUDIT.csv",
        "PHASE09_VARIABLE_COMPARISONS.csv", "PHASE09_EVENT_EVIDENCE_RESULTS.csv",
        "PHASE09_SENSITIVITY_ANALYSIS.csv", "PHASE09_EXCLUSION_REGISTER.csv",
        "PHASE09_VALIDATION_DECISION.json", "PHASE09_REPRODUCIBILITY_MANIFEST.json")):
        raise FileExistsError(f"Refusing to overwrite Phase 09 outputs: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)

    candidates_path = ROOT / "phase03_model_revalidation" / "candidate_observations_8of12.csv"
    candidates = pd.read_csv(candidates_path)
    selected = select_phase03_events(candidates)
    prior_event_register = pd.read_csv(PH07 / "candidate_event_register.csv")
    prior_signature = set(zip(prior_event_register.event_type,
                              pd.to_datetime(prior_event_register.candidate_timestamp_utc, utc=True).astype(str)))
    new_signature = set(zip(selected.event_type, selected.candidate_timestamp_utc.astype(str)))
    if prior_signature != new_signature:
        raise AssertionError("Phase 09 deterministic event selection differs from preserved Phase 07 event register")

    vild = read_native("VILD")
    patiala = read_native("42101")
    vild_lat, vild_lon = 30.8547, 75.9526
    patiala_lat, patiala_lon = 30.3333333, 76.4666667
    distance = haversine_km(vild_lat, vild_lon, patiala_lat, patiala_lon)
    zone = "C"  # provisional A–E bands from Phase 06/08; station-reference points only

    source_lineage = pd.read_csv(PH07 / "source_lineage_register.csv")
    phase04_manifest = json.loads((PH04 / "retrieval_manifest.json").read_text(encoding="utf-8"))
    phase06_manifest = json.loads((PH06 / "primary_retrieval_manifest.json").read_text(encoding="utf-8"))
    phase07_manifest = json.loads((PH07 / "external_reference_manifest.json").read_text(encoding="utf-8"))
    dataset_register = [
        {"dataset_id":"PHASE03_VILD0_CANDIDATES","station_id":"VILD0 (historical candidate series)","station_identity":"ICAO VILD crosswalk at station-record level only","reporting_system":"Not retained per candidate row","original_provider":"Meteostat 1.7.6 historical notebook retrieval","retrieval_timestamp":"Not present in candidate CSV","period":"2025-03-28 through 2026-03-09 candidate table","rows":len(candidates),"variables":"temp,dwpt,rhum,prcp,wspd,pres and derived temporal signals","units":"mixed fields; historical conventions","qc_status":"Not retained per row","coordinates":"Station reference only; exact sensor location unknown","lineage_classification":"UNKNOWN_LINEAGE","hash":sha256(candidates_path),"limitation":"Archived retrieval default model=True, flags=False; candidate values are not verified direct observations or ground truth."},
        {"dataset_id":"VILD0_METEOSTAT_PHASE06","station_id":"VILD0 / ICAO VILD","station_identity":"Verified at airport-station record level; sensor location unknown","reporting_system":"Meteostat source IDs metar and ghcnh","original_provider":"Meteostat 2.2.3 returned hourly source-level rows","retrieval_timestamp":phase06_manifest.get("retrieved_at_utc"),"period":f"{phase06_manifest.get('requested_start_utc')} to {phase06_manifest.get('requested_end_utc_inclusive')}","rows":1390,"variables":"temp,dwpt,rhum,prcp,wdir,wspd,pres","units":"Meteostat conventions; wind km/h in prior app outputs","qc_status":"Provider QC not retained","coordinates":"30.8547,75.9526 station-record reference","lineage_classification":"POSSIBLY_SHARED_EVIDENCE","hash":sha256(PH06 / "raw_station_data" / "VILD0_hourly_source_level.csv"),"limitation":"Model/fill/clean disabled, but package export is not original provider payload and row-to-original-report IDs are absent."},
        {"dataset_id":"WMO_42099_METEOSTAT_ISDLITE","station_id":"WMO 42099 / Ludhiana","station_identity":"Station record verified; no authoritative link to VILD0","reporting_system":"ISD-Lite","original_provider":"Meteostat 2.2.3 returned source-level rows","retrieval_timestamp":phase04_manifest.get("retrieved_at_utc"),"period":"2025-03-28 to 2025-08-24","rows":567,"variables":"temp,rhum,wspd,pres; no valid dwpt/prcp","units":"Meteostat conventions","qc_status":"Original complex QC not retained in ISD-Lite export","coordinates":"30.866667,75.933333 station record; ~2.27 km from VILD0 reference","lineage_classification":"UNKNOWN_LINEAGE","hash":sha256(PH04 / "raw_station_data" / "42099_hourly_source_level.csv"),"limitation":"Excluded from independent evidence; close record coordinates do not prove separate sensor/site."},
        {"dataset_id":"WMO_42101_METEOSTAT_ISDLITE","station_id":"WMO 42101 / Patiala","station_identity":"Verified WMO station record; sensor metadata incomplete","reporting_system":"ISD-Lite","original_provider":"Meteostat 2.2.3 returned source-level rows","retrieval_timestamp":phase04_manifest.get("retrieved_at_utc"),"period":"2025-03-28 to 2025-08-24","rows":1187,"variables":"temp,rhum,wspd,pres; no valid dwpt/prcp","units":"Meteostat conventions","qc_status":"Original complex QC not retained in ISD-Lite export","coordinates":"30.3333333,76.4666667 station record; ~76.04 km from VILD0 reference","lineage_classification":"POSSIBLY_SHARED_EVIDENCE","hash":sha256(PH04 / "raw_station_data" / "42101_hourly_source_level.csv"),"limitation":"Strong same-station fingerprint with NOAA GHCNh; excluded from independent votes."},
        {"dataset_id":"WMO_42101_METEOSTAT_GHCNH","station_id":"WMO 42101 / Patiala","station_identity":"Same WMO station record as native GHCNh","reporting_system":"GHCNh provider output","original_provider":"Meteostat 2.2.3 re-exposed NOAA GHCNh observations","retrieval_timestamp":phase04_manifest.get("retrieved_at_utc"),"period":"2026-01-01 to 2026-03-09","rows":532,"variables":"temp,rhum,wspd,pres","units":"Meteostat conventions","qc_status":"Provider row flags incomplete","coordinates":"Patiala station record","lineage_classification":"DERIVED_SAME_OBSERVATION","hash":sha256(PH04 / "raw_station_data" / "42101_hourly_source_level.csv"),"limitation":"Value fingerprints identify a mirror/repackaging of the NOAA GHCNh product; the saved file also contains 1,187 ISD-Lite rows."},
        {"dataset_id":"VILD0_NOAA_GHCNH_NATIVE","station_id":"INI0000VILD / ICAO-VILD","station_identity":"Official NOAA station record matches VILD0 airport station record; sensor location unknown","reporting_system":"FM15 METAR per variable","original_provider":"NOAA NCEI GHCNh v1.1.0 harmonized native station-year PSV; REM may retain report text","retrieval_timestamp":phase07_manifest.get("retrieved_at_utc"),"period":f"{vild.time.min().isoformat()} to {vild.time.max().isoformat()}","rows":len(vild),"variables":"temperature,dewpoint,relative humidity,wind,altimeter; no VILD precipitation values","units":"degC,%,m/s,degree,hPa","qc_status":"Per-element QC/source/report/measurement fields retained","coordinates":"30.8547,75.9526; elevation 254.2m; station record, not sensor","lineage_classification":"INDEPENDENT_REPORT_EVIDENCE relative to WMO-42101 FM12 at report-system level only","hash":"MULTIYEAR_FILES_HASHED_SEPARATELY_IN_MANIFEST","limitation":"Harmonized product; instrument/operator/calibration independence unverified; RH derived when measurement code D."},
        {"dataset_id":"WMO_42101_NOAA_GHCNH_NATIVE","station_id":"INM00042101 / WMO-42101","station_identity":"Official NOAA station record for Patiala; exact instrument details unknown","reporting_system":"FM12 SYNOP per variable","original_provider":"NOAA NCEI GHCNh v1.1.0 harmonized native station-year PSV","retrieval_timestamp":phase07_manifest.get("retrieved_at_utc"),"period":f"{patiala.time.min().isoformat()} to {patiala.time.max().isoformat()}","rows":len(patiala),"variables":"temperature,dewpoint,relative humidity,wind,sea-level pressure; precipitation at multi-hour intervals only","units":"degC,%,m/s,degree,hPa","qc_status":"Per-element QC/source/report/measurement fields retained","coordinates":"30.3333333,76.4666667; elevation 251m; station record","lineage_classification":"INDEPENDENT_REPORT_EVIDENCE relative to VILD FM15 at report-system level only","hash":"MULTIYEAR_FILES_HASHED_SEPARATELY_IN_MANIFEST","limitation":"Separate report record, not proof of independent organization/instruments; RH derived when measurement code D."},
        {"dataset_id":"IMD_ORIGINAL_ARCHIVE","station_id":"Ludhiana/Patiala exact requested sites","station_identity":"Not obtained","reporting_system":"Not established","original_provider":"IMD possible original station archive","retrieval_timestamp":"NOT_OBTAINED","period":"Not confirmed","rows":0,"variables":"Potentially temp,RH,wind,pressure,rain; no file received","units":"Unknown","qc_status":"Unknown","coordinates":"Not verified for sensor","lineage_classification":"UNKNOWN_LINEAGE","hash":"NOT_APPLICABLE","limitation":"Formal archive inquiry required; no observations downloaded."},
        {"dataset_id":"AWC_ARCHIVE","station_id":"VILD airport METAR feed","station_identity":"Airport station-level mapping exists; separate old archive not obtained","reporting_system":"FM15 METAR","original_provider":"AWC/NCEI source report archive; not separately accessed","retrieval_timestamp":"NOT_OBTAINED","period":"Candidate dates outside recent AWC API window","rows":0,"variables":"METAR variables if acquired","units":"METAR conventions","qc_status":"No separate archive payload","coordinates":"Airport report site","lineage_classification":"POSSIBLY_SHARED_EVIDENCE with VILD GHCNh/Meteostat METAR","hash":"NOT_APPLICABLE","limitation":"Native GHCNh VILD REM is present but not a separate sensor/source."},
        {"dataset_id":"ERA5_CONTEXT","station_id":"Grid cell near Ludhiana","station_identity":"Grid cell, not station","reporting_system":"Reanalysis/data assimilation","original_provider":"Copernicus C3S","retrieval_timestamp":"NOT_DOWNLOADED","period":"Not retrieved","rows":0,"variables":"Potential context","units":"Not applicable","qc_status":"Not a station QC system","coordinates":"Grid cell; exact requested point not extracted","lineage_classification":"CONTEXT_ONLY","hash":"NOT_APPLICABLE","limitation":"Not downloaded; assimilation context cannot count as independent station observation."},
    ]

    eligibility_audit: list[dict[str, Any]] = []
    variable_summary: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    native_pair_stats: dict[tuple[str, int], dict[str, Any]] = {}
    metric_valid_pairs: dict[tuple[str, int], list[dict[str, Any]]] = {}
    exclusions: list[dict[str, Any]] = []

    for variable in ("temperature", "dewpoint", "relative_humidity", "wind_speed", "wind_direction"):
        primary = get_variable_frame(vild, variable, "VILD")
        reference = get_variable_frame(patiala, variable, "42101")
        primary_missing = int(primary.value.isna().sum())
        reference_missing = int(reference.value.isna().sum())
        if variable == "wind_direction":
            primary_sentinel = int(primary.value.eq(999).sum())
            reference_sentinel = int(reference.value.eq(999).sum())
            primary.loc[primary.value.eq(999), "value"] = np.nan
            reference.loc[reference.value.eq(999), "value"] = np.nan
            if primary_sentinel or reference_sentinel:
                exclusions.append({"record_scope":"native_pairwise_source_rows","source_pair":"VILD_FM15_vs_42101_FM12","variable":variable,"reason":"UNDEFINED_DIRECTION_SENTINEL_999_EXCLUDED","primary_rows":primary_sentinel,"reference_rows":reference_sentinel,"impact":"Not paired or used in direction metrics; raw sentinel retained in source file."})

        p_values = pd.Series(primary.value.to_numpy(), index=pd.DatetimeIndex(primary.time))
        r_values = pd.Series(reference.value.to_numpy(), index=pd.DatetimeIndex(reference.time))
        for tolerance in TOLERANCES_MIN:
            pairs = nearest_timestamp_pairs(p_values, r_values, tolerance)
            matched = pairs[pairs.neighbor_time.notna()].copy()
            descriptive_pairs: list[dict[str, Any]] = []
            qc_excluded = derived_excluded = metadata_excluded = 0
            for pair in matched.itertuples(index=False):
                p_row = primary.loc[primary.time.eq(pair.primary_time)].iloc[0]
                r_row = reference.loc[reference.time.eq(pair.neighbor_time)].iloc[0]
                record = policy_record(p_row, r_row, variable=variable, distance_km=distance,
                                       tolerance_minutes=tolerance, primary_value=pair.primary_value,
                                       reference_value=pair.neighbor_value,
                                       primary_unit=VARIABLE_FIELDS[variable]["unit"],
                                       reference_unit=VARIABLE_FIELDS[variable]["unit"])
                # The policy receives no invented agreement tolerance: this is a
                # descriptive pairing, so it must not emit support/conflict.
                phase08 = evaluate_evidence_record(record, tolerances={}, tolerance_minutes=tolerance)
                p_qc, r_qc = qc_status(p_row.qc_code), qc_status(r_row.qc_code)
                p_measure, r_measure = str(p_row.measurement_code), str(r_row.measurement_code)
                metadata_ok = bool(p_row.metadata_identity_valid and r_row.metadata_identity_valid)
                is_derived = (variable == "relative_humidity" and (p_measure == "D" or r_measure == "D"))
                is_estimated = p_measure == "E" or r_measure == "E"
                qc_ok = p_qc == "GOOD" and r_qc == "GOOD"
                element_ok = variable != "pressure"
                descriptive_ok = metadata_ok and qc_ok and not is_derived and not is_estimated and element_ok
                if not qc_ok:
                    qc_excluded += 1
                if is_derived or is_estimated:
                    derived_excluded += 1
                if not metadata_ok or not element_ok:
                    metadata_excluded += 1
                disposition = ("DESCRIPTIVE_PAIR_VALID_NO_EVENT_THRESHOLD" if descriptive_ok else
                               "NOT_COMPARABLE_DERIVED_OR_ESTIMATED_VARIABLE" if (is_derived or is_estimated) else
                               "NOT_COMPARABLE_PRESSURE_ELEMENT_SEMANTICS" if not element_ok else
                               "NOT_COMPARABLE_QC_NOT_GOOD" if not qc_ok else
                               "UNAVAILABLE_SOURCE_ROW_IDENTITY_NOT_VERIFIED")
                audit = {
                    "record_scope":"native_report_pairwise_descriptive","source_pair":"VILD_FM15_vs_42101_FM12",
                    "variable":variable,"tolerance_minutes":tolerance,
                    "primary_station_id":p_row.source_station_id,"reference_station_id":r_row.source_station_id,
                    "primary_report_system":p_row.report_type,"reference_report_system":r_row.report_type,
                    "primary_source_report_key":report_key(p_row),"reference_source_report_key":report_key(r_row),
                    "report_key_kind":"CONSTRUCTED station ID + UTC timestamp + report type; not provider-issued report identifier",
                    "lineage_classification":phase08["lineage_classification"],
                    "phase08_comparison_eligibility":phase08["comparison_eligibility"],
                    "phase08_outcome":phase08["outcome"],"phase08_reason":phase08["comparison_reason"],
                    "phase09_descriptive_pair_disposition":disposition,
                    "phase09_descriptive_pair_reason":("Variable measurements are comparable for description, but no event agreement threshold is preregistered." if descriptive_ok else disposition),
                    "primary_timestamp_utc":pd.Timestamp(pair.primary_time).isoformat(),
                    "reference_timestamp_utc":pd.Timestamp(pair.neighbor_time).isoformat(),
                    "offset_minutes_reference_minus_primary":float(pair.offset_minutes),
                    "distance_km_station_record_points":distance,"provisional_zone":zone,
                    "primary_value":float(pair.primary_value),"reference_value":float(pair.neighbor_value),
                    "primary_unit":VARIABLE_FIELDS[variable]["unit"],"reference_unit":VARIABLE_FIELDS[variable]["unit"],
                    "primary_qc_code":p_row.qc_code,"primary_qc_status":p_qc,
                    "reference_qc_code":r_row.qc_code,"reference_qc_status":r_qc,
                    "primary_measurement_code":p_row.measurement_code,"reference_measurement_code":r_row.measurement_code,
                    "measurement_basis":"DERIVED_FROM_TEMPERATURE_AND_DEWPOINT" if is_derived else "SOURCE_NATIVE_OR_BASIS_UNRESOLVED",
                    "is_imputed":False,"policy_tolerance_supplied":False,
                    "independence_scope":"DISTINCT REPORT SYSTEMS ONLY; sensor/operator independence not established",
                }
                eligibility_audit.append(audit)
                if descriptive_ok:
                    descriptive_pairs.append({"primary_time":pair.primary_time,
                                              "primary_value":float(pair.primary_value),
                                              "reference_value":float(pair.neighbor_value)})

            pair_frame = pd.DataFrame(descriptive_pairs, columns=["primary_time", "primary_value", "reference_value"])
            metric = compute_descriptive_metrics(variable, pair_frame,
                                                 minimum_pairs=MIN_PAIRS,
                                                 minimum_distinct_dates=MIN_DATES)
            summary = {
                "source_pair":"VILD_FM15_vs_42101_FM12", "lineage":"INDEPENDENT_REPORT_EVIDENCE_ONLY",
                "variable":variable,"primary_field":VARIABLE_FIELDS[variable]["vild"],
                "reference_field":VARIABLE_FIELDS[variable]["patiala"],
                "primary_source_rows":len(primary),"reference_source_rows":len(reference),
                "primary_valid_values":int(primary.value.notna().sum()),
                "reference_valid_values":int(reference.value.notna().sum()),
                "primary_missing_values":primary_missing,"reference_missing_values":reference_missing,
                "tolerance_minutes":tolerance,"time_match_method":"deterministic one-to-one max-cardinality; exact and tolerance windows separate",
                "n_value_pairs":len(matched),"n_descriptive_qc_and_basis_valid_pairs":len(descriptive_pairs),
                "n_qc_excluded_pairs":qc_excluded,"n_derived_or_estimated_excluded_pairs":derived_excluded,
                "n_semantics_or_identity_excluded_pairs":metadata_excluded,
                "n_distinct_dates":metric["n_distinct_dates"],"metrics_status":metric["metrics_status"],
                "bias_reference_minus_primary":metric["bias_reference_minus_primary"],
                "mae":metric["mae"],"rmse":metric["rmse"],
                "median_absolute_error":metric["median_absolute_error"],
                "correlation":metric["correlation"],"correlation_method":metric["correlation_method"],
                "agreement_count":None,"disagreement_count":None,
                "agreement_threshold":"NOT_PREREGISTERED; no binary agreement decision",
                "statistical_scope":"Descriptive report-level pair metrics only; not event truth, fault diagnosis, or evidence weights.",
            }
            variable_summary.append(summary)
            native_pair_stats[(variable, tolerance)] = summary
            metric_valid_pairs[(variable, tolerance)] = descriptive_pairs
            sensitivity_rows.append({
                "sensitivity_type":"TIME_TOLERANCE", "source_pair":"VILD_FM15_vs_42101_FM12",
                "variable":variable,"tolerance_minutes":tolerance,"n_value_pairs":len(matched),
                "n_descriptive_valid_pairs":len(descriptive_pairs),"n_distinct_dates":metric["n_distinct_dates"],
                "bias_reference_minus_primary":metric["bias_reference_minus_primary"],
                "mae":metric["mae"],"rmse":metric["rmse"],
                "status":metric["metrics_status"],
                "interpretation":"Availability and descriptive-metric sensitivity only; no event outcome without preregistered thresholds."})
            sensitivity_rows.append({
                "sensitivity_type":"QC_FILTER", "source_pair":"VILD_FM15_vs_42101_FM12",
                "variable":variable,"tolerance_minutes":tolerance,"n_value_pairs":len(matched),
                "n_descriptive_valid_pairs":len(descriptive_pairs),"n_distinct_dates":metric["n_distinct_dates"],
                "bias_reference_minus_primary":None,"mae":None,"rmse":None,
                "status":"QC_FILTERED" if qc_excluded else "NO_QC_EXCLUSIONS_IN_MATCHED_ROWS",
                "interpretation":f"{qc_excluded} matched pairs excluded because both elements were not QC code 1; no failed-QC pair used in metrics."})

    # Product-lineage and data-availability sensitivity rows; no shared products are pooled.
    sensitivity_rows += [
        {"sensitivity_type":"LINEAGE_EXCLUSION","source_pair":"Phase 06 VILD METAR versus 42099 ISD-Lite","variable":"all","tolerance_minutes":None,"n_value_pairs":None,"n_descriptive_valid_pairs":0,"status":"EXCLUDED_UNKNOWN_LINEAGE","interpretation":"42099 ISD-Lite has no authoritative row lineage or VILD0 equivalence; excluded from independent evidence."},
        {"sensitivity_type":"LINEAGE_EXCLUSION","source_pair":"Phase 06 VILD METAR versus 42101 ISD-Lite","variable":"all","tolerance_minutes":None,"n_value_pairs":None,"n_descriptive_valid_pairs":0,"status":"EXCLUDED_POSSIBLY_SHARED","interpretation":"Same-station ISD-Lite/GHCNh fingerprints and ISD/GHCNh source ecosystem; not an independent vote."},
        {"sensitivity_type":"LINEAGE_EXCLUSION","source_pair":"Phase 04 Meteostat 42101 GHCNh versus NOAA native GHCNh","variable":"all","tolerance_minutes":None,"n_value_pairs":None,"n_descriptive_valid_pairs":0,"status":"EXCLUDED_DERIVED_SAME_OBSERVATION","interpretation":"Meteostat GHCNh output mirrors the NOAA GHCNh product; excluded from independent votes."},
        {"sensitivity_type":"LINEAGE_EXCLUSION","source_pair":"Phase 06 VILD METAR versus NOAA native VILD GHCNh","variable":"all","tolerance_minutes":None,"n_value_pairs":None,"n_descriptive_valid_pairs":0,"status":"EXCLUDED_POSSIBLY_SHARED","interpretation":"Strong same-station timestamp/value fingerprints; not a second independent station."},
        {"sensitivity_type":"IMPUTATION_EXCLUSION","source_pair":"Native NOAA VILD FM15 versus 42101 FM12","variable":"all","tolerance_minutes":None,"n_value_pairs":None,"n_descriptive_valid_pairs":0,"status":"NATIVE_REPORT_ROWS_ONLY","interpretation":"No model-filled rows were added; the historical Phase 03 candidate series remains possibly model-filled and is excluded from event validation."},
        {"sensitivity_type":"DISTANCE_ZONE_SENSITIVITY","source_pair":"VILD record versus 42101 record","variable":"all","tolerance_minutes":None,"n_value_pairs":None,"n_descriptive_valid_pairs":0,"status":"NOT_PERFORMED_NO_ALTERNATIVE_BANDS_PREREGISTERED","interpretation":"Observed reference-point separation is 76.04 km (provisional zone C). Alternative boundaries would be arbitrary; zones are not validated weather-event radii."},
        {"sensitivity_type":"PRECIPITATION_INTERVAL","source_pair":"VILD versus 42101","variable":"precipitation","tolerance_minutes":None,"n_value_pairs":0,"n_descriptive_valid_pairs":0,"status":"NOT_COMPARABLE","interpretation":"VILD native product has no valid precipitation values; Patiala has multi-hour accumulations without matching primary intervals."},
    ]

    # Event selection is reproduced directly from the 123-row Phase 03 source,
    # then each archived Phase 07 reference row is passed through Phase 08.
    phase07_comparisons = pd.read_csv(PH07 / "event_level_comparison.csv")
    events_out: list[dict[str, Any]] = []
    event_results: list[dict[str, Any]] = []
    for index, event in enumerate(selected.itertuples(index=False), 1):
        event_id = f"P09E{index:02d}"
        timestamp = pd.Timestamp(event.candidate_timestamp_utc)
        existing = phase07_comparisons[phase07_comparisons.event_id.eq(
            prior_event_register.loc[prior_event_register.event_type.eq(event.event_type), "event_id"].iloc[0])]
        candidate_var = event.event_variable
        report_refs = 0
        qcg_refs = 0
        match_status_counts = {"EXACT_MATCH":0,"TOLERANCE_MATCH":0,"MISSING_REFERENCE_VALUE":0,
                               "NO_MATCH_WITHIN_TOLERANCE":0}
        lineage_counts = {"INDEPENDENT_REPORT_EVIDENCE":0,"POSSIBLY_SHARED_EVIDENCE":0,
                          "DERIVED_SAME_OBSERVATION":0,"CONTEXT_ONLY":0,"UNKNOWN_LINEAGE":0,
                          "NOT_COMPARABLE":0}
        for _, comp in existing.iterrows():
            match_status = str(comp.time_match_status)
            if match_status in match_status_counts:
                match_status_counts[match_status] += 1
            product_lineage = str(comp.lineage_class_vs_primary_station)
            if product_lineage == "INDEPENDENT_OBSERVING_SYSTEM":
                product_lineage = INDEPENDENT
            elif product_lineage.startswith("POSSIBLY_SHARED"):
                product_lineage = "POSSIBLY_SHARED_EVIDENCE"
            elif product_lineage == "DERIVED_FROM_SAME_REPORT":
                product_lineage = "DERIVED_SAME_OBSERVATION"
            elif product_lineage == "NOT_COMPARABLE":
                product_lineage = NOT_COMPARABLE
            elif product_lineage not in lineage_counts:
                product_lineage = UNKNOWN
            lineage_counts[product_lineage] += 1
            if str(comp.time_match_status) in {"EXACT_MATCH", "TOLERANCE_MATCH", "MISSING_REFERENCE_VALUE"}:
                report_refs += 1
            if (comp.reference_product == "WMO_42101_NOAA_GHCNH"
                    and comp.quality_status == "GOOD"
                    and str(comp.time_match_status) in {"EXACT_MATCH", "TOLERANCE_MATCH"}
                    and not (comp.variable == "rhum" and comp.measurement_basis == "DERIVED_FROM_TEMPERATURE_AND_DEWPOINT")
                    and comp.units_comparable):
                qcg_refs += 1
            # The archived candidate row has no original report key/system and
            # the Meteostat 1.7.6 retrieval may have used model-filled values.
            record = {
                "source_id":comp.reference_source_id,"station_id":comp.original_station_id,
                "original_report_id":comp.original_station_id if pd.notna(comp.original_station_id) else None,
                "lineage_classification":UNKNOWN,"variable":{
                    "temp":"temperature","rhum":"relative_humidity","wspd":"wind_speed","pres":"pressure"
                }.get(str(comp.variable),str(comp.variable)),
                "primary_value":comp.candidate_value_common_unit,
                "primary_unit":comp.candidate_original_unit,
                "reference_value":comp.reference_value_common_unit,"reference_unit":comp.reference_units,
                "candidate_timestamp":timestamp,
                "reference_timestamp":comp.matched_timestamp_utc if pd.notna(comp.matched_timestamp_utc) else None,
                "qc_status":comp.quality_status,"is_imputed":None,
                "distance_km":distance,
            }
            evaluated = evaluate_evidence_record(record, tolerances={}, tolerance_minutes=60)
            eligibility_audit.append({
                "record_scope":"historical_candidate_event_reference","event_id":event_id,
                "source_pair":"PHASE03_HISTORICAL_CANDIDATE_vs_"+str(comp.reference_product),
                "variable":candidate_var,"tolerance_minutes":60,
                "primary_station_id":"VILD0 (station-record mapping only)",
                "reference_station_id":comp.original_station_id,
                "primary_report_system":"NOT_RETAINED", "reference_report_system":comp.report_type,
                "primary_report_key":None,"reference_report_key":"NOT_AVAILABLE_PER_PHASE07_EXPORT",
                "candidate_pair_lineage":UNKNOWN,"reference_product_lineage_vs_vild_record":product_lineage,
                "phase08_comparison_eligibility":evaluated["comparison_eligibility"],
                "phase08_outcome":evaluated["outcome"],"phase08_reason":evaluated["comparison_reason"],
                "phase09_event_eligibility":"INELIGIBLE_UNKNOWN_CANDIDATE_ROW_LINEAGE",
                "phase09_event_reason":"Historical candidate row has no provider/report identifier and may include model fills; a distinct neighbor station report cannot validate an unverified candidate row.",
                "reference_match_status":comp.time_match_status,
                "offset_minutes_reference_minus_primary":comp.offset_minutes_neighbor_minus_event,
                "primary_timestamp_utc":timestamp.isoformat(),
                "reference_timestamp_utc":comp.matched_timestamp_utc,
                "primary_value":comp.candidate_value_common_unit,
                "reference_value":comp.reference_value_common_unit,
                "primary_unit":comp.candidate_original_unit,"reference_unit":comp.reference_units,
                "reference_qc_code":comp.quality_code,"reference_qc_status":comp.quality_status,
                "reference_measurement_code":comp.measurement_code,
                "reference_measurement_basis":comp.measurement_basis,
                "is_imputed":"UNKNOWN_CANDIDATE_MAY_BE_MODEL_FILLED",
                "evidence_role":"NOT_INDEPENDENTLY_ELIGIBLE_FOR_EVENT_VALIDATION",
            })
        event_outcome = "UNAVAILABLE"  # Candidate/report lineage is unresolved for all selected events.
        events_out.append({
            "event_id":event_id,"source_event_id":prior_event_register.loc[prior_event_register.event_type.eq(event.event_type),"event_id"].iloc[0],
            "primary_station":"VILD0 / ICAO VILD station record","candidate_timestamp_local":event.candidate_timestamp_local,
            "candidate_timestamp_utc":timestamp.isoformat(),"variable":candidate_var,
            "candidate_value":getattr(event,candidate_var),"selection_metric":event.selection_metric,
            "selection_direction":event.selection_direction,"selection_method":"Mechanical extrema over all Phase 03 8-of-12 candidates; no neighbor agreement used.",
            "configuration_votes":int(event.configuration_votes),"episode_id":int(event.episode_id),
            "original_anomaly_label":"NOT_INDEPENDENTLY_ADJUDICATED; candidate/model evidence only",
            "e1_e2_e4_event_labels":"NOT_AVAILABLE_IN_CANDIDATE_ARTIFACT",
            "candidate_lineage":"UNKNOWN_LINEAGE; historical Meteostat 1.7.6 model=True default and flags=False",
            "reference_product_rows_audited":len(existing),"reference_rows_within_60m_or_missing_value":report_refs,
            "qc_good_compatible_pat901_rows_within_60m":qcg_refs,
            **{f"{k.lower()}_reference_rows":v for k,v in lineage_counts.items()},
            "eligible_independent_candidate_comparisons":0,
            "policy_outcome":event_outcome,
            "interpretation":"Reference availability is descriptive; none of the historical candidate values are independently validated.",
        })
        event_results.append({
            "event_id":event_id,"candidate_timestamp_utc":timestamp.isoformat(),"variable":candidate_var,
            "eligible_independent_references":0,"potentially_shared_references":lineage_counts["POSSIBLY_SHARED_EVIDENCE"],
            "duplicated_references":lineage_counts["DERIVED_SAME_OBSERVATION"],
            "contextual_references":lineage_counts["CONTEXT_ONLY"],"unknown_lineage_references":lineage_counts["UNKNOWN_LINEAGE"],
            "noncomparable_references":lineage_counts["NOT_COMPARABLE"],
            "eligible_comparisons":0,"excluded_comparisons":len(existing),
            "reference_availability":("MATCHED_AND_MISSING" if match_status_counts["MISSING_REFERENCE_VALUE"] and (match_status_counts["EXACT_MATCH"] + match_status_counts["TOLERANCE_MATCH"])
                                       else "MATCHED_VALUES" if (match_status_counts["EXACT_MATCH"] + match_status_counts["TOLERANCE_MATCH"])
                                       else "MISSING_VALUE_ONLY" if match_status_counts["MISSING_REFERENCE_VALUE"]
                                       else "TEMPORALLY_MISMATCHED" if match_status_counts["NO_MATCH_WITHIN_TOLERANCE"]
                                       else "UNAVAILABLE"),
            "exact_reference_matches":match_status_counts["EXACT_MATCH"],
            "tolerance_reference_matches":match_status_counts["TOLERANCE_MATCH"],
            "missing_value_reference_rows":match_status_counts["MISSING_REFERENCE_VALUE"],
            "temporally_unmatched_reference_rows":match_status_counts["NO_MATCH_WITHIN_TOLERANCE"],
            "coverage_status":"UNAVAILABLE","outcome":"UNAVAILABLE",
            "reason":"Unknown candidate lineage and no preregistered numeric tolerances; cannot classify event support/conflict.",
            "event_validation_suitable":False,
        })

    # Include the formal comparisons of pressure, precipitation, and RH even
    # though the strict variable gates produce no independent metrics.
    for variable, reason in (
        ("pressure", "Primary reports altimeter/QNH while Patiala reports sea-level pressure; pressure elements are not demonstrated equivalent."),
        ("precipitation", "No primary VILD precipitation values; Patiala values are multi-hour accumulation elements without matching primary windows."),
        ("relative_humidity", "GHCNh measurement code D derives RH from temperature/dewpoint; native RH QC is not retained as a direct independent humidity measurement."),
    ):
        v = get_variable_frame(vild, variable, "VILD")
        p = get_variable_frame(patiala, variable, "42101")
        variable_summary.extend([{
            "source_pair":"VILD_FM15_vs_42101_FM12","lineage":"INDEPENDENT_REPORT_EVIDENCE_ONLY",
            "variable":variable,"primary_field":VARIABLE_FIELDS[variable]["vild"],
            "reference_field":VARIABLE_FIELDS[variable]["patiala"],
            "primary_source_rows":len(v),"reference_source_rows":len(p),
            "primary_valid_values":int(v.value.notna().sum()),"reference_valid_values":int(p.value.notna().sum()),
            "primary_missing_values":int(v.value.isna().sum()),"reference_missing_values":int(p.value.isna().sum()),
            "tolerance_minutes":tolerance,"time_match_method":"NO BINARY EVENT COMPARISON",
            "n_value_pairs":0,"n_descriptive_qc_and_basis_valid_pairs":0,
            "n_qc_excluded_pairs":0,"n_derived_or_estimated_excluded_pairs":0,
            "n_semantics_or_identity_excluded_pairs":0,"n_distinct_dates":0,
            "metrics_status":"NOT_COMPARABLE","bias_reference_minus_primary":None,"mae":None,"rmse":None,
            "median_absolute_error":None,"correlation":None,"correlation_method":"NOT_COMPUTED",
            "agreement_count":None,"disagreement_count":None,
            "agreement_threshold":"NOT_PREREGISTERED","statistical_scope":reason,
        } for tolerance in TOLERANCES_MIN])

    # Event product categories are reported alongside a separate outcome.
    candidate_df = pd.DataFrame(events_out)
    results_df = pd.DataFrame(event_results)

    # Dataset register details for native source files and preserved lineage entries.
    for row in dataset_register:
        row["distance_zone_reference"] = zone if row["dataset_id"] == "WMO_42101_NOAA_GHCNH_NATIVE" else (
            "A (provisional station-record distance)" if row["dataset_id"] == "WMO_42099_METEOSTAT_ISDLITE" else None)
        row["elevation_m"] = 251 if row["dataset_id"] == "WMO_42101_NOAA_GHCNH_NATIVE" else (
            254.2 if row["dataset_id"] == "VILD0_NOAA_GHCNH_NATIVE" else None)

    # Event selection categories that cannot be populated are explicit rather than fabricated.
    event_categories = {name:0 for name in ("SUPPORTS_LOCAL_EVENT", "CONFLICTS_WITH_LOCAL_EVENT",
                                            "REGIONAL_SUPPORT", "WIDER_CONTEXT_SUPPORT", "MIXED_SPATIAL_EVIDENCE",
                                            "INSUFFICIENT_COVERAGE", "TEMPORALLY_MISMATCHED", "UNAVAILABLE",
                                            "NOT_COMPARABLE")}
    event_categories["UNAVAILABLE"] = len(events_out)
    exclusions += [
        {"record_scope":"event_candidate_series","source_pair":"Phase03 candidate values","variable":"all","reason":"UNKNOWN_LINEAGE_AND_POSSIBLE_MODEL_FILL","n_records":len(events_out),"effect":"All event-level support/conflict outcomes unavailable."},
        {"record_scope":"native_station_series","source_pair":"VILD_FM15_vs_42101_FM12","variable":"relative_humidity","reason":"DERIVED_RH_AND_NATIVE_RH_QC_UNAVAILABLE","n_records":int(sum(row.get("n_derived_or_estimated_excluded_pairs",0) for row in variable_summary if row.get("variable")=="relative_humidity")),"effect":"No independent humidity evidence or RH outcome count."},
        {"record_scope":"native_station_series","source_pair":"VILD_FM15_vs_42101_FM12","variable":"pressure","reason":"ALTIMETER_VERSUS_SEA_LEVEL_PRESSURE","n_records":0,"effect":"Not numerically compared despite same units."},
        {"record_scope":"native_station_series","source_pair":"VILD_FM15_vs_42101_FM12","variable":"precipitation","reason":"NO_SHARED_PRIMARY_INTERVAL_OR_VALID_PRIMARY_VALUES","n_records":0,"effect":"Not comparable; rainfall intermittency cannot be interpreted as fault."},
    ]

    # Add tolerance-count sensitivity before writing the table once.
    sensitivity_rows.extend(summarize_tolerance_sensitivity([
        {"source_pair":row["source_pair"],"variable":row["variable"],
         "tolerance_minutes":row["tolerance_minutes"],"n_value_pairs":row["n_value_pairs"]}
        for row in variable_summary if row["variable"] in VARIABLE_FIELDS and row.get("n_value_pairs") is not None
    ]))

    # Write tables before producing hashes.
    write_csv("PHASE09_DATASET_REGISTER.csv", dataset_register)
    write_csv("PHASE09_EVENT_REGISTER.csv", events_out)
    write_csv("PHASE09_ELIGIBILITY_AUDIT.csv", eligibility_audit)
    write_csv("PHASE09_VARIABLE_COMPARISONS.csv", variable_summary)
    write_csv("PHASE09_EVENT_EVIDENCE_RESULTS.csv", event_results)
    write_csv("PHASE09_SENSITIVITY_ANALYSIS.csv", sensitivity_rows)
    write_csv("PHASE09_EXCLUSION_REGISTER.csv", exclusions)

    phase_decision = {
        "phase":"09_e3_empirical_validation", "decision":"DESCRIPTIVE_ONLY",
        "phase08_readiness":"PARTIALLY_READY", "candidate_events_selected":len(events_out),
        "candidate_events_suitable_for_empirical_validation":0,
        "independent_report_pair":"VILD ICAO-VILD FM15 and WMO-42101 FM12, limited report-system distinction only",
        "eligible_event_outcomes":0,"event_outcome_counts":event_categories,
        "empirical_result_scope":"Descriptive native report-level comparisons only; no preregistered numerical tolerances, no candidate-to-original-report linkage, and no independent event truth labels.",
        "fault_inference":False,"fault_probability":None,"e3_classifier_integration":False,
        "shared_sources_excluded":["VILD Meteostat METAR versus NOAA GHCNh fingerprint pair","42101 ISD-Lite versus GHCNh product pair","Meteostat 42101 GHCNh mirror"],
        "unknown_lineage_excluded":["WMO 42099 ISD-Lite","Phase03 historical candidate values"],
        "unavailable_variables":{"relative_humidity":"derived and no direct QC","precipitation":"no primary values / incompatible accumulation windows","pressure":"altimeter versus sea-level pressure"},
        "rationale":"There are hundreds of QC-good, variable-compatible native FM15/FM12 report pairs suitable for descriptive statistics, but no numeric tolerances were preregistered and none of the selected historical anomaly rows can be linked to an original primary report. Thus no candidate event can be classified as regionally supported or station-specific suspicious.",
        "limitations":["report-level distinctness does not establish separate instruments, operators, calibration, or organizational independence","station-record coordinates are not exact sensor positions","Phase03 candidate data may contain model fills and lack row-level QC/source IDs","no independently adjudicated E1/E2/E4 event labels","no precipitation pair with compatible intervals","no agreement thresholds or fault labels"],
    }
    write_json("PHASE09_VALIDATION_DECISION.json", phase_decision)

    exact_results = {row["variable"]:row for row in variable_summary
                     if row.get("tolerance_minutes") == 0 and row.get("n_value_pairs") is not None}
    report = f"""# Phase 09 — Empirical Validation of E3 Spatial Evidence

**Decision: `DESCRIPTIVE_ONLY`**
**Selected candidate events:** {len(events_out)}
**Suitable for event-level empirical validation:** 0
**Eligible event support/conflict outcomes:** 0
**Source data downloaded in Phase 09:** none; only preserved Phase 04–08 data were analyzed.

## Research conclusion

The preserved NOAA native GHCNh station-year files permit descriptive comparisons of the VILD FM15 report stream and Patiala WMO-42101 FM12 stream. These are distinct station/report records and support a restricted report-level comparison; instrument, operator, calibration, and organization independence remain unverified. Exact UTC matches and one-to-one 15/30/60-minute matches were calculated separately, with per-element QC and measurement codes retained. The 76.04 km separation is based on station-record reference points and falls in provisional zone C; it does not imply shared local weather.

These observation-pair statistics do **not** validate any anomaly event. The eight selected Phase 03 candidate values have unresolved row-level source lineage (Meteostat 1.7.6 historical call defaults included `model=True`, and row flags were not requested). No original candidate report ID, independent event adjudication, or E1/E2/E4 event label is available. The Phase 08 evaluator was invoked on each event/reference row; candidate pairs are excluded as `UNKNOWN_LINEAGE`. No numerical agreement tolerance is preregistered, so the Phase 08 evaluator does not emit support/conflict outcomes even for otherwise sound descriptive report pairs.

## Sources and lineage

The primary empirical comparison uses native NOAA GHCNh rows for `INI0000VILD` (`ICAO-VILD`, FM15) and `INM00042101` (`WMO-42101`, FM12). A deterministic composite row key of station ID, UTC timestamp, and report type is used only for pairing/deduplication; it is **not** a provider-issued original report identifier. Provider/source fields and original report remarks are preserved in the source files. Measurements remain NOAA-harmonized source records.

VILD Meteostat METAR is treated as potentially shared with VILD GHCNh; Patiala ISD-Lite as potentially shared with native GHCNh; Meteostat Patiala GHCNh as a mirrored/derived product; and WMO 42099 ISD-Lite as unknown lineage. These products are excluded from independent votes. No IMD original archive, separate AWC historical order, or ERA5 grid was downloaded.

## Variable-specific findings

See `PHASE09_VARIABLE_COMPARISONS.csv`. At exact UTC timestamps, temperature has {exact_results['temperature']['n_value_pairs']} available value pairs ({exact_results['temperature']['n_descriptive_qc_and_basis_valid_pairs']} QC-good, metadata-valid pairs; bias {exact_results['temperature']['bias_reference_minus_primary']:.3f} °C and RMSE {exact_results['temperature']['rmse']:.3f} °C); dewpoint has {exact_results['dewpoint']['n_value_pairs']} available pairs ({exact_results['dewpoint']['n_descriptive_qc_and_basis_valid_pairs']} valid; bias {exact_results['dewpoint']['bias_reference_minus_primary']:.3f} °C, RMSE {exact_results['dewpoint']['rmse']:.3f} °C); wind speed has {exact_results['wind_speed']['n_value_pairs']} available pairs ({exact_results['wind_speed']['n_descriptive_qc_and_basis_valid_pairs']} valid; bias {exact_results['wind_speed']['bias_reference_minus_primary']:.3f} m/s, RMSE {exact_results['wind_speed']['rmse']:.3f} m/s). Wind direction has {exact_results['wind_direction']['n_value_pairs']} available and {exact_results['wind_direction']['n_descriptive_qc_and_basis_valid_pairs']} valid circular pairs; its circular metrics are tabulated separately. Each of these variables meets the Phase 05 pragmatic descriptive minimum of 30 valid pairs across 10 dates. That minimum is a reporting convention, not a scientifically validated threshold. Relative humidity is coded derived from temperature/dewpoint and its native RH QC is not retained as a direct measurement; no independent RH metrics are reported. VILD has no valid precipitation values while Patiala precipitation fields are multi-hour accumulations, so no same-interval comparison is possible. VILD altimeter/QNH and Patiala sea-level pressure are distinct elements and are not numerically compared.

No agreement threshold was invented. Bias, MAE, RMSE, median absolute error, and Pearson correlation (where appropriate) are descriptive only. `agreement_count` and `disagreement_count` remain uncomputed. Broader 60-minute matching adds temporally offset rows; it is not presumed more appropriate than exact matching.

## Candidate event selection and outcomes

The event selection is reproducibly recomputed from all 123 rows in `phase03_model_revalidation/candidate_observations_8of12.csv`: extrema for rapid temperature rise/drop, min/max temperature, min/max RH, max wind speed, and min pressure. The selected signature is checked against the preserved Phase 07 register. No neighbor agreement is used in selection.

All {len(events_out)} candidate events have `UNAVAILABLE` as an E3 event outcome because the primary candidate rows cannot be linked to independent source reports. The event comparison register separately records matched, missing-value, and temporally mismatched reference products, including three QC-good Patiala rows within 60 minutes found in Phase 07. These remain availability observations, not candidate-event validation. Agreement, disagreement, regional/context support, and mixed-event outcomes are therefore not assigned. No fault probability or fault diagnosis is produced.

## Sensitivity and policy audit

`PHASE09_SENSITIVITY_ANALYSIS.csv` reports exact/15/30/60-minute availability and descriptive metrics, QC exclusions, derived-field exclusions, and source-lineage exclusion decisions. Shared and unknown products are not pooled as independent evidence. Alternative zone boundaries are not tested because no alternate bands were preregistered; changing provisional labels would not establish atmospheric similarity. Imputed Phase 03 candidate values are excluded; native report rows were not model-filled by this analysis.

The Phase 08 policy was applied as written. Two limitations were observed and recorded rather than silently changed: it checks numeric units but not pressure-element semantics (altimeter versus sea-level pressure), and it has no measurement-basis gate for derived RH or estimated elements. Phase 09 applies explicit additional exclusions for those cases; a future Phase 08 policy revision should add typed measurement basis/element metadata and an imputation/estimated provenance status. Also, because the Phase 08 evaluator requires an experiment-supplied tolerance before comparison eligibility, it cannot express “valid descriptive pair, no event outcome”; Phase 09 keeps descriptive pair validity separate from policy event eligibility.

## Decision and next work

`DESCRIPTIVE_ONLY`: real report-level observation comparisons are possible, but the available artifacts cannot validate E3's ability to distinguish unusual regional weather from a suspicious station-specific observation. Obtain original report payloads and mappings for candidate rows, IMD archives and instrument/site histories, documented uncertainty/QC specifications, and independently adjudicated normal/anomaly events. Then preregister variable and event-window thresholds before a held-out event evaluation.

No classifier integration, model retraining, E1/E2/E4 modification, station replacement, or historical raw-file change occurred. Input/output hashes, settings, references, and software versions are recorded in `PHASE09_REPRODUCIBILITY_MANIFEST.json`.
"""
    report_path = OUT / "PHASE09_EMPIRICAL_VALIDATION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    input_files: dict[str, dict[str, Any]] = {}
    for relative in SOURCE_INPUTS:
        path = ROOT / relative
        if path.is_file():
            input_files[relative] = {"sha256":sha256(path),"bytes":path.stat().st_size}
        else:
            input_files[relative] = {"status":"NOT_PRESENT"}
    phase07_sources = {item["file"]:item.get("source_url") for item in phase07_manifest.get("station_year_files_and_station_list", [])}
    outputs = [
        "PHASE09_EMPIRICAL_VALIDATION_REPORT.md", "PHASE09_DATASET_REGISTER.csv",
        "PHASE09_EVENT_REGISTER.csv", "PHASE09_ELIGIBILITY_AUDIT.csv",
        "PHASE09_VARIABLE_COMPARISONS.csv", "PHASE09_EVENT_EVIDENCE_RESULTS.csv",
        "PHASE09_SENSITIVITY_ANALYSIS.csv", "PHASE09_EXCLUSION_REGISTER.csv",
        "PHASE09_VALIDATION_DECISION.json",
    ]
    manifest = {
        "phase":"09_e3_empirical_validation", "branch":"feature/phase09-e3-empirical-validation",
        "base_commit":"7baf75a8a9682e611fb8a4b1cd248a1a6144cc65",
        "execution_timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "software_versions":{"python":sys.version.split()[0],"platform":platform.platform(),"pandas":pd.__version__,"numpy":np.__version__,"meteostat_phase04_06":"2.2.3","NOAA_GHCNh":"v1.1.0"},
        "input_files":input_files,
        "source_references":{
            "NOAA_GHCNh_product":"https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly",
            "NOAA_GHCNh_documentation":"https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh_DOCUMENTATION.pdf",
            "NOAA_GHCNh_VILD_2025":phase07_sources.get("GHCNh_INI0000VILD_2025.psv"),
            "NOAA_GHCNh_VILD_2026":phase07_sources.get("GHCNh_INI0000VILD_2026.psv"),
            "NOAA_GHCNh_42101_2025":phase07_sources.get("GHCNh_INM00042101_2025.psv"),
            "NOAA_GHCNh_42101_2026":phase07_sources.get("GHCNh_INM00042101_2026.psv"),
            "IMD_data_supply":"https://mausam.imd.gov.in/thiruvananthapuram/Datasupply.php",
        },
        "configuration":{"pairing":"Phase 06 nearest_timestamp_pairs, deterministic one-to-one max-cardinality; windows 0/15/30/60 minutes","distance_km":distance,"distance_zone":zone,"zone_bands_km":DISTANCE_ZONES,"statistical_pragmatic_minimum":{"valid_pairs":MIN_PAIRS,"distinct_dates":MIN_DATES,"source":"Phase 05 prospective variable comparison protocol; not validated threshold"},"numeric_agreement_tolerance":"NOT_PREREGISTERED; binary support/conflict not computed","pressure":"excluded: VILD altimeter/QNH versus Patiala sea-level pressure","precipitation":"no valid primary precipitation and accumulation intervals not pairable","relative_humidity":"derived measurement code D; independent RH evidence excluded","imputation":"historical candidate series potentially model-filled; excluded from event validation; source-level native GHCNh reports analyzed"},
        "candidate_selection":{"input":"phase03_model_revalidation/candidate_observations_8of12.csv","input_rows":len(candidates),"selected_events":len(events_out),"method":"Phase 07 deterministic full-table extrema reproduced; selection independent of neighbor agreement"},
        "decision":"DESCRIPTIVE_ONLY","candidate_events_suitable_for_empirical_validation":0,
        "generated_artifacts":{str((OUT/name).relative_to(ROOT)).replace("\\", "/"):{"sha256":sha256(OUT/name),"bytes":(OUT/name).stat().st_size} for name in outputs},
        "no_raw_input_overwrite":True,"no_data_downloaded_in_phase09":True,
        "no_model_retraining":True,"no_e1_e2_e4_changes":True,"no_classifier_integration":True,
    }
    manifest_path = OUT / "PHASE09_REPRODUCIBILITY_MANIFEST.json"
    write_json(manifest_path.name, manifest)


if __name__ == "__main__":
    main()
