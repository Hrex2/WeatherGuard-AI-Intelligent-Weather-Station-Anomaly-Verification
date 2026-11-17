# Station identity assessment — Phase 1B

**Assessed:** 2026-11-17 (UTC)  
**Starting point:** Phase 1A commit `cbe53f830a2941556f7a9c48101da51536259b62`  
**Classification of VILD0 ↔ 42099:** `IDENTITY_UNRESOLVED`

## Findings

The public Meteostat station directory returns different station IDs and names: VILD0 is “Ludhiana / Doraha,” while 42099 is “Ludhiana.” VILD0 lists ICAO `VILD`, IATA `LUH`, and GHCNh identifier `INI0000VILD`; 42099 lists WMO `42099`, GHCN `IN018091100`, and USAF `420990`. Their provider coordinates are 30.8547, 75.9526 and 30.8667, 75.9333, respectively: 2.27 km apart by Haversine. Their elevations differ by 1 m. The official IMD climatological table identifies 42099 as Ludhiana, but does not provide a verified coordinate/site crosswalk to VILD0.

The matching city label and similar elevation are consistent with either two nearby sites or an alias/cross-provider mapping. The 2.27 km coordinate separation is too large to dismiss as coordinate rounding at the published precision. No official station register, operator history, move record, installation history, or synchronized observation series was found to distinguish those explanations. Meteostat's provider directory records do not state that these IDs map to the same instrument. Therefore neither an alias nor distinct physical stations is confirmed. Keep both IDs separate and do not count 42099 as independent spatial evidence until an operator or official register resolves the relationship.

## Candidate station metadata

All coordinates, elevations, names and cross-provider identifiers in `station_identity_crosswalk.csv` are Meteostat directory metadata, not field-verified locations. Provider inventory dates are data inventory periods, not station opening or closure dates. Operator, instrument history, relocation history, and local administrative coordinates remain unknown for all five records. 42099/Ludhiana and 42101/Patiala also appear in the IMD 1991–2020 climatological table under those station numbers; this corroborates the station labels/numbers, not exact current observing-site continuity.

| ID | Provider identity evidence | Distance from VILD0 | Identity / E3 assessment |
|---|---|---:|---|
| VILD0 | Meteostat ID; ICAO VILD; GHCNh INI0000VILD | Primary | `PRIMARY_STATION_CANDIDATE`; project anchor name/source link still not independently verified |
| 42099 | Meteostat ID; WMO 42099; IMD table lists Ludhiana | 2.27 km | `IDENTITY_UNRESOLVED`; close candidate but independence cannot be assumed |
| 42101 | Meteostat ID; WMO 42101; IMD table lists Patiala | 76.04 km | `CONDITIONAL_CANDIDATE`; regional context, distance and local climate representativeness need review |
| 42105 | Meteostat ID; WMO 42105; ICAO VICG | 89.92 km | `CONDITIONAL_CANDIDATE`; provider observation inventories exist, but distance and site identity need review |
| 42096 | Meteostat ID; WMO 42096 | 122.90 km | `UNSUITABLE` for hourly project window based on current metadata: no direct hourly inventory listed; available direct daily precipitation ends 1970 |

The distance estimates use only provider coordinates. 42099, 42101 and 42105 are conditional candidates, not suitable E3 neighbors: matching populated timestamps, event-relevant parameter coverage, source flags, sensor history, and geographic representativeness have not been checked. No station is presently approved as an independent neighbor.

## Resolution needed

Request from IMD/airport or relevant station operator: official station-register record; coordinates and elevation; identifier history and crosswalk; operating organization; dates and details of any relocation; instrument/site history; and confirmation whether VILD0 and WMO 42099 are separate sites or aliases for the same observing site. Preserve each identifier separately until that evidence is available.

## Sources

- Meteostat station metadata: [VILD0](https://meteostat.net/en/station/VILD0), [42099](https://meteostat.net/en/station/42099), [42101](https://meteostat.net/en/station/42101), [42105](https://meteostat.net/en/station/42105), [42096](https://meteostat.net/en/station/42096).
- Meteostat JSON station-directory metadata dataset: `https://data.meteostat.net/stations/{station_id}.json` (five small metadata responses queried 2026-11-17; no observation data).
- IMD [Climatological Tables 1991–2020](https://imdpune.gov.in/library/public/Climatological%20Tables%201991-2020.pdf): station indices 42099 Ludhiana and 42101 Patiala.
