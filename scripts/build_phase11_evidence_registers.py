"""Build Phase 11 audit registers from fixed Phase 10 events and acquired files."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from weather_research.e3_evidence_policy import UNKNOWN
from weather_research.phase11_adjudication import (
    apply_phase08_policy, exact_candidate_link, find_duplicate_reports,
    record_fingerprint, sha256_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase11_original_observations_event_adjudication"
PH10 = ROOT / "outputs" / "phase10_independent_reference_data"
IEM_LOG = OUT / "iem_retrieval_log.json"
IEM_BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 11 artifact: {path}")
    fields = list(dict.fromkeys(k for row in rows for k in row)) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metar_variable_check(variable: str, candidate_value: Any, raw_message: str) -> tuple[str, str, Any]:
    """Conservative report/value compatibility; never treats derived RH as direct."""
    try:
        expected = float(candidate_value)
    except (TypeError, ValueError):
        expected = None
    temp_group = re.search(r"\b(M?\d{2})/(M?\d{2})\b", raw_message)
    if variable == "temp":
        if not temp_group or expected is None:
            return "NOT_ASSESSABLE", "METAR temperature group or candidate value is absent.", None
        raw_t = temp_group.group(1)
        observed = -int(raw_t[1:]) if raw_t.startswith("M") else int(raw_t)
        return ("VALUE_COMPATIBLE" if expected == observed else "VALUE_MISMATCH",
                "Candidate numeric value equals the whole-degree Celsius value encoded in the raw METAR; exact equality only, no scientific agreement tolerance applied.", observed)
    if variable == "rhum":
        if not temp_group or expected is None:
            return "NOT_ASSESSABLE", "METAR temperature/dewpoint pair or candidate value is absent.", None
        temperatures = []
        for token in temp_group.groups():
            temperatures.append(-int(token[1:]) if token.startswith("M") else int(token))
        if temperatures[0] == temperatures[1]:
            derived = 100.0
        else:
            def es(value: float) -> float:
                return 6.112 * math.exp((17.67 * value) / (value + 243.5))
            derived = min(100.0, max(0.0, 100.0 * es(temperatures[1]) / es(temperatures[0])))
        compatible = expected == derived
        return ("DERIVED_VALUE_COMPATIBLE_NOT_DIRECT_RH" if compatible else "DERIVED_VALUE_MISMATCH_NOT_DIRECT_RH",
                "METAR contains temperature/dewpoint, not direct RH; derived numerical value is descriptive and is not an independent direct measurement.", derived)
    if variable == "pres":
        qnh = re.search(r"\bQ(\d{4})\b", raw_message)
        if not qnh:
            return "NOT_ASSESSABLE", "METAR QNH group is absent; pressure semantics need explicit matching.", None
        return "NOT_COMPARABLE_PRESSURE_DEFINITION", "METAR QNH is altimeter setting; candidate pressure definition was not established as equivalent.", int(qnh.group(1))
    if variable == "wspd":
        wind = re.search(r"\b\d{3}(\d{2,3})(?:G\d{2,3})?KT\b", raw_message)
        if not wind:
            return "NOT_ASSESSABLE", "METAR wind group is absent.", None
        knots = int(wind.group(1))
        return "NOT_COMPARABLE_TIME_OR_VALUE", "METAR wind is encoded in knots; candidate linkage has no exact report at this event timestamp.", knots
    return "NOT_COMPARABLE", "No registered METAR variable interpretation is defined.", None


def parse_daily_files() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    log = json.loads(IEM_LOG.read_text(encoding="utf-8"))
    frames, manifest = [], []
    for entry in log["request_entries"]:
        path = OUT / entry["saved_file"]
        body = path.read_bytes()
        if digest(path) != entry["sha256"]:
            raise ValueError(f"response hash mismatch: {path.name}")
        rows = []
        if entry["complete_response"] and entry["http_status"] == 200:
            try:
                frame = pd.read_csv(path, dtype=str, keep_default_na=False)
                if {"station", "valid", "metar"}.issubset(frame.columns):
                    rows = frame.to_dict(orient="records")
            except pd.errors.EmptyDataError:
                rows = []
        for index, row in enumerate(rows, start=2):
            row["source_file"] = path.name
            row["source_line_number"] = index
            frames.append(row)
        manifest.append({"source_id": "IEM_VILD_METAR_ARCHIVE",
                         "source_organization": "Iowa State University Iowa Environmental Mesonet",
                         "source_product": "ASOS/METAR historical archive; raw metar field",
                         "source_url": entry["request_url"], "requested_station": "VILD",
                         "requested_utc_date": entry["requested_date_utc"],
                         "requested_variable": "metar", "timestamp_timezone": "UTC query",
                         "retrieved_at_utc": entry.get("retrieved_at_utc"),
                         "response_status": entry["http_status"],
                         "complete_response": entry["complete_response"],
                         "observation_rows": len(rows), "response_bytes": len(body),
                         "sha256": entry["sha256"], "file": path.name,
                         "record_origin": "ARCHIVED_RAW_MESSAGE_NO_PROVIDER_ID" if rows else "NO_OBSERVATION_ROWS_RETURNED",
                         "provider_report_id": "NOT_PROVIDED",
                         "access_limitation": "Downstream multisource archive; source may include Unidata IDD, NOAA NCEI ISD, and MADIS; very little QC."})
    data = pd.DataFrame(frames, columns=["station", "valid", "metar", "source_file", "source_line_number"])
    if not data.empty:
        data["valid_timezone"] = "UTC per explicit IEM request parameter tz=UTC"
        data["provider_record_id"] = "NOT_PROVIDED"
        data["record_origin"] = "ARCHIVED_RAW_MESSAGE_NO_PROVIDER_ID"
        data["lineage_classification"] = UNKNOWN
        data["report_fingerprint_local"] = [record_fingerprint(r.station, r.valid, r.metar)
                                             for r in data.itertuples(index=False)]
    return data, manifest


def main() -> None:
    if not OUT.is_dir():
        raise FileNotFoundError("Phase 11 acquisition directory not found")
    expected = ["PHASE11_ACQUISITION_REPORT.md", "source_access_register.csv",
                "original_observation_manifest.csv", "parsed_archive_observations.csv",
                "PHASE11_INPUT_MANIFEST.csv",
                "station_lineage_register.csv", "instrument_lineage_register.csv",
                "candidate_event_register.csv", "candidate_report_linkage.csv",
                "event_adjudication_register.csv", "evidence_provenance_audit.csv",
                "data_quality_audit.csv", "iem_failed_attempt_log.json",
                "acquisition_blockers.md", "PHASE11_DECISION.md",
                "SHA256SUMS.txt"]
    existing = [name for name in expected if (OUT / name).exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite Phase 11 artifacts: {existing}")

    events = pd.read_csv(PH10 / "PHASE10_CANDIDATE_EVENT_REGISTER.csv")
    reports, observation_manifest = parse_daily_files()
    raw_rows = reports[["station", "valid", "metar"]].to_dict(orient="records") if not reports.empty else []
    duplicate_rows = find_duplicate_reports(raw_rows)
    links, adjudications, audits = [], [], []
    event_rows = []
    for _, event in events.iterrows():
        candidate = event.to_dict()
        linked = exact_candidate_link(candidate, reports[["station", "valid", "metar"]] if not reports.empty else pd.DataFrame())
        archive = reports[(reports.valid.astype(str).str[:10] == str(event.timestamp_utc_reproduction)[:10]) &
                          (reports.station.astype(str).str.upper() == "VILD")] if not reports.empty else pd.DataFrame()
        if linked["linkage_status"] == "PROVISIONAL":
            compat, explanation, decoded = metar_variable_check(str(event.variable), event.candidate_value_original,
                                                                 str(linked.get("raw_message", "")))
        else:
            compat, explanation, decoded = "NO_EXACT_REPORT", "No exact station/time/raw-message-time report was available in the retrieved archive.", None
        date = pd.Timestamp(event.timestamp_utc_reproduction).tz_convert("UTC").strftime("%Y-%m-%d")
        links.append({"event_id": event.event_id, "primary_station": event.primary_station,
                      "candidate_timestamp_original": event.timestamp_original,
                      "candidate_timestamp_utc": event.timestamp_utc_reproduction,
                      "candidate_timezone": "UTC timestamp reproduced from Phase 10 local timestamp",
                      "candidate_variable": event.variable, "candidate_value": event.candidate_value_original,
                      "candidate_unit": {"temp":"degC", "rhum":"%", "pres":"hPa", "wspd":"m/s"}.get(event.variable, "UNKNOWN"),
                      "source_organization": "Iowa State University Iowa Environmental Mesonet",
                      "source_dataset": "ASOS/METAR archive", "source_station_id": linked.get("source_station_id", "VILD"),
                      "source_record_id": linked.get("source_record_id", "NOT_AVAILABLE"),
                      "original_report_id": "NOT_PROVIDED_AS_UNIQUE_ID",
                      "report_timestamp_utc": linked.get("source_valid_timestamp", ""),
                      "raw_report_text": linked.get("raw_message", ""),
                      "report_fingerprint_local": linked.get("report_fingerprint", ""),
                      "temporal_offset_seconds": linked.get("temporal_offset_seconds"),
                      "match_rule": linked["link_rule"], "linkage_status": linked["linkage_status"],
                      "record_origin": linked.get("record_origin", "NO_OBSERVATION_ROW"),
                      "lineage_classification": UNKNOWN,
                      "variable_compatibility": compat, "decoded_reference_value": decoded,
                      "quality_control_status": "NOT_PROVIDED_BY_ARCHIVE; raw METAR only",
                      "imputation_status": "NOT_ASSESSABLE_FOR_PHASE03_CANDIDATE; phase lineage remains unresolved",
                      "archive_rows_on_candidate_utc_date": len(archive),
                      "linkage_reason": linked["reason"] + " " + explanation})
        # Phase 08 is the single evidence eligibility policy. Unknown lineage is deliberately ineligible.
        policy = apply_phase08_policy({"lineage_classification": UNKNOWN,
                                       "variable": {"temp":"temperature", "rhum":"relative_humidity",
                                                    "pres":"pressure", "wspd":"wind_speed"}.get(str(event.variable), str(event.variable)),
                                       "primary_value": event.candidate_value_original,
                                       "reference_value": decoded,
                                       "primary_unit": {"temp":"degC", "rhum":"%", "pres":"hPa", "wspd":"m/s"}.get(event.variable),
                                       "reference_unit": {"temp":"degC", "rhum":"%", "pres":"hPa", "wspd":"knot"}.get(event.variable),
                                       "candidate_timestamp": event.timestamp_utc_reproduction,
                                       "reference_timestamp": linked.get("source_valid_timestamp"),
                                       "qc_status": "NOT_PROVIDED", "is_imputed": None})
        event_rows.append({**candidate, "phase11_linkage_status": linked["linkage_status"],
                           "phase11_variable_compatibility": compat,
                           "adjudication_status": "NOT_ADJUDICATED"})
        adjudications.append({"event_id": event.event_id,
                              "original_anomaly_evidence": "Phase 03/10 model-candidate indication only; candidate row has unresolved source/imputation lineage.",
                              "independent_reference_evidence": "IEM downstream raw METAR archive queried on candidate UTC date; exact report linkage is provisional for two events and unavailable for six.",
                              "evidence_provenance": "IEM archive is multi-source; no provider-issued report IDs; potential overlap with NOAA NCEI ISD and candidate METAR lineage is unresolved.",
                              "station_instrument_lineage_confidence": "LOW/UNKNOWN; exact VILD sensor history unavailable.",
                              "temporal_alignment_quality": "EXACT_STATION_TIME_RAW_MESSAGE_TIME" if linked["linkage_status"] == "PROVISIONAL" else "NO_EXACT_LINK",
                              "measurement_comparability": compat,
                              "qc_limitations": "Archive offers raw report text and very little QC; no independent QC status or candidate QC record.",
                              "human_or_authoritative_adjudication_evidence": "NONE",
                              "adjudication_status": "NOT_ADJUDICATED", "adjudication_label": "",
                              "rationale": "No independent station evidence or documented human adjudication. A same-station archive copy cannot establish a regional event or sensor failure.",
                              "unresolved_uncertainties": "Candidate may be model-filled; source report identity, independent source chain, instrument/site history, and corroborating station observations are unresolved."})
        audits.append({"event_id": event.event_id, "reference_source": "IEM_VILD_METAR_ARCHIVE",
                       "lineage_classification": UNKNOWN,
                       "phase08_comparison_eligibility": policy["comparison_eligibility"],
                       "phase08_outcome": policy["outcome"], "phase08_reason": policy["comparison_reason"],
                       "event_report_linkage": linked["linkage_status"],
                       "independent_vote_count": 0,
                       "missing_is_conflict": False,
                       "limitation": "Same primary station archive / unknown underlying provider; no independent corroboration or event label."})

    station_lineage = [
        {"station_id":"VILD0", "official_identifier":"ICAO VILD", "name":"Ludhiana Airport station record",
         "latitude":"30.8547", "longitude":"75.9526", "elevation_m":"254.2",
         "verified_facts":"Phase 05 crosswalk identifies airport-level association; AAI aerodrome METAR service documented.",
         "metadata_gaps":"Exact sensor coordinates, relocation history, instrument make/serial/calibration, and observer/operator epochs not resolved.",
         "independence_status":"Not independent of candidate; primary station record."},
        {"station_id":"WMO-42099", "official_identifier":"WIGOS 0-20000-0-42099", "name":"Ludhiana",
         "latitude":"30.8666667", "longitude":"75.9333333", "elevation_m":"255",
         "verified_facts":"WMO OSCAR metadata snapshot says fixed land station, established 1982-04-03, operational, IMD listed as organization.",
         "metadata_gaps":"No historical coordinates, sensor/instrument history, or observation series acquired; no authoritative VILD0 alias.",
         "independence_status":"Unknown; proximity and name do not prove equivalence or independent site."},
        {"station_id":"WMO-42101", "official_identifier":"WIGOS 0-20000-0-42101", "name":"Patiala",
         "latitude":"30.3333333", "longitude":"76.4666667", "elevation_m":"251",
         "verified_facts":"WMO OSCAR metadata snapshot says fixed land station, established 1948-04-10, operational, IMD listed as organization.",
         "metadata_gaps":"No historical coordinates, sensor/instrument history, or original IMD observation series acquired.",
         "independence_status":"Distinct station/report record, but instrument/operator/calibration independence not proven."},
    ]
    instruments = [{"station_id": row["station_id"], "instrument_id": "NOT_AVAILABLE",
                    "instrument_type": "NOT_RESOLVED_FROM_REVIEWED_AUTHORITATIVE_METADATA",
                    "measurement_method": "UNKNOWN", "installation_or_replacement_history": "NOT_FOUND",
                    "calibration_history": "NOT_FOUND", "observation_schedule": "Unknown for complete historical period",
                    "operator_or_responsible_organization": "IMD listed in OSCAR for WMO 42099/42101; historical epochs and VILD responsibility not fully established",
                    "source_reviewed": "WMO OSCAR snapshot, Phase 05 crosswalk, NOAA GHCNh station metadata, IEM archive docs",
                    "confidence": "LOW/UNKNOWN", "limitation": "Station identity metadata do not establish physical instrument independence."}
                   for row in station_lineage]

    source_access = [
        {"source_id":"IEM_VILD_METAR_BROAD_QUERY", "organization":"Iowa State University Iowa Environmental Mesonet",
         "url":"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=VILD&data=metar&sts=2025-04-18T00:00:00Z&ets=2026-01-29T00:00:00Z&tz=UTC&format=onlycomma",
         "access_method":"One broad public GET covering candidate period; read failed on chunked response. Retried as eight daily UTC queries.",
         "retrieved_at_utc":"NOT_CAPTURED_BY_FAILED_CLIENT; Phase 11 session date 2026-11-19 Asia/Kolkata",
         "requested_stations":"VILD", "requested_period":"2025-04-18 through 2026-01-28 UTC",
         "variables_resolution":"Raw METAR text requested.", "authentication_license":"Public endpoint; rate limit/throttle applies.",
         "result":"FAILED_INCOMPLETE_CHUNKED_RESPONSE", "observation_records":0,
         "limitation":"Client reported IncompleteRead after 55,956 response bytes; response body not saved, so no observation rows were used. See iem_failed_attempt_log.json."},
        {"source_id":"IMD_DSP_HISTORICAL", "organization":"India Meteorological Department, National Data Centre Pune",
         "url":"https://dsp.imdpune.gov.in/", "access_method":"Official portal and station/data categories inspected; no account/request submitted.",
         "retrieved_at_utc":"2026-11-19", "requested_stations":"WMO 42099, WMO 42101, ICAO VILD", "requested_period":"Candidate dates 2025-04-18 through 2026-01-28",
         "variables_resolution":"Hourly temperature, RH, wind, pressure, rainfall were listed for selected stations; station-specific holdings not verified.",
         "authentication_license":"Account enrollment/login, station/date availability and estimate; terms, certificate, payment may apply.",
         "result":"NOT_ACQUIRED", "observation_records":0, "limitation":"Exact availability is only established after formal request/availability check."},
        {"source_id":"IMD_MC_CHANDIGARH", "organization":"India Meteorological Department Meteorological Centre Chandigarh",
         "url":"https://mausam.imd.gov.in/chandigarh/docs/data-procedure.pdf", "access_method":"Official procedure PDF inspected; no email/request sent.",
         "retrieved_at_utc":"2026-11-19", "requested_stations":"Ludhiana / Patiala; precise station IDs to confirm with IMD", "requested_period":"Candidate dates / original archive window",
         "variables_resolution":"Hourly temperature, RH, wind, station/MSL pressure, rainfall available only at selected stations; other variables/products listed.",
         "authentication_license":"Formal data request, purpose, cost estimate, certificate of undertaking, payment/DD/GST; terms restrict use to stated purpose.",
         "result":"NOT_ACQUIRED", "observation_records":0, "limitation":"Need researcher/institution letterhead, exact request and authorization/payment decision."},
        {"source_id":"IMD_PUBLIC_API", "organization":"India Meteorological Department",
         "url":"https://api.imd.gov.in/public/api_reference.html", "access_method":"Public API documentation inspected; no API data downloaded.",
         "retrieved_at_utc":"2026-11-19", "requested_stations":"Current city/station services", "requested_period":"Current/recent only per described endpoints",
         "variables_resolution":"Current weather and forecasts; API reference does not establish historical raw archive coverage for Phase 03 events.",
         "authentication_license":"Public portal describes account/API services; historical scope unverified.",
         "result":"DOCUMENTATION_ONLY", "observation_records":0, "limitation":"Not a demonstrated historical candidate-date archive."},
        {"source_id":"NOAA_AWC_CURRENT_API", "organization":"NOAA Aviation Weather Center",
         "url":"https://aviationweather.gov/data/api/", "access_method":"Official API docs inspected; candidate dates not queried because outside available period.",
         "retrieved_at_utc":"2026-11-19", "requested_stations":"ICAO VILD", "requested_period":"Candidate dates 2025–2026",
         "variables_resolution":"Raw METAR and decoded outputs, database only previous 30 days.",
         "authentication_license":"Public API, query/rate limits apply.", "result":"HISTORICAL_WINDOW_EXPIRED", "observation_records":0,
         "limitation":"Candidate dates are older than documented 30-day query window."},
        {"source_id":"NOAA_NCEI_SRRS", "organization":"NOAA National Centers for Environmental Information / NWS SRRS",
         "url":"https://www.ncei.noaa.gov/products/weather-climate-models/service-records-retention", "access_method":"Official product page and AIRS order form inspected; order not submitted.",
         "retrieved_at_utc":"2026-11-19", "requested_stations":"ICAO VILD not submitted", "requested_period":"Candidate dates 2025–2026 not submitted",
         "variables_resolution":"Historical SRRS text/bulletin archive includes METAR-formatted surface weather products; coverage for VILD/bulletin/date unverified.",
         "authentication_license":"AIRS order requires station/bulletin/date selection and email; max 5 days per order within same month.",
         "result":"ACCESS_ROUTE_IDENTIFIED_NOT_ACQUIRED", "observation_records":0,
         "limitation":"SRRS stores NWS products; international VILD bulletin availability and source completeness must be confirmed before ordering."},
        {"source_id":"IEM_VILD_METAR_ARCHIVE", "organization":"Iowa State University Iowa Environmental Mesonet",
         "url":IEM_BASE, "access_method":"Public GET to documented ASOS/METAR archive; preserved exact raw HTTP response per candidate UTC date.",
         "retrieved_at_utc":"See iem_retrieval_log.json (UTC)", "requested_stations":"VILD", "requested_period":"Eight complete UTC dates matching Phase 10 events",
         "variables_resolution":"Raw METAR text and archive observation timestamp; report set is not complete original-provider archive.",
         "authentication_license":"Public endpoint; site requests one-second throttle and documents as-is records.",
         "result":"PARTIAL_ARCHIVE_ROWS_ACQUIRED", "observation_records":len(reports),
         "limitation":"Archive is downstream multisource (Unidata IDD, NCEI ISD, MADIS); raw messages have no provider-issued unique IDs; very little QC."},
        {"source_id":"NOAA_GHCNH_PHASE07_REUSE", "organization":"NOAA NCEI GHCNh v1.1.0 harmonized product",
         "url":"https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly", "access_method":"Existing Phase 07 records reviewed as prior evidence only; not reacquired/reprocessed.",
         "retrieved_at_utc":"Phase 07 2026-11-18", "requested_stations":"INI0000VILD, INM00042101", "requested_period":"2025–2026 existing station-year files",
         "variables_resolution":"Harmonized hourly/sub-hourly station reports depending element/source.",
         "authentication_license":"Public bulk files; source component and record-level organization not fully resolved.",
         "result":"REUSED_PRIOR_PHASE_ONLY", "observation_records":0,
         "limitation":"Explicitly not counted as newly acquired independent observation data in Phase 11."},
        {"source_id":"WMO_OSCAR_PHASE10_REUSE", "organization":"World Meteorological Organization OSCAR/Surface",
         "url":"https://oscar.wmo.int/surface/", "access_method":"Phase 10 sanitized station metadata reused; no new Phase 11 query.",
         "retrieved_at_utc":"Phase 10 2026-11-18", "requested_stations":"WMO 42099, WMO 42101", "requested_period":"Current metadata snapshot",
         "variables_resolution":"Station metadata only, no weather observation series.", "authentication_license":"Public metadata endpoint.",
         "result":"METADATA_REUSED_NOT_OBSERVATIONS", "observation_records":0,
         "limitation":"No instrument deployments, calibration history, or raw observations."},
    ]

    reviewed_at_utc = datetime.now(timezone.utc).isoformat()
    for row in source_access:
        row["investigated_at_utc"] = reviewed_at_utc

    write_csv(OUT / "source_access_register.csv", source_access)
    write_csv(OUT / "original_observation_manifest.csv", observation_manifest)
    input_paths = [PH10 / "PHASE10_CANDIDATE_EVENT_REGISTER.csv",
                   PH10 / "PHASE10_REPRODUCIBILITY_MANIFEST.json",
                   PH10 / "PHASE10_OSCAR_STATION_METADATA.json",
                   ROOT / "outputs/phase05_primary_station_verification/vild0_identity_crosswalk.csv",
                   ROOT / "outputs/phase07_independent_evidence/external_reference_data/ghcnh-station-list.csv",
                   ROOT / "src/weather_research/e3_evidence_policy.py"]
    input_manifest = [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path),
                       "bytes": path.stat().st_size,
                       "role": ("fixed Phase 10 event selection" if path.name == "PHASE10_CANDIDATE_EVENT_REGISTER.csv" else
                               "unchanged Phase 08 evidence policy" if path.name == "e3_evidence_policy.py" else
                               "prior-phase station identity/provenance context")}
                      for path in input_paths]
    write_csv(OUT / "PHASE11_INPUT_MANIFEST.csv", input_manifest)
    parsed = reports.copy()
    if not parsed.empty:
        parsed["valid_timestamp_original"] = parsed["valid"]
        parsed["valid_timestamp_utc"] = pd.to_datetime(parsed["valid"], utc=True).astype(str)
        parsed["raw_metar_original"] = parsed["metar"]
        parsed["source_provider_record_id"] = "NOT_PROVIDED"
        parsed["derived_record_fingerprint"] = parsed["report_fingerprint_local"]
    write_csv(OUT / "parsed_archive_observations.csv", parsed.to_dict(orient="records"))
    write_csv(OUT / "station_lineage_register.csv", station_lineage)
    write_csv(OUT / "instrument_lineage_register.csv", instruments)
    write_csv(OUT / "candidate_event_register.csv", event_rows)
    write_csv(OUT / "candidate_report_linkage.csv", links)
    write_csv(OUT / "event_adjudication_register.csv", adjudications)
    write_csv(OUT / "evidence_provenance_audit.csv", audits)

    quality = [
        {"scope":"IEM archive responses", "measure":"candidate_dates_queried", "value":8,
         "status":"VERIFIED", "limitation":"One complete UTC day per preselected candidate date; no arbitrary matching window."},
        {"scope":"IEM archive responses", "measure":"raw_METAR_rows_returned", "value":len(reports),
         "status":"VERIFIED", "limitation":"Downstream multisource archive; not all reports may be present."},
        {"scope":"IEM archive responses", "measure":"candidate_dates_with_any_rows", "value":int(sum((reports.valid.astype(str).str[:10] == d).any() for d in sorted(set(reports.valid.astype(str).str[:10])))) if not reports.empty else 0,
         "status":"VERIFIED", "limitation":"Coverage is date-level availability only."},
        {"scope":"IEM archive responses", "measure":"duplicate_station_time_rows", "value":int(reports.duplicated(["station", "valid"]).sum()) if not reports.empty else 0,
         "status":"VERIFIED", "limitation":"Duplicate test is exact station+archive valid timestamp within retrieved files."},
        {"scope":"IEM archive responses", "measure":"duplicate_raw_report_fingerprints", "value":len(duplicate_rows),
         "status":"VERIFIED", "limitation":"Locally derived fingerprints, not provider IDs."},
        {"scope":"candidate linkage", "measure":"provisional_exact_report_links", "value":sum(x["linkage_status"] == "PROVISIONAL" for x in links),
         "status":"VERIFIED", "limitation":"Provisional archive-copy matches only; lineage unknown."},
        {"scope":"candidate linkage", "measure":"confirmed_original_provider_report_links", "value":0,
         "status":"VERIFIED", "limitation":"No provider-issued report IDs/direct-provider responses."},
        {"scope":"candidate events", "measure":"independently_adjudicated_events", "value":0,
         "status":"VERIFIED", "limitation":"No independent station records or human/authoritative adjudication."},
        {"scope":"candidate value quality", "measure":"archive_quality_flag", "value":"NOT_PROVIDED",
         "status":"VERIFIED", "limitation":"IEM describes its archive as as-is with very little QC; raw METAR text retained."},
        {"scope":"candidate value quality", "measure":"candidate_imputation_status", "value":"UNKNOWN",
         "status":"VERIFIED", "limitation":"Phase 03 candidate-to-source retrieval linkage remains unresolved."},
    ]
    write_csv(OUT / "data_quality_audit.csv", quality)

    failed_attempt = {"source_id":"IEM_VILD_METAR_BROAD_QUERY",
                      "request_url":source_access[0]["url"],
                      "attempted_at_utc":"NOT_CAPTURED_BY_FAILED_CLIENT; Phase 11 session date 2026-11-19 Asia/Kolkata",
                      "error":"http.client.IncompleteRead: 55,956 response bytes read before chunked response ended",
                      "response_body_preserved":False,
                      "usable_observation_rows":0,
                      "handling":"No partial response was parsed or treated as observations; request was replaced by eight complete UTC-day requests whose raw responses are preserved separately."}
    (OUT / "iem_failed_attempt_log.json").write_text(json.dumps(failed_attempt, indent=2) + "\n", encoding="utf-8")

    blocking_md = """# Phase 11 acquisition blockers

1. **Original IMD station observations:** The IMD Data Service Portal and Meteorological Centre Chandigarh both document historical observation access, including hourly products for selected stations. No researcher account, availability request, data request, undertaking, or payment was submitted. Next action: the researcher/institution must provide the purpose and desired dates/stations to IMD Data Supply, verify station-specific availability, review terms/cost, and authorize the request and any required payment.
2. **Authorized VILD report archive:** NOAA AWC's live API is limited to recent data. NCEI SRRS/AIRS accepts date/bulletin orders, but its form limits a request to five days within a month and the availability of international VILD bulletins was not confirmed. Next action: confirm relevant bulletin IDs and submit properly scoped orders for event months if authorized.
3. **IEM coverage and lineage:** IEM returned 31 raw messages on four candidate dates. It is an as-is, multi-source archive, with no provider unique report IDs. Two candidate event links are provisional; six have no exact link in the queried daily coverage. Next action: obtain the direct reporting-service archive or a provider-backed report log and cross-check any matching text.
4. **Candidate source provenance:** Phase 03 candidate rows have no report identifiers and may be model-filled. Exact raw-message matches do not establish the candidate data's retrieval route or provider lineage. Next action: reproduce the original Meteostat request metadata and map each candidate row to a provider-issued/raw report identifier, if available.
5. **Station/instrument history:** WMO metadata identifies station records and organizations but not historical sensor coordinates, site moves, instruments, replacements, calibrations, or observation practices. Next action: obtain official station history and instrument/QC documentation from IMD/Airport Authority.
6. **Independent adjudication:** No independent event/control labels, observer review, or authoritative event adjudication were available. Next action: preregister a blinded review protocol with meteorological reviewers and independent data sources before assigning any event outcome.
"""
    (OUT / "acquisition_blockers.md").write_text(blocking_md, encoding="utf-8")

    decision_text = f"""# Phase 11 decision

**Decision: `INSUFFICIENT_INDEPENDENT_DATA`**

Phase 11 acquired {len(reports)} archived raw METAR message rows from Iowa State IEM on five of eight queried UTC dates. These are downstream archive copies from a multi-source archive; they are not treated as direct-provider exports, independent station votes, or ground truth. Two events have provisional exact station/time/raw-message-time links, including one temperature value compatible with the report's whole-degree Celsius group. A second event has a report link but only a derived RH implication from the METAR temperature/dewpoint pair; it is not direct RH corroboration. The other six events have no exact report link in the queried archive coverage. No provider-issued record IDs were returned.

No original IMD station observation series, direct NCEI SRRS order, independent station reference series, or human/authoritative adjudication was acquired. All eight events remain `NOT_ADJUDICATED`. The Phase 08 evidence policy returns unavailable/ineligible for E3 voting because the archive lineage is unknown; missing rows are not treated as conflict. The dataset is insufficient for controlled E3 validation.

Primary blocker: **independent data lineage and source access**. Secondary blockers: candidate-to-original report identity, instrument/site history, variable comparability/QC, and event adjudication. No numerical agreement threshold or matching tolerance was invented. Event linking used exact station identity, UTC timestamp, and the station/time group in the raw METAR text; no proximity matching was applied.

Phase 11 does not change the Phase 10 candidate selection, Phase 08 evidence policy, model, baseline, E1/E2/E4, primary station, or classifier. No fault probability or definitive anomaly label is assigned.
"""
    (OUT / "PHASE11_DECISION.md").write_text(decision_text, encoding="utf-8")
    report = f"""# Phase 11 — Original Observations Acquisition & Independent Event Adjudication

**Decision:** `INSUFFICIENT_INDEPENDENT_DATA`  
**Branch/base:** `feature/phase11-original-observations-event-adjudication` from `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`  
**Acquisition result:** {len(reports)} archived raw METAR message rows, five of eight candidate dates; zero original IMD observations.

## Acquisition and provenance

The [IMD Data Service Portal](https://dsp.imdpune.gov.in/) documents access to historical observations through enrolment/login, data availability and cost estimate, and request workflow. IMD Meteorological Centre Chandigarh's [official data procedure](https://mausam.imd.gov.in/chandigarh/docs/data-procedure.pdf) documents hourly temperature, humidity, wind, pressure and rainfall for selected stations, with formal request, purpose, undertaking and payment procedures. No account was used, no availability request or email was sent, and no charges or undertaking were initiated. The precise next action is for the researcher/institution to submit a scoped request for WMO 42099 and 42101 (and ask IMD to resolve any VILD observing-station mapping), for the Phase 03 candidate dates plus a scientifically preregistered surrounding period, listing requested elements, units, QC/provenance metadata, station histories, and intended research use; review IMD's availability, terms and estimate before authorizing any paid order.

The [NOAA Aviation Weather Center API](https://aviationweather.gov/data/api/) is documented for raw METAR, but its observation database covers only the previous 30 days. NOAA NCEI [SRRS](https://www.ncei.noaa.gov/products/weather-climate-models/service-records-retention)/[AIRS](https://www.ncei.noaa.gov/has/HAS.FileAppRouter?datasetname=9957ANX&outdest=FILE&subqueryby=STATION) provides an official order route for text products and its current form limits each order to five days within the same month. The SRRS archive retains NWS products; this review did not verify that VILD international reports are present in a selected bulletin. No order was submitted. The exact candidate-to-raw-report acquisition can proceed by confirming VILD bulletin availability with NCEI and ordering each necessary short period if authorized.

Iowa State University's [IEM archive](https://mesonet.agron.iastate.edu/request/download.phtml?network=AR__ASOS) provides an unauthenticated historical ASOS/METAR query and supports raw report text. Its [archive documentation](https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?help=) says the archive is an as-is, multi-source collection (including Unidata IDD, NOAA NCEI ISD, and MADIS) with very little quality control; the returned `valid` time is the observation time, and no unique provider record identifier is returned. A broad multi-month request failed while reading a chunked response; no partial response from that failed attempt was retained as an observation dataset. Eight separate, complete UTC-day queries were then made for the exact pre-existing Phase 10 candidate dates. Raw responses, including three complete header-only responses, were preserved unchanged. The result was {len(reports)} raw METAR rows across five dates, with no rows for the other three dates. Per-response retrieval timestamps, URLs, statuses, byte counts and hashes are in `iem_retrieval_log.json` and `original_observation_manifest.csv`.

## Candidate event links

The eight Phase 10 candidate IDs/timestamps were reused unchanged. An exact link requires VILD station identity, the exact UTC archive timestamp, and a matching day/hour/minute group in the raw report message; no arbitrary time tolerance is used. **Two links are provisional archive-copy matches** and **six are unavailable in the queried IEM dates**. The provisional link on 2025-12-02 05:00 UTC has report temperature 19 °C matching the candidate's reported precision. The 2025-12-22 04:00 UTC event has a raw report whose temperature and dewpoint are both 8 °C, so 100% RH is only a derived implication, not a direct humidity observation. This is not independent evidence: candidate source lineage, archive component source, and provider IDs are unresolved. All Phase 08 eligibility results remain ineligible/unavailable for independent voting.

## Station and instrument lineage

The reused [WMO OSCAR/Surface](https://oscar.wmo.int/surface/) snapshot identifies Ludhiana WMO 42099 and Patiala WMO 42101 as fixed land stations with IMD listed as organization. The snapshot gives coordinates/elevation and establishment dates but not historical position changes, instrument identity/replacement/calibration, observer practice, or full operator epochs. The Phase 05 crosswalk verifies VILD0 at the airport-station level and documents the airport meteorological service; it does not establish exact sensor coordinates or complete history, nor does it authoritatively equate VILD0 and WMO 42099. Patiala is a distinct WMO/report record but separate instrumentation and operator independence are not established. Instrument register values are explicitly unavailable, not inferred.

## Adjudication and sufficiency

All eight event statuses are `NOT_ADJUDICATED`. No independent reference station series, original IMD records, independently identified direct-provider METAR source record, or documented blinded human review was available. A same-station report copy cannot distinguish unusual regional weather from a station-specific observation issue. The outputs preserve missing evidence separately from conflicting evidence; there are zero independent votes and zero fault labels/probabilities.

Primary decision blocker is source lineage/access; event adjudication and instrument/site history also fail. Phase 11 does not establish E3 validation. See `acquisition_blockers.md` for the exact next actions. Phase 08 was reused unchanged; model, baseline, E1/E2/E4, primary station, and classifier behavior are untouched.

## Reproducibility

Raw IEM CSV files are unchanged. `parsed_archive_observations.csv` is a separate parsed representation retaining the original METAR text and source file/line pointers. `PHASE11_INPUT_MANIFEST.csv` hashes the fixed Phase 10 event selection, Phase 08 policy, and reused station-identity context. `SHA256SUMS.txt` hashes every final file in this output directory except itself. Phase 04–10 ignored outputs and inherited dirty files were preserved. No commit, push, or merge was made.
"""
    (OUT / "PHASE11_ACQUISITION_REPORT.md").write_text(report, encoding="utf-8")

    # Every Phase 11 output except the checksum list itself is hashed after final writes.
    sums = []
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            sums.append(f"{digest(path)}  {path.relative_to(ROOT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print(json.dumps({"archive_rows": len(reports),
                      "raw_candidate_links": sum(x["linkage_status"] == "PROVISIONAL" for x in links),
                      "unavailable_links": sum(x["linkage_status"] == "UNAVAILABLE" for x in links),
                      "adjudicated_events": 0, "decision": "INSUFFICIENT_INDEPENDENT_DATA",
                      "artifact_count": len(sums)}, indent=2))


if __name__ == "__main__":
    main()
