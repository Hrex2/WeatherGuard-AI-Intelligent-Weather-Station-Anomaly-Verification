from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
from weather_research.station_preflight import (  # noqa: E402
    PARAMETERS, classify_suitability, inventory_parameter_records, parse_station_inventory,
    write_preflight_manifest,
)

INVENTORY = ROOT / "outputs" / "station_provenance" / "station_manifest.json"
OUT = ROOT / "research_results" / "phase1a_station_preflight"
SOURCES = {
    "repository_inventory": "outputs/station_provenance/station_manifest.json",
    "phase02_report": "PHASE02_PROVENANCE_REPORT.md",
    "spatial_summary": "phase03_model_revalidation/spatial_comparison_summary.csv",
    "phase03_manifest": "phase03_model_revalidation/phase03_integrity_manifest.json",
    "meteostat_vild0": "https://meteostat.net/en/station/VILD0",
    "meteostat_42099": "https://meteostat.net/en/station/42099",
    "meteostat_42101": "https://meteostat.net/en/station/42101",
    "meteostat_42105": "https://meteostat.net/en/station/42105",
    "meteostat_42096": "https://meteostat.net/en/station/42096",
    "meteostat_inventory_docs": "https://dev.meteostat.net/python/stations/inventory",
    "meteostat_hourly_docs": "https://dev.meteostat.net/data/timeseries/hourly.html",
    "meteostat_station_inventory_docs": "https://dev.meteostat.net/python/stations/inventory",
    "imd_station_list": "https://imdpune.gov.in/library/public/Climatological%20Tables%201991-2020.pdf",
    "imd_wis2_station_api": "https://wis2box.imd.gov.in/oapi/collections/stations/items/0-20000-0-42099?f=html",
    "imd_data_portal": "https://dsp.imdpune.gov.in/",
}
METEOSTAT_FACTS = {
    "VILD0": {"name": "Ludhiana / Doraha", "lat": 30.8547, "lon": 75.9526, "elev": 254,
              "region": "PB", "provider_id": "VILD0", "national_id": None, "wmo": None, "icao": "VILD",
              "hourly": ("2020-06-18", "2026-03-09"), "daily": None, "source": SOURCES["meteostat_vild0"]},
    "42099": {"name": "Ludhiana", "lat": 30.8667, "lon": 75.9333, "elev": 255,
              "region": "PB", "provider_id": "42099", "national_id": None, "wmo": "42099", "icao": None,
              "hourly": ("1973-01-01", "2025-08-24"), "daily": ("1901-01-01", "2025-08-24"), "source": SOURCES["meteostat_42099"]},
    "42101": {"name": "Patiala", "lat": 30.3333, "lon": 76.4667, "elev": 249,
              "region": "PB", "provider_id": "42101", "national_id": None, "wmo": "42101", "icao": None,
              "hourly": ("1973-01-01", "2025-04-05"), "daily": ("1975-03-20", "2026-02-28"),
              "source": "https://meteostat.net/en/station/42101"},
    "42105": {"name": "Chandigarh / Sarajpur", "lat": 30.7333, "lon": 76.8833, "elev": 347,
              "region": "CH", "provider_id": "42105", "national_id": None, "wmo": "42105", "icao": "VICG",
              "hourly": ("2015-12-09", "2025-11-13"), "daily": ("1954-01-08", "2025-08-22"),
              "source": "https://meteostat.net/en/station/42105"},
    "42096": {"name": "Ferozepur", "lat": 30.9167, "lon": 74.6667, "elev": 199,
              "region": "PB", "provider_id": "42096", "national_id": None, "wmo": "42096", "icao": None,
              "hourly": None, "daily": ("1950-01-11", "1970-12-31"),
              "source": "https://meteostat.net/en/station/42096"},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a conservative Phase 1A station preflight.")
    parser.add_argument("--online", action="store_true", help="Attempt optional installed Meteostat inventory checks; never downloads observations.")
    args = parser.parse_args()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    stations = parse_station_inventory(inventory)
    # Keep provider identities separate. Repository links between codes and IDs are leads, not identity merges.
    rows = []
    for station in stations:
        sid = station["station_id"]
        facts = METEOSTAT_FACTS.get(sid)
        providers = ["Meteostat", "IMD"]
        for provider in providers:
            meteo = facts if provider == "Meteostat" else None
            rows.append({"station_id": sid, "station_code": sid if sid == "VILD0" else "",
                         "station_name": meteo["name"] if meteo else (station["reported_location"] or "Unverified candidate identity"),
                         "provider": provider,
                         "provider_station_id": meteo["provider_id"] if meteo else None,
                         "national_id": meteo["national_id"] if meteo else None,
                         "wmo_id": meteo["wmo"] if meteo else None, "icao_id": meteo["icao"] if meteo else None,
                         "latitude": meteo["lat"] if meteo else None, "longitude": meteo["lon"] if meteo else None,
                         "elevation_m": meteo["elev"] if meteo else None,
                         "country": "IN (provider-reported)" if meteo else None,
                         "administrative_region": meteo["region"] if meteo else None,
                         "metadata_source": meteo["source"] if meteo else SOURCES["repository_inventory"],
                         "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                         "verification_status": "PROVIDER_METADATA_REVIEWED" if meteo else "METADATA_ONLY",
                         "confidence": "PROVIDER_REPORTED_NOT_INDEPENDENTLY_FIELD_VERIFIED" if meteo else "LOW_UNVERIFIED",
                         "hourly_inventory_start": meteo["hourly"][0] if meteo and meteo["hourly"] else None,
                         "hourly_inventory_end": meteo["hourly"][1] if meteo and meteo["hourly"] else None,
                         "daily_inventory_start": meteo["daily"][0] if meteo and meteo["daily"] else None,
                         "daily_inventory_end": meteo["daily"][1] if meteo and meteo["daily"] else None,
                         "notes": "Provider station-page metadata; not proof of populated direct observations or historical project source." if meteo else "IMD identity/coordinates/provider linkage were not checked for this row."})

    availability = []
    network_status = "DOCUMENTATION_AND_STATION_METADATA_REVIEWED_API_NOT_QUERIED"
    online_notes = "Reviewed public station metadata pages and docs; parameter-specific inventory API was not called, and no raw observations were downloaded."
    if args.online:
        try:
            import meteostat as ms
            version = importlib.metadata.version("meteostat")
            network_status = "ATTEMPTED"
            for sid in [s["station_id"] for s in stations]:
                try:
                    inv = ms.stations.inventory(sid)
                    availability.extend(inventory_parameter_records(sid, inv))
                except Exception as exc:
                    for parameter in PARAMETERS:
                        availability.append({"station_id": sid, "provider": "Meteostat", "parameter": parameter,
                                             "availability_status": "NOT_CHECKED", "frequency": "", "start_date": "", "end_date": "",
                                             "data_type": "", "source_indicator_available": "", "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                             "notes": f"Inventory request unavailable: {type(exc).__name__}"})
            online_notes = f"Installed Meteostat {version}; inventory call attempted. Inventory metadata only; no observation rows fetched."
        except importlib.metadata.PackageNotFoundError:
            network_status = "NOT_CHECKED_PACKAGE_NOT_INSTALLED"
            online_notes = "--online requested, but Meteostat Python package is not installed; no dependency was installed."
    if not availability:
        for station in stations:
            for provider in ("Meteostat", "IMD"):
                for parameter in PARAMETERS:
                    facts = METEOSTAT_FACTS.get(station["station_id"]) if provider == "Meteostat" else None
                    interval = facts["hourly"] if facts else None
                    status = "NOT_CHECKED"
                    availability.append({"station_id": station["station_id"], "provider": provider, "parameter": parameter,
                                         "availability_status": status,
                                         "frequency": "hourly station inventory (not parameter-level)" if interval else ("daily only; hourly inventory not listed" if facts else ""),
                                         "start_date": interval[0] if interval else "", "end_date": interval[1] if interval else "",
                                         "data_type": "provider-aggregated inventory; source per observation not retrieved" if facts else "",
                                         "source_indicator_available": "Documented per variable in bulk format; values not fetched" if facts else "",
                                         "retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                                         "notes": ("Station-level inventory only; this does not verify this parameter's populated timestamps or direct/model source." if facts else "IMD parameter-specific coverage not checked.")})

    suitability = []
    primary = next(s for s in stations if s["role"] == "primary")
    primary_meta = METEOSTAT_FACTS.get(primary["station_id"])
    for station in stations:
        if station["role"] == "primary":
            continue
        facts = METEOSTAT_FACTS.get(station["station_id"])
        if facts and primary_meta:
            from weather_research.station_preflight import haversine_km
            distance = haversine_km(primary_meta["lat"], primary_meta["lon"], facts["lat"], facts["lon"])
            elev_diff = facts["elev"] - primary_meta["elev"]
        else:
            distance, elev_diff = None, None
        category, reason = classify_suitability(primary_coordinates=bool(primary_meta),
                                                  neighbor_coordinates=bool(facts),
                                                  elevation_known=bool(facts), parameter_overlap=False,
                                                  observed_overlap=False, direct_source=False)
        if facts and facts["hourly"] is None:
            category, reason = "UNSUITABLE", "Meteostat page lists no hourly inventory and daily inventory ends in 1970; current candidate period does not overlap the processed 2021–2026 project period."
        suitability.append({"primary_station": primary["station_id"], "candidate_neighbor": station["station_id"],
                            "distance_km": round(distance, 2) if distance is not None else None,
                            "elevation_difference_m": elev_diff,
                            "parameter_overlap": "NOT_CHECKED", "temporal_overlap_status": "INVENTORY_PERIOD_OVERLAPS_NOT_OBSERVATION_VERIFIED" if facts and facts["hourly"] else "NO_HOURLY_INVENTORY_LISTED",
                            "suitability_category": category,
                            "reason": reason + " Distances use provider-reported coordinates only; parameter-populated observations and direct source are unverified."})

    if OUT.exists() and any(OUT.iterdir()):
        raise FileExistsError(f"Refusing to overwrite existing preflight results: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT / "station_inventory.csv", index=False)
    pd.DataFrame(availability).to_csv(OUT / "station_parameter_availability.csv", index=False)
    pd.DataFrame(suitability).to_csv(OUT / "neighbour_suitability.csv", index=False)
    reviewed = {"meteostat_vild0", "meteostat_42099", "meteostat_42101", "meteostat_42105", "meteostat_42096",
                "meteostat_inventory_docs", "meteostat_hourly_docs", "imd_station_list"}
    sources = {"retrieval_timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "query_type": "repository inventory and public provider station-page/documentation review; parameter API and observations not queried",
               "provider_versions": {"meteostat_python": None, "reason": "package not installed"},
               "network_status": network_status, "provider_notes": online_notes,
               "sources": [{"name": k, "url_or_path": v,
                            "response_status": ("REPOSITORY_READ" if not v.startswith("http") else
                                                "DOCUMENTATION_OR_METADATA_REVIEWED" if k in reviewed else
                                                "NOT_VERIFIED" if k == "imd_data_portal" else "REQUEST_TIMED_OUT"),
                            "verification_note": "Does not establish observation availability or historical dataset provenance."}
                           for k, v in SOURCES.items()]}
    (OUT / "station_source_registry.json").write_text(json.dumps(sources, indent=2)+"\n", encoding="utf-8")
    report = f'''# Phase 1A Station Availability and Provenance Preflight

**Status: PARTIALLY_COMPLETE_EXTERNAL_DATA_ACCESS_REQUIRED**
**Executed:** {datetime.now(timezone.utc).isoformat()}
**Base commit:** {subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()}

## Executive summary

The repository identifies primary candidate VILD0 and four neighbor candidates (42099, 42101, 42105, 42096). This preflight did not find raw primary or neighbor observation exports with source/retrieval metadata. Existing spatial CSVs are derived comparison products and are not evidence of independent source provenance. No parameter-specific populated observation coverage was verified. E3 suitability therefore remains **INSUFFICIENT_METADATA** for all four candidates. No raw observations were downloaded.

## Repository inventory findings

Candidate identities originate in `outputs/station_provenance/station_manifest.json`, `PHASE02_PROVENANCE_REPORT.md`, notebook cells in `Weather_Station_Anomaly_Detection_Master.ipynb` and `Weather_Station_Anomaly_Detection_Exploratory_Archive.ipynb`, and derived `phase03_model_revalidation/spatial_comparison_*.csv` files. Public Meteostat station pages supplied provider-reported metadata and station-level inventory intervals for all five IDs. These do not prove the processed project files were acquired from Meteostat, or that hourly rows are direct observations. No Meteostat package is installed.

| Candidate | Repository role/name lead | Reported history only | Metadata/data status |
|---|---|---|---|
| VILD0 | Ludhiana / Doraha; 30.8547, 75.9526; 254 m; ICAO VILD; hourly inventory 2020-06-18–2026-03-09 | Processed snapshot 2021-01-05–2026-03-09 | Provider-page metadata reviewed; instrument/source history unverified |
| 42099 | Ludhiana; 30.8667, 75.9333; 255 m; WMO 42099; hourly inventory 1973-01-01–2025-08-24 | 567 rows and 2025 dates are repository claims; Haversine to VILD0 is 2.27 km using provider coordinates | Provider page metadata; observation-level directness unverified |
| 42101 | Patiala; 30.3333, 76.4667; 249 m; WMO 42101; hourly inventory 1973-01-01–2025-04-05 | 1,188 rows and 2025 dates are repository claims; calculated distance is 76.04 km | Provider page and IMD climatological station listing identify Patiala; raw coverage unverified |
| 42105 | Chandigarh / Sarajpur; 30.7333, 76.8833; 347 m; WMO 42105, ICAO VICG; hourly inventory 2015-12-09–2025-11-13 | 6 rows claim; calculated distance is 89.92 km | Provider page metadata; raw coverage unverified |
| 42096 | Ferozepur; 30.9167, 74.6667; 199 m; WMO 42096; no hourly interval listed, daily inventory 1950-01-11–1970-12-31 | Repository reports 0 records for an investigated interval | Not suitable for current hourly E3 period on inventory evidence; absence of hourly listing is not proof of permanent nonexistence |

## Identity and provider findings

Meteostat public station pages report names, coordinates, elevation, provider IDs and inventory ranges for all candidates (retrieved by page review on the execution date). These are provider metadata, not independent instrument verification. VILD0 and 42099 are distinct Meteostat station identifiers with coordinates only 2.27 km apart; do not merge them. IMD's climatological station table identifies 42099 as Ludhiana and 42101 as Patiala. The other IDs have not been confirmed against an official IMD station list in this preflight. Meteostat pages list data provided from NOAA, DWD and Environment Canada generally, but do not establish variable-level sources for candidate records without retrieving data and source flags.

## Parameter availability and temporal coverage

Meteostat pages report station-level hourly inventory ranges for VILD0, 42099, 42101 and 42105; 42096 lists no hourly interval and only a historic daily interval. These ranges overlap the project snapshot period for the first four stations at inventory level only. The installed Meteostat package is absent, so its documented provider/parameter-specific `stations.inventory` API could not be invoked. All seven parameter rows remain `NOT_CHECKED`; station-level inventory does not verify parameter-populated timestamps. Meteostat hourly data documentation says records aggregate historical databases, METAR and SYNOP, may use model data as a substitute, and include per-variable source columns. No observation timestamp or source-indicator values were fetched.

## Preliminary neighbor suitability

All four candidates remain conditional or unsuitable for E3. Meteostat-coordinate Haversine distances/elevation differences from VILD0 are: 42099 2.27 km / +1 m; 42101 76.04 km / −5 m; 42105 89.92 km / +93 m; 42096 122.90 km / −55 m. 42099, 42101 and 42105 are `CONDITIONAL_CANDIDATE`: station-level hourly ranges overlap, but parameter-populated timestamp overlap and direct-source status are unverified. 42096 is `UNSUITABLE` for the current hourly period because Meteostat lists no hourly range and daily inventory ends in 1970. Distances are descriptive; no universal cutoff was chosen. No overlap was calculated from observation records.

## IMD and Meteostat access

- **IMD:** The public climatological station list can establish station-index identity for 42099, but not hourly historical availability. The IMD Data Service Portal was not inspected beyond its public landing URL; request requirements, fees, variables and historical coverage are `NOT_VERIFIED`. No login/payment was attempted.
- **Meteostat:** Official docs describe `stations.inventory` and hourly timeseries/bulk products. Inventory is parameter/provider specific. The current installed Python package is absent; no version/API call was attempted. Provider pages list hourly station-level ranges for VILD0, 42099, 42101 and 42105, and no hourly range for 42096. Hourly bulk data combine multiple sources and may substitute model data; per-variable source indicators are documented. Bulk files and observations were not downloaded. No provider response established populated direct observations for individual parameters.

## Provenance limitations and unresolved questions

Meteostat metadata pages provide coordinates/elevation but remain provider-reported; no independent geodetic/field or sensor history was inspected. Raw data, parameter-level availability, retrieval query, package/API version, quality flags and readback hashes remain unavailable. Official IMD identifiers were confirmed for 42099 and 42101, but IMD DSP access/requests were not verified. The existing spatial comparisons cannot establish direct station measurements or temporal representativeness.

## Recommended Phase 1B actions

1. Independently verify Meteostat coordinates and station identities with official station-register/operator metadata, including VILD0 and all four candidates.
2. Determine IMD portal request requirements manually; confirm hourly variables and years before submitting any request.
3. If Meteostat is to be evaluated, install/pin its current documented client only in an isolated environment and query inventory by station, provider and parameter. Preserve the raw response and software version.
4. Before any bulk retrieval, obtain approval and define a bounded year/station request. Retain per-variable source indicators; exclude model/interpolated values from primary E3 evidence.
5. Retrieve small controlled samples only after access and provenance are confirmed, then audit timestamps, cadence, duplicates, missingness, flags and true observed temporal overlap.

No E3 validation, event confirmation, station fault conclusion, model fitting, prediction generation or historical result modification occurred.
'''
    (OUT / "PHASE1A_STATION_PREFLIGHT_REPORT.md").write_text(report, encoding="utf-8")
    input_paths = [INVENTORY, ROOT / "PHASE02_PROVENANCE_REPORT.md",
                   ROOT / "phase03_model_revalidation" / "phase03_integrity_manifest.json",
                   ROOT / "phase03_model_revalidation" / "spatial_comparison_summary.csv"]
    try:
        meteostat_version = importlib.metadata.version("meteostat")
    except importlib.metadata.PackageNotFoundError:
        meteostat_version = None
    write_preflight_manifest(OUT, commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                             inputs=input_paths,
                             summary={"station_count": len(stations), "candidate_neighbor_count": len(suitability),
                                      "provider_metadata_reviewed_identity_count": len(METEOSTAT_FACTS),
                                      "imd_station_index_id_count": 2,
                                      "independently_field_verified_identity_count": 0,
                                      "parameter_count": len(PARAMETERS),
                                      "availability_statuses": {"NOT_CHECKED": len(availability)},
                                      "suitability_statuses": {key: sum(row["suitability_category"] == key for row in suitability)
                                                               for key in sorted({row["suitability_category"] for row in suitability})},
                                      "historical_files_modified": False},
                             network_status=network_status,
                             environment={"python": platform.python_version(), "platform": platform.platform(),
                                          "meteostat_package_version": meteostat_version}, repo_root=ROOT)
    from weather_research.station_preflight import verify_preflight_manifest
    verify_preflight_manifest(OUT, repo_root=ROOT)
    print(f"Wrote Phase 1A preflight to {OUT}")
    print(f"Stations: {len(stations)}; candidates: {len(suitability)}; parameter rows: {len(availability)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
