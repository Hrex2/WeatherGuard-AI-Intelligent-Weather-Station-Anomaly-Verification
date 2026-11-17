# Phase 1C pilot data-quality protocol

This protocol applies only after explicit user approval and a supported provider/date window. It does not label a station or value faulty and does not judge whether an event is regional.

## Immutable capture

1. Generate a unique UTC run ID and create `runs/<run_id>/{raw,processed,quality,metadata,reports}` exclusively; fail if the directory already exists.
2. Retrieve VILD0 and 42105 separately with `providers=[Provider.METAR]` and exactly `temp`, `rhum`, `wspd`, `wdir`, `pres`. Do not substitute stations/providers or retry with combined hourly, model, or forecast data.
3. Preserve each returned Meteostat `TimeSeries` DataFrame export in `raw/`, before local cleaning, sorting, imputation, deletion, or unit conversion. Since the package returns a DataFrame and discards the source HTTP response body, record the artifact type truthfully; do not call it raw HTTP bytes.
4. Preserve per-variable source columns from `fetch(sources=True)`, missing values, source timestamps, units and quality indicators as returned. Write a manifest with query, package, environment, UTC retrieval time and SHA-256. Never overwrite a prior run.
5. Keep raw files immutable. Derived checks and any timestamp normalization belong in separate `processed/` and `quality/` artifacts.

## Coverage per station and parameter

The requested exclusive UTC window contains 720 expected hourly instants (`2025-09-01T00:00Z` through `2025-09-30T23:00Z`). For each station and each of the five fields, report input row count, non-null count, missing expected hours, completeness percentage, first/last valid UTC timestamp, source values, unknown-source count and original data type/unit. If rows contain duplicate timestamps, report them; do not silently deduplicate.

Meteostat 2.2.3 calculates RHUM from METAR temperature and dew point. Preserve that field and explicitly mark it as derived by the package; do not call it a directly encoded METAR humidity measurement.

## Time quality and station overlap

- Interpret Meteostat naive hourly timestamps as UTC according to its documentation and make a separate UTC-aware comparison index.
- Report duplicate and non-monotonic timestamps, timestamps outside the requested half-open window, repeated/unexpected intervals, and missing hourly instants. The expected grid is only a diagnostic; do not add the absent times to the observations.
- For each variable, compute non-null timestamp sets for both stations; report A count, B count, shared count, A-only count, B-only count, and paired non-null values/source labels at exact shared instants.
- Do not round timestamps, interpolate, aggregate, forward-fill, or force a match. The raw rows and original timestamp index remain untouched.

## Source and value checks

- Record each returned `<parameter>_source` value as provided. A missing source column or blank source entry becomes `UNKNOWN`; do not infer source from a non-null reading.
- Report any source labels other than the requested `metar` provider as a provider mismatch. Model/interpolation labels are not included; stop if a non-METAR source appears.
- Record units and data types. Meteostat metric units are °C, %, km/h, degrees, and hPa for the requested parameters.
- Count values outside broad physical screening bounds in the machine-readable output and retain every such value in raw data. These bounds identify items for review only; they do not define automatic deletion or invalidity. Unusual weather must remain available for research review.
- Report missingness and source uncertainty. Do not impute any variable.

## Interpretation boundary

A successful one-month data return establishes only that this source produced parseable records for the pilot window. It does not prove station-site independence, instrument quality, representativeness, regional event behavior, or E3 effectiveness. In particular, VILD0/42105 remain conditional station candidates, and VILD0/42099 remains identity-unresolved and excluded from this pilot.
