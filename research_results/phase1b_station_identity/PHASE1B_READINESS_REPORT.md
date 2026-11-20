# Phase 1B — Station Identity and Data Acquisition Readiness

**Assessment date:** 2026-11-17  
**Base:** `cbe53f830a2941556f7a9c48101da51536259b62`  
**Status:** `PARTIALLY_COMPLETE_EXTERNAL_ACCESS_REQUIRED`

## 1. Executive summary

Phase 1B improves on the Phase 1A station-page review by querying Meteostat 2.2.3's provider- and parameter-specific station inventory for all five candidates. The inventory returned 179 records with station, source-provider ID, parameter, start/end dates and a provider-reported completeness percentage. This checked metadata only. No weather observation rows or source-flag values were fetched.

VILD0 and 42099 remain `IDENTITY_UNRESOLVED`: their different provider IDs/names and 2.27 km coordinate separation do not prove either aliasing or distinct instruments. The IMD public portal confirms an authenticated request workflow and exposes a station/parameter availability and cost-estimate form, but this review did not log in or test station-specific availability. VILD0 and 42105 show overlapping Meteostat METAR inventories for five fields within the project interval; this is a bounded candidate request, not verified observation-level overlap. No candidate is yet approved as an E3-suitable neighbor.

The proposal is restricted to a first-stage, source-filtered Meteostat `metar` request for VILD0 and 42105, five listed variables, and 2021-01-05 through 2026-03-09 inclusive. Approval is required before any observation retrieval. Identity resolution, row-level source/quality review, and actual timestamp overlap remain outstanding.

## 2. Starting Phase 1A evidence

Phase 1A (`cbe53f8`) preserved the five candidate IDs, provider-page inventory periods, preliminary distances, and the distinction between catalogue inventory and observations. Its seven fields remained unchecked at parameter level. This phase leaves the Phase 1A directory untouched; the new analysis is in this directory. The prior package check had no Meteostat Python package installed.

## 3. Identity assessment

`station_identity_crosswalk.csv` records the provider metadata and uncertainty for VILD0, 42099, 42101, 42105, and 42096. Five small public station-directory JSON metadata responses were retrieved. They include Meteostat identifier, multilingual name, provider IDs, coordinates, elevation, region and timezone. They do not include independent operator/site history; no opening, closure or relocation dates were obtained.

VILD0 (ICAO VILD; GHCNh `INI0000VILD`) and 42099 (WMO 42099; GHCN `IN018091100`) have different identifiers, names, and coordinates (30.8547, 75.9526 vs 30.8667, 75.9333). The 2.27 km separation is larger than rounding at four decimal places; their elevations differ only 1 m. IMD's 1991–2020 climatological table lists station 42099 as Ludhiana, but does not establish that VILD0 is its alias or a distinct nearby site. Identity classification is `IDENTITY_UNRESOLVED`. Keep the records separate and do not count 42099 as independent corroboration pending an official station/operator crosswalk and history.

The assessment and evidence details are in [station_identity_assessment.md](station_identity_assessment.md).

## 4. Meteostat metadata and access

The current official Python inventory documentation describes `stations.inventory(station, providers=...)` as parameter- and provider-specific. The CLI also supports granularity, parameter and provider filters. Since neither package nor CLI was installed in the project's environment and the documented inventory mechanism was appropriate, Meteostat 2.2.3 was installed in an isolated temporary virtual environment and used for metadata-only inventory queries. No `requirements.txt` change was made. The inventory table was queried for all five stations in one batched call and preserved in `meteostat_inventory_metadata.csv` (179 records).

The public station JSON directory separately supplied metadata. Meteostat's authenticated JSON API documents RapidAPI key/subscription requirements (500 calls/month on its free tier). No API key was available or used. The inventory call used the package's station/inventory metadata database and did not fetch observation timeseries. Package version: 2.2.3; environment Python 3.12; no project dependency added.

### Provider-level inventory highlights

- **VILD0:** METAR inventory lists temp, relative humidity, wind direction, wind speed and pressure. Temp/RH/wind inventory bounds start 2020-06-18; pressure starts 2020-06-18; end bounds vary from 2026-05-23 to 2026-06-19. These records show 11–13% inventory completeness. No METAR dew point or precipitation row is listed. GHCN-Hourly inventory lists RH/temp/wind only from 2026-01-01 to 2026-06-19 (23%); not enough to establish pre-2026 coverage.
- **42099:** NOAA ISD Lite lists temp, RH, pressure, wind direction and wind speed from 1973-01-01 through 2025-08-24, with 5–7% provider completeness. Its daily GHCN precipitation is 1901-01-01 through 2025-08-24. Hourly precipitation appears only on 2012-09-04 in ISD Lite. No ISD Lite dew-point record is listed.
- **42101:** NOAA ISD Lite lists temperature, RH, pressure, direction and speed through 2025-08-24 (47–53% reported completeness; RH/temp start 1973-01-03). Hourly precipitation is listed for only 2012-09-04. GHCN-Hourly fields appear only from 2026-01-01, outside the original target's useful history for part of the period. Daily GHCN temperature/precipitation inventories are not hourly substitutes.
- **42105:** METAR lists temperature, RH, pressure, wind direction and speed from 2017-01-20 through 2026-11-15 (13–30%). NOAA ISD Lite has temp, RH, wind direction and speed through 2025-02-19 at 3–4% and no pressure row. GHCN-Hourly starts 2026-03-28, after the proposed end date. No METAR dew point or precipitation row is listed.
- **42096:** No historical direct hourly archive provider is listed in the inventory snapshot. GHCN-Daily lists precipitation 1950-01-11 to 1970-12-31. Forecast inventory is not direct historical observation evidence.

All provider/parameter inventory records are preserved in the CSV. `NOT_LISTED_IN_INVENTORY` means the parameter was absent from that provider's returned inventory snapshot; it does not prove no station ever observed it. Provider-reported “completeness” is reproduced verbatim and was not interpreted as expected record counts or a quality score.

## 5. Parameter availability and source attribution

Meteostat's inventory response provides parameter-specific inventory rows for actual provider IDs. Every listed row is classified `INVENTORY_ONLY`; it does not verify non-null values, data quality, or exact timestamps. Absent parameter/provider pairs are `NOT_CHECKED`/not listed in that provider inventory. IMD parameter coverage remains `NOT_CHECKED` for all five stations and seven requested fields.

The official Meteostat provider catalogue identifies METAR, NOAA ISD Lite, NOAA GHCN-Hourly and GHCN-Daily as named data providers, and separately identifies MET Norway Forecast and ERA5/reanalysis as forecast/model sources. The hourly dataset documentation states there is a `_source` field for each weather parameter and warns that the broad hourly annual dump can substitute model data for missing observations. No data rows were retrieved, so no per-row `_source` code, directness, aggregation lineage, or quality flag was inspected. Provider identity in the inventory is not a substitute for the row-level provenance field. Leave direct observation evidence unverified until an approved response is examined.

## 6. IMD access assessment

The public Data Service Portal describes itself as a historical observation procurement service. Its registration page states users must register, verify email, submit identity card and/or undertaking documentation, then complete an online Data Request Form; charges may apply. The portal also says users may explore NDC availability and estimate charges before request. Its public availability form exposes surface/rainfall and other product categories, station and parameter selectors, and daily/monthly frequency choices; no hourly choice was visible in the accessible form. Thus hourly access is not established. No account was created, no station/parameter search was made, and no request/payment was submitted. Fees depend on applicant category/product; they were not determined.

## 7. Primary and neighbor strategy

- **Primary candidate:** VILD0, because it is the project anchor and has METAR inventory for five relevant variables during the target period. Its linkage to the exact site/source of the processed project data still requires official confirmation.
- **Conditional neighbor candidate:** 42105. The METAR inventory includes the same five fields and bounds overlap the original period, but station separation is 89.92 km and elevation differs by +93 m. It may be regional context; terrain/climate representativeness is unassessed.
- **Conditional regional candidate:** 42101, 76.04 km away, with NOAA ISD Lite inventory for five fields. Actual common timestamps and field validity are unverified.
- **Identity-unresolved candidate:** 42099, 2.27 km away. Do not count as independent until physical-site alias status is resolved.
- **Excluded for proposed hourly period:** 42096; current direct historical inventory is daily precipitation ending in 1970, with no historical direct hourly provider listed.

None is yet classified `SUITABLE_NEIGHBOUR_CANDIDATE`. No distance threshold or geographic representativeness decision is asserted.

## 8. Proposed common observation period

For VILD0 and 42105, the five METAR parameter inventories have date envelopes overlapping the processed project interval: 2021-01-05 through 2026-03-09 inclusive. This interval is selected because it is the original processed data window and falls within the common inventory bounds for each of the five fields. It is not verified shared timestamp coverage. Inventory completeness is low or modest, and no expected rows, filesizes, or non-null fractions can be calculated from this evidence. Dew point and precipitation are omitted because the chosen VILD0/42105 METAR inventories do not list them.

## 9. Bounded retrieval proposal

The concrete proposal and preservation controls are in [RAW_DATA_RETRIEVAL_PROPOSAL.md](RAW_DATA_RETRIEVAL_PROPOSAL.md): Meteostat `metar`, VILD0 and 42105, five listed variables, hourly, 2021-01-05 through 2026-03-09 inclusive. Do not include 42099 as an independent station without identity verification. Do not fill data gaps from forecast/model rows. Exact row counts and sizes remain unknown. User approval is required for this exact station/provider/variable/period combination before observation retrieval.

## 10. Risks and unresolved questions

1. VILD0's physical-site link to 42099 and to the processed dataset is unresolved.
2. Provider inventory date ranges are metadata bounds, not proof of populated records or pairwise timestamps.
3. Some provider inventory rows have end dates after the 2026-11-17 metadata query date (through 2026-11-25). They are preserved verbatim but treated as anomalous and excluded from the proposed interval.
4. Source fields and quality flags remain unseen until observation retrieval is approved.
5. METAR inventory completeness is low; usable event coverage could be sparse.
6. IMD station-specific hourly availability and fees remain unverified; public form only showed daily/monthly frequency choices.
7. A 76–90 km station separation may not represent local spatial corroboration for the event scales of interest.
8. Licensing and usage conditions must be checked at retrieval time and preserved with the exact provider data response.

## 11. Status and next user decision

**Phase 1B status: `PARTIALLY_COMPLETE_EXTERNAL_ACCESS_REQUIRED`.** Station/provider/parameter inventory metadata is now checked, but primary-site identity linkage, neighbor independence and representativeness, IMD coverage, direct row provenance, and actual timestamp overlap remain unresolved. E3 is not scientifically validated, and this branch does not implement E3.

The next decision is whether to approve the exact provisional Meteostat request in `RAW_DATA_RETRIEVAL_PROPOSAL.md` (VILD0 + 42105; METAR; temperature, relative humidity, wind speed, wind direction and pressure; hourly; 2021-01-05 to 2026-03-09) for a bounded observation-level provenance/overlap check. If the user does not approve, the next work should remain metadata-only and resolve the VILD0/42099 physical identity and IMD availability manually.

## 12. Scope record

No raw historical observations were downloaded, no E3 algorithm was implemented, no Phase 01/03 snapshot or Phase 1A output was modified, no model campaign was regenerated, and no user account/request/payment was initiated. E3 remains unvalidated. Phase 2 independent event and fault references remain outstanding.
