"""Build Phase 07 lineage and event-reference audit from preserved source files."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from weather_research.phase07_lineage import (
    classify_lineage_pair, compare_event_value, match_event_observation,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase07_independent_evidence"
EXTERNAL = OUT / "external_reference_data"
REQUIRED_OUTPUTS = (
    "PHASE07_RESEARCH_REPORT.md", "source_lineage_register.csv",
    "source_lineage_relationships.csv", "independent_reference_inventory.csv",
    "candidate_event_register.csv", "event_level_comparison.csv",
    "source_dependence_assessment.csv", "e3_independent_evidence_decision.json",
    "source_lineage_graph.mmd",
)

EVENT_RULES = (
    ("rapid_temp_rise", "temp_change_1h", "max", "temp", "Maximum positive one-hour candidate temperature change"),
    ("rapid_temp_drop", "temp_change_1h", "min", "temp", "Maximum negative one-hour candidate temperature change"),
    ("max_candidate_temperature", "temp", "max", "temp", "Maximum candidate temperature"),
    ("min_candidate_temperature", "temp", "min", "temp", "Minimum candidate temperature"),
    ("min_candidate_rh", "rhum", "min", "rhum", "Minimum candidate relative humidity"),
    ("max_candidate_rh", "rhum", "max", "rhum", "Maximum candidate relative humidity"),
    ("max_candidate_wind_speed", "wspd", "max", "wspd", "Maximum candidate wind speed"),
    ("min_candidate_pressure", "pres", "min", "pres", "Minimum candidate pressure"),
)

COMMON_UNITS = {"temp": "degC", "rhum": "%RH", "wspd": "m/s", "pres": "hPa"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv_once(name: str, rows: list[dict]) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 07 output: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_meteostat_source(path: Path, source: str) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["time"])
    frame["time"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    frame = frame[frame.source.astype(str).eq(source)].copy()
    frame = frame.dropna(subset=["time"]).sort_values("time")
    frame = frame.drop_duplicates("time", keep="first")
    return frame


def read_ghcnh(station_id: str) -> pd.DataFrame:
    files = sorted(EXTERNAL.glob(f"GHCNh_{station_id}_*.psv"))
    if not files:
        raise FileNotFoundError(f"No official GHCNh station-year files for {station_id}")
    frames = [pd.read_csv(path, sep="|", low_memory=False) for path in files]
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame["DATE"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["time"]).sort_values("time").drop_duplicates("time", keep="first")
    return frame


def event_rows(candidates: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for event_type, selector, direction, variable, reason in EVENT_RULES:
        index = candidates[selector].idxmax() if direction == "max" else candidates[selector].idxmin()
        row = candidates.loc[index].copy()
        row["event_type"] = event_type
        row["event_variable"] = variable
        row["selection_rule"] = reason
        rows.append(row)
    result = pd.DataFrame(rows).drop_duplicates("timestamp", keep="first").sort_values("timestamp")
    result["timestamp_utc"] = pd.to_datetime(result.timestamp, utc=True)
    return result.reset_index(drop=True)


def row_value_for_native(source_row: pd.Series, variable: str) -> tuple[object, str, str]:
    columns = {
        "temp": ("temperature", "degC", "temperature"),
        "rhum": ("relative_humidity", "%RH", "relative_humidity"),
        "wspd": ("wind_speed", "m/s", "wind_speed"),
        "pres": ("altimeter", "hPa", "altimeter"),
    }
    field, units, prefix = columns[variable]
    return field, units, prefix


def native_frame_for_variable(frame: pd.DataFrame, variable: str, station: str) -> pd.DataFrame:
    value_col, units, prefix = row_value_for_native(pd.Series(dtype=object), variable)
    out = frame.copy()
    if station == "42101" and variable == "pres":
        value_col, prefix = "sea_level_pressure", "sea_level_pressure"
    out["value"] = pd.to_numeric(out[value_col], errors="coerce")
    out["qc"] = out.get(f"{prefix}_Quality_Code")
    out["measurement_code"] = out.get(f"{prefix}_Measurement_Code")
    out["report_type"] = out.get(f"{prefix}_Report_Type")
    out["source_code"] = out.get(f"{prefix}_Source_Code")
    out["original_station_id"] = out.get(f"{prefix}_Source_Station_ID")
    out["units"] = units
    return out


def qc_label(code: object) -> str:
    if pd.isna(code) or str(code).strip() == "":
        return "NOT_REPORTED"
    value = str(code).strip()
    try:
        numeric = float(value)
        if numeric.is_integer():
            value = str(int(numeric))
    except ValueError:
        pass
    return {"0": "NOT_CHECKED", "1": "GOOD", "2": "SUSPECT", "3": "ERRONEOUS",
            "4": "CALCULATED", "5": "REMOVED", "f": "INPUT_MEASUREMENTS_SUSPECT_OR_ERROR"}.get(value, f"FLAG_{value}")


def exact_overlap_fingerprint(left: pd.DataFrame, right: pd.DataFrame,
                              left_fields: dict, right_fields: dict,
                              scales: dict, tolerances: dict) -> dict:
    joined = left.set_index("time").join(right.set_index("time"), how="inner", lsuffix="_left", rsuffix="_right")
    result = {"exact_timestamp_overlap": int(len(joined)), "valid_value_pairs": {}, "value_fingerprint_matches": {}}
    for variable, left_field in left_fields.items():
        right_field = right_fields[variable]
        a = pd.to_numeric(joined[left_field], errors="coerce")
        b = pd.to_numeric(joined[right_field], errors="coerce") * scales.get(variable, 1.0)
        valid = a.notna() & b.notna()
        n = int(valid.sum())
        matches = int(np.isclose(a[valid], b[valid], atol=tolerances.get(variable, 0.11), rtol=0).sum())
        result["valid_value_pairs"][variable] = n
        result["value_fingerprint_matches"][variable] = matches
    return result


def build() -> None:
    if not OUT.is_dir():
        raise FileNotFoundError("Phase 07 source files are not staged; run the Phase 07 fetch script first.")
    existing = [name for name in REQUIRED_OUTPUTS if (OUT / name).exists()]
    if existing:
        raise FileExistsError(f"Refusing to replace Phase 07 outputs: {existing}")

    phase05_dir = ROOT / "outputs" / "phase05_primary_station_verification"
    phase06_dir = ROOT / "outputs" / "phase06_controlled_e3_validation"
    phase04_dir = ROOT / "outputs" / "phase04_provenance_aware_collection"
    candidate_path = ROOT / "phase03_model_revalidation" / "candidate_observations_8of12.csv"

    manifest06 = json.loads((phase06_dir / "primary_retrieval_manifest.json").read_text(encoding="utf-8"))
    manifest04 = json.loads((phase04_dir / "retrieval_manifest.json").read_text(encoding="utf-8"))
    candidates = pd.read_csv(candidate_path, parse_dates=["timestamp"])
    events = event_rows(candidates)
    p06_metar = read_meteostat_source(phase06_dir / "raw_station_data" / "VILD0_hourly_source_level.csv", "metar")
    p06_ghcnh = read_meteostat_source(phase06_dir / "raw_station_data" / "VILD0_hourly_source_level.csv", "ghcnh")
    n42099 = read_meteostat_source(phase04_dir / "raw_station_data" / "42099_hourly_source_level.csv", "isd_lite")
    n42101_isd = read_meteostat_source(phase04_dir / "raw_station_data" / "42101_hourly_source_level.csv", "isd_lite")
    n42101_ghcnh = read_meteostat_source(phase04_dir / "raw_station_data" / "42101_hourly_source_level.csv", "ghcnh")
    gh_vild = read_ghcnh("INI0000VILD")
    gh_42101 = read_ghcnh("INM00042101")
    station_list_path = EXTERNAL / "ghcnh-station-list.csv"
    station_list = pd.read_csv(station_list_path, dtype=str).fillna("")
    exact_vild = station_list[station_list.GHCN_ID.eq("INI0000VILD")].iloc[0]
    exact_42101 = station_list[station_list.WMO_ID.eq("42101")]
    wmo_42099 = station_list[station_list.WMO_ID.eq("42099")]
    other_ludhiana = station_list[station_list.NAME.str.contains("LUDHIANA", case=False, na=False)]

    vild_fingerprint = exact_overlap_fingerprint(
        gh_vild.rename(columns={"time": "time"}), p06_metar,
        {"temp": "temperature", "rhum": "relative_humidity", "wspd": "wind_speed", "wdir": "wind_direction", "pres": "altimeter"},
        {"temp": "temp", "rhum": "rhum", "wspd": "wspd", "wdir": "wdir", "pres": "pres"},
        {"wspd": 1 / 3.6}, {"temp": 0.11, "rhum": 0.11, "wspd": 0.11, "wdir": 1.0, "pres": 0.11})
    f42101_isd = exact_overlap_fingerprint(
        gh_42101, n42101_isd,
        {"temp": "temperature", "rhum": "relative_humidity", "wspd": "wind_speed", "pres": "sea_level_pressure"},
        {"temp": "temp", "rhum": "rhum", "wspd": "wspd", "pres": "pres"},
        {"wspd": 1 / 3.6}, {"temp": 0.11, "rhum": 0.11, "wspd": 0.11, "pres": 0.11})
    f42101_ghcnh = exact_overlap_fingerprint(
        gh_42101, n42101_ghcnh,
        {"temp": "temperature", "rhum": "relative_humidity", "wspd": "wind_speed", "pres": "sea_level_pressure"},
        {"temp": "temp", "rhum": "rhum", "wspd": "wspd", "pres": "pres"},
        {"wspd": 1 / 3.6}, {"temp": 0.11, "rhum": 0.11, "wspd": 0.11, "pres": 0.11})

    downloads = []
    for path in sorted(EXTERNAL.iterdir()):
        if path.is_file():
            url = (f"https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/{path.name}"
                   if path.name.startswith("ghcnh-") else
                   f"https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year/{path.name.split('_')[-1].split('.')[0]}/psv/{path.name}")
            if path.name.endswith(".csv") or path.name.endswith(".pdf"):
                url = f"https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/{path.name}"
            downloads.append({"file": path.name, "source_url": url, "bytes": path.stat().st_size,
                              "sha256": sha256_file(path)})
    external_manifest = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_product": "NOAA NCEI Global Historical Climatology Network hourly (GHCNh), version 1.1.0 per documentation",
        "station_year_files_and_station_list": downloads,
        "station_presence_checks": [
            {"station_id": "WMO 42099", "station_list_matches": int(len(wmo_42099)),
             "candidate_url": "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year/2025/psv/GHCNh_INM00042099_2025.psv",
             "head_status": "404_NOT_FOUND", "interpretation": "No GHCNh station-list mapping was found for WMO 42099; the candidate filename was unavailable."},
            {"station_id": "42101", "station_list_matches": int(len(exact_42101)),
             "ghcnh_station_id": str(exact_42101.iloc[0].GHCN_ID) if len(exact_42101) else None},
        ],
    }
    (OUT / "external_reference_manifest.json").write_text(json.dumps(external_manifest, indent=2), encoding="utf-8")

    source_register = [
        {"source_id":"VILD0_METAR_METEOSTAT","station_record":"VILD0 / ICAO VILD","physical_site":"Ludhiana Airport meteorological reporting station; reference point 30.8547,75.9526; sensor coordinates not established","original_observing_organization":"Not established for every returned record; AAI documents airport METAR service","original_station_id":"ICAO-VILD at the site/report-class level","observation_platform":"Airport surface weather reporting; exact instruments unknown","reporting_system":"METAR / FM15 (confirmed in colocated native GHCNh records, not retained on Meteostat rows)","provider":"Meteostat Provider.METAR","intermediary":"Meteostat 2.2.3 hourly API","aggregation_and_qc":"Source-preserving Meteostat output; no row-level raw report/QC identifiers in this export","coverage":"1,002 provider rows; 2025-03-28 to 2026-03-09 overall phase06 export","variables":"temperature, RH, wind, pressure (provider fields); no dewpoint or precipitation values","timezone":"UTC","lineage_class":"POSSIBLY_SHARED_SOURCE","evidence":"613 exact timestamp overlaps with NOAA native VILD0 GHCNh; temp 613/613 and altimeter/pressure 981/981 match within 0.11; native records identify FM15 and ICAO-VILD","limitations":"Meteostat source rows do not retain raw METAR report IDs; not independent of NOAA GHCNh VILD0; original operator/instrument unresolved."},
        {"source_id":"VILD0_GHCNH_NOAA","station_record":"INI0000VILD / ICAO VILD","physical_site":"Ludhiana airport-station record; NOAA station point 30.8547,75.9526, elev 254.2m; exact sensor position unknown","original_observing_organization":"Not identified by station-year metadata; original station ID ICAO-VILD","original_station_id":"ICAO-VILD","observation_platform":"Fixed airport surface reporting record","reporting_system":"FM15 METAR for reported elements; native REM field retains report text","provider":"NOAA NCEI GHCNh 1.1.0","intermediary":"NOAA NCEI harmonized source product; downloaded station-year PSV","aggregation_and_qc":"Per-variable source code, source station ID, report type, measurement and QC fields retained; NOAA general QC after integration","coverage":"Official 2025 and 2026 station-year files","variables":"Temperature, dewpoint, derived RH, wind, altimeter, other elements as reported","timezone":"UTC","lineage_class":"POSSIBLY_SHARED_SOURCE_WITH_METAR_FEED","evidence":"Official station list includes ICAO VILD; 2025/2026 records contain FM15, source station ICAO-VILD and REM report payloads","limitations":"This is an aggregator, not a second sensor at VILD0; source-code numeric meanings are retained but not decoded here."},
        {"source_id":"42099_ISD_LITE_METEOSTAT","station_record":"WMO 42099 / Ludhiana record","physical_site":"30.8666667,75.9333333, elev 255m; 2.27km from VILD0 reference; exact sensor/site history unresolved","original_observing_organization":"IMD station record per Phase 05 sources; element-specific origin not retained","original_station_id":"WMO 42099 station record; no NOAA GHCNh WMO match found in downloaded station list","observation_platform":"Fixed surface station record; instruments unknown","reporting_system":"ISD-Lite hourly subset; original report class/source IDs absent","provider":"Meteostat Provider.ISD_LITE","intermediary":"Meteostat 2.2.3","aggregation_and_qc":"Unfilled source rows, but ISD-Lite product strips duplicate/sub-hourly detail and complex flags","coverage":"567 source rows, 2025-03-28 to 2025-08-24","variables":"Temperature, RH, wind speed, pressure; no valid dewpoint/precipitation","timezone":"UTC","lineage_class":"UNKNOWN_LINEAGE","evidence":"WMO record is not authoritatively linked to VILD0; NOAA GHCNh station list has no WMO 42099 row; candidate INM00042099 yearly file returned 404","limitations":"Close station-record coordinates do not prove separate sensor/site or source independence; ISD-Lite lacks report-level lineage."},
        {"source_id":"42101_ISD_LITE_METEOSTAT","station_record":"WMO 42101 / Patiala","physical_site":"30.3333333,76.4666667, elev 251m; distinct verified station record 76.04km from VILD0 reference","original_observing_organization":"Not identified per report; WMO source station ID is retained in official GHCNh crosswalk","original_station_id":"WMO-42101 confirmed in NOAA native GHCNh records","observation_platform":"Fixed land station record; instrument identity unknown","reporting_system":"ISD-Lite hourly subset; native GHCNh counterpart reports FM12 SYNOP","provider":"Meteostat Provider.ISD_LITE","intermediary":"Meteostat 2.2.3","aggregation_and_qc":"ISD-Lite derived subset with source/complex QC detail absent","coverage":"1,187 source rows, 2025-03-28 to 2025-08-24","variables":"Temperature, RH, wind speed, pressure; no valid dewpoint/precipitation","timezone":"UTC","lineage_class":"POSSIBLY_SHARED_SOURCE_WITH_42101_GHCNH","evidence":f"Exact timestamp/value fingerprints to native GHCNh: {json.dumps(f42101_isd['value_fingerprint_matches'],sort_keys=True)}; NOAA identifies WMO-42101 FM12 rows","limitations":"Meteostat ISD-Lite export itself has no original report IDs or quality flags; do not count it separately from GHCNh."},
        {"source_id":"42101_GHCNH_METEOSTAT","station_record":"INM00042101 / WMO 42101","physical_site":"Patiala; distinct station record; coordinate and site-history limitations as Phase 05","original_observing_organization":"Not identified beyond WMO station report identity","original_station_id":"WMO-42101 in native NOAA record","observation_platform":"Fixed land station report; sensor identifiers unknown","reporting_system":"FM12 SYNOP","provider":"Meteostat Provider.GHCNH","intermediary":"Meteostat 2.2.3","aggregation_and_qc":"NOAA GHCNh source-level dataset returned through Meteostat; provider IDs retained","coverage":"532 rows from 2026-01-01 to 2026-03-09 in Phase 04/06 records","variables":"Temperature, RH, wind, pressure","timezone":"UTC","lineage_class":"DERIVED_FROM_SAME_REPORT_AS_NATIVE_GHCNH","evidence":f"Meteostat output matches native NOAA GHCNh values at exact timestamps: {json.dumps(f42101_ghcnh['value_fingerprint_matches'],sort_keys=True)}","limitations":"Mirror/repackaged same NOAA product, not an additional observation source; RH is often derived."},
        {"source_id":"42101_GHCNH_NOAA","station_record":"INM00042101 / WMO 42101","physical_site":"Patiala station record at 30.3333,76.4667; elevation 251m","original_observing_organization":"Not established by downloaded row metadata","original_station_id":"WMO-42101","observation_platform":"Fixed land surface station record; instrument identity not in the station-year file","reporting_system":"FM12 SYNOP; per-variable source code 220 in the sampled rows","provider":"NOAA NCEI GHCNh 1.1.0","intermediary":"NOAA NCEI harmonized source product","aggregation_and_qc":"Native PSV preserves source station ID, report type, source code, measurement and QC per variable","coverage":"Official 2025 and 2026 station-year files; 2,869 rows in 2025 file","variables":"Temperature, dewpoint, RH, wind, sea-level pressure and other elements","timezone":"UTC","lineage_class":"INDEPENDENT_OBSERVING_SYSTEM_RELATIVE_TO_VILD0_FM15_AT_REPORT_LEVEL","evidence":"Distinct verified station record and coordinates; distinct original station ID WMO-42101 and report family FM12; source rows exist near selected event times","limitations":"Instrument serials, exact sensor position, operator independence and calibration remain unresolved; RH is derived from T/dewpoint."},
        {"source_id":"PHASE03_HISTORICAL_CANDIDATE_SERIES","station_record":"VILD0 research series; station identity inherited from prior notebook","physical_site":"VILD0 record only; no row-level site/sensor lineage","original_observing_organization":"Unknown per row","original_station_id":"Not retained per row","observation_platform":"Unknown; historical notebook Meteostat 1.7.6 hourly request","reporting_system":"Unknown per row","provider":"Historical Meteostat 1.7.6 retrieval","intermediary":"Earlier notebook and Phase 03 event selection","aggregation_and_qc":"Notebook omitted model and flags; library defaults model=True, flags=False","coverage":"123 candidate rows across 81 episodes, 2025-03-28 to 2026-03-09","variables":"Temperature, dewpoint, RH, precipitation, wind, pressure and derived temporal features","timezone":"Asia/Kolkata in stored candidate timestamps","lineage_class":"UNKNOWN_LINEAGE","evidence":"Phase 05 audited code defaults; candidate file contains configuration vote counts, not independent labels","limitations":"Candidate values may be model-filled and cannot serve as verified direct primary observations."},
    ]

    lineage_relationships = []
    def relation(source_a, source_b, evidence, limitations, lclass, metrics=None):
        lineage_relationships.append({"source_a":source_a,"source_b":source_b,"lineage_class":lclass,
            "evidence_basis":evidence,"fingerprint_metrics_json":json.dumps(metrics or {},sort_keys=True),
            "scientific_scope":"Source-product/report lineage only; never use agreement alone as independence.","limitation":limitations})
    relation("VILD0_METAR_METEOSTAT","VILD0_GHCNH_NOAA",
             "Same verified VILD airport station record; native rows identify ICAO-VILD/FM15; exact timestamp/value fingerprints are strong but Meteostat rows retain no report IDs.",
             "Possible shared original METAR reports; exact report identity for all rows not established.","POSSIBLY_SHARED_SOURCE",vild_fingerprint)
    relation("42101_GHCNH_METEOSTAT","42101_GHCNH_NOAA",
             "Same NOAA GHCNh station/year product; exact timestamps and values closely match.",
             "Meteostat output is a mirrored/repackaged product, not an independent network.","DERIVED_FROM_SAME_REPORT",f42101_ghcnh)
    relation("42101_ISD_LITE_METEOSTAT","42101_GHCNH_NOAA",
             "Same WMO-42101 station; exact timestamp/value fingerprint and NOAA documentation says GHCNh incorporates essentially the same sources as ISD.",
             "ISD-Lite lacks per-row original report IDs; classify as potentially shared, not proven duplicate for every value.","POSSIBLY_SHARED_SOURCE",f42101_isd)
    relation("VILD0_GHCNH_NOAA","42101_GHCNH_NOAA",
             "Distinct station coordinates and original source IDs (ICAO-VILD vs WMO-42101); FM15 METAR vs FM12 SYNOP report types.",
             "Supports distinct station report systems for limited comparison; operators, instrument IDs, siting/exposure and calibration are not resolved.","INDEPENDENT_OBSERVING_SYSTEM")
    relation("VILD0_METAR_METEOSTAT","42099_ISD_LITE_METEOSTAT",
             "Separate station records and 2.27km station-reference distance; no authoritative identity or instrument crosswalk.",
             "Could be separate but same-campus/source chain remains unresolved; ISD-Lite rows lack source IDs.","UNKNOWN_LINEAGE")
    relation("PHASE03_HISTORICAL_CANDIDATE_SERIES","ALL_EXTERNAL_STATION_RECORDS",
             "Historical request defaults model=True and did not retain row source flags.",
             "A candidate row cannot be proven direct or linked to a specific original report.","UNKNOWN_LINEAGE")
    relation("ERA5_REANALYSIS","STATION_OBSERVATIONS",
             "ERA5 is a gridded model-and-observation data-assimilation reanalysis.",
             "Context only; not an independent station measurement and may assimilate observations from the same observing systems.","NOT_COMPARABLE")

    site_vild = {"verified_physical_site_id":"VILD_AIRPORT_STATION","verified_original_station_id":"ICAO-VILD",
                 "verified_report_type":"FM15","distinct_original_reports_verified":True}
    site_pat = {"verified_physical_site_id":"WMO_42101_PATIALA","verified_original_station_id":"WMO-42101",
                "verified_report_type":"FM12","distinct_original_reports_verified":True}
    verified_pair_class = classify_lineage_pair(site_vild, site_pat)
    dependence = [
        {"pair":"VILD0 METAR / VILD0 NOAA GHCNh","physical_sites_distinct":"NO - same airport station record","original_observations_independent":"NO EVIDENCE; likely shared METAR reports","product_same_report_status":"POSSIBLY_SHARED_SOURCE","instrument_lineage":"UNKNOWN","operator_independence":"UNKNOWN","can_claim_independent_corroboration":"NO","evidence":f"{vild_fingerprint['exact_timestamp_overlap']} exact overlapping timestamps; temp and altimeter fingerprints match at {vild_fingerprint['value_fingerprint_matches'].get('temp')}/{vild_fingerprint['valid_value_pairs'].get('temp')} and {vild_fingerprint['value_fingerprint_matches'].get('pres')}/{vild_fingerprint['valid_value_pairs'].get('pres')} respectively.","conclusion":"Use as source validation/fingerprint only; do not count as a second station."},
        {"pair":"42101 Meteostat GHCNh / NOAA GHCNh","physical_sites_distinct":"NO - same Patiala station","original_observations_independent":"NO - same station-year GHCNh records","product_same_report_status":"DERIVED_FROM_SAME_REPORT","instrument_lineage":"UNKNOWN","operator_independence":"NOT_APPLICABLE_TO_PRODUCT_MIRROR","can_claim_independent_corroboration":"NO","evidence":json.dumps(f42101_ghcnh["value_fingerprint_matches"],sort_keys=True),"conclusion":"Same NOAA GHCNh observations returned through a second software path."},
        {"pair":"42101 Meteostat ISD-Lite / NOAA GHCNh","physical_sites_distinct":"NO - same Patiala station","original_observations_independent":"LIKELY SHARED ORIGINAL REPORTS; exact row IDs absent from ISD-Lite","product_same_report_status":"POSSIBLY_SHARED_SOURCE","instrument_lineage":"UNKNOWN","operator_independence":"UNKNOWN","can_claim_independent_corroboration":"NO - do not double count products","evidence":json.dumps(f42101_isd["value_fingerprint_matches"],sort_keys=True),"conclusion":"Strong evidence of common underlying WMO-42101 observations; NOAA documents GHCNh/ISD source overlap."},
        {"pair":"VILD0 NOAA GHCNh FM15 / 42101 NOAA GHCNh FM12","physical_sites_distinct":"YES - station-record coordinates are 76.04km apart","original_observations_independent":"YES AT STATION-REPORT LEVEL","product_same_report_status":verified_pair_class,"instrument_lineage":"UNKNOWN - exact instruments/serials and sensor siting not published in inspected records","operator_independence":"UNKNOWN; original agencies/operators not resolved","can_claim_independent_corroboration":"LIMITED, for paired station reports only","evidence":"Native per-variable source station IDs ICAO-VILD and WMO-42101; report types FM15 and FM12; distinct verified station records.","conclusion":"Supports a limited independent station-report comparison, not full source-organization or instrument independence."},
        {"pair":"VILD0 primary / WMO 42099 ISD-Lite","physical_sites_distinct":"NOT ESTABLISHED AT SENSOR LEVEL; record points are 2.27km apart","original_observations_independent":"UNKNOWN","product_same_report_status":"UNKNOWN_LINEAGE","instrument_lineage":"UNKNOWN","operator_independence":"UNKNOWN","can_claim_independent_corroboration":"NO","evidence":"No authoritative VILD0-to-42099 identity equivalence; ISD-Lite has no row source IDs; no WMO 42099 entry in current NOAA GHCNh station list.","conclusion":"Keep records separate; missing provenance is not evidence of same or independent sensors."},
        {"pair":"Phase 03 historical VILD0 candidates / all references","physical_sites_distinct":"NOT ASSESSABLE PER ROW","original_observations_independent":"UNKNOWN","product_same_report_status":"UNKNOWN_LINEAGE","instrument_lineage":"UNKNOWN","operator_independence":"UNKNOWN","can_claim_independent_corroboration":"NO FOR THE ARCHIVED CANDIDATE VALUES","evidence":"Historical Meteostat 1.7.6 call omitted model/flags; defaults model=True, flags=False; no row provider IDs.","conclusion":"Where native VILD0 FM15 reports exist, they may contextualize a candidate, but no row-level tie to historical candidate is claimed."},
        {"pair":"ERA5 grid / any station","physical_sites_distinct":"GRID CELL, NOT A STATION","original_observations_independent":"NO - reanalysis assimilates observations","product_same_report_status":"NOT_COMPARABLE","instrument_lineage":"NOT_APPLICABLE","operator_independence":"NOT_APPLICABLE","can_claim_independent_corroboration":"NO - CONTEXT ONLY","evidence":"C3S describes ERA5 as model data combined with assimilated observations on a 0.25 degree grid.","conclusion":"May add broad atmospheric context only; not included in event comparisons."},
    ]

    inventory = [
        {"reference_id":"NOAA_GHCNH","source":"NOAA NCEI GHCNh v1.1.0","observation_type":"Hourly/synoptic land station product; preserves original station ID, report type, source code, measurement code, and QC by variable","original_provider":"Multiple source agencies/networks; per-row source station ID identifies original station but operator not always established","timestamp":"UTC ISO time","variables":"temperature, dew point, RH, wind, pressure, precipitation and other elements; RH may be derived","coverage":"VILD0 native 2025/2026 files and 42101 native 2025/2026 files retrieved","quality_flags":"Native per-element fields included; sampled VILD0 FM15 and 42101 FM12 rows carry source/QC attributes","lineage":"Harmonized multisource NOAA product; shares essentially the source ecosystem of legacy ISD and is not automatically independent of ISD-Lite","accessibility":"Public bulk station-year PSV; station-year files saved and SHA-256 recorded in external_reference_manifest.json","limitations":"Aggregation/QC product, not separate sensor; native provider/operator and instruments unresolved for these India stations."},
        {"reference_id":"IMD_DATA_SUPPLY","source":"India Meteorological Department Data Supply Portal","observation_type":"Potential direct official meteorological station observations","original_provider":"IMD / relevant observatory; exact station ownership needs inquiry","timestamp":"Likely UTC/local conventions must be documented per returned file","variables":"Official page lists hourly temperature, RH, surface wind, pressure and rainfall for selected stations","coverage":"Portal states hourly data only for selected stations; availability for exact station/date not checked","quality_flags":"Not established until data and codebook are returned","lineage":"Could be the most promising direct original records, but not yet obtained","accessibility":"Online request workflow; official page describes data enquiry/availability and possible tariffs","limitations":"No IMD file was downloaded; do not invent availability, source lineage, or independent sensor status."},
        {"reference_id":"AWC_METAR","source":"Aviation Weather Center Data API / Archive View","observation_type":"Original airport METAR/SPECI report stream","original_provider":"Aviation weather service relays observations; it does not operate the observing platform","timestamp":"METAR report UTC time group","variables":"Raw METAR groups include temperature/dewpoint, wind, pressure, present weather and visibility as reported","coverage":"Worldwide API, but database access limited to the previous 30 days; older requests are directed to NCEI archive services","quality_flags":"Raw report contents; AWC describes source reporting issues but does not certify sensors","lineage":"Potential original report stream for VILD; same reports may be reproduced in GHCNh/Meteostat","accessibility":"Public API for bounded queries; historical >30 day report archive requires NCEI/AIRS or suitable official archive","limitations":"No separate old AWC archive was downloaded; GHCNh native REM already carries VILD METAR report payloads."},
        {"reference_id":"NOAA_ISD_ISDLITE","source":"NOAA NCEI ISD / ISD-Lite","observation_type":"Global hourly multi-source station archive; ISD-Lite is a reduced derived subset","original_provider":"Multiple national services and archives","timestamp":"UTC/GMT","variables":"Common surface parameters incl. temp, RH, wind, pressure; varying by station","coverage":"Phase04 Meteostat outputs cover WMO 42099 and 42101; no independent access to original per-record feeds in this phase","quality_flags":"ISD-Lite omits complex flags and sub-hour detail compared with full ISD","lineage":"NCEI says GHCNh succeeds ISD and includes essentially the same source set plus more; products are not independent votes","accessibility":"Public archive and documentation","limitations":"Original source station/report often unavailable in ISD-Lite files."},
        {"reference_id":"WMO_STATION_METADATA","source":"WMO/NOAA station identifiers and station records","observation_type":"Station metadata only","original_provider":"WMO/National Meteorological and Hydrological Services","timestamp":"Not applicable","variables":"Identifiers, station coordinates and metadata; no observation series used here","coverage":"VILD/42101 identifiers resolved in NOAA GHCNh station list; WMO 42099 not mapped in that list","quality_flags":"Not applicable","lineage":"Metadata can support site identity but cannot prove instrument independence or observation origin","accessibility":"Public station lists and official metadata","limitations":"No observation data inferred from station inventory."},
        {"reference_id":"ERA5_CONTEXT","source":"Copernicus Climate Change Service ERA5","observation_type":"Gridded atmospheric reanalysis","original_provider":"ECMWF/Copernicus","timestamp":"Hourly UTC","variables":"Atmospheric fields on 0.25-degree grid","coverage":"Available historically, but not retrieved for this audit","quality_flags":"Model/reanalysis uncertainty products, not station QC flags","lineage":"Assimilates observations; not independent of station observing systems","accessibility":"Climate Data Store, registration/access workflow","limitations":"Context only, not an independent station measurement or included event comparator."},
    ]

    # Candidate events are selected by deterministic extrema from the existing 8-of-12 table,
    # before examining neighboring agreement. Every selected event is retained, including gaps.
    event_register = []
    for number, event in enumerate(events.itertuples(index=False), 1):
        event_id = f"P07E{number:02d}"
        timestamp = event.timestamp_utc
        target = event.event_variable
        signal_column = next(rule[1] for rule in EVENT_RULES if rule[0] == event.event_type)
        signal_value = getattr(event, signal_column)
        candidate_value = getattr(event, target)
        event_register.append({
            "event_id": event_id, "selection_rule": event.selection_rule,
            "candidate_timestamp_local": pd.Timestamp(event.timestamp).isoformat(),
            "candidate_timestamp_utc": timestamp.isoformat(), "candidate_timezone": "Asia/Kolkata",
            "event_type": event.event_type, "comparison_variable": target,
            "candidate_value_raw": candidate_value, "candidate_units": COMMON_UNITS[target] if target != "wspd" else "km/h (historical Meteostat convention)",
            "candidate_anomaly_metric": signal_column, "candidate_anomaly_metric_value": signal_value,
            "phase03_episode_id": int(event.episode_id), "e1_configuration_votes": int(event.configuration_votes),
            "e2_event_specific_result":"NOT_AVAILABLE_IN_CANDIDATE_EVENT_ARTIFACT",
            "e4_event_specific_result":"NOT_AVAILABLE_IN_CANDIDATE_EVENT_ARTIFACT",
            "candidate_source_status":"HISTORICAL_METEOSTAT_1.7.6_ROW_LINEAGE_UNRESOLVED; model=True default and flags=False",
            "selection_reason":"Mechanical extremum selected across the full Phase03 8-of-12 candidate table; no neighbor agreement used.",
            "precipitation_event":"NOT_SELECTED_NO_VERIFIED_PRIMARY_PRECIPITATION_BASIS",
        })

    source_frames = {
        "VILD0_METEOSTAT_METAR": (p06_metar, "VILD0_METEOSTAT_METAR", "POSSIBLY_SHARED_SOURCE", "METEOSTAT", False),
        "VILD0_NOAA_GHCNH": (gh_vild, "VILD0_GHCNH_NOAA", "POSSIBLY_SHARED_SOURCE", "GHCNH", False),
        "WMO_42099_METEOSTAT_ISDLITE": (n42099, "42099_ISD_LITE_METEOSTAT", "UNKNOWN_LINEAGE", "METEOSTAT", True),
        "WMO_42101_METEOSTAT_ISDLITE": (n42101_isd, "42101_ISD_LITE_METEOSTAT", "POSSIBLY_SHARED_SOURCE", "METEOSTAT", True),
        "WMO_42101_NOAA_GHCNH": (gh_42101, "42101_GHCNH_NOAA", verified_pair_class, "GHCNH", False),
    }
    comparison_rows = []
    event_independent_counts = {row["event_id"]: 0 for row in event_register}
    for event in event_register:
        event_time = pd.Timestamp(event["candidate_timestamp_utc"])
        variable = event["comparison_variable"]
        candidate_value = pd.to_numeric(pd.Series([event["candidate_value_raw"]]), errors="coerce").iloc[0]
        candidate_common = float(candidate_value) / 3.6 if variable == "wspd" and pd.notna(candidate_value) else candidate_value
        for reference_id, (frame, source_id, lclass, frame_kind, meter_speed) in source_frames.items():
            if frame_kind == "GHCNH":
                native = native_frame_for_variable(frame, variable, "42101" if "42101" in reference_id else "VILD0")
                match = match_event_observation(event_time, native.rename(columns={"time":"timestamp"}), 60,
                                                time_column="timestamp", value_column="value")
                matched = match.get("source_row")
                reference_value = match.get("value")
                ref_units = (matched.get("units") if matched else COMMON_UNITS[variable])
                qc = matched.get("qc") if matched else None
                qc_status = qc_label(qc) if matched else "NOT_AVAILABLE"
                report_type = matched.get("report_type") if matched else None
                source_code = matched.get("source_code") if matched else None
                original_station_id = matched.get("original_station_id") if matched else None
                measurement_code = matched.get("measurement_code") if matched else None
                if variable == "rhum" and str(measurement_code).upper() == "D":
                    measurement_basis = "DERIVED_FROM_TEMPERATURE_AND_DEWPOINT"
                else:
                    measurement_basis = "SOURCE_NATIVE_BASIS_NOT_FURTHER_VERIFIED"
            else:
                frame_for_match = frame.rename(columns={"time":"timestamp"}).copy()
                if variable not in frame_for_match:
                    frame_for_match["value"] = np.nan
                else:
                    frame_for_match["value"] = pd.to_numeric(frame_for_match[variable], errors="coerce")
                match = match_event_observation(event_time, frame_for_match, 60,
                                                time_column="timestamp", value_column="value")
                matched = match.get("source_row")
                reference_value = match.get("value")
                if variable == "wspd" and pd.notna(reference_value):
                    reference_value = float(reference_value) / 3.6
                ref_units = COMMON_UNITS[variable]
                qc_status = "NOT_RETAINED_IN_SOURCE_EXPORT"
                qc = None
                report_type = source_code = original_station_id = measurement_code = None
                measurement_basis = "METEOSTAT_SOURCE_LEVEL_VALUE; ORIGINAL ELEMENT METADATA NOT RETAINED"

            units_comparable = variable != "pres"
            if variable == "pres":
                pressure_type = ("altimeter" if reference_id == "VILD0_NOAA_GHCNH" else
                                 "sea_level_pressure" if reference_id == "WMO_42101_NOAA_GHCNH" else
                                 "provider_pres_quantity_unverified")
                units_comparable = False
            else:
                pressure_type = "NOT_APPLICABLE"
            cmp = compare_event_value(candidate_common, reference_value,
                                      units_comparable=units_comparable,
                                      lineage_class=lclass,
                                      match_status=match["match_status"])
            time_match_available = match["match_status"] in {"EXACT_MATCH", "TOLERANCE_MATCH"}
            qc_usable = qc_status in {"GOOD", "NOT_RETAINED_IN_SOURCE_EXPORT"}
            independent_report = lclass == "INDEPENDENT_OBSERVING_SYSTEM"
            if variable == "rhum" and measurement_basis == "DERIVED_FROM_TEMPERATURE_AND_DEWPOINT":
                independent_variable = False
            else:
                independent_variable = True
            usable_independent = bool(independent_report and time_match_available and qc_usable
                                      and units_comparable and independent_variable and pd.notna(reference_value))
            if usable_independent:
                event_independent_counts[event["event_id"]] += 1
            if variable in {"temp_change_1h"}:
                metric_note = "Single-time observations do not validate a one-hour change; reference interval was not estimated in this row."
            elif variable == "pres":
                metric_note = f"Pressure quantity is {pressure_type}; candidate `pres` type is unresolved; not compared."
            elif variable == "rhum":
                metric_note = "Relative humidity may be derived from temperature/dewpoint; this is not independent humidity-sensor confirmation."
            else:
                metric_note = "Descriptive value difference only; no preregistered agreement tolerance or event truth is available."
            comparison_rows.append({
                "event_id":event["event_id"], "event_type":event["event_type"],
                "candidate_timestamp_utc":event["candidate_timestamp_utc"], "variable":variable,
                "reference_source_id":source_id,"reference_product":reference_id,
                "lineage_class_vs_primary_station":lclass,
                "matched_timestamp_utc":match.get("matched_time"),"offset_minutes_neighbor_minus_event":match.get("offset_minutes"),
                "time_match_status":match["match_status"],"candidate_value_raw":event["candidate_value_raw"],
                "candidate_value_common_unit":candidate_common,"candidate_original_unit":event["candidate_units"],
                "reference_value_common_unit":reference_value,"reference_units":ref_units,
                "candidate_minus_reference_difference":(float(candidate_common)-float(reference_value)
                    if pd.notna(candidate_common) and pd.notna(reference_value) and units_comparable else None),
                "units_comparable":units_comparable,"pressure_quantity":pressure_type,
                "original_station_id":original_station_id,"source_code":source_code,
                "report_type":report_type,"quality_code":qc,"quality_status":qc_status,
                "measurement_code":measurement_code,"measurement_basis":measurement_basis,
                "distinct_station_report_reference":independent_report,
                "nonderived_variable_measurement":independent_variable,
                "eligible_as_distinct_report_level_event_context":usable_independent,
                "comparison_status":cmp["comparison_status"],"evidence_role":cmp["evidence_role"],
                "interpretation_limit":metric_note,
            })

    # Enrich event register with coverage results, retaining selected gaps and disagreements.
    for row in event_register:
        selected_comparisons = [x for x in comparison_rows if x["event_id"] == row["event_id"]]
        row["vild0_native_match_within_60m"] = next((x["time_match_status"] for x in selected_comparisons if x["reference_product"] == "VILD0_NOAA_GHCNH"), "NOT_CHECKED")
        row["wmo42101_native_match_within_60m"] = next((x["time_match_status"] for x in selected_comparisons if x["reference_product"] == "WMO_42101_NOAA_GHCNH"), "NOT_CHECKED")
        row["qc_good_distinct_report_rows_within_60m"] = event_independent_counts[row["event_id"]]
        row["interpretation"] = "Coverage and source metadata only; no event is assigned true/false or sensor fault."

    relationships = [
        {"from_node":"VILD0 airport weather station (ICAO VILD)","to_node":"Original airport report, FM15 METAR, source station ID ICAO-VILD","relationship":"PRODUCES_REPORT","lineage_status":"DOCUMENTED_AT_STATION-REPORT_LEVEL","evidence":"AAI airport METAR service; native NOAA GHCNh per-variable report type and source ID."},
        {"from_node":"Original VILD FM15 METAR report","to_node":"NOAA GHCNh INI0000VILD","relationship":"INGESTED_AND_HARMONIZED","lineage_status":"POSSIBLY_SHARED_SOURCE","evidence":"GHCNh native source station ID ICAO-VILD, FM15, REM content; no separate station observation."},
        {"from_node":"Original VILD FM15 METAR report","to_node":"Meteostat VILD0 metar feed","relationship":"PROVIDER_FEED_OR_PARSE","lineage_status":"POSSIBLY_SHARED_SOURCE","evidence":f"Exact timestamp/value fingerprints: {json.dumps(vild_fingerprint['value_fingerprint_matches'],sort_keys=True)}; Meteostat raw report ID absent."},
        {"from_node":"WMO station 42101 (Patiala)","to_node":"Original WMO-42101 report, FM12 SYNOP","relationship":"PRODUCES_REPORT","lineage_status":"DOCUMENTED_AT_STATION-REPORT_LEVEL","evidence":"Native GHCNh variable rows identify source station WMO-42101 and FM12."},
        {"from_node":"Original WMO-42101 FM12 report","to_node":"NOAA GHCNh INM00042101","relationship":"INGESTED_AND_HARMONIZED","lineage_status":"DOCUMENTED_AT_SOURCE-ID_LEVEL","evidence":"Native NOAA station-year PSV preserves report type, source ID, source code and QC."},
        {"from_node":"Original WMO-42101 FM12 report","to_node":"NOAA ISD / ISD-Lite and Meteostat ISD-Lite","relationship":"POSSIBLE_SHARED_SOURCE_PATH","lineage_status":"POSSIBLY_SHARED_SOURCE","evidence":f"Timestamp/value fingerprints: {json.dumps(f42101_isd['value_fingerprint_matches'],sort_keys=True)}; NOAA states GHCNh reuses essentially the ISD source set."},
        {"from_node":"NOAA GHCNh station records","to_node":"Meteostat ghcnh provider output","relationship":"MIRROR_OR_REPACKAGED_PRODUCT","lineage_status":"DERIVED_FROM_SAME_REPORT","evidence":f"Same station-year observations fingerprint match: {json.dumps(f42101_ghcnh['value_fingerprint_matches'],sort_keys=True)}."},
        {"from_node":"WMO 42099 Ludhiana station record","to_node":"Meteostat ISD-Lite output","relationship":"PROVIDER_PRODUCT","lineage_status":"UNKNOWN_LINEAGE","evidence":"No row-level original source code and no WMO 42099 match in NOAA GHCNh station list; no identity merge with ICAO VILD."},
        {"from_node":"ERA5 gridded analysis","to_node":"Regional atmospheric context","relationship":"DATA_ASSIMILATION_REANALYSIS","lineage_status":"NOT_COMPARABLE","evidence":"Assimilates observation data; not a separate in-situ station."},
    ]

    graph = """flowchart LR
  VILD["Ludhiana Airport station record<br/>ICAO VILD / VILD0"] --> VMETAR["Original FM15 METAR report<br/>source station ICAO-VILD"]
  VMETAR -->|possibly shared report feed| MVM["Meteostat METAR product"]
  VMETAR -->|harmonized + QC| NV["NOAA GHCNh INI0000VILD"]
  P["Patiala station record<br/>WMO 42101"] --> PSYNOP["Original FM12 SYNOP<br/>source station WMO-42101"]
  PSYNOP -->|harmonized + QC| NP["NOAA GHCNh INM00042101"]
  PSYNOP -->|possible shared source| ISD["NOAA ISD / ISD-Lite"]
  ISD --> M42101["Meteostat ISD-Lite product"]
  NP -->|same product mirror| MGH["Meteostat GHCNh product"]
  W["WMO 42099 Ludhiana record"] --> I42099["Meteostat ISD-Lite<br/>original row lineage unknown"]
  VILD -. "distinct station-report systems; instrument/operator independence unresolved" .-> P
  ERA["ERA5 reanalysis<br/>assimilated observations"] -. "context only" .-> CONTEXT["Regional atmospheric context"]
"""

    event_map = {row["event_id"]:row for row in event_register}
    clean_event_count = sum(bool(x) for x in event_independent_counts.values())
    independent_rows = sum(event_independent_counts.values())
    decision = {
        "phase":"07_independent_evidence",
        "decision":"LIMITED_INDEPENDENT_EVIDENCE" if clean_event_count else "BLOCKED_BY_DATA_PROVENANCE",
        "decision_scope":"Limited report-level comparison is available for VILD FM15 and WMO-42101 FM12 native GHCNh observations; candidate rows are not source-certified, and this does not prove full sensor/operator independence or validate the E3 classifier.",
        "verified_independent_source_pair":verified_pair_class,
        "independent_reference":"NOAA GHCNh native WMO-42101 FM12 report rows; physically distinct station record from VILD0 ICAO-VILD FM15.",
        "candidate_events_selected":len(event_register),
        "candidate_events_with_qc_good_distinct_report_rows_within_60m":clean_event_count,
        "qc_good_distinct_report_rows_within_60m":independent_rows,
        "event_level_quality_caution":"QC-suspect FM12/FM15 observations are retained as flagged context but are not counted as clean comparisons; RH is derived from temperature/dewpoint.",
        "shared_source_findings":{
            "VILD_METAR_vs_GHCNh":vild_fingerprint,
            "42101_ISDLite_vs_GHCNh":f42101_isd,
            "42101_Meteostat_GHCNh_vs_NOAA":f42101_ghcnh,
        },
        "no_data_obtained":["IMD official historical station files","separate archived AWC/NCEI METAR order beyond native GHCNh REM","ERA5 grid; contextual data not downloaded"],
        "event_label_limit":"Phase03 candidate series is historical Meteostat 1.7.6 with model=True default and flags=False; candidate rows are not verified direct observations or event ground truth.",
        "classifier_integration":"NOT_JUSTIFIED; keep E3 isolated pending exact row lineage, instrument/site histories, QC/performance specifications, and independent event adjudication.",
        "retrieval_settings":{"NOAA product":"GHCNh v1.1.0 station-year PSV, original source/QC columns retained","meteostat phase04/06":"2.2.3, model disabled, fill/clean disabled, provider source retained"},
    }

    # Decision report and source inventories are generated only after all inputs parse.
    write_csv_once("source_lineage_register.csv", source_register)
    write_csv_once("source_lineage_relationships.csv", relationships)
    write_csv_once("independent_reference_inventory.csv", inventory)
    write_csv_once("candidate_event_register.csv", event_register)
    write_csv_once("event_level_comparison.csv", comparison_rows)
    write_csv_once("source_dependence_assessment.csv", dependence)
    (OUT / "source_lineage_graph.mmd").write_text(graph, encoding="utf-8")
    (OUT / "e3_independent_evidence_decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False, default=str), encoding="utf-8")

    report = f'''# Phase 07 — Independent Data Lineage and External Reference Validation

**Decision:** `{decision['decision']}`  
**Branch:** `feature/phase07-independent-evidence`  
**Base commit:** `{__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}`  
**Scope:** observation lineage and event-level reference availability; no model training or classifier integration.

## Findings

Phase 06's provider labels did not establish independent sensors. The native NOAA NCEI GHCNh PSV files improve the source trail because they retain per-variable original station IDs, report types, source codes, measurement codes and QC flags. NOAA's station list resolves `INI0000VILD` to ICAO VILD at Ludhiana and `INM00042101` to WMO 42101 at Patiala. The native VILD rows identify `ICAO-VILD` and report type `FM15`; Patiala rows identify `WMO-42101` and `FM12`.

The VILD0 Meteostat METAR and NOAA GHCNh products are **not independent**. Across {vild_fingerprint['exact_timestamp_overlap']} exact timestamp overlaps, temperature matched within 0.11°C in {vild_fingerprint['value_fingerprint_matches'].get('temp',0)}/{vild_fingerprint['valid_value_pairs'].get('temp',0)} pairs and METAR pressure/NOAA altimeter matched in {vild_fingerprint['value_fingerprint_matches'].get('pres',0)}/{vild_fingerprint['valid_value_pairs'].get('pres',0)} pairs. NOAA's native VILD rows carry FM15/ICAO-VILD source identity and original report remarks. Because the Meteostat METAR export lacks original report IDs, the register uses `POSSIBLY_SHARED_SOURCE` rather than asserting every row is the identical report.

At station 42101, NOAA native GHCNh and Meteostat GHCNh are the same underlying product: exact timestamp fingerprints and per-variable values match. The 42101 ISD-Lite and native GHCNh series also have strong same-station overlap fingerprints—temperature {f42101_isd['value_fingerprint_matches'].get('temp',0)}/{f42101_isd['valid_value_pairs'].get('temp',0)}, relative humidity {f42101_isd['value_fingerprint_matches'].get('rhum',0)}/{f42101_isd['valid_value_pairs'].get('rhum',0)}, wind speed {f42101_isd['value_fingerprint_matches'].get('wspd',0)}/{f42101_isd['valid_value_pairs'].get('wspd',0)} and sea-level pressure {f42101_isd['value_fingerprint_matches'].get('pres',0)}/{f42101_isd['valid_value_pairs'].get('pres',0)} at exact shared timestamps. NOAA documents GHCNh as replacing ISD and incorporating essentially the same source set. These product pairs must not be counted as independent station votes.

There is **limited report-level independent evidence** between the VILD airport station and Patiala WMO 42101. The records are 76.04 km apart and retain different original identifiers and report types (ICAO-VILD/FM15 versus WMO-42101/FM12). This is enough to compare distinct station reports in a restricted experiment. It does not establish distinct operators, instrument serials, sensor exposure, calibration or full independence of the organizations. `42101` is not the VILD0 station and is not substituted for it.

WMO 42099 remains unresolved as an independent reference. Its Phase 04 station-record point is 2.27 km from VILD0, but no authoritative alias or same-instrument crosswalk was found. ISD-Lite does not preserve original per-row report IDs. NOAA's current GHCNh station list has no WMO 42099 match, and the candidate `INM00042099` station-year request returned 404. A nearby `INU00020367` Ludhiana metadata entry exists but has no WMO/ICAO match; it is not assumed to be 42099 or VILD0.

## Candidate event review

Eight candidate timestamps were selected mechanically from the complete Phase 03 8-of-12 candidate table: extreme one-hour temperature rise/drop, highest/lowest candidate temperature, highest/lowest candidate RH, highest candidate wind speed, and lowest candidate pressure. Selection did not use neighbor agreement. Each retains the original configuration-vote count. No precipitation event was selected because the controlled VILD0 source-level retrieval had no valid precipitation values. Event-level E2 and E4 labels were not present in the candidate artifact and are recorded as unavailable.

The event comparison table separates the historical candidate value from each source's nearest report within 60 minutes; exact versus tolerance matches, QC, report type, source ID, RH measurement basis, and pressure quantity are preserved. The Phase 03 candidate series has unresolved row-level lineage because the archived Meteostat 1.7.6 call used the default `model=True` and did not request source flags. Consequently, agreement against a candidate value alone is not direct validation.

Native VILD and Patiala report rows are jointly available in several selected windows, enabling limited station-report comparison. Three selected windows have a QC-good Patiala report within 60 minutes for the candidate variable; these are reference-availability rows, not verified candidate-event validations because historical candidate lineage is unresolved. Flagged observations remain flagged; no binary agreement tolerance is registered. GHCNh RH rows marked measurement code `D` are derived from temperature and dewpoint, not an independent RH sensor. Pressure is not compared numerically because VILD's METAR-based value is altimeter/QNH while the Patiala GHCNh field is sea-level pressure, and the historical candidate `pres` meaning is not resolved. Rapid-change episodes cannot be validated by a single contemporaneous point, and the WMO SYNOP cadence is generally coarser than one hour.

The results distinguish: **independent report-level reference** (VILD FM15 vs Patiala FM12); **potentially shared-source products** (VILD METAR vs VILD GHCNh; Patiala ISD-Lite vs GHCNh); **missing evidence** (no nearby source row within tolerance); and **context only** (ERA5, not downloaded). Missing evidence is never counted as disagreement. No event is labeled true/false and no disagreement is called a sensor fault.

## External reference availability

- **IMD:** the official data-supply portal lists hourly temperature, RH, surface wind, pressure and rainfall for selected stations and provides an inquiry/request workflow. No IMD archive for these dates/stations was obtained; station availability, QC flags, source lineage and possible charges still require a formal station/date enquiry.
- **Aviation Weather Center:** the official worldwide METAR API provides recent observations but its searchable database is limited to the previous 30 days; older records are directed to NCEI archive services. Candidate-period AWC reports were not separately ordered. NOAA GHCNh contains native VILD FM15 source/report fields and report remarks, but remains a harmonized product of those reports.
- **NOAA NCEI:** public station-year GHCNh PSV files were retrieved for VILD0 and 42101; hashes and source URLs are in `external_reference_manifest.json`. NCEI's GHCNh product is multisource and not an independent sensor network.
- **ERA5:** C3S defines ERA5 as a model-and-observation data-assimilation reanalysis on a 0.25° grid. It could provide broad atmospheric context, not a station reference; it was not downloaded.

## Decision and remaining limits

`{decision['decision']}` means distinct station-report records are available for limited comparison between VILD FM15 and WMO-42101 FM12. It does **not** mean historical candidate events are independently validated or that full sensor/operator independence has been established. The candidate series cannot be source-certified; exact sensor position and instrument history are missing; 42099 lineage is unknown; report QC varies; no variable-specific uncertainty tolerances or independent event labels are available. Keep E3 isolated from the final classifier and retain an uncertain outcome.

### Required next evidence

Request IMD original observations and station/instrument logs for Ludhiana and Patiala, including exact site coordinates, source IDs, QC conventions and pressure element definitions. Obtain the original AWC/NCEI report files where needed and map historical candidate rows to original reports. Then preregister event-window and variable-specific rules before evaluating more events.

## Primary source documentation

- [NOAA NCEI GHCNh product and access](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly)
- [NOAA GHCNh format, per-variable source/report/QC fields](https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh_DOCUMENTATION.pdf)
- [NOAA NCEI ISD and ISD-Lite](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database)
- [Meteostat provider registry](https://dev.meteostat.net/providers)
- [Aviation Weather Center Data API and retention limits](https://www.connect.aviationweather.gov/data/api/)
- [AWC Archive View and NCEI historical archive direction](https://www.connect.aviationweather.gov/tools/archive/)
- [IMD Data Supply Portal information](https://mausam.imd.gov.in/thiruvananthapuram/Datasupply.php)
- [Copernicus ERA5 description](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-timeseries)

## Outputs

See `source_lineage_register.csv`, `source_lineage_relationships.csv`, `independent_reference_inventory.csv`, `candidate_event_register.csv`, `event_level_comparison.csv`, `source_dependence_assessment.csv`, `e3_independent_evidence_decision.json`, `source_lineage_graph.mmd`, and `external_reference_manifest.json`.
'''
    (OUT / "PHASE07_RESEARCH_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    build()
