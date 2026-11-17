# Bounded raw-data retrieval proposal — approval required

**Prepared:** 2026-11-17  
**State:** Proposal only; no observation retrieval started.

## Purpose and evidence basis

Meteostat Python 2.2.3 `stations.inventory()` was run in a temporary isolated virtual environment on five station IDs. It returned 179 station × provider × parameter inventory metadata rows with date bounds and completeness percentages. This reads inventory metadata only; it does not fetch timeseries. The exact rows and retrieval/software timestamp are preserved in `meteostat_inventory_metadata.csv`. The repeated inventory response includes future end dates beyond the run date (up to 2026-11-25); they are retained in the source artifact but excluded from this proposal.

The available evidence is enough to define a provisional bounded request for observation-level inspection. It is not evidence of observed timestamp overlap or of seven-variable availability. The inventory lists `metar` for VILD0 with temperature, relative humidity, wind direction, wind speed, and pressure from 2020-06-18 through 2026-05-23/2026-06-19 depending on parameter; dew point and precipitation are not listed. 42105 has METAR inventory for those same five fields from 2017-01-20 through 2026-11-15; dew point and precipitation are not listed. For the source archive `isd_lite`, 42099 and 42101 show temperature, relative humidity, wind, pressure and wind direction through 2025-08-24; parameter completeness ranges 7–53%. 42105 ISD Lite shows temperature, relative humidity, wind and wind direction through 2025-02-19, with 1–4% completeness. These completeness values are provider inventory metadata, not computed from downloaded rows.

## Provisional staged request

### Primary and neighbor

- **Primary candidate:** VILD0. Reason: it is the current project station candidate, with provider METAR inventory for five event-relevant fields. Physical station linkage to the original processed project dataset still needs official verification.
- **First neighbor candidate:** 42105 (Chandigarh/Sarajpur, WMO 42105, ICAO VICG). Reason: a separate Meteostat record with METAR inventory for the same five fields and an inventory-envelope overlap with VILD0 across the project's full target period. At 89.92 km and +93 m elevation difference, it is only a conditional regional comparator; not yet justified as a local neighbor.
- **Conditional alternate:** 42101 (Patiala, WMO 42101), 76.04 km and −5 m provider-coordinate elevation difference. NOAA ISD Lite inventory indicates five hourly fields through 2025-08-24, but 42101 is not shown with overlapping METAR inventory and the source-specific data must be checked. Treat as regional context only.
- **Do not count 42099 yet:** It is 2.27 km from VILD0 and has ISD Lite inventory for five fields, but could be a duplicate/alias or distinct site. Exclude it from independent E3 corroboration pending official identity resolution. An optional non-independent comparison may be approved only to investigate duplicate behavior.
- **Exclude 42096:** no direct hourly source inventory is listed; its NOAA GHCN daily precipitation inventory ends 1970-12-31, before the project period. Forecast inventory is not a substitute for direct observation.

No candidate has enough evidence to be classified `SUITABLE_NEIGHBOUR_CANDIDATE` yet.

### Providers and fields

- Provider to request first: **Meteostat, filtered to provider `metar`**, for VILD0 and 42105. This is a provider-specific archived METAR source. It is not a claim that every returned row is a verified surface instrument reading; returned row-level `_source` fields and quality fields must be preserved and inspected.
- Potential later alternate: **Meteostat `isd_lite`** for 42101, and possibly 42099 only after identity resolution. Keep provider output separate; do not blend with METAR rows until source semantics and deduplication are documented.
- Proposed fields: temperature (`temp`), relative humidity (`rhum`), wind direction (`wdir`), wind speed (`wspd`), and pressure (`pres`). Inventory indicates these five fields for both VILD0 and 42105 METAR. Treat this as inventory-only pending records.
- Not proposed in the first bounded request: dew point (`dwpt`) and precipitation (`prcp`), because the selected station × METAR inventories do not list them for both stations. Do not infer or derive values for this request.
- Frequency: hourly dataset records. Do not aggregate daily values or mix them with hourly rows.

### Period, volume, and access

- **Start:** 2021-01-05.
- **End:** 2026-03-09 (inclusive), matching the processed project period. Provider-specific inventory bounds overlap this interval for the five proposed fields at both VILD0 and 42105.
- **Expected record count/file size:** unknown. Inventory bounds and completeness percentages cannot establish non-null row counts, exact shared timestamps, file volume, or source flag distributions. Do not budget or describe the provider files as complete hourly coverage.
- **Expected file count:** unknown until the approved retrieval client and response partitioning are fixed. At minimum, the preservation package would contain one raw provider response per station (two station payloads if the service returns one series per request), plus a manifest and provenance metadata. The provider may partition its response differently; do not assume the payload count.
- **Access:** Meteostat's public JSON API requires a RapidAPI key and subscription; its free tier is documented as 500 monthly calls. The Python package inventory call used no observation API key, but a bounded data request's current access/terms must be confirmed before retrieval. Meteostat documentation states its open hourly annual CSV endpoint combines historical databases, METAR and SYNOP, may substitute model data, and has per-variable `_source` columns; the proposal instead restricts provider metadata to `metar` to avoid intentionally requesting a mixed provider stream.

## Retrieval and provenance controls

After explicit approval, retrieval must preserve original provider response/file bytes, query parameters, provider and station IDs, UTC retrieval time, timestamp/timezone convention, original units, all `_source` fields, quality flags, missing values, package and dependency versions, license/usage terms, and SHA-256 hashes. Retain station/provider inventories separately from observations. Validate duplicated timestamps, cadence, out-of-period values, gaps, missingness and actual shared timestamps before any E3 design. Do not fill missing observations from forecasts, models, interpolation, daily data, or another station.

The provider-level inventory end dates contain values after the 2026-11-17 retrieval date. Treat those future values as a provider metadata anomaly; they are excluded from the proposed period and should be rechecked immediately before any approved retrieval.

## Outstanding conditions

1. Resolve whether VILD0 and 42099 are aliases or distinct physical sites through an official operator/IMD station-register record.
2. Confirm VILD0's relation to the project processed data source and obtain operator history/relocation evidence.
3. Confirm that Meteostat allows a source-filtered `metar` request for these IDs and that row-level source flags can be retained.
4. Verify actual populated values, quality flags, timestamp conventions, and common timestamps after approval; inventory ranges are only temporal envelopes.
5. Decide whether 42105 at 89.92 km has appropriate regional representativeness for the research question.
6. For any IMD alternative, check station and variable availability through the public portal and obtain the applicable registration documents, cost estimate, permission, and usage terms before request.

**NO RAW HISTORICAL DATA DOWNLOAD UNTIL THE USER APPROVES THE PROPOSED STATIONS, VARIABLES, PERIOD AND PROVIDERS.**
