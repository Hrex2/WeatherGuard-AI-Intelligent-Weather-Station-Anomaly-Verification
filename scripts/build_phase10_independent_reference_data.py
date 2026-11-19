"""Build Phase 10 reference data and acquisition evidence from preserved inputs."""
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
    CONTEXT, DERIVED, INDEPENDENT, NOT_COMPARABLE, SHARED, UNKNOWN,
)
from weather_research.phase10_reference import (
    apply_phase08_policy, classify_raw_value, deterministic_event_registry,
    observation_fingerprint, report_payload_fingerprint,
    validate_adjudication_register, validate_sufficiency_assessment,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase10_independent_reference_data"
PH04 = ROOT / "outputs" / "phase04_provenance_aware_collection"
PH05 = ROOT / "outputs" / "phase05_primary_station_verification"
PH06 = ROOT / "outputs" / "phase06_controlled_e3_validation"
PH07 = ROOT / "outputs" / "phase07_independent_evidence"
PH08 = ROOT / "outputs" / "phase08_e3_evidence_policy"
PH09 = ROOT / "outputs" / "phase09_e3_empirical_validation"
NATIVE = PH07 / "external_reference_data"

DATA_ELEMENTS = {
    "temperature": ("temperature", "degC", "instantaneous/dry bulb"),
    "dew_point_temperature": ("dew_point_temperature", "degC", "instantaneous"),
    "relative_humidity": ("relative_humidity", "%", "source-dependent; may be derived"),
    "wet_bulb_temperature": ("wet_bulb_temperature", "degC", "source-dependent; may be derived"),
    "station_level_pressure": ("station_level_pressure", "hPa", "station-level pressure"),
    "sea_level_pressure": ("sea_level_pressure", "hPa", "sea-level-reduced pressure"),
    "altimeter": ("altimeter", "hPa", "altimeter setting"),
    "pressure_3hr_change": ("pressure_3hr_change", "hPa", "3-hour change; tendency code retained"),
    "wind_direction": ("wind_direction", "degree", "true-north direction; zero/calm code retained"),
    "wind_speed": ("wind_speed", "m/s", "source averaging basis retained in measurement code"),
    "wind_gust": ("wind_gust", "m/s", "peak short-duration gust"),
    "precipitation": ("precipitation", "mm", "nominal hourly; interval can vary by source/report"),
    "precipitation_5_minute": ("precipitation_5_minute", "mm", "5-minute accumulation"),
    "precipitation_15_minute": ("precipitation_15_minute", "mm", "15-minute accumulation"),
    "precipitation_3_hour": ("precipitation_3_hour", "mm", "3-hour accumulation"),
    "precipitation_6_hour": ("precipitation_6_hour", "mm", "6-hour accumulation"),
    "precipitation_9_hour": ("precipitation_9_hour", "mm", "9-hour accumulation"),
    "precipitation_12_hour": ("precipitation_12_hour", "mm", "12-hour accumulation"),
    "precipitation_15_hour": ("precipitation_15_hour", "mm", "15-hour accumulation"),
    "precipitation_18_hour": ("precipitation_18_hour", "mm", "18-hour accumulation"),
    "precipitation_21_hour": ("precipitation_21_hour", "mm", "21-hour accumulation"),
    "precipitation_24_hour": ("precipitation_24_hour", "mm", "24-hour accumulation"),
    "report_payload": ("REM", "raw report text", "provider-retained encoded report payload"),
}

NATIVE_FILES = {
    "VILD": [NATIVE / "GHCNh_INI0000VILD_2025.psv", NATIVE / "GHCNh_INI0000VILD_2026.psv"],
    "42101": [NATIVE / "GHCNh_INM00042101_2025.psv", NATIVE / "GHCNh_INM00042101_2026.psv"],
}
STATION_META = {
    "VILD": {"station_id": "INI0000VILD", "source_station_id": "ICAO-VILD",
             "source_name": "LUDHIANA", "lineage": "POSSIBLY_SHARED_EVIDENCE",
             "pair_scope": "VILD FM15 report stream versus products with same VILD METAR fingerprints"},
    "42101": {"station_id": "INM00042101", "source_station_id": "WMO-42101",
              "source_name": "PATIALA", "lineage": "INDEPENDENT_REPORT_EVIDENCE",
              "pair_scope": "FM12/FM94_1 report records versus VILD report stream; report-level distinction only"},
}

INPUTS = [
    "PROJECT_STATUS.md",
    "phase03_model_revalidation/candidate_observations_8of12.csv",
    "outputs/phase04_provenance_aware_collection/PHASE04_AUDIT_REPORT.md",
    "outputs/phase04_provenance_aware_collection/retrieval_manifest.json",
    "outputs/phase04_provenance_aware_collection/raw_station_data/42099_hourly_source_level.csv",
    "outputs/phase04_provenance_aware_collection/raw_station_data/42101_hourly_source_level.csv",
    "outputs/phase05_primary_station_verification/PHASE05_PRIMARY_IDENTITY_REPORT.md",
    "outputs/phase05_primary_station_verification/vild0_identity_crosswalk.csv",
    "outputs/phase06_controlled_e3_validation/PHASE06_RESEARCH_REPORT.md",
    "outputs/phase06_controlled_e3_validation/primary_retrieval_manifest.json",
    "outputs/phase06_controlled_e3_validation/raw_station_data/VILD0_hourly_source_level.csv",
    "outputs/phase07_independent_evidence/PHASE07_RESEARCH_REPORT.md",
    "outputs/phase07_independent_evidence/external_reference_manifest.json",
    "outputs/phase07_independent_evidence/source_lineage_register.csv",
    "outputs/phase07_independent_evidence/source_dependence_assessment.csv",
    "outputs/phase07_independent_evidence/candidate_event_register.csv",
    "outputs/phase07_independent_evidence/event_level_comparison.csv",
    "outputs/phase07_independent_evidence/external_reference_data/ghcnh-station-list.csv",
    "outputs/phase07_independent_evidence/external_reference_data/ghcnh-source-list.pdf",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INI0000VILD_2025.psv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INI0000VILD_2026.psv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INM00042101_2025.psv",
    "outputs/phase07_independent_evidence/external_reference_data/GHCNh_INM00042101_2026.psv",
    "outputs/phase08_e3_evidence_policy/PHASE08_E3_EVIDENCE_POLICY.md",
    "outputs/phase08_e3_evidence_policy/E3_READINESS_GATES.json",
    "outputs/phase08_e3_evidence_policy/E3_POLICY_DECISION.json",
    "outputs/phase08_e3_evidence_policy/E3_VALIDATION_TEST_MATRIX.csv",
    "outputs/phase09_e3_empirical_validation/PHASE09_EMPIRICAL_VALIDATION_REPORT.md",
    "outputs/phase09_e3_empirical_validation/PHASE09_DATASET_REGISTER.csv",
    "outputs/phase09_e3_empirical_validation/PHASE09_EVENT_REGISTER.csv",
    "outputs/phase09_e3_empirical_validation/PHASE09_EVENT_EVIDENCE_RESULTS.csv",
    "outputs/phase09_e3_empirical_validation/PHASE09_REPRODUCIBILITY_MANIFEST.json",
    "src/weather_research/e3_evidence_policy.py",
    "src/weather_research/phase09_validation.py",
    "src/weather_research/phase10_reference.py",
    "scripts/build_phase10_independent_reference_data.py",
    "tests/test_e3_evidence_policy.py",
    "tests/test_phase09_validation.py",
    "tests/test_phase10_reference.py",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(name: str, rows: list[dict[str, Any]]) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 10 artifact: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def write_json(name: str, value: dict[str, Any]) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 10 artifact: {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
                    encoding="utf-8")


def read_native_files() -> tuple[dict[str, pd.DataFrame], dict[str, list[str]]]:
    frames: dict[str, pd.DataFrame] = {}
    raw_lines: dict[str, list[str]] = {}
    for station, files in NATIVE_FILES.items():
        parts = []
        for path in files:
            lines = path.read_bytes().decode("utf-8").splitlines()
            if not lines:
                raise ValueError(f"empty NOAA station file: {path}")
            frame = pd.read_csv(path, sep="|", dtype=str, keep_default_na=False,
                                na_filter=False, low_memory=False)
            if len(lines) - 1 != len(frame):
                raise ValueError(f"raw line count differs from parsed row count: {path}")
            source_ref = path.relative_to(ROOT).as_posix()
            frame["_source_file"] = source_ref
            frame["_source_line_number"] = range(2, len(frame) + 2)
            frame["_source_line_hash"] = [hashlib.sha256(line.encode("utf-8")).hexdigest()
                                          for line in lines[1:]]
            parts.append(frame)
            raw_lines[source_ref] = lines[1:]
        merged = pd.concat(parts, ignore_index=True).copy()
        if merged.duplicated(["STATION", "DATE"]).any():
            raise ValueError(f"duplicate station/timestamp records in {station} source files")
        frames[station] = merged
    return frames, raw_lines


def _row_report_meta(row: pd.Series) -> dict[str, Any]:
    payload = row.get("REM", "")
    report_type = row.get("REM_Report_Type", "")
    source_id = row.get("REM_Source_Station_ID", "")
    source_code = row.get("REM_Source_Code", "")
    station = str(row.get("STATION", ""))
    timestamp = str(row.get("DATE", ""))
    report_fp = report_payload_fingerprint(station, timestamp, payload)
    return {"station_id": station, "timestamp_raw": timestamp,
            "report_payload_raw": payload, "report_type": report_type,
            "source_station_id": source_id, "source_code": source_code,
            "report_payload_fingerprint": report_fp}


def build_provenance_and_dataset(frames: dict[str, pd.DataFrame]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    dataset: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    dataset_variable_counts: list[dict[str, Any]] = []
    for station_key, frame in frames.items():
        lineage = STATION_META[station_key]
        for _, row in frame.iterrows():
            values = row.to_dict()
            series = row
            meta = _row_report_meta(series)
            element_provenance: dict[str, dict[str, Any]] = {}
            for element, (field, unit, semantics) in DATA_ELEMENTS.items():
                if element == "report_payload":
                    raw = str(values.get(field, ""))
                else:
                    raw = str(values.get(field, ""))
                status, numeric = classify_raw_value(raw)
                qc = str(values.get(f"{field}_Quality_Code", ""))
                measurement = str(values.get(f"{field}_Measurement_Code", ""))
                report_type = str(values.get(f"{field}_Report_Type", ""))
                source_code = str(values.get(f"{field}_Source_Code", ""))
                source_station_id = str(values.get(f"{field}_Source_Station_ID", ""))
                item_fp = observation_fingerprint(
                    str(values.get("STATION", "")), str(values.get("DATE", "")),
                    element, raw, unit)
                observation_key = "P10O-" + hashlib.sha256(
                    f"{values.get('_source_line_hash')}|{element}".encode("utf-8")).hexdigest()[:28]
                estimate_status = "ESTIMATED_FLAG_E" if measurement.upper() == "E" else "NOT_MARKED_AS_ESTIMATED"
                basis = ("DERIVED_FROM_TEMPERATURE_AND_DEWPOINT"
                         if element == "relative_humidity" and measurement.upper() == "D" else
                         "DERIVED_FROM_TEMPERATURE_DEWPOINT_AND_PRESSURE"
                         if element == "wet_bulb_temperature" and measurement.upper() == "D" else
                         "SOURCE_BASIS_RETAINED_UNINTERPRETED")
                data_row = {
                    "observation_record_id": observation_key,
                    "shared_observation_id": meta["report_payload_fingerprint"],
                    "shared_id_kind": "SHA256 station + exact UTC timestamp + raw REM payload; derived fingerprint, not provider report ID",
                    "observation_value_fingerprint": item_fp,
                    "station_id": values.get("STATION"), "station_name": values.get("Station_name"),
                    "source_station_id": source_station_id,
                    "timestamp_original": values.get("DATE"), "timestamp_timezone": "UTC per NOAA GHCNh documentation",
                    "variable": element, "source_element_field": field,
                    "value_original": raw, "value_numeric_parsed": numeric,
                    "value_status": status, "unit_original": unit,
                    "unit_conversion_applied": "NONE; source value string retained",
                    "measurement_semantics": semantics,
                    "qc_status_raw": qc, "qc_interpretation": "NOT_NORMALIZED; code semantics vary by source/element",
                    "measurement_code_raw": measurement, "measurement_basis": basis,
                    "imputation_status": estimate_status,
                    "report_type": report_type, "source_code_raw": source_code,
                    "original_report_id": "NOT_PROVIDED_AS_A_UNIQUE_ID",
                    "provider_record_id": "NOT_PROVIDED; see source row fingerprint and REM payload fingerprint",
                    "report_payload_fingerprint": meta["report_payload_fingerprint"],
                    "source_payload_variable": "REM", "source_row_fingerprint_sha256": values.get("_source_line_hash"),
                    "source_file": values.get("_source_file"), "source_line_number": values.get("_source_line_number"),
                    "source_product": "NOAA NCEI GHCNh v1.1.0 harmonized station-year PSV",
                    "source_provider": "NOAA National Centers for Environmental Information",
                    "source_retrieval_timestamp_utc": "2026-11-18T16:05:55.587365+00:00 (Phase 07 acquisition; reused in Phase 10)",
                    "latitude_original": values.get("LATITUDE"), "longitude_original": values.get("LONGITUDE"),
                    "elevation_m_original": values.get("ELEVATION"),
                    "lineage_classification_vs_primary": lineage["lineage"],
                    "lineage_scope": lineage["pair_scope"],
                    "processing_history": "Direct field extraction from preserved PSV; no fill, QC filtering, timestamp conversion, duplicate merge, or numeric unit conversion.",
                }
                dataset.append(data_row)
                element_provenance[element] = {
                    "report_type": report_type, "source_code": source_code,
                    "source_station_id": source_station_id, "qc_code": qc,
                    "measurement_code": measurement, "value_status": status,
                    "source_element_field": field,
                }
                dataset_variable_counts.append({"station_key": station_key, "variable": element,
                                               "value_status": status, "qc_status_raw": qc,
                                               "report_type": report_type, "source_code": source_code})
            provenance.append({
                "report_payload_fingerprint": meta["report_payload_fingerprint"],
                "station_id": meta["station_id"], "station_name": values.get("Station_name"),
                "source_station_id": meta["source_station_id"],
                "timestamp_original": meta["timestamp_raw"], "timestamp_timezone": "UTC per NOAA GHCNh documentation",
                "original_report_id": "NOT_PROVIDED_AS_A_UNIQUE_ID",
                "report_payload_raw": meta["report_payload_raw"],
                "report_type_raw": meta["report_type"], "source_code_raw": meta["source_code"],
                "provider_record_id": "NOT_PROVIDED",
                "source_row_fingerprint_sha256": values.get("_source_line_hash"),
                "source_file": values.get("_source_file"), "source_line_number": values.get("_source_line_number"),
                "latitude_original": values.get("LATITUDE"), "longitude_original": values.get("LONGITUDE"),
                "elevation_m_original": values.get("ELEVATION"),
                "element_provenance_json": json.dumps(element_provenance, sort_keys=True),
                "lineage_classification_vs_primary": lineage["lineage"],
                "limitation": "REM is provider-retained encoded report text; fingerprint is locally derived and is not a provider-issued report ID.",
            })
    stats: dict[str, Any] = {}
    counts = pd.DataFrame(dataset_variable_counts)
    data = pd.DataFrame(dataset)
    for station_key, subset in data.groupby(data.station_id.map(
            lambda x: "VILD" if x == "INI0000VILD" else "42101")):
        report_rows = pd.DataFrame([r for r in provenance if r["station_id"] == STATION_META[station_key]["station_id"]])
        station_stats = {"station_key": station_key,
                         "source_report_rows": int(len(report_rows)),
                         "unique_underlying_report_fingerprints": int(report_rows.report_payload_fingerprint.nunique()),
                         "timestamp_min_original": str(report_rows.timestamp_original.min()),
                         "timestamp_max_original": str(report_rows.timestamp_original.max()),
                         "duplicate_station_timestamp_rows": int(report_rows.duplicated(["station_id", "timestamp_original"]).sum()),
                         "variables": {}}
        for variable, group in subset.groupby("variable", sort=True):
            raw_codes = counts[(counts.station_key == station_key) & (counts.variable == variable)]
            station_stats["variables"][variable] = {
                "source_records_including_missing": int(len(group)),
                "present_values": int(group.value_status.eq("PRESENT").sum()),
                "blank_missing": int(group.value_status.eq("BLANK_MISSING").sum()),
                "provider_sentinel_missing": int(group.value_status.eq("PROVIDER_MISSING_SENTINEL").sum()),
                "nonnumeric_retained": int(group.value_status.eq("NONNUMERIC_RETAINED").sum()),
                "qc_codes_raw": {str(k): int(v) for k, v in raw_codes.qc_status_raw.value_counts(dropna=False).items()},
                "report_types_raw": {str(k): int(v) for k, v in raw_codes.report_type.value_counts(dropna=False).items()},
                "source_codes_raw": {str(k): int(v) for k, v in raw_codes.source_code.value_counts(dropna=False).items()},
            }
        stats[station_key] = station_stats
    stats["overall"] = {
        "station_timestamp_rows": int(len(provenance)),
        "long_element_records_including_missing": int(len(dataset)),
        "unique_underlying_report_fingerprints": int(pd.DataFrame(provenance).report_payload_fingerprint.nunique()),
        "provider_report_ids_present": 0,
    }
    return dataset, provenance, stats


def _native_lookup(frames: dict[str, pd.DataFrame], station_key: str) -> dict[pd.Timestamp, dict[str, Any]]:
    frame = frames[station_key]
    output: dict[pd.Timestamp, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        timestamp = pd.to_datetime(row["DATE"], utc=True)
        meta = _row_report_meta(row)
        output[timestamp] = {"row": row, "meta": meta}
    return output


def build_shared_observation_register(frames: dict[str, pd.DataFrame]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dependencies = pd.read_csv(PH07 / "source_dependence_assessment.csv", dtype=str).fillna("")
    native_lookup = {key: _native_lookup(frames, key) for key in frames}
    product_specs = [
        {"name": "VILD0_METEOSTAT_METAR_vs_NOAA_GHCNH", "station": "VILD",
         "path": PH06 / "raw_station_data" / "VILD0_hourly_source_level.csv", "source_filter": "metar",
         "lineage": SHARED, "mapping": {"temp": ("temperature", "degC"), "rhum": ("relative_humidity", "%"),
                                      "pres": ("altimeter", "hPa"), "wdir": ("wind_direction", "degree")}},
        {"name": "WMO42101_METEOSTAT_GHCNH_vs_NOAA_GHCNH", "station": "42101",
         "path": PH04 / "raw_station_data" / "42101_hourly_source_level.csv", "source_filter": "ghcnh",
         "lineage": DERIVED, "mapping": {"temp": ("temperature", "degC"), "rhum": ("relative_humidity", "%"),
                                          "pres": ("sea_level_pressure", "hPa")}},
        {"name": "WMO42101_METEOSTAT_ISDLITE_vs_NOAA_GHCNH", "station": "42101",
         "path": PH04 / "raw_station_data" / "42101_hourly_source_level.csv", "source_filter": "isd_lite",
         "lineage": SHARED, "mapping": {"temp": ("temperature", "degC"), "rhum": ("relative_humidity", "%"),
                                          "pres": ("sea_level_pressure", "hPa")}},
    ]
    exact_links: dict[tuple[str, str], dict[str, Any]] = {}
    pair_counts: dict[str, dict[str, Any]] = {}
    for spec in product_specs:
        product = pd.read_csv(spec["path"], dtype=str, keep_default_na=False, na_filter=False)
        product = product[product.source.eq(spec["source_filter"])].copy()
        links = 0
        by_variable: dict[str, int] = {}
        lookup = native_lookup[spec["station"]]
        for index, row in product.iterrows():
            timestamp = pd.to_datetime(row["time"], utc=True)
            native = lookup.get(timestamp)
            if native is None:
                continue
            nrow = native["row"]
            for product_field, (native_field, unit) in spec["mapping"].items():
                p_raw = str(row.get(product_field, ""))
                n_raw = str(nrow.get(native_field, ""))
                p_status, p_value = classify_raw_value(p_raw)
                n_status, n_value = classify_raw_value(n_raw)
                if p_status != "PRESENT" or n_status != "PRESENT" or p_value != n_value:
                    continue
                key = (spec["name"], native["meta"]["report_payload_fingerprint"])
                item = exact_links.setdefault(key, {
                    "record_type": "EXACT_TIMESTAMP_AND_EXACT_VALUE_PRODUCT_FINGERPRINT_LINK",
                    "shared_observation_id": native["meta"]["report_payload_fingerprint"],
                    "shared_id_kind": "Derived from NOAA station + original timestamp + REM payload; not provider-issued report ID",
                    "source_product_pair": spec["name"], "source_a": "Meteostat 2.2.3 preserved Phase 04/06 CSV",
                    "source_b": "NOAA NCEI GHCNh v1.1.0 native PSV",
                    "source_a_record_ref": f"{spec['path'].relative_to(ROOT).as_posix()}#data-row-{int(index) + 1}",
                    "source_b_record_ref": f"{nrow['_source_file']}#line-{nrow['_source_line_number']}",
                    "station_id": str(nrow["STATION"]), "timestamp_source_a_original": str(row["time"]),
                    "timestamp_source_b_original": str(nrow["DATE"]), "matched_elements": [],
                    "original_report_id_available": False, "underlying_observation_count": 1,
                    "independent_vote_count": 0,
                    "lineage_classification": spec["lineage"],
                    "interpretation": "An exact timestamp/value fingerprint links product records to the same NOAA report payload; not separate corroboration.",
                })
                item["matched_elements"].append({"variable": native_field,
                                                  "value_source_a_raw": p_raw,
                                                  "value_source_b_raw": n_raw,
                                                  "unit": unit,
                                                  "match_basis": "exact numeric value equality; no threshold"})
                links += 1
                by_variable[native_field] = by_variable.get(native_field, 0) + 1
        pair_counts[spec["name"]] = {"lineage_classification": spec["lineage"],
                                      "exact_value_element_links": links,
                                      "unique_shared_report_fingerprints": sum(1 for pair, _ in exact_links if pair == spec["name"]),
                                      "matched_elements_by_variable": by_variable,
                                      "source_filter": spec["source_filter"]}
    exact_rows = list(exact_links.values())
    for row in exact_rows:
        row["matched_elements"] = json.dumps(row["matched_elements"], sort_keys=True)
    summaries = []
    for pair, evidence in pair_counts.items():
        phase07_row = dependencies[dependencies.pair.str.contains(
            "VILD0 METAR / VILD0 NOAA" if pair.startswith("VILD0") else
            "42101 Meteostat GHCNh / NOAA GHCNh" if "GHCNH_vs" in pair else
            "42101 Meteostat ISD-Lite / NOAA GHCNh", regex=False)]
        summary_text = phase07_row.iloc[0].to_dict() if len(phase07_row) else {}
        summaries.append({"record_type": "SOURCE_PAIR_LINEAGE_SUMMARY", "shared_observation_id": "",
                          "source_product_pair": pair, "lineage_classification": evidence["lineage_classification"],
                          "exact_value_element_links": evidence["exact_value_element_links"],
                          "unique_shared_report_fingerprints": evidence["unique_shared_report_fingerprints"],
                          "matched_elements_by_variable": json.dumps(evidence["matched_elements_by_variable"], sort_keys=True),
                          "phase07_assessment": summary_text.get("conclusion", ""),
                          "phase07_evidence": summary_text.get("evidence", ""),
                          "independent_vote_count": 0,
                          "interpretation": "Provider duplicates and likely common source records are retained as lineage evidence and count as one underlying report.",
                          "source_a": "Meteostat 2.2.3 preserved Phase 04/06 CSV",
                          "source_b": "NOAA NCEI GHCNh v1.1.0 native PSV"})
    summaries.append({"record_type": "UNKNOWN_LINEAGE_NO_LINK", "shared_observation_id": "",
                      "source_product_pair": "WMO42099_METEOSTAT_ISDLITE_vs_VILD0_PRIMARY",
                      "lineage_classification": UNKNOWN, "exact_value_element_links": 0,
                      "unique_shared_report_fingerprints": 0,
                      "matched_elements_by_variable": "{}", "phase07_assessment": "UNKNOWN_LINEAGE",
                      "phase07_evidence": "42099 has no authoritative VILD0 alias and no NOAA GHCNh station-list record; its Meteostat ISD-Lite file lacks source/report IDs.",
                      "independent_vote_count": 0,
                      "interpretation": "No match is not evidence of independence; station and sensor lineage remain unresolved.",
                      "source_a": "WMO42099 Meteostat ISD-Lite", "source_b": "VILD0 primary"})
    return exact_rows, summaries


def build_event_register() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates_path = ROOT / "phase03_model_revalidation" / "candidate_observations_8of12.csv"
    candidates = pd.read_csv(candidates_path)
    phase09_events = pd.read_csv(PH09 / "PHASE09_EVENT_REGISTER.csv")
    selected = deterministic_event_registry(candidates,
                                             pd.read_csv(PH07 / "candidate_event_register.csv"))
    events: list[dict[str, Any]] = []
    adjudication: list[dict[str, Any]] = []
    policy_rows: list[dict[str, Any]] = []
    phase07_comps = pd.read_csv(PH07 / "event_level_comparison.csv")
    for idx, event in selected.iterrows():
        prior = phase09_events.iloc[idx]
        source_event_id = str(prior.source_event_id)
        old_rows = phase07_comps[phase07_comps.event_id.eq(source_event_id)]
        for _, reference in old_rows.iterrows():
            raw_lineage = str(reference.lineage_class_vs_primary_station)
            ref_lineage = (INDEPENDENT if raw_lineage == "INDEPENDENT_OBSERVING_SYSTEM" else
                           SHARED if "POSSIBLY_SHARED" in raw_lineage else
                           DERIVED if "DERIVED_FROM_SAME_REPORT" in raw_lineage else
                           CONTEXT if raw_lineage == "CONTEXT_ONLY" else
                           NOT_COMPARABLE if raw_lineage == "NOT_COMPARABLE" else UNKNOWN)
            policy_record = {
                "source_id": reference.reference_source_id,
                "station_id": reference.original_station_id,
                "primary_station_id": "VILD0 / ICAO-VILD",
                "lineage_classification": UNKNOWN,
                "variable": {"temp":"temperature", "rhum":"relative_humidity",
                             "wspd":"wind_speed", "pres":"pressure"}.get(str(reference.variable), str(reference.variable)),
                "primary_value": reference.candidate_value_common_unit,
                "primary_unit": reference.candidate_original_unit,
                "reference_value": reference.reference_value_common_unit,
                "reference_unit": reference.reference_units,
                "candidate_timestamp": prior.candidate_timestamp_utc,
                "reference_timestamp": reference.matched_timestamp_utc,
                "qc_status": reference.quality_status,
                "is_imputed": None,
                "distance_km": 76.04,
            }
            outcome = apply_phase08_policy(policy_record, tolerances={}, tolerance_minutes=60)
            policy_rows.append({"record_scope":"historical_candidate_to_reference_pair",
                                "event_id":str(event.event_id), "reference_source":reference.reference_product,
                                "reference_lineage_classification":ref_lineage,
                                "candidate_lineage_classification":UNKNOWN,
                                "candidate_original_report_id":"NOT_AVAILABLE",
                                "phase08_comparison_eligibility":outcome["comparison_eligibility"],
                                "phase08_outcome":outcome["outcome"],
                                "phase08_reason":outcome["comparison_reason"],
                                "reference_time_status":reference.time_match_status,
                                "policy_tolerance_supplied":False,
                                "independent_vote_count":0,
                                "limitation":"Candidate row source lineage and possible model-fill status are unresolved; policy result is unavailable, not disagreement."})
        events.append({
            "event_id": str(event.event_id), "phase09_source_event_id": source_event_id,
            "primary_station": "VILD0 / ICAO-VILD station record",
            "timestamp_original": str(event.candidate_timestamp_local),
            "timestamp_utc_reproduction": str(event.candidate_timestamp_utc),
            "variable": str(event.event_variable), "candidate_value_original": str(getattr(event, event.event_variable)),
            "candidate_selection_method": "Phase 03 full-table deterministic extrema; Phase 07/09 signature reproduced before reference inspection",
            "selection_metric": str(event.selection_metric), "selection_direction": str(event.selection_direction),
            "configuration_votes": int(event.configuration_votes), "episode_id": int(event.episode_id),
            "original_anomaly_indication": "8-of-12 candidate series indication only; not ground truth",
            "primary_original_report_id": "NOT_AVAILABLE; historical candidate row has no source report ID",
            "reference_products_reviewed": int(len(old_rows)),
            "phase09_qc_good_pat901_rows_within_60m": int(prior.qc_good_compatible_pat901_rows_within_60m),
            "spatial_coverage": "VILD airport station record and Patiala ~76.04 km station record; WMO 42099 record ~2.27 km is metadata-known but no linked observation series acquired",
            "temporal_coverage": (
                f"{prior.reference_rows_within_60m_or_missing_value} Phase 09 reference rows were within 60 minutes or had missing values; "
                f"{prior.qc_good_compatible_pat901_rows_within_60m} QC-good compatible Patiala rows within 60 minutes"
            ),
            "variable_coverage": "Reference product rows and variable-specific metadata retained in Phase 07; no eligible event comparison",
            "selection_exclusion_reason": "Candidate row lacks original source/report ID and may contain historical model-filled values; no independent event truth label.",
            "adjudication_status": "NOT_ADJUDICATED", "adjudication_label": "",
        })
        adjudication.append({
            "event_id": str(event.event_id), "adjudication_status": "NOT_ADJUDICATED",
            "adjudication_label": None, "reviewer_or_method": "No independent human/authoritative adjudication was available",
            "evidence_considered": "Phase 03 candidate row; Phase 07 source-level reference availability; Phase 10 NOAA GHCNh and WMO station metadata",
            "sources_consulted": "Phase 07/09 local evidence; no original IMD station observations or independent event label source acquired",
            "source_independence": "FM15/FM12 report-level distinction only; instruments/operators/calibration unresolved",
            "temporal_compatibility": "Candidate-to-original-report tie unavailable; nearby report timestamps are availability only",
            "spatial_relevance": "Patiala ~76.04 km; WMO42099 station record ~2.27 km but no corresponding raw independent time series",
            "variable_compatibility": str(event.event_variable), "quality_control": "Candidate row QC/source unavailable; source QC retained only in GHCNh rows",
            "rationale": "No E1/E2/E3/E4 prediction was used as a ground-truth label; evidence is insufficient to adjudicate this candidate.",
            "confidence_limitations": "No reviewer panel, event-level original reports, instrument histories, or independent normal/anomaly labels.",
        })
    validate_adjudication_register(pd.DataFrame(adjudication))
    return events, adjudication, policy_rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    required_outputs = [
        "PHASE10_DATA_ACQUISITION_REPORT.md", "PHASE10_SOURCE_INVENTORY.csv",
        "PHASE10_STATION_LINEAGE_REGISTER.csv", "PHASE10_OBSERVATION_PROVENANCE_REGISTER.csv",
        "PHASE10_REFERENCE_DATASET.csv", "PHASE10_SHARED_OBSERVATION_REGISTER.csv",
        "PHASE10_CANDIDATE_EVENT_REGISTER.csv", "PHASE10_EVENT_ADJUDICATION_REGISTER.csv",
        "PHASE10_DATASET_SUFFICIENCY.json", "PHASE10_DECISION.json",
        "PHASE10_REPRODUCIBILITY_MANIFEST.json",
    ]
    already = [name for name in required_outputs if (OUT / name).exists()]
    if already:
        raise FileExistsError(f"Refusing to overwrite Phase 10 outputs: {already}")
    metadata_path = OUT / "PHASE10_OSCAR_STATION_METADATA.json"
    if not metadata_path.is_file():
        raise FileNotFoundError("Public WMO OSCAR metadata capture is missing; acquire it first and preserve the response.")
    oscar_meta = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    if len(oscar_meta.get("records", [])) != 2:
        raise ValueError("expected sanitized WMO OSCAR metadata for WMO 42099 and 42101")

    frames, _ = read_native_files()
    dataset, provenance, data_stats = build_provenance_and_dataset(frames)
    shared_exact, shared_summaries = build_shared_observation_register(frames)
    events, adjudication, policy_rows = build_event_register()
    shared_rows = shared_exact + shared_summaries

    oscar_by_wigos = {row["wigos_station_id"]: row for row in oscar_meta["records"]}
    phase07_manifest = json.loads((PH07 / "external_reference_manifest.json").read_text(encoding="utf-8"))
    phase07_files = {row["file"]: row for row in phase07_manifest.get("station_year_files_and_station_list", [])}
    p09_decision = json.loads((PH09 / "PHASE09_VALIDATION_DECISION.json").read_text(encoding="utf-8"))
    station_list = pd.read_csv(NATIVE / "ghcnh-station-list.csv", dtype=str).fillna("")
    native_metadata: dict[str, dict[str, Any]] = {}
    for station_key, spec in STATION_META.items():
        row = station_list[station_list.GHCN_ID.eq(spec["station_id"])].iloc[0]
        native_metadata[station_key] = row.to_dict()

    source_inventory = [
        {"source_id":"NOAA_GHCNH_VILD_NATIVE","source_category":"historical station reports","status":"ACQUIRED_IN_PHASE07_REUSED_AND_RECONCILED_IN_PHASE10","provider":"NOAA NCEI; harmonized multisource dataset","original_reporting_organization":"Not established by GHCNh metadata for each VILD record","station_identity":"INI0000VILD / ICAO-VILD / Ludhiana airport station record","reporting_system":"FM15; FM16 rows also present in 2026; per-element report type/source code retained","frequency":"source reports irregular/hourly; timestamps in UTC","variables_units":"GHCNh element fields and units in reference dataset; RH measurement basis retained","qc":"per-element raw QC and measurement codes retained; semantics source/element-specific","original_identifiers":"Source station ID, raw REM payload and deterministic row/payload fingerprints; no provider-issued unique report ID","access_method":"Public NOAA NCEI HTTPS station-year PSV bulk files; already present from Phase 07; no Phase 10 download","license_access_restrictions":"NCEI data are public for research; specific license text not identified in the product README; cite NOAA DOI/provider","lineage_classification":"POSSIBLY_SHARED_EVIDENCE","raw_observations_acquired_in_phase10":False,"limitation":"Multisource harmonized rows; station/sensor/operator independence and report ID are not fully established."},
        {"source_id":"NOAA_GHCNH_42101_NATIVE","source_category":"historical station reports","status":"ACQUIRED_IN_PHASE07_REUSED_AND_RECONCILED_IN_PHASE10","provider":"NOAA NCEI; harmonized multisource dataset","original_reporting_organization":"India Meteorological Department per WMO OSCAR station metadata; row-specific original organization is not explicit","station_identity":"INM00042101 / WMO-42101 / Patiala","reporting_system":"FM12 plus FM94_1 in 2026; per-element report type/source code retained","frequency":"synoptic and source-dependent reports; timestamps in UTC","variables_units":"GHCNh element fields and units in reference dataset; RH and precip bases retained","qc":"per-element raw QC and measurement codes retained; source-specific semantics","original_identifiers":"WMO-42101 source station ID and raw REM payload; no unique provider-issued report ID","access_method":"Public NOAA NCEI HTTPS station-year PSV bulk files; already present from Phase 07; no Phase 10 download","license_access_restrictions":"NCEI data are public for research; specific license text not identified in product README; cite NOAA DOI/provider","lineage_classification":"INDEPENDENT_REPORT_EVIDENCE relative to VILD FM15 at report-system level only; same-site source products are shared/derived","raw_observations_acquired_in_phase10":False,"limitation":"Not proof of independent instruments/operator; same reporting agency IMD appears in WMO metadata for 42099 and 42101."},
        {"source_id":"WMO_OSCAR_SURFACE_METADATA","source_category":"official station metadata","status":"ACQUIRED_PHASE10_PUBLIC_READ_API","provider":"World Meteorological Organization OSCAR/Surface","original_reporting_organization":"IMD recorded for WMO 42099 and WMO 42101","station_identity":"WIGOS 0-20000-0-42099 Ludhiana and 0-20000-0-42101 Patiala","reporting_system":"Station class includes surface land meteorological/SYNOP; metadata only","frequency":"Metadata snapshot retrieved 2026-11-18 UTC; no observation frequency data series acquired","variables_units":"Not observation data","qc":"Not applicable","original_identifiers":"WIGOS station identifiers and OSCAR station IDs 6406/6407","access_method":"Public GET search/stationReport API; sanitized response preserved in PHASE10_OSCAR_STATION_METADATA.json","license_access_restrictions":"Public metadata endpoint; no record-specific license surfaced; WMO requests acknowledgement of OSCAR where used","lineage_classification":"NOT_COMPARABLE as weather-observation evidence","raw_observations_acquired_in_phase10":False,"limitation":"No sensor deployment, instrument serial/calibration, raw report archive, or historical station observations in response."},
        {"source_id":"IMD_DATA_SUPPLY_PORTAL","source_category":"potential original station observations","status":"ACCESSIBLE_BY_APPLICATION_NOT_ACQUIRED","provider":"India Meteorological Department / National Data Centre","original_reporting_organization":"IMD station observations, if station and period available","station_identity":"Candidate requests WMO 42099 Ludhiana and WMO 42101 Patiala; exact sensor/site history still required","reporting_system":"Hourly/daily station observations offered in data categories; selected stations only","frequency":"Hourly availability is station-dependent","variables_units":"IMD lists rainfall, temperature, RH, wind, station/sea-level pressure and weather phenomena","qc":"Archived original QC/revision details must be requested","original_identifiers":"Would need request response metadata and report/source identifiers","access_method":"Public portal/docs inspected. Registration, email validation, identity/certificate submission, data request, payment receipt if charges apply are required; no request submitted.","license_access_restrictions":"Data supply may be chargeable; portal rules and supplied-use terms apply","lineage_classification":"UNKNOWN_LINEAGE until source rows and metadata acquired","raw_observations_acquired_in_phase10":False,"limitation":"No institutional credentials/identity documents or payment/request authorization supplied; exact station data availability not yet confirmed."},
        {"source_id":"NOAA_AWC_METAR_API","source_category":"original aviation observations","status":"HISTORICAL_WINDOW_INSUFFICIENT_FOR_CANDIDATE_DATES","provider":"NOAA Aviation Weather Center API","original_reporting_organization":"Airport METAR origin/operator not established by API alone","station_identity":"ICAO VILD","reporting_system":"Raw METAR and decoded formats; API current database","frequency":"Near-real-time reports","variables_units":"Raw METAR groups; variable semantics encoded in report","qc":"Report content; not an independent QC archive","original_identifiers":"Raw METAR text may carry date/time/station but not stable provider record ID","access_method":"Official API documentation inspected; API allows up to previous 30 days only; candidate events are older; no data fetched","license_access_restrictions":"Rate limits and max result count apply","lineage_classification":"POSSIBLY_SHARED_EVIDENCE with VILD GHCNh/Meteostat METAR","raw_observations_acquired_in_phase10":False,"limitation":"No old event reports through the current API window."},
        {"source_id":"NOAA_NCEI_SRRS_METAR_ARCHIVE","source_category":"historical aviation report archive","status":"ORDER_PATH_CONFIRMED_NOT_SUBMITTED","provider":"NOAA NCEI Archive Information Request System / SRRS","original_reporting_organization":"Archived METAR/SPECI text; original airport operator not established here","station_identity":"Potential ICAO VILD bulletin/station query","reporting_system":"SRRS historical text products include METAR-formatted observations","frequency":"Archive search/order; max 5 days per order within a month on surfaced form","variables_units":"Raw report text","qc":"Original report text; archive retention/availability must be confirmed per requested bulletin","original_identifiers":"Bulletin and raw report text expected; request not submitted","access_method":"Official request form and Archive View instructions inspected; no order submitted","license_access_restrictions":"Order workflow requires email/delivery details; no user request submitted","lineage_classification":"POSSIBLY_SHARED_EVIDENCE with VILD reports unless separate source is shown","raw_observations_acquired_in_phase10":False,"limitation":"Historical source access may exist but per-period availability, bulletin mapping and use terms remain unconfirmed."},
        {"source_id":"DATA_GOV_IN_IMD_GRIDDED_RAIN_TEMPERATURE","source_category":"gridded contextual product","status":"PUBLIC_CATALOG_IDENTIFIED_NOT_ACQUIRED","provider":"IMD/NRSC records catalogued via data.gov.in","original_reporting_organization":"Gridded station-derived IMD product; source gauge membership must be established","station_identity":"Grid cells, not a station record","reporting_system":"Daily/gridded product, not hourly station report","frequency":"Daily/context-dependent","variables_units":"Rainfall and temperature products described in catalog","qc":"Grid product QC details would need product-specific review","original_identifiers":"Grid cell and product metadata, not report ID","access_method":"Official catalog inspected; no download performed","license_access_restrictions":"Catalog states NDSAP for listed resource; resource-specific terms apply","lineage_classification":"CONTEXT_ONLY","raw_observations_acquired_in_phase10":False,"limitation":"Not independent station evidence; not adequate for station-level hourly E3 adjudication."},
        {"source_id":"ERA5_CONTEXT","source_category":"reanalysis/context","status":"NOT_ACQUIRED","provider":"Copernicus Climate Change Service","original_reporting_organization":"Assimilated multi-source analysis; not a station organization","station_identity":"Grid cell","reporting_system":"Reanalysis","frequency":"Hourly product options; no dataset retrieved","variables_units":"Would require product selection and unit review","qc":"Model/assimilation uncertainty; not station QC","original_identifiers":"Grid/time coordinates","access_method":"Not downloaded in Phase 10","license_access_restrictions":"Copernicus product terms would apply","lineage_classification":CONTEXT,"raw_observations_acquired_in_phase10":False,"limitation":"Must remain context-only; assimilation may reuse station reports."},
    ]

    source_lineage = [
        {"station_or_product":"VILD0 / ICAO-VILD / NOAA GHCNh INI0000VILD","station_identity":"Ludhiana Airport station record; VILD0 mapping retained from Phase 05","original_reporting_organization":"Not established per observation in NOAA station-year data; WMO OSCAR query did not return a VILD WIGOS record in the selected geographic result","coordinates":f"{native_metadata['VILD'].get('LATITUDE')},{native_metadata['VILD'].get('LONGITUDE')}","elevation_m":native_metadata['VILD'].get('ELEVATION'),"station_history":"Exact sensor coordinates, moves and deployment history not verified","instrument_calibration":"Unknown","reporting_system":"FM15 and some FM16 report payloads in 2026","source_identifier":"ICAO-VILD; element source codes retained verbatim","provider_transformation":"NOAA NCEI GHCNh harmonization; source station ID/report type/QC/measurement code and REM retained","lineage_classification":SHARED,"pair_scope":"Potentially shared with Phase06 Meteostat METAR product; distinct report from Patiala only at report-system level","evidence":"Phase07 fingerprint assessment plus exact timestamp/value links generated in Phase10; airport station-level crosswalk from Phase05","limitations":"Provider-source codes not fully decoded here; report payload is not a provider-issued unique ID; no instrument/operator/calibration independence."},
        {"station_or_product":"WMO 42099 / GHCN identifier not present","station_identity":"Official OSCAR WIGOS 0-20000-0-42099, LUDHIANA; distinct WMO station record","original_reporting_organization":"India Meteorological Department per WMO OSCAR metadata (valid since 2016-04-28)","coordinates":"30.8666666667,75.9333333333","elevation_m":255,"station_history":"OSCAR date established 1982-04-03; no site move/instrument deployment detail supplied","instrument_calibration":"Unknown","reporting_system":"SYNOP station class in OSCAR; no raw station report series acquired in Phase 10","source_identifier":"WMO-42099 / WIGOS 0-20000-0-42099","provider_transformation":"Phase04 Meteostat ISD-Lite 567 rows; NOAA GHCNh station list has no 42099 match and candidate station file was 404 in Phase07","lineage_classification":UNKNOWN,"pair_scope":"No authoritative alias to VILD0; 2.27 km station-record distance is not a sensor identity link","evidence":"Public WMO OSCAR metadata retrieved Phase10; Phase07 source inventory and Phase04 dataset","limitations":"Station identity/IMD operator is now documented, but exact historical sensor, observations, source row lineage and relation to airport site are unresolved."},
        {"station_or_product":"WMO 42101 / NOAA GHCNh INM00042101","station_identity":"Official OSCAR WIGOS 0-20000-0-42101, PATIALA; matches NOAA WMO station ID","original_reporting_organization":"India Meteorological Department per WMO OSCAR metadata (valid since 2016-04-28)","coordinates":"30.3333333333,76.4666666667","elevation_m":251,"station_history":"OSCAR date established 1948-04-10; no current sensor deployment/calibration data in response","instrument_calibration":"Unknown","reporting_system":"FM12 and FM94_1 element report types in preserved NOAA product","source_identifier":"WMO-42101; element-level WMO-42101 source IDs retained","provider_transformation":"NOAA NCEI GHCNh harmonization, plus same-source Meteostat mirrors and ISD-Lite subset","lineage_classification":INDEPENDENT,"pair_scope":"Distinct report/station record relative to ICAO-VILD FM15 only; full organizational/instrument independence not established; IMD is metadata organization for 42099 and 42101","evidence":"WMO OSCAR station response and NOAA native GHCNh per-element metadata","limitations":"No instrument identifiers, exact sensor position, calibration, or direct link to candidate historical records."},
        {"station_or_product":"WMO 42101 Meteostat GHCNh product","station_identity":"Same WMO 42101 Patiala station as native NOAA GHCNh","original_reporting_organization":"Not separate from original data product","coordinates":"same as WMO 42101","elevation_m":251,"station_history":"Derived product path","instrument_calibration":"Not applicable to mirror","reporting_system":"GHCNh report metadata re-exposed via Meteostat","source_identifier":"Meteostat source=ghcnh; NOAA native IDs match","provider_transformation":"Meteostat wrapper/repackaging of NOAA GHCNh; Phase07 matched value fingerprints","lineage_classification":DERIVED,"pair_scope":"Same underlying provider data; count as one observation","evidence":"Phase07 dependence audit and Phase10 exact field links","limitations":"Do not count as another independent station/source."},
        {"station_or_product":"WMO 42101 Meteostat ISD-Lite product","station_identity":"Same WMO 42101 station as native NOAA product","original_reporting_organization":"Per-observation organization not retained in ISD-Lite","coordinates":"same station record","elevation_m":251,"station_history":"Hourly subset strips sub-hourly records and complex flags","instrument_calibration":"Unknown","reporting_system":"ISD-Lite","source_identifier":"Meteostat Provider.ISD_LITE; original report source IDs absent","provider_transformation":"Derived subset from same NOAA station ecosystem; row-level originals missing","lineage_classification":SHARED,"pair_scope":"Potentially shared original reports; exact same-station fingerprints matched in Phase07/Phase10","evidence":"Phase07 source dependence assessment and exact row-value fingerprint links","limitations":"Must not count as an independent vote alongside GHCNh."},
        {"station_or_product":"ERA5 or IMD gridded context","station_identity":"Not a station","original_reporting_organization":"Multi-source assimilated or gridded product","coordinates":"Grid cells","elevation_m":"Not a sensor elevation","station_history":"Not applicable","instrument_calibration":"Not applicable","reporting_system":"Analysis product","source_identifier":"Product/grid/time IDs","provider_transformation":"Gridded/reanalysis assimilation or station-based spatial interpolation","lineage_classification":CONTEXT,"pair_scope":"Context only","evidence":"Not acquired in Phase 10","limitations":"Cannot be treated as independent station observation or adjudicated truth."},
    ]

    phase09_event_rows = pd.read_csv(PH09 / "PHASE09_EVENT_REGISTER.csv")
    event_index = {row["phase09_source_event_id"]: row for row in events}
    for _, event in phase09_event_rows.iterrows():
        event_id = str(event.source_event_id)
        local = event_index[event_id]
        local["phase09_source_event_id"] = event_id

    # Dimension gates summarize available evidence, not software execution.
    sufficiency = validate_sufficiency_assessment({
        "provenance": "PARTIAL", "geographic": "PARTIAL", "temporal": "PARTIAL",
        "measurement": "PARTIAL", "event": "PARTIAL", "adjudication": "FAIL",
    })
    event_outcomes = {"REGIONALLY_SUPPORTED_EVENT":0,"LOCALIZED_EVENT":0,
                      "STATION_SPECIFIC_SUSPICIOUS_OBSERVATION":0,"INCONCLUSIVE":0,
                      "INSUFFICIENT_REFERENCE_DATA":0,"NOT_ADJUDICATED":len(events)}
    decision = {
        "phase":"10_independent_reference_data", "decision":"INSUFFICIENT_INDEPENDENT_DATA",
        "phase09_decision":p09_decision["decision"], "raw_observations_acquired_in_phase10":False,
        "new_reference_data_rows":int(len(dataset)), "unique_underlying_report_fingerprints":data_stats["overall"]["unique_underlying_report_fingerprints"],
        "candidate_events":len(events), "independently_adjudicated_events":0,
        "event_adjudication_counts":event_outcomes,
        "event_results_from_phase08_policy":"No support/conflict classification; missing candidate original report IDs lead to UNAVAILABLE, and shared product records are excluded.",
        "independent_evidence_scope":"Distinct report/station metadata only. NOAA product's component source code is retained, but physical instrument, calibration, exact siting, and original reporting organization are not established for every row.",
        "sufficiency":sufficiency,
        "fault_inference":False,"fault_probability":None,"e3_classifier_integration":False,
        "primary_station_replaced":False,"baseline_retrained":False,
        "reason":"Phase 10 creates a provenance-preserving dataset from already acquired NOAA GHCNh records and acquires public WMO station metadata, but does not obtain IMD original observations or independent human/authoritative event labels. Public access/order routes exist, but their data acquisition steps require a formal request not made in this run.",
    }

    # Phase 08 policy audit for event rows and duplicated observation links.
    for link in shared_exact:
        policy = apply_phase08_policy({"lineage_classification": str(link["lineage_classification"])})
        policy_rows.append({"record_scope":"exact_shared_product_fingerprint",
                            "event_id":"", "reference_source":link["source_product_pair"],
                            "reference_lineage_classification":link["lineage_classification"],
                            "candidate_lineage_classification":"NOT_APPLICABLE",
                            "candidate_original_report_id":"NOT_APPLICABLE",
                            "phase08_comparison_eligibility":policy["comparison_eligibility"],
                            "phase08_outcome":policy["outcome"],"phase08_reason":policy["comparison_reason"],
                            "reference_time_status":"EXACT_TIMESTAMP_AND_VALUE_FINGERPRINT",
                            "policy_tolerance_supplied":False,"independent_vote_count":0,
                            "limitation":"Shared/derived product record cannot add an independent vote."})

    report = f"""# Phase 10 — Independent Data Acquisition and Event Reference Dataset Development

**Decision: `INSUFFICIENT_INDEPENDENT_DATA`**

## Acquisition outcome

Phase 10 did not obtain new weather observation files. It reused the already preserved Phase 07 NOAA NCEI GHCNh v1.1.0 station-year files for ICAO-VILD and WMO-42101 and constructed a separate, hashed, long-format reference dataset without changing the original raw files. The new `PHASE10_OSCAR_STATION_METADATA.json` is a sanitized public WMO OSCAR/Surface response for WMO 42099 and 42101; it is station metadata, not observations. The dataset contains {data_stats['overall']['station_timestamp_rows']} source station/time rows, {data_stats['overall']['unique_underlying_report_fingerprints']} report-payload fingerprints, and {data_stats['overall']['long_element_records_including_missing']} variable/element rows including blanks and provider sentinels. No missing values were filled, no QC filters were applied, and no values or timestamps were normalized in the stored dataset.

The official NOAA GHCNh bulk product is publicly accessible as station/year PSV files and documents UTC timestamps, element definitions, and per-element source/report/measurement/QC fields. It is a harmonized multisource product. The raw `REM` payload is retained, but GHCNh does not supply a unique provider-issued report identifier in the station-year files; Phase 10 fingerprints are locally derived identifiers, not original report IDs. NOAA's station list places VILD at 30.8547, 75.9526/elevation 254.2 m and Patiala at 30.3333, 76.4667/elevation 251 m. Those are station-record coordinates.

## Sources investigated and access

| Source | Finding | Phase 10 status |
|---|---|---|
| NOAA NCEI GHCNh | Existing VILD and Patiala station-year data include report payloads and variable-specific source metadata; public bulk downloads are reproducible. GHCNh harmonizes many source systems, so provider is not equivalent to the original observer. | Reused prior Phase 07 files; no new raw download |
| WMO OSCAR/Surface | Public metadata query returns official WIGOS station records for WMO 42099 Ludhiana and 42101 Patiala, both with IMD listed as organization. No instrument deployment/calibration or time series was returned. | Metadata acquired and sanitized response preserved |
| IMD Data Supply Portal | Historical station data include the requested variable families, but are selected-station and request-dependent. Registration, verified identity/certificate, request submission, and possibly payment are required. No request was submitted. | Not acquired; request path identified |
| NOAA Aviation Weather Center API | Raw METAR access is documented, but the API supports only the previous 30 days; Phase 03 candidate dates fall outside that window. | Not acquired through current API |
| NOAA NCEI SRRS archive | Official historical METAR-formatted reports can be ordered; the surfaced form limits each order to five days within one month. Period/bulletin availability is not yet confirmed. No order was submitted. | Request path identified; not acquired |
| data.gov.in IMD gridded rainfall/temperature | Public catalog entries are daily/gridded or sub-basin products, not hourly station report archives. They could be context only unless gauge membership and processing are documented. | Not downloaded; context only |
| ERA5 | Reanalysis would be contextual, not an independent station report; no Phase 10 download was made. | Not acquired |

IMD's public portal instructions describe registration and an online request/payment process; this run did not submit identity documents, a data order, or payment. The AWC API and NCEI archive paths were reviewed without bypassing their access or order workflows. No email or external request was sent.

## Station identity and source lineage

WMO OSCAR reports WMO 42099 as LUDHIANA, WIGOS `0-20000-0-42099`, at 30.8666667, 75.9333333, elevation 255 m, established 1982-04-03, operational, with India Meteorological Department listed as organization. WMO 42101 is PATIALA, WIGOS `0-20000-0-42101`, at 30.3333333, 76.4666667, elevation 251 m, established 1948-04-10, also with IMD listed. Both records are fixed land stations. These records improve station identity and operator metadata, but do not document the instrument serials, sensor positions, calibration histories, or site moves needed for physical measurement independence. VILD0 remains verified only at the ICAO VILD airport-station record level; exact sensor location/operator history remains unresolved. No WMO 42099 observations were acquired and no VILD0↔42099 equivalence is asserted.

The curated native records distinguish VILD FM15/FM16 source rows from Patiala FM12/FM94_1 source rows at report level. Different report type does not prove independent sensor or organization. The OSCAR metadata indicates the same organization (IMD) for WMO 42099 and 42101; this must be considered when evaluating organizational independence. NOAA's numeric per-element source codes and report fields are preserved verbatim; they are not all mapped to an original provider organization in this phase. RH and wet-bulb measurement codes are retained because they can indicate derived values; precipitation accumulation elements remain separate. Pressure elements are separate fields and are not pooled.

The shared-observation register links product records only when timestamps and raw values match exactly for an element. It records VILD Meteostat METAR/NOAA, Patiala Meteostat GHCNh/NOAA, and Patiala ISD-Lite/NOAA relationships. These links count as one underlying report, with zero additional independent votes. The separate phase inventory retains WMO 42099 Meteostat ISD-Lite as `UNKNOWN_LINEAGE`; absent a matching NOAA row is not proof of independence.

## Dataset coverage and limitations

The transformed dataset preserves `{len(dataset)}` rows across the source elements in both stations, including blank fields, source/QC/report/measurement metadata, original timestamp strings, raw report text, row hashes, and source-file line references. `PHASE10_OBSERVATION_PROVENANCE_REGISTER.csv` has one entry per source station/time record. `PHASE10_REFERENCE_DATASET.csv` is a long-format derived dataset: it records original raw value strings and a separate numeric parse for analysis, and explicitly records that no unit conversion was applied. See station/variable availability summaries in `PHASE10_DATASET_SUFFICIENCY.json` and the source inventory.

Original unique report IDs are unavailable; report fingerprints are derived from station, original UTC timestamp, and raw `REM` content. QC codes are kept raw because their meanings vary with source and variable. Missing values and sentinels remain distinguished. The dataset's lineage classifications are scoped relative to the primary station and explicitly do not establish instrument independence.

## Candidate event registry and adjudication

The event registry deterministically reproduces the eight Phase 09 Phase 03 full-table extrema from the 123-row candidate series and verifies the preserved event signature. It includes temperature, RH, wind and pressure candidate types without selecting on neighbor agreement. These are model-candidate indications, not anomaly truth labels. Zero events were independently adjudicated. All eight adjudication statuses are `NOT_ADJUDICATED`; no E1/E2/E3/E4 result is used as ground truth, and no sensor-fault label or probability is created. The registry records available neighboring report coverage, exclusions, temporal/spatial limits, and variable coverage.

The Phase 08 policy is applied to candidate/reference rows. Candidate source lineage is unknown, so those event comparisons remain `UNAVAILABLE`. Exact duplicate/shared products are passed to the Phase 08 policy as shared/derived evidence and are `NOT_COMPARABLE` for independent voting. No numerical agreement tolerance was invented.

## Sufficiency and next evidence needed

| Dimension | Assessment | Basis |
|---|---|---|
| Provenance | `PARTIAL` | Native GHCNh per-element metadata and report payloads retained; unique provider report IDs and component organizations are incomplete |
| Geography | `PARTIAL` | WMO/NOAA station records identified; VILD sensor point and all instrument siting/history are unknown |
| Temporal | `PARTIAL` | NOAA UTC timestamps are documented; candidate row-to-original-report linkage and additional event windows are missing |
| Measurement | `PARTIAL` | Variables, units, QC and measurement codes retained; derived RH, source semantics and precipitation intervals constrain valid comparisons |
| Event | `PARTIAL` | Eight deterministic model-candidate events exist, but not a diverse independently labeled event/control set; no arbitrary sample minimum imposed |
| Adjudication | `FAIL` | No independent human or authoritative event reference labels |

The next research steps are to request and preserve original IMD station observations and their documentation for 42099/42101, acquire archived raw VILD METAR reports for selected dates through an authorized NCEI route, resolve station/instrument/site histories, link candidate values to original report payloads, and establish independent reviewer/authoritative event adjudication before preregistered event evaluation. Until then the dataset is suitable for provenance and descriptive report-level research, not controlled E3 validation.

## Reproducibility and scope

The reproducibility manifest hashes all source inputs, the sanitized WMO metadata response and generated files. The transformed dataset is deterministic with respect to preserved NOAA files and the captured WMO snapshot. Output artifacts are under `outputs/phase10_independent_reference_data/`; repository `.gitignore` excludes `outputs/*`, so these output files are present locally but untracked by Git. No ignore rule was changed. Phase 00–09 raw/derived outputs were not overwritten.

**No independent fault truth is claimed. No classifier, E1/E2/E4, or baseline behavior was changed.**
"""

    write_csv("PHASE10_SOURCE_INVENTORY.csv", source_inventory)
    write_csv("PHASE10_STATION_LINEAGE_REGISTER.csv", source_lineage)
    write_csv("PHASE10_OBSERVATION_PROVENANCE_REGISTER.csv", provenance)
    write_csv("PHASE10_REFERENCE_DATASET.csv", dataset)
    write_csv("PHASE10_SHARED_OBSERVATION_REGISTER.csv", shared_rows)
    write_csv("PHASE10_CANDIDATE_EVENT_REGISTER.csv", events)
    write_csv("PHASE10_EVENT_ADJUDICATION_REGISTER.csv", adjudication)
    write_csv("PHASE10_POLICY_ELIGIBILITY_AUDIT.csv", policy_rows)
    write_csv("PHASE10_VARIABLE_AVAILABILITY.csv", [
        {"station_id": station_id, "station_name": STATION_META[station_key]["source_name"],
         "variable": variable, **values}
        for station_key, station_id in [(key, STATION_META[key]["station_id"]) for key in frames]
        for variable, values in data_stats[station_key]["variables"].items()
    ])
    write_json("PHASE10_DATASET_SUFFICIENCY.json", {
        "phase":"10_independent_reference_data", "sufficiency":sufficiency,
        "counts":data_stats, "candidate_events":len(events), "independently_adjudicated_events":0,
        "event_outcome_counts":event_outcomes,
        "shared_product_link_counts":shared_summaries,
        "thresholds": "No minimum event count or numerical weather agreement threshold was invented.",
        "evidence_gaps":["original IMD observations", "candidate-to-original-report linkage",
                          "instrument/site history", "independent event adjudication",
                          "specification-supported tolerances"],
    })
    write_json("PHASE10_DECISION.json", decision)
    report_path = OUT / "PHASE10_DATA_ACQUISITION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")

    inputs: dict[str, dict[str, Any]] = {}
    for relative in INPUTS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"required reproducibility input missing: {relative}")
        inputs[relative] = {"sha256":digest(path),"bytes":path.stat().st_size}
    metadata_relative = metadata_path.relative_to(ROOT).as_posix()
    inputs[metadata_relative] = {"sha256":digest(metadata_path),"bytes":metadata_path.stat().st_size,
                                 "retrieved_at_utc":oscar_meta.get("retrieved_at_utc"),
                                 "source_url":oscar_meta.get("query_url")}
    refs = {
        "NOAA_GHCNh_product":"https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly",
        "NOAA_GHCNh_documentation":"https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh_DOCUMENTATION.pdf",
        "NOAA_GHCNh_metadata_doi":"https://doi.org/10.25921/jp3d-3v19",
        "WMO_OSCAR_surface":"https://oscar.wmo.int/surface/",
        "WMO_OSCAR_public_station_search_api":oscar_meta.get("query_url"),
        "WMO_OSCAR_station_report_api":oscar_meta.get("station_report_endpoint"),
        "IMD_data_supply_portal":"https://dsp.imdpune.gov.in/home_registration_form.php",
        "IMD_data_payment":"https://dsp.imdpune.gov.in/home_paymentprocedure_indian.php",
        "NOAA_AWC_data_api":"https://aviationweather.gov/data/api/",
        "NOAA_AWC_archive_instructions":"https://aviationweather.gov/tools/archive/",
        "NOAA_NCEI_SRRS_request":"https://www.ncei.noaa.gov/has/HAS.DsSelect",
        "data_gov_in_rainfall_catalog":"https://data.gov.in/catalog/rainfall",
    }
    generated = [name for name in required_outputs if name != "PHASE10_REPRODUCIBILITY_MANIFEST.json"]
    generated.append("PHASE10_OSCAR_STATION_METADATA.json")
    manifest = {
        "phase":"10_independent_reference_data",
        "branch":"feature/phase10-independent-reference-data",
        "base_commit":"7baf75a8a9682e611fb8a4b1cd248a1a6144cc65",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "software_versions":{"python":sys.version.split()[0],"platform":platform.platform(),
                              "pandas":pd.__version__,"numpy":np.__version__},
        "input_files":inputs,
        "source_references":refs,
        "acquisition_status":{"new_station_observation_downloads_in_phase10":0,
                              "reused_NOAA_GHCNh_phase07_station_rows":data_stats["overall"]["station_timestamp_rows"],
                              "WMO_OSCAR_station_metadata_records_acquired":len(oscar_meta["records"]),
                              "IMD_request_submitted":False,"NOAA_SRRS_order_submitted":False,
                              "AWC_api_data_fetched":False,"raw_inputs_modified":False},
        "configuration":{"source_elements":DATA_ELEMENTS,
                          "timestamp_handling":"Exact raw DATE preserved; documentation identifies UTC; no parse/rewrite in output data field",
                          "unit_handling":"Raw source units copied; no conversion in reference dataset",
                          "missingness":"blank, -9999 sentinel, nonnumeric raw token, and numeric value recorded distinctly; source strings retained",
                          "qc":"raw QC codes retained; no filtering or generic normalization",
                          "report_identity":"No provider unique ID; derived SHA256 of station + timestamp + REM payload is explicitly a fingerprint only",
                          "duplicate_policy":"Exact timestamp/raw-value fingerprint links product copies; shared products count as zero additional independent votes",
                          "event_selection":"Phase 03 deterministic full-table extrema reproduced and signature verified against Phase 07/09",
                          "event_adjudication":"NOT_ADJUDICATED where no independent reviewer/authoritative label available",
                          "e3_policy":"src/weather_research/e3_evidence_policy.py; unchanged; no threshold supplied"},
        "dataset_counts":data_stats,
        "decision":"INSUFFICIENT_INDEPENDENT_DATA",
        "generated_artifacts":{(OUT / name).relative_to(ROOT).as_posix():
                                {"sha256":digest(OUT / name),"bytes":(OUT / name).stat().st_size}
                                for name in generated},
        "outputs_ignored_by_git":"outputs/*; no ignore rule changed",
        "no_raw_input_overwrite":True,"no_commit_push_or_merge":True,
        "no_classifier_or_baseline_changes":True,"no_e1_e2_e4_changes":True,
    }
    write_json("PHASE10_REPRODUCIBILITY_MANIFEST.json", manifest)


if __name__ == "__main__":
    main()
