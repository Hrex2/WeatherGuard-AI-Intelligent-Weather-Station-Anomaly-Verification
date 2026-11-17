"""Generate Phase 1B readiness artifacts from reviewed metadata; never fetch observations."""
from __future__ import annotations

import argparse
import csv
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "research_results" / "phase1b_station_identity"
STATIONS = [
    {"id":"VILD0","name":"Ludhiana / Doraha","official":"","aliases":"Doraha; Ludhiana","icao":"VILD","wmo":"","ghcn":"","lat":30.8547,"lon":75.9526,"elev":254,"region":"PB","hourly_start":"2020-06-18","hourly_end":"2026-03-09","daily_start":"","daily_end":"","url":"https://meteostat.net/en/station/VILD0","note":"ICAO VILD; Meteostat directory also lists IATA LUH and GHCNh INI0000VILD. Operator and history not verified."},
    {"id":"42099","name":"Ludhiana","official":"WMO 42099","aliases":"Ludhiana","icao":"","wmo":"42099","ghcn":"IN018091100","lat":30.8667,"lon":75.9333,"elev":255,"region":"PB","hourly_start":"1973-01-01","hourly_end":"2025-08-24","daily_start":"1901-01-01","daily_end":"2025-08-24","url":"https://meteostat.net/en/station/42099","note":"Meteostat identifiers include WMO 42099, GHCN IN018091100, USAF 420990. IMD climatological table lists Ludhiana 42099; no coordinates/site history verified."},
    {"id":"42101","name":"Patiala","official":"WMO 42101","aliases":"Patiala","icao":"","wmo":"42101","ghcn":"IN018103100","lat":30.3333,"lon":76.4667,"elev":249,"region":"PB","hourly_start":"1973-01-01","hourly_end":"2025-04-05","daily_start":"1975-03-20","daily_end":"2026-02-28","url":"https://meteostat.net/en/station/42101","note":"Meteostat identifiers include WMO 42101, GHCN IN018103100, USAF 421010, GHCNh INM00042101. IMD climatological table lists Patiala 42101; no site history verified."},
    {"id":"42105","name":"Chandigarh / Sarajpur","official":"WMO 42105","aliases":"Chandigarh; Sarajpur","icao":"VICG","wmo":"42105","ghcn":"IN006011400","lat":30.7333,"lon":76.8833,"elev":347,"region":"CH","hourly_start":"2015-12-09","hourly_end":"2025-11-13","daily_start":"1954-01-08","daily_end":"2025-08-22","url":"https://meteostat.net/en/station/42105","note":"Meteostat identifiers include WMO 42105, ICAO VICG, GHCN IN006011400, USAF 427052, GHCNh INI0000VICG. Operator/history not verified."},
    {"id":"42096","name":"Ferozepur","official":"WMO 42096","aliases":"Ferozepur; Firozpur","icao":"","wmo":"42096","ghcn":"IN018031000","lat":30.9167,"lon":74.6667,"elev":199,"region":"PB","hourly_start":"","hourly_end":"","daily_start":"1950-01-11","daily_end":"1970-12-31","url":"https://meteostat.net/en/station/42096","note":"Meteostat identifiers include WMO 42096, GHCN IN018031000, GHCNh INM00042096. Operator/history not verified; no hourly range listed."},
]
PARAMETERS = ["temperature","dew_point","relative_humidity","precipitation","wind_speed","wind_direction","pressure"]
PARAM_CODES = {"temp":"temperature","dwpt":"dew_point","rhum":"relative_humidity","prcp":"precipitation","wspd":"wind_speed","wdir":"wind_direction","pres":"pressure"}
PROVIDER_FREQUENCIES = {"ghcnd":"daily","daily":"daily","climat":"monthly","hourly":"hourly","ghcnh":"hourly","isd_lite":"hourly","metar":"hourly","metno_forecast":"hourly","era5":"hourly","reanalysis":"hourly"}
NON_OBSERVATION_PROVIDERS = {"metno_forecast","era5","reanalysis","dwd_mosmix"}


def write_csv(path: Path, rows: list[dict]) -> None:
    if rows:
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    crosswalk=[]
    for s in STATIONS:
        crosswalk.append({"provider":"Meteostat","provider_station_id":s["id"],"official_station_id":s["official"],"station_name":s["name"],"alternative_names":s["aliases"],"latitude":s["lat"],"longitude":s["lon"],"elevation_m":s["elev"],"operator":"Unknown / not verified","country":"IN","administrative_region":s["region"],"icao_id":s["icao"],"wmo_id":s["wmo"],"other_provider_ids":s["ghcn"],"hourly_inventory_start":s["hourly_start"],"hourly_inventory_end":s["hourly_end"],"daily_inventory_start":s["daily_start"],"daily_inventory_end":s["daily_end"],"identity_relationship":"IDENTITY_UNRESOLVED","verification_status":"PROVIDER_METADATA_REVIEWED_NOT_FIELD_VERIFIED","source_url":s["url"],"metadata_retrieved_utc":timestamp,"confidence":"MEDIUM_FOR_PROVIDER_METADATA_LOW_FOR_PHYSICAL_IDENTITY","notes":s["note"]})
    write_csv(OUT/"station_identity_crosswalk.csv",crosswalk)
    inventory_path=OUT/"meteostat_inventory_metadata.csv"
    inventory=[]
    if inventory_path.is_file():
        with inventory_path.open(encoding="utf-8-sig",newline="") as stream:
            inventory=list(csv.DictReader(stream))
    availability=[]
    for s in STATIONS:
      station_rows=[row for row in inventory if row["station_id"]==s["id"]]
      providers=sorted({row["provider_id"] for row in station_rows})
      for provider_id in providers:
       frequency=PROVIDER_FREQUENCIES.get(provider_id,"unknown")
       for p in PARAMETERS:
        code=next((code for code,target in PARAM_CODES.items() if target==p),"")
        match=next((row for row in station_rows if row["provider_id"]==provider_id and row["parameter_code"]==code),None)
        availability.append({"provider":"Meteostat","provider_id":provider_id,"station_id":s["id"],"parameter":p,"potential_inventory_availability":"LISTED" if match else "NOT_LISTED_FOR_PROVIDER","observation_availability_verification":"INVENTORY_ONLY" if match else "NOT_LISTED_IN_INVENTORY","direct_observation_evidence":"PROVIDER_TYPE_OBSERVATION_ARCHIVE" if match and provider_id in {"metar","isd_lite","ghcnh","ghcnd"} else ("MODEL_OR_FORECAST_PROVIDER" if match and provider_id in NON_OBSERVATION_PROVIDERS else "SOURCE_NOT_ESTABLISHED"),"source_indicator_availability":"DATA_FORMAT_DOCUMENTS_PER_COLUMN_SOURCE_FIELD; ROW_VALUES_NOT_RETRIEVED","sampling_frequency":frequency,"inventory_start":match["start_date"] if match else "","inventory_end":match["end_date"] if match else "","completeness_percent":match["completeness_percent"] if match else "","retrieved_utc":match["retrieved_utc"] if match else timestamp,"package_version":match["meteostat_python_version"] if match else "2.2.3","evidence_url":"https://dev.meteostat.net/python/stations/inventory","verification_status":"INVENTORY_ONLY" if match else "NOT_CHECKED","notes":"Provider/parameter inventory metadata only; no populated observation rows or per-variable source values fetched. Inventory end dates later than retrieval date were preserved verbatim and excluded from proposals."})
      for p in PARAMETERS:
        availability.append({"provider":"IMD","provider_id":"","station_id":s["id"],"parameter":p,"potential_inventory_availability":"NOT_CHECKED","observation_availability_verification":"NOT_CHECKED","direct_observation_evidence":"NOT_CHECKED","source_indicator_availability":"NOT_VERIFIED","sampling_frequency":"Public availability form shows daily/monthly only; hourly history not established","inventory_start":"","inventory_end":"","completeness_percent":"","retrieved_utc":timestamp,"package_version":"","evidence_url":"https://dsp.imdpune.gov.in/home_availability.php","verification_status":"NOT_CHECKED","notes":"No station/parameter availability selection performed; no request submitted."})
    write_csv(OUT/"provider_availability_comparison.csv",availability)
    files=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!="artifact_manifest.json"]
    manifest={"schema_version":1,"generated_utc":timestamp,"base_commit":"cbe53f830a2941556f7a9c48101da51536259b62","mode":"offline artifact generation from recorded metadata; no weather observation endpoint called","raw_observation_download_started":False,"files":[{"path":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"size_bytes":p.stat().st_size} for p in files]}
    (OUT/"artifact_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-raw-download",action="store_true",help="Reserved; this workflow has no bulk download implementation.")
    args=parser.parse_args()
    if args.approve_raw_download:
        parser.error("This Phase 1B preflight has no observation retrieval implementation; use a separately reviewed, explicitly bounded workflow.")
    build()


if __name__=="__main__": main()
