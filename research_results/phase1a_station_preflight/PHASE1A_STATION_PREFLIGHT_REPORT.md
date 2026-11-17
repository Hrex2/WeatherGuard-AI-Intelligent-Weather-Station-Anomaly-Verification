# Phase 1A Station Availability and Provenance Preflight

**Status: PARTIALLY_COMPLETE_EXTERNAL_DATA_ACCESS_REQUIRED**  
**Executed:** 2026-11-17T10:08:23.161872+00:00  
**Base commit:** 9a3e5c9143f9a639088ba1ffb1e07377e8aac76c

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
