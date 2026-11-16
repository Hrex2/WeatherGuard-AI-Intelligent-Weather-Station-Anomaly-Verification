# Phase 02 station provenance and coverage report

**Status: In progress; not verified.** No fresh retrieval was attempted.

The archive has no primary raw acquisition CSV and no neighbor observation CSVs for 42099, 42101, 42105, or 42096. It contains derived spatial comparison tables for 42099 and 42101 only. Those tables do not permit reconstruction of provider metadata, full cadence, missing timestamp runs, source version, query parameters, read-back hashes, or the raw station time series.

## Information established from supplied project history

- VILD0 is identified in the project as the primary VILD0 station near Ludhiana/Doraha, Punjab, India; timezone Asia/Kolkata. `verified_phase01/model_df.csv` spans 2021-01-05 19:30 +05:30 through 2026-03-09 23:30 +05:30, but this is a processed snapshot, not the raw provider acquisition.
- Neighbor 42099: 567 reported observations, 2025-03-28 through 2025-08-24. Approximate distance from VILD0: 2.27 km.
- Neighbor 42101: 1,188 reported observations, 2025-03-28 through 2025-08-24. Approximate distance from VILD0: 76.04 km.
- Neighbor 42105: 6 reported observations; investigated interval and metadata remain unverified.
- Neighbor 42096: no records returned in the reported investigation; query details and period are absent.
- Coordinates, elevation, provider/source identifiers, retrieval date, retrieval parameters, package version, variable missingness, duplicates, exact cadence, and read-back hashes are not available in this archive.

The inventory in `outputs/station_provenance/station_manifest.json` labels each field as reported, computed from a processed snapshot, or unavailable. Do not infer instrument-level provenance from model-data flags, and do not interpret “no records returned” as permanent station absence.

## Required next input

Provide the original observation exports and retrieval/read-back metadata for VILD0 and each neighbor. Then compute station-level actual coverage, cadence and gaps, duplicates, variable missingness, timezone alignment, hashes, and source limitations from those artifacts. Preserve the existing derived comparisons and do not overwrite them.
