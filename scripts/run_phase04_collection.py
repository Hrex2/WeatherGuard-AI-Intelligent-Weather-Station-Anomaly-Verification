"""Run a bounded, source-preserving Meteostat 2.2.3 Phase 04 collection.

The script refuses to overwrite prior output, retrieves only stations with an
independent official identity/site record, and does no model fitting or imputation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
import platform
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase04_provenance_aware_collection"
RAW = OUT / "raw_station_data"
START = pd.Timestamp("2025-03-28T00:00:00Z")
END = pd.Timestamp("2026-03-09T23:59:00Z")
TIMEZONE = "UTC"
STATIONS = ["VILD0", "42099", "42101", "42105", "42096"]
VARIABLES = ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"]
UNITS = {"temp":"degC", "dwpt":"degC", "rhum":"percent", "prcp":"mm", "wspd":"km/h", "pres":"hPa"}
VERIFIED = "VERIFIED_IDENTITY_AND_HISTORIC_SITE_METADATA"

from weather_research.e3_spatial import nearest_timestamp_pairs
from weather_research.phase04_collection import (
    coverage_metrics, eligible_for_retrieval, fetch_observation_sources,
    missingness_rows, sha256_file, source_provider_grade_map, source_series,
    time_index, source_index, write_raw_frame,
)


METADATA = [
    {"station_id":"VILD0","station_name":"Ludhiana Airport / Meteostat VILD0 candidate","physical_identity_status":"UNVERIFIED",
     "official_station_identifier":"ICAO VILD (airport); Meteostat VILD0 crosswalk not independently documented",
     "latitude":None,"longitude":None,"elevation_m":None,"station_type":"Airport instrument exists; exact Meteostat sensor/site unresolved",
     "metadata_source":"AAI AIP VILD aerodrome data confirms airport identifier/location; IMD Aviation SOP lists VILD surface instrument; neither establishes Meteostat VILD0 identity",
     "source_url":"https://aim-india.aai.aero.in/eaip/eaip-v2-04-2026/eAIP/IN-AD%202.1VILD-en-GB.html | https://mausamaudit.imd.gov.in/imd_latest/contents/pdf/aviation_sop.pdf",
     "verification_notes":"Airport reference point is not an independently verified sensor coordinate. Excluded from retrieval and geographic calculations."},
    {"station_id":"42099","station_name":"Ludhiana","physical_identity_status":VERIFIED,
     "official_station_identifier":"WMO 42099; IMD/WIS2 station item 0-20000-0-42099",
     "latitude":30.8666667,"longitude":75.9333333,"elevation_m":255,"station_type":"WMO landFixed; IMD D.O.(IIa) surface observatory",
     "metadata_source":"IMD/WIS2 current station item plus IMD Climatological Normals 1981-2010, station location history table",
     "source_url":"https://wis2box.imd.gov.in/oapi/collections/stations/items/0-20000-0-42099?f=html | https://imdpune.gov.in/library/public/Climatological%20Normals%20%281981-2010%29/1981-2010%20CLIM%20NORMALS%20%28ALPHABETICAL%29.pdf",
     "verification_notes":"IMD source gives 30°52′N, 75°56′E, Hp 255 m and describes Civil Surgeon's Office observatory. Coordinates are historical minute-resolution; current site continuity/relocations not documented."},
    {"station_id":"42101","station_name":"Patiala","physical_identity_status":VERIFIED,
     "official_station_identifier":"WMO 42101; IMD/WIS2 station item 0-20000-0-42101",
     "latitude":30.3333333,"longitude":76.4666667,"elevation_m":251,"station_type":"WMO landFixed; IMD D.O.(I) surface observatory",
     "metadata_source":"IMD/WIS2 current station item plus IMD Climatological Normals 1981-2010, station location history table",
     "source_url":"https://wis2box.imd.gov.in/oapi/collections/stations/items/0-20000-0-42101?f=html | https://imdpune.gov.in/library/public/Climatological%20Normals%20%281981-2010%29/1981-2010%20CLIM%20NORMALS%20%28ALPHABETICAL%29.pdf",
     "verification_notes":"IMD source gives 30°20′N, 76°28′E, Hp 251 m and says Mohindra College; WIS2 operational item reports barometer height 252 m. Historical site/current continuity still needs instrument/site history."},
    {"station_id":"42105","station_name":"Chandigarh / Sarajpur (provider catalogue label)","physical_identity_status":"UNVERIFIED",
     "official_station_identifier":"Provider claims WMO 42105 / ICAO VICG; not matched to an official station record in this audit",
     "latitude":None,"longitude":None,"elevation_m":None,"station_type":"Unknown",
     "metadata_source":"Prior Meteostat crosswalk and provider catalogue only; official crosswalk not located",
     "source_url":"https://wis2box.imd.gov.in/oapi/collections/stations/items?f=html | https://meteostat.net/en/station/42105",
     "verification_notes":"Official IMD pages identify Chandigarh airport/city observatories but do not establish this provider ID's specific site. Excluded from retrieval and zones."},
    {"station_id":"42096","station_name":"Ferozepur (provider catalogue label)","physical_identity_status":"UNVERIFIED",
     "official_station_identifier":"Provider claims WMO 42096; official current identifier/site crosswalk not found",
     "latitude":None,"longitude":None,"elevation_m":None,"station_type":"Unknown",
     "metadata_source":"Prior Meteostat crosswalk only; no official station metadata source found",
     "source_url":"https://wis2box.imd.gov.in/oapi/collections/stations/items?f=html | https://meteostat.net/en/station/42096",
     "verification_notes":"No hourly range was listed in Phase 1B inventory. Excluded from retrieval and zones."},
]


def provider_counts(frame: pd.DataFrame) -> dict:
    return {str(source):int(count) for source,count in source_index(frame).value_counts(dropna=False).items()}


def _write_csv_once(frame: pd.DataFrame, path: Path) -> None:
    contents=frame.to_csv(index=False)
    if path.exists():
        existing=path.read_text(encoding="utf-8").replace("\r\n","\n")
        if existing == contents.replace("\r\n","\n"):
            return
        raise FileExistsError(f"Refusing to replace existing Phase 04 output: {path}")
    path.write_text(contents,encoding="utf-8")


def _write_outputs(frames: dict, per_station: dict, grades: dict, retrieved_at: str) -> None:
    metadata = pd.DataFrame(METADATA)
    metadata["metadata_retrieved_utc"] = retrieved_at
    _write_csv_once(metadata, OUT / "station_metadata_verification.csv")

    coverage_rows=[]
    miss_rows=[]
    all_source_counts={}
    interval_rows=[]
    candidate_file=ROOT / "phase03_model_revalidation" / "candidate_observations_8of12.csv"
    candidate_times=pd.DatetimeIndex(pd.to_datetime(pd.read_csv(candidate_file)["timestamp"],utc=True).unique()).sort_values()
    for station, frame in frames.items():
        if frame is None:
            continue
        metrics=coverage_metrics(frame, START, END, VARIABLES)
        entry=per_station[station]
        coverage_rows.append({"station_id":station,"retrieval_status":entry["status"],
                              **{k:v for k,v in metrics.items() if k!="variable_summary"},
                              "source_distribution_json":json.dumps(provider_counts(frame),sort_keys=True),
                              "candidate_timestamps_exact":None,
                              "candidate_timestamps_within_15min":None,
                              "candidate_timestamps_within_30min":None,
                              "candidate_timestamps_within_60min":None,
                              "model_sources_present":False if entry["settings"].get("model_setting") is False else None,
                              "provenance_completeness":"SOURCE_PROVIDER_IDS_RETAINED; upstream sensor chain unknown"})
        expected=pd.date_range(start=START,end=END,freq="h")
        present=pd.DatetimeIndex(time_index(frame).unique())
        absent=expected.difference(present)
        if len(absent):
            starts=[0]+[i for i in range(1,len(absent)) if absent[i]-absent[i-1] != pd.Timedelta(hours=1)]
            ends=starts[1:]+[len(absent)]
            for first,last in zip(starts,ends):
                interval_rows.append({"station_id":station,"gap_start_utc":absent[first],"gap_end_utc":absent[last-1],
                                      "missing_hour_count":last-first,"gap_type":"EXPECTED_TIMESTAMP_NOT_RETURNED"})
        for tol in (0,15,30,60):
            cand_dummy=pd.Series(1.0,index=candidate_times)
            station_dummy=pd.Series(1.0,index=present)
            cand_pairs=nearest_timestamp_pairs(cand_dummy,station_dummy,tol)
            coverage_rows[-1][f"candidate_timestamps_{'exact' if tol==0 else f'within_{tol}min'}"]=int(cand_pairs.neighbor_time.notna().sum())
        miss_rows.extend(missingness_rows(station,frame,START,END,VARIABLES))
    for station in STATIONS:
        if station not in frames:
            coverage_rows.append({"station_id":station,"retrieval_status":per_station[station]["status"],
                                  "source_time_rows":None,"unique_timestamps":None,"duplicate_source_time_rows":None,
                                  "timestamps_with_multiple_source_rows":None,"first_timestamp":None,"last_timestamp":None,
                                  "expected_hourly_timestamps":None,"available_expected_timestamps":None,
                                  "missing_expected_timestamps":None,"unexpected_timestamps_outside_requested_grid":None,
                                  "timezone":None,"source_distribution_json":"{}","model_sources_present":None,
                                  "provenance_completeness":"NOT_RETRIEVED"})
    _write_csv_once(pd.DataFrame(coverage_rows), OUT / "station_coverage_summary.csv")
    _write_csv_once(pd.DataFrame(miss_rows), OUT / "missingness_report.csv")
    _write_csv_once(pd.DataFrame(interval_rows), OUT / "missing_timestamp_intervals.csv")

    overlap_rows=[]
    comparisons=[]
    eligible_stations=list(frames)
    # No comparison against VILD0 unless its provider ID is tied to a verified
    # physical station and a station-level raw series is collected.
    for station in ["42099","42101","42105","42096"]:
        overlap_rows.append({"reference_station":"VILD0","station_id":station,"match_type":"EXACT_AND_TOLERANCE",
                             "matched_timestamp_pairs":None,"status":"NOT_COMPUTED_PRIMARY_STATION_IDENTITY_UNVERIFIED"})
        for variable in VARIABLES:
            for tolerance in (0,15,30,60):
                comparisons.append({"station_a":"VILD0","station_b":station,"variable":variable,"units":UNITS[variable],
                                    "source_a":None,"source_b":None,"tolerance_minutes":tolerance,"valid_pairs":None,
                                    "bias_neighbor_minus_primary":None,"rmse":None,
                                    "status":"NOT_COMPUTED_PRIMARY_STATION_IDENTITY_UNVERIFIED"})

    # Compare the two verified neighbors to assess their data availability and
    # preserve provider-source strata. This is descriptive, not E3 validation.
    if "42099" in frames and "42101" in frames:
        a,b=frames["42099"],frames["42101"]
        ia,ib=pd.DatetimeIndex(time_index(a).unique()),pd.DatetimeIndex(time_index(b).unique())
        for tol in (0,15,30,60):
            dummy_a=pd.Series(1.0,index=ia); dummy_b=pd.Series(1.0,index=ib)
            tm=nearest_timestamp_pairs(dummy_a,dummy_b,tol)
            overlap_rows.append({"reference_station":"42099","station_id":"42101",
                                 "match_type":"EXACT" if tol==0 else f"WITHIN_{tol}MIN",
                                 "matched_timestamp_pairs":int(tm.neighbor_time.notna().sum()),
                                 "status":"TIMESTAMP_COVERAGE_ONLY; not a VILD0 comparison"})
    for station,frame in frames.items():
        present=pd.DatetimeIndex(time_index(frame).unique())
        for tol in (0,15,30,60):
            pairs=nearest_timestamp_pairs(pd.Series(1.0,index=candidate_times),pd.Series(1.0,index=present),tol)
            overlap_rows.append({"reference_station":"8of12_candidate_times","station_id":station,
                                 "match_type":"EXACT" if tol==0 else f"WITHIN_{tol}MIN",
                                 "matched_timestamp_pairs":int(pairs.neighbor_time.notna().sum()),
                                 "status":"CANDIDATE_TIME_AVAILABILITY_ONLY; not a primary-station pair"})
    if "42099" in frames and "42101" in frames:
        a,b=frames["42099"],frames["42101"]
        for variable in VARIABLES:
            src_a,src_b=source_series(a,variable),source_series(b,variable)
            for source_a,ser_a in src_a.items():
                for source_b,ser_b in src_b.items():
                    grade_a,grade_b=grades.get(source_a,"UNSPECIFIED"),grades.get(source_b,"UNSPECIFIED")
                    for tol in (0,15,30,60):
                        pairs=nearest_timestamp_pairs(ser_a,ser_b,tol)
                        valid=pairs.neighbor_time.notna() & pairs.primary_value.notna() & pairs.neighbor_value.notna()
                        diffs=pairs.loc[valid,"difference_neighbor_minus_primary"].astype(float)
                        comparisons.append({"station_a":"42099","station_b":"42101","variable":variable,"units":UNITS[variable],
                                            "source_a":source_a,"source_grade_a":grade_a,"source_b":source_b,"source_grade_b":grade_b,
                                            "tolerance_minutes":tol,"valid_pairs":int(valid.sum()),
                                            "bias_neighbor_minus_primary":float(diffs.mean()) if len(diffs) else None,
                                            "rmse":float((diffs.pow(2).mean())**0.5) if len(diffs) else None,
                                            "status":"DESCRIPTIVE_PROVIDER_SOURCE_PAIR; NOT E3 corroboration; source/sensor lineage still limited"})
    _write_csv_once(pd.DataFrame(overlap_rows), OUT / "timestamp_overlap_report.csv")
    _write_csv_once(pd.DataFrame(comparisons), OUT / "pairwise_station_comparison.csv")

    # Coordinates are not assigned to the four candidates because the primary
    # physical sensor location (VILD0) is unresolved. Keep all provisional bands
    # with a clear non-assignment status rather than inventing a zone.
    zone_rows=[]
    for station in STATIONS:
        meta=next(row for row in METADATA if row["station_id"]==station)
        zone_rows.append({"station_id":station,"verified_latitude":meta["latitude"],"verified_longitude":meta["longitude"],
                          "distance_from_VILD0_km":None,"elevation_difference_m":None,"zone":None,
                          "metadata_source":meta["source_url"],"verification_status":meta["physical_identity_status"],
                          "assignment_status":"NOT_ASSIGNED_PRIMARY_SENSOR_COORDINATES_UNVERIFIED"})
    _write_csv_once(pd.DataFrame(zone_rows), OUT / "geographic_zone_assignment.csv")

    eligible_count=sum(row["physical_identity_status"]==VERIFIED for row in METADATA if row["station_id"]!="VILD0")
    exact_neighbor_overlap=next((row["matched_timestamp_pairs"] for row in overlap_rows
                                 if row["reference_station"]=="42099" and row["station_id"]=="42101" and row["match_type"]=="EXACT"),0)
    readiness={
        "status":"BLOCKED_BY_METADATA",
        "assessment_date_utc":retrieved_at,
        "verified_neighbor_count":eligible_count,
        "verified_primary_count":0,
        "primary_station":"VILD0",
        "exact_timestamp_overlap_with_primary":None,
        "tolerance_overlap_with_primary":None,
        "exact_timestamp_overlap_between_verified_neighbors":exact_neighbor_overlap,
        "source_provenance":"Meteostat provider source IDs retained; model/analysis/forecast grades excluded by package config. Upstream sensor chain and independence not established.",
        "geographic_zones_assigned":False,
        "reason":"The exact physical sensor/site represented by VILD0 is unresolved, so no verified primary timestamps or primary-relative distances can be used. Two neighboring WMO stations are identified, but their source labels alone do not prove independent sensor lineage.",
        "missing_data_semantics":"Missing data are reported as unavailable and are not interpreted as contradictory evidence.",
        "scientific_validation":"E3 not validated; current pairwise 42099/42101 output is descriptive availability/consistency only.",
    }
    readiness_text=json.dumps(readiness,indent=2)
    readiness_path=OUT / "e3_readiness_assessment.json"
    if readiness_path.exists():
        if readiness_path.read_text(encoding="utf-8") != readiness_text:
            raise FileExistsError(f"Refusing to replace existing Phase 04 output: {readiness_path}")
    else:
        readiness_path.write_text(readiness_text,encoding="utf-8")

    file_list=sorted(str(path.relative_to(OUT)).replace("\\","/") for path in OUT.rglob("*")
                     if path.is_file() and "_superseded_derived" not in path.parts)
    report=f"""# Phase 04 — Provenance-Aware Collection and Station Verification

**Status:** retrieval completed for two stations whose WMO identity and historical site metadata could be independently matched. No data were retrieved for stations with unresolved identity. No historical artifact was overwritten.

## Verified

- Meteostat **2.2.3** was installed in an isolated temporary environment for source inspection and retrieval; the project dependency file was not changed. Python was {platform.python_version()}.
- The v2.2.3 API has no `Hourly(model=False, flags=True)` signature. The verified API uses `config.include_model_data=False`; `TimeSeries.fetch` accepts `fill`, `sources`, and `clean`. This run explicitly set model inclusion false, `fill=False`, `clean=False`, `squash=False`, and `sources=True`. With unsquashed output, Meteostat retains source IDs as a `source` index level. The model setting was restored after each fetch.
- IMD/WIS2 identifies 42099 as Ludhiana (WMO 42099; barometer height 255 m; operational) and 42101 as Patiala (WMO 42101; operational; barometer height 252 m). IMD's 1981–2010 station metadata lists coordinates, site descriptions and elevations for both. The two were retrieved separately, preserving source-level rows.
- AAI's AIP identifies airport ICAO VILD and provides airport reference coordinates; IMD's Aviation SOP lists a surface instrument at VILD. These sources do not independently link Meteostat ID VILD0 to that instrument or establish the exact sensor coordinate, so VILD0 remains unverified.

## Repository and historical-artifact audit

- `requirements.txt` does not install or pin Meteostat. It contains only a commented historical `meteostat==1.7.6` note. Phase 1B records an isolated Meteostat 2.2.3 metadata query; Phase 1C's METAR adapter was blocked for the historical target interval.
- Existing station sources include the Phase 1A inventories and the Phase 1B station crosswalk/provider inventory. `outputs/station_provenance/station_manifest.json` says no observation retrieval was performed. Existing `verified_phase01/model_df.csv` and `X_multi.csv` are processed/model datasets, not raw station acquisition.
- Before this run, no raw station observation files were present in the repository. The earlier Phase 00 exports were supplied externally; their provenance remains unknown. The previous E3 report and historical experiment outputs are preserved and unchanged.
- `src/weather_research/retrieval.py` is retained for compatibility, but its v1 `Hourly(model=False)` branch does not request source flags; its v2 fallback does not pass `sources=True`. Phase 04 uses a new isolated retrieval helper and leaves the existing helper untouched.
- `SECOND_PASS_AUDIT.md` and `PROJECT_STATUS.md` were read. Their test counts describe historical checkpoints, not this Phase 04 run. The final test count is recorded after the full current suite is run.

## Station verification

| Candidate | Result | Retrieval |
|---|---|---|
| VILD0 | Airport VILD exists; Meteostat-ID-to-sensor crosswalk unverified | Not attempted |
| 42099 | WMO/IMD Ludhiana identity and historical site metadata verified | Retrieved with model exclusion and source IDs |
| 42101 | WMO/IMD Patiala identity and historical site metadata verified | Retrieved with model exclusion and source IDs |
| 42105 | Provider ID/site crosswalk unverified | Not attempted |
| 42096 | Official identifier/site crosswalk unverified; no hourly inventory | Not attempted |

Coordinates for 42099 and 42101 are minute-resolution historical IMD station coordinates. Current station operation is documented, but exact site-continuity/relocation records were not found. The VILD0 sensor site is unresolved; consequently **no distance or zone assignments** were made for any station.

## Retrieval results

Requested UTC period: {START.isoformat()} through {END.isoformat()} (inclusive request bounds). Raw, unsquashed Meteostat-returned frames and SHA-256 digests are in `retrieval_manifest.json` and `raw_station_data/`. The manifest records versions, settings, status, returned variables, missingness and source distribution. These are package-returned source-level records, not original provider HTTP payloads.

| Station | Status | Source-time rows | Unique timestamps | First | Last |
|---|---|---:|---:|---|---|
{''.join(f"| {r['station_id']} | {r['retrieval_status']} | {r['source_time_rows']} | {r['unique_timestamps']} | {r['first_timestamp']} | {r['last_timestamp']} |\n" for r in coverage_rows)}

The station coverage, variable missingness and exact/15/30/60-minute availability are in the corresponding CSVs. Tolerance matching remains distinct from exact matching. Precipitation is reported independently. Missingness is not evidence of disagreement.

## Source provenance and pairwise results

Meteostat source/provider identifiers were retained per source-level row. Forecast/analysis-grade providers were excluded by the version-specific model filter. The provider grade/source label does not establish the upstream instrument, correction history, or independence from other feeds; those limitations remain in the manifest.

Pairwise numerical summaries between 42099 and 42101 are source-stratified and descriptive only. Comparisons of either candidate to VILD0 were not computed because there is no verified primary series; no Phase 00 values were substituted. Precipitation has its own comparison rows and missingness status.

## E3 readiness: `BLOCKED_BY_METADATA`

Two neighbor identities are sufficiently verified for provenance-aware collection, but **zero verified primary identities** are available. Exact timestamp overlap between the two retrieved neighbor datasets is reported separately; it is not overlap with VILD0. No zone has adequate verified membership because primary sensor coordinates are unresolved. Source IDs are available, but do not provide complete sensor-lineage assurance. E3 remains unvalidated.

## Remaining requirements

1. Obtain an authoritative crosswalk and site history tying VILD0 to the primary sensor and its observation coordinates.
2. Resolve identities/site histories for 42105 and 42096 before collecting or zoning them.
3. Obtain instrument/source lineage and quality-control information for each source represented by Meteostat IDs.
4. After primary verification, calculate VILD0-relative distances and repeat exact/tolerance coverage and variable-wise comparisons without imputation.
5. Set variable-specific spatial agreement criteria before interpreting support or disagreement.

## Outputs

{''.join(f'- `{name}`\n' for name in file_list)}
"""
    report_path=OUT / "PHASE04_AUDIT_REPORT.md"
    if report_path.exists():
        if report_path.read_text(encoding="utf-8") != report:
            raise FileExistsError(f"Refusing to replace existing Phase 04 output: {report_path}")
    else:
        report_path.write_text(report,encoding="utf-8")


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--finalize-existing",action="store_true",help="Build missing derived reports from saved raw exports; never contacts Meteostat")
    args=parser.parse_args()
    if args.finalize_existing:
        manifest_path=OUT/"retrieval_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("Cannot finalize: retrieval_manifest.json is missing")
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        frames={}
        per_station=manifest["station_results"]
        for station,entry in per_station.items():
            if entry.get("status")=="SUCCESS_WITH_DATA":
                raw_path=OUT/entry["output_file"]
                if sha256_file(raw_path)!=entry["sha256"]:
                    raise RuntimeError(f"Raw-data hash mismatch; refusing to use {raw_path}")
                frame=pd.read_csv(raw_path,parse_dates=["time"])
                frame=frame.set_index(["time","source"])
                frames[station]=frame
        import meteostat as ms
        grades=source_provider_grade_map(ms)
        _write_outputs(frames,per_station,grades,manifest["retrieved_at_utc"])
        manifest["output_files"] = sorted(str(p.relative_to(OUT)).replace("\\","/") for p in OUT.rglob("*")
                                          if p.is_file() and "_superseded_derived" not in p.parts)
        for entry in manifest["station_results"].values():
            if entry.get("settings") and entry["settings"].get("meteostat_version") == "2.2.3":
                entry["settings"]["flags_setting"] = "NOT_SUPPORTED_AS_SEPARATE_ARGUMENT; source IDs retained via sources=True and squash=False"
        manifest["api_semantics"] = {
            "meteostat_version": "2.2.3",
            "hourly_model_argument": "NOT_SUPPORTED",
            "model_filter": "config.include_model_data=False",
            "source_retention": "fetch(sources=True, squash=False); source index retained",
            "fill": False,
            "clean": False,
            "cache_during_retrieval": False,
        }
        manifest_path.write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")
        return
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 04 output directory: {OUT}; use --finalize-existing to finish derived reports from recorded raw files")
    OUT.mkdir(parents=True)
    RAW.mkdir(parents=True)
    metadata=pd.DataFrame(METADATA)
    verified={row["station_id"]:row["physical_identity_status"] for row in METADATA}
    import meteostat as ms

    params=[ms.Parameter.TEMP,ms.Parameter.DWPT,ms.Parameter.RHUM,ms.Parameter.PRCP,ms.Parameter.WSPD,ms.Parameter.PRES]
    grades=source_provider_grade_map(ms)
    retrieved_at=datetime.now(timezone.utc).isoformat()
    frames={}
    per_station={}
    for station in STATIONS:
        if not eligible_for_retrieval(station,verified[station]):
            per_station[station]={"station_id":station,"status":"NOT_ATTEMPTED_IDENTITY_UNVERIFIED",
                                  "retrieved_at_utc":None,"row_count":None,"output_file":None,"sha256":None,
                                  "settings":{"model_setting":False,"fill_setting":False,"source_setting":True},
                                  "reason":"Excluded because authoritative station identity/site metadata is unresolved."}
            continue
        started=datetime.now(timezone.utc).isoformat()
        try:
            frame,settings=fetch_observation_sources(ms,station,START.to_pydatetime(),END.to_pydatetime(),TIMEZONE,params)
            if frame is None:
                status="SUCCESS_NO_DATA"
                raw_path=None
                digest=None
                row_count=0
                frames[station]=pd.DataFrame()
                cov={"variable_summary":{}}
                source_counts={}
            else:
                status="SUCCESS_WITH_DATA" if len(frame) else "SUCCESS_NO_DATA"
                source_counts=provider_counts(frame)
                forbidden={str(src):grades.get(str(src),"UNSPECIFIED") for src in source_counts
                           if grades.get(str(src),"UNSPECIFIED") in {"1","2"}}
                if forbidden:
                    raise RuntimeError(f"Model/analysis source IDs remained after explicit exclusion: {forbidden}")
                raw_path=RAW / f"{station}_hourly_source_level.csv"
                digest=write_raw_frame(frame,raw_path)
                row_count=len(frame)
                frames[station]=frame
                cov=coverage_metrics(frame,START,END,VARIABLES)
            entry={"station_id":station,"status":status,"retrieval_started_utc":started,
                   "retrieval_completed_utc":datetime.now(timezone.utc).isoformat(),"row_count":row_count,
                   "first_timestamp":cov.get("first_timestamp"),"last_timestamp":cov.get("last_timestamp"),
                   "output_file":str(raw_path.relative_to(OUT)).replace("\\","/") if raw_path else None,
                   "sha256":digest,"settings":settings,"available_variables":list(frame.columns) if frame is not None else [],
                   "missingness":cov.get("variable_summary",{}),"source_distribution":source_counts,
                   "provider_grades":{source:grades.get(source,"UNSPECIFIED") for source in source_counts},
                   "source_provenance_status":"SOURCE_IDS_RETAINED; UPSTREAM_SENSOR_LINEAGE_UNVERIFIED"}
            per_station[station]=entry
        except Exception as exc:
            per_station[station]={"station_id":station,"status":"FAILED","retrieval_started_utc":started,
                                  "retrieval_completed_utc":datetime.now(timezone.utc).isoformat(),"row_count":None,
                                  "output_file":None,"sha256":None,"settings":{"model_setting":False,"fill_setting":False,
                                  "source_setting":True},"error":repr(exc)}

    manifest={"schema_version":1,"phase":"04_provenance_aware_collection","retrieved_at_utc":retrieved_at,
              "repository_package_pin":None,"isolated_retrieval_package_version":ms.__version__,"python_version":platform.python_version(),
              "requested_start_utc":START.isoformat(),"requested_end_utc_inclusive":END.isoformat(),"timezone":TIMEZONE,
              "primary_station":"VILD0","retrieval_source":"Meteostat Provider.HOURLY annual source files via package API",
              "source_grade_map":grades,"station_results":per_station,
              "raw_export_semantics":"Unsquashed, unfilled, uncleaned DataFrame returned by Meteostat 2.2.3; source is an index level. Not original provider bytes.",
              "data_license_note":"Meteostat data attribution/non-commercial terms apply; verify exact provider license before publication or redistribution.",
              "no_model_training":True,"no_imputation":True,"no_existing_output_overwrite":True}
    (OUT/"retrieval_manifest.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")
    _write_outputs(frames,per_station,grades,retrieved_at)
    # Refresh manifest with hashes of generated raw files and declared output files.
    for station,entry in per_station.items():
        if entry.get("output_file"):
            entry["sha256_verified_after_export"]=sha256_file(OUT/entry["output_file"])
    manifest["station_results"]=per_station
    manifest["output_files"] = sorted(str(p.relative_to(OUT)).replace("\\","/") for p in OUT.rglob("*") if p.is_file())
    (OUT/"retrieval_manifest.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")


if __name__ == "__main__":
    main()
