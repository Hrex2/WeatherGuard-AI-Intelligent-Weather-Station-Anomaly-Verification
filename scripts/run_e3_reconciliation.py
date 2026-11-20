"""Reconcile the supplied Phase 00 archive and notebook; performs no retrieval."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from weather_research.e3_spatial import DEFAULT_ZONES, nearest_timestamp_pairs


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "multi_zone_spatial"
PHASE00_ZIP = Path(r"D:\Download\weather_anomaly_phase00-20261118T100505Z-1-001.zip")
RESEARCH_ZIP = Path(r"D:\Download\weather_anomaly_research_cleaned-20261118T100504Z-1-001.zip")
NOTEBOOK = Path(r"D:\Download\Weather_Anomaly_Detection_2.ipynb")
STATIONS = ["VILD0", "42099", "42101", "42105", "42096"]
VARIABLES = ["temp", "dwpt", "rhum", "prcp", "snow", "wdir", "wspd", "wpgt", "pres", "tsun", "coco"]
PAIR_VARIABLES = ["temp", "dwpt", "rhum", "pres", "wspd", "wpgt", "wdir", "prcp", "snow"]
UNITS = {"temp":"degC", "dwpt":"degC", "rhum":"percent", "pres":"hPa", "wspd":"km/h", "wpgt":"km/h", "wdir":"degrees", "prcp":"mm", "snow":"mm", "tsun":"minutes", "coco":"code"}
COORDS = {
    # Meteostat station-catalogue values displayed by notebook cell 141;
    # retained as unverified metadata, never treated as field-verified locations.
    "VILD0": (30.8547, 75.9526), "42099": (30.8667, 75.9333),
    "42101": (30.3333, 76.4667), "42105": (30.7333, 76.8833),
    "42096": (30.9167, 74.6667),
}
CATALOGUE = {
    "VILD0": ("Ludhiana / Dor?ha", "IN", "PB", 254.0),
    "42099": ("Ludhiana", "IN", "PB", 255.0),
    "42101": ("Patiala", "IN", "PB", 249.0),
    "42105": ("Chandigarh / S?rajpur", "IN", "CH", 347.0),
    "42096": ("Ferozepur", "IN", "PB", 199.0),
}


def read_archived_csv(archive: zipfile.ZipFile, name: str) -> pd.DataFrame:
    return pd.read_csv(archive.open(name), parse_dates=["time"]).set_index("time")


def csv_write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(OUT / name, index=False)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not all(p.is_file() for p in (PHASE00_ZIP, RESEARCH_ZIP, NOTEBOOK)):
        raise FileNotFoundError("One or more supplied source files are missing; no inputs were substituted.")
    phase = zipfile.ZipFile(PHASE00_ZIP)
    names = {station: f"weather_anomaly_phase00/{station}_observed.csv" for station in STATIONS}
    frames = {station: read_archived_csv(phase, name) for station, name in names.items()}
    manifest = json.loads(phase.read("weather_anomaly_phase00/phase00_observed_manifest.json"))
    integrity = pd.read_csv(phase.open("weather_anomaly_phase00/phase01_dataset_integrity_report.csv"))
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    research = zipfile.ZipFile(RESEARCH_ZIP)

    # Machine-readable provenance/inventory, with each version separately represented.
    notebook_retrieval = "\n".join(notebook["cells"][143].get("outputs", [{}])[0].get("text", []))
    retrieval_rows = []
    for station in STATIONS:
        reported = manifest[station]
        retrieval_rows.append({
            "dataset_version": "phase00_20261115_sparse_export", "station_id": station,
            "row_count": len(frames[station]), "manifest_count": reported.get("records_retrieved"),
            "method": "CSV export; fetch implementation/version not identified in supplied manifest",
            "model_data_enabled": "UNKNOWN", "source_flags_available": "NO",
            "source_or_provenance": "UNKNOWN; manifest labels observed but does not establish direct observation",
            "query_start": reported.get("query_start"), "query_end": reported.get("query_end"),
            "manifest_status": reported.get("status"),
        })
    for station, count in zip(STATIONS, [6024, 6024, 6024, 6024, 3267]):
        retrieval_rows.append({
            "dataset_version": "notebook_cell143_saved_output", "station_id": station,
            "row_count": count, "manifest_count": "", "method": "Meteostat 1.7.6 Hourly(...).fetch()",
            "model_data_enabled": "YES; Hourly default model=True", "source_flags_available": "NO; flags default False",
            "source_or_provenance": "Mixed/unknown; model-filled values possible and source flags were not retained",
            "query_start": "2025-03-28", "query_end": "2025-12-03 23:59", "manifest_status": "Notebook output only; full series not archived",
        })
    retrieval = pd.DataFrame(retrieval_rows)
    csv_write(retrieval, "retrieval_version_reconciliation.csv")

    candidates = pd.read_csv(ROOT / "phase03_model_revalidation" / "candidate_observations_8of12.csv", parse_dates=["timestamp"])
    candidate_times = pd.DatetimeIndex(candidates.timestamp)
    candidate_min, candidate_max = candidate_times.min(), candidate_times.max()
    coverage_rows, pair_rows, timestamp_rows, missing_rows, candidate_tolerance_rows = [], [], [], [], []
    primary = frames["VILD0"]
    primary.index = pd.DatetimeIndex(primary.index)
    for sid, frame in frames.items():
        frame.index = pd.DatetimeIndex(frame.index)
        if frame.index.tz is None and primary.index.tz is not None:
            frame.index = frame.index.tz_localize(primary.index.tz)
        elif frame.index.tz != primary.index.tz:
            frame.index = frame.index.tz_convert(primary.index.tz)
        duplicate_count = int(frame.index.duplicated(keep="first").sum())
        frame = frame[~frame.index.duplicated(keep="first")].sort_index()
        frames[sid] = frame
        expected = pd.date_range(frame.index.min(), frame.index.max(), freq="h") if len(frame) else pd.DatetimeIndex([], tz=primary.index.tz)
        gaps = expected.difference(frame.index)
        in_period = frame.loc[(frame.index >= candidate_min) & (frame.index <= candidate_max)] if len(frame) else frame
        outside = frame.loc[(frame.index < candidate_min) | (frame.index > candidate_max)] if len(frame) else frame
        values = {v: int(pd.to_numeric(frame[v], errors="coerce").notna().sum()) if v in frame else 0 for v in VARIABLES}
        period_values = {v: int(pd.to_numeric(in_period[v], errors="coerce").notna().sum()) if v in in_period else 0 for v in VARIABLES}
        outside_values = {v: int(pd.to_numeric(outside[v], errors="coerce").notna().sum()) if v in outside else 0 for v in VARIABLES}
        coverage_rows.append({
            "station_id": sid, "rows": len(frame), "unique_timestamps": frame.index.nunique(),
            "duplicate_timestamps_removed_for_analysis": duplicate_count,
            "first_timestamp": frame.index.min() if len(frame) else "", "last_timestamp": frame.index.max() if len(frame) else "",
            "missing_hourly_slots_between_first_last": len(gaps),
            "candidate_period_start": candidate_min, "candidate_period_end": candidate_max,
            "rows_in_candidate_period": len(in_period), "rows_outside_candidate_period": len(outside),
            "valid_counts_json": json.dumps(values), "candidate_valid_counts_json": json.dumps(period_values),
            "outside_candidate_valid_counts_json": json.dumps(outside_values), "provenance": "UNKNOWN; cannot assert observed-direct",
        })
        candidate_presence = frame.index.intersection(candidate_times)
        timestamp_rows.append({"station_id":sid,"candidate_timestamps":len(candidate_times),"exact_timestamp_overlap":len(candidate_presence),"exact_absent_candidate_timestamps":len(candidate_times.difference(frame.index))})
        for variable in PAIR_VARIABLES:
            series = pd.to_numeric(frame[variable], errors="coerce") if variable in frame else pd.Series(index=frame.index, dtype=float)
            primary_series = pd.to_numeric(primary[variable], errors="coerce") if variable in primary else pd.Series(index=primary.index, dtype=float)
            for tol in (0, 15, 30, 60):
                pairs = nearest_timestamp_pairs(primary_series, series, tol)
                valid = pairs.neighbor_time.notna() & pairs.primary_value.notna() & pairs.neighbor_value.notna()
                diffs = pairs.loc[valid, "difference_neighbor_minus_primary"].astype(float)
                if variable == "wdir":
                    diffs = ((pairs.loc[valid, "neighbor_value"].astype(float) -
                              pairs.loc[valid, "primary_value"].astype(float) + 180) % 360) - 180
                pair_rows.append({
                    "reference_station":"VILD0", "station_id":sid, "variable":variable,
                    "units":UNITS[variable], "tolerance_minutes":tol, "valid_pairs":int(valid.sum()),
                    "exact_pairs":int((valid & pairs.match_type.eq("EXACT")).sum()),
                    "tolerance_pairs":int((valid & pairs.match_type.eq("TOLERANCE_MATCH")).sum()),
                    "mean_difference_neighbor_minus_primary":float(diffs.mean()) if len(diffs) else np.nan,
                    "bias":float(diffs.mean()) if len(diffs) else np.nan,
                    "rmse":float(np.sqrt(np.mean(diffs ** 2))) if len(diffs) else np.nan,
                    "mean_absolute_difference":float(diffs.abs().mean()) if len(diffs) else np.nan,
                    "evidence_eligibility":"DESCRIPTIVE_ONLY_PROVENANCE_UNKNOWN",
                })
                # Candidate-time alignment is counted separately from whole-series pairs.
                cand = pd.Series(index=candidate_times, data=np.nan, dtype=float)
                # nearest matching against each candidate timestamp; reuse generic matcher.
                cser = pd.Series(index=candidate_times, data=np.arange(len(candidate_times), dtype=float))
                cp = nearest_timestamp_pairs(cser, series, tol)
                candidate_pair = cp.neighbor_time.notna() & cp.neighbor_value.notna()
                primary_candidate = primary_series.reindex(candidate_times)
                for ix, pair in cp.iterrows():
                    ts = pair.primary_time
                    pval = primary_candidate.loc[ts] if ts in primary_candidate.index else np.nan
                    nval = pair.neighbor_value
                    valid_pair = pd.notna(pval) and pd.notna(nval)
                    difference = float(nval - pval) if valid_pair else np.nan
                    if variable == "wdir" and valid_pair:
                        difference = float(((nval - pval + 180) % 360) - 180)
                    candidate_tolerance_rows.append({
                        "candidate_timestamp_utc":ts, "reference_station":"VILD0", "station_id":sid,
                        "variable":variable,"units":UNITS[variable],"tolerance_minutes":tol,
                        "nearest_station_timestamp_utc":pair.neighbor_time,
                        "offset_minutes_neighbor_minus_candidate":pair.offset_minutes,
                        "primary_value":pval,"neighbor_value":nval,"difference_neighbor_minus_primary":difference,
                        "match_status":"VALID_PAIR_DESCRIPTIVE_ONLY" if valid_pair else ("TIMESTAMP_MATCH_PRIMARY_VALUE_MISSING" if pd.notna(pair.neighbor_time) and pd.isna(pval) else "NO_NEIGHBOR_MATCH"),
                        "e3_verdict":"UNAVAILABLE_PROVENANCE_UNVERIFIED" if valid_pair else "MISSING_NOT_CONTRADICTORY",
                    })
                missing_rows.append({
                    "reference_station":"VILD0", "station_id":sid, "variable":variable,
                    "tolerance_minutes":tol, "candidate_timestamps":len(candidate_times),
                    "timestamp_matches":int(candidate_pair.sum()),
                    "valid_pairs_with_primary_and_neighbor":int((candidate_pair & primary_series.reindex(candidate_times).notna().to_numpy()).sum()),
                    "missing_candidate_timestamps":int((~candidate_pair).sum()),
                    "interpretation":"MISSING/NO MATCH is not contradictory evidence; source provenance remains unknown",
                })

    coverage = pd.DataFrame(coverage_rows)
    csv_write(coverage, "station_coverage.csv")
    overlap_rows = []
    for i, sid_a in enumerate(STATIONS):
        for sid_b in STATIONS[i + 1:]:
            idx_a, idx_b = frames[sid_a].index, frames[sid_b].index
            shared = idx_a.intersection(idx_b)
            overlap_rows.append({"station_a":sid_a,"station_b":sid_b,"rows_a":len(idx_a),"rows_b":len(idx_b),
                                 "unique_exact_shared_timestamps":len(shared),"union_timestamps":len(idx_a.union(idx_b)),
                                 "a_only_timestamps":len(idx_a.difference(idx_b)),"b_only_timestamps":len(idx_b.difference(idx_a)),
                                 "shared_timestamps_have_any_valid_variable_pair":int(sum(
                                     any(pd.notna(frames[sid_a].at[t,v]) and pd.notna(frames[sid_b].at[t,v])
                                         for v in VARIABLES if v in frames[sid_a] and v in frames[sid_b]) for t in shared))})
    csv_write(pd.DataFrame(overlap_rows), "timestamp_intersections.csv")
    pairwise = pd.DataFrame(pair_rows)
    csv_write(pairwise, "pairwise_comparisons.csv")
    csv_write(pd.DataFrame(timestamp_rows), "candidate_timestamp_overlap.csv")
    missing = pd.DataFrame(missing_rows).drop_duplicates(["reference_station","station_id","variable","tolerance_minutes"])
    csv_write(missing, "missing_data_report.csv")
    candidate_tolerance = pd.DataFrame(candidate_tolerance_rows)
    csv_write(candidate_tolerance, "candidate_tolerance_pairs.csv")

    # Candidate-time evidence by station: categorical coverage only, no E3 verdict.
    cand_evidence = []
    for sid, frame in frames.items():
        for ts in candidate_times:
            exact = ts in frame.index
            row = {"timestamp":ts,"station_id":sid,"exact_index_present":exact}
            for v in VARIABLES:
                primary_val = pd.to_numeric(pd.Series([primary[v].reindex([ts]).iloc[0] if v in primary else np.nan]), errors="coerce").iloc[0]
                val = pd.to_numeric(pd.Series([frame[v].reindex([ts]).iloc[0] if v in frame else np.nan]), errors="coerce").iloc[0]
                row[v+"_valid_pair_exact"] = bool(pd.notna(primary_val) and pd.notna(val))
                row[v+"_difference_neighbor_minus_primary"] = float(val-primary_val) if pd.notna(val) and pd.notna(primary_val) else np.nan
            row["e3_state"] = "UNAVAILABLE_PROVENANCE_UNVERIFIED" if exact else "MISSING_NOT_CONTRADICTORY"
            cand_evidence.append(row)
    candidate_report = pd.DataFrame(cand_evidence)
    csv_write(candidate_report, "candidate_spatial_evidence.csv")

    # Coordinates are retained only as unverified catalogue metadata. Do not calculate distances or
    # assign zones until station identity/location is independently verified.
    zone_rows = []
    for sid, (lat, lon) in COORDS.items():
        name,country,region,elevation = CATALOGUE[sid]
        zone_rows.append({"station_id":sid,"catalogue_name_as_saved":name,"country":country,"region":region,
                          "latitude":lat,"longitude":lon,"elevation_m":elevation,"distance_km_from_VILD0":np.nan,
                          "provisional_zone":"UNASSIGNED_COORDINATES_UNVERIFIED",
                          "coordinate_source":"Meteostat station catalogue displayed in notebook cell 141 (v1.7.6); not independently verified",
                          "zone_status":"NOT_ASSIGNED_PENDING_VERIFIED_STATION_IDENTITY_AND_COORDINATES"})
    zones = pd.DataFrame(zone_rows)
    csv_write(zones, "provisional_zone_evidence.csv")
    csv_write(pd.DataFrame([{"zone":z.name,"lower_km_inclusive":z.lower_km,"upper_km_exclusive":z.upper_km,
                             "status":"CONFIGURATION_ONLY_NOT_SCIENTIFICALLY_VALIDATED"} for z in DEFAULT_ZONES]),
              "distance_zone_configuration.csv")
    csv_write(zones[["station_id","catalogue_name_as_saved","country","region","latitude","longitude","elevation_m"]].assign(
        metadata_source="Notebook cell 141 Meteostat Stations().nearby(...) output",
        identity_status="CATALOGUE_MATCH_ONLY_PHYSICAL_IDENTITY_UNVERIFIED"), "station_identity_crosswalk.csv")
    pair_zones = pairwise.merge(zones[["station_id", "provisional_zone"]], on="station_id", how="left")
    neighbor_pairs = pair_zones[pair_zones.station_id.ne("VILD0")].copy()
    zone_rows_out = []
    for (zone, variable, tolerance), group in neighbor_pairs.groupby(["provisional_zone", "variable", "tolerance_minutes"], dropna=False):
        valid = group[group.valid_pairs.gt(0)]
        n = int(valid.valid_pairs.sum())
        pooled_bias = float((valid.bias * valid.valid_pairs).sum() / n) if n else np.nan
        pooled_rmse = float(np.sqrt((valid.rmse.pow(2) * valid.valid_pairs).sum() / n)) if n else np.nan
        miss = missing[(missing.station_id.isin(group.station_id)) & (missing.variable.eq(variable)) & (missing.tolerance_minutes.eq(tolerance))]
        zone_rows_out.append({"provisional_zone":zone,"variable":variable,"units":UNITS[variable],"tolerance_minutes":tolerance,
                              "neighbor_stations":";".join(group.station_id.astype(str)),"station_count":len(group),
                              "descriptive_valid_pairs":n,"pooled_bias_neighbor_minus_VILD0":pooled_bias,"pooled_rmse":pooled_rmse,
                              "candidate_timestamp_matches":int(miss.timestamp_matches.sum()),
                              "candidate_valid_pairs":int(miss.valid_pairs_with_primary_and_neighbor.sum()),
                              "interpretation":"UNASSIGNED_COORDINATES_UNVERIFIED; unknown data provenance; no E3 support/conflict assigned"})
    for zone in [z.name for z in DEFAULT_ZONES]:
        for variable in PAIR_VARIABLES:
            for tolerance in (0,15,30,60):
                zone_rows_out.append({"provisional_zone":zone,"variable":variable,"units":UNITS[variable],"tolerance_minutes":tolerance,
                                      "neighbor_stations":"","station_count":0,"descriptive_valid_pairs":np.nan,
                                      "pooled_bias_neighbor_minus_VILD0":np.nan,"pooled_rmse":np.nan,
                                      "candidate_timestamp_matches":np.nan,"candidate_valid_pairs":np.nan,
                                      "interpretation":"NOT_ASSIGNABLE: no verified station coordinates; no measurements placed in this zone"})
    zone_level = pd.DataFrame(zone_rows_out)
    csv_write(zone_level, "zone_level_evidence.csv")

    source_audit = {
        "notebook_sha256":sha256(NOTEBOOK), "phase00_zip_sha256":sha256(PHASE00_ZIP), "research_zip_sha256":sha256(RESEARCH_ZIP),
        "phase00_zip_crc_test":phase.testzip(), "research_zip_crc_test":research.testzip(),
        "phase00_manifest":manifest, "phase00_integrity_report_rows":integrity.to_dict(orient="records"),
        "phase00_member_csv_sha256":{name:hashlib.sha256(phase.read(name)).hexdigest() for name in names.values()},
        "notebook_meteostat_version":"1.7.6 (saved cell output)",
        "notebook_hourly_signature_fact":"v1.7.6 Hourly defaults model=True and flags=False; notebook passed neither model nor flags",
        "notebook_saved_full_station_series":False,
        "phase00_fetch_package_version":"UNKNOWN", "phase00_model_setting":"UNKNOWN", "phase00_source_flags":"NOT PRESENT IN EXPORT",
        "phase00_integrity_report_scope":"The included report covers baseline train/test pipeline checks, not file-level validation or provenance for the Phase 00 station CSVs.",
        "earlier_notebook_rows":{"VILD0":6024,"42099":6024,"42101":6024,"42105":6024,"42096":3267},
        "phase00_rows":{sid:len(frame) for sid,frame in frames.items()},
    }
    (OUT / "provenance_audit.json").write_text(json.dumps(source_audit, indent=2, default=str), encoding="utf-8")

    coverage_table = "\n".join(
        f"| {r.station_id} | {r.rows} | {r.unique_timestamps} | {r.missing_hourly_slots_between_first_last} | {r.rows_in_candidate_period} | {r.rows_outside_candidate_period} |"
        for r in coverage.itertuples()
    )
    overlap_table = "\n".join(
        f"| {r.station_id} | {r.exact_timestamp_overlap} | {r.exact_absent_candidate_timestamps} |"
        for r in pd.DataFrame(timestamp_rows).itertuples()
    )
    temperature_pairs = pairwise[(pairwise.variable == "temp") & pairwise.station_id.isin(["42099", "42101", "42105", "42096"])]
    pair_table = "\n".join(
        f"| {r.station_id} | {r.tolerance_minutes} | {r.valid_pairs} | {r.bias:.3f} | {r.rmse:.3f} |"
        for r in temperature_pairs.itertuples()
    )

    report = f"""# E3 data reconciliation and implementation audit

Generated from supplied local files only; no weather retrieval, model training, or changes to E1/E2/E4 were made.

## Verified

- The supplied Phase 00 ZIP contains five station CSVs and a manifest. CSV row counts are **{', '.join(f'{s}: {len(frames[s]):,}' for s in STATIONS)}** (total **{sum(map(len,frames.values())):,}**); these agree with the manifest's counts. `42096` has zero rows. ZIP integrity entries are retained in `provenance_audit.json`.
- The supplied notebook reports Meteostat **1.7.6**. Its retrieval code calls `Hourly(..., timezone='Asia/Kolkata').fetch()` without `model` or `flags`; the tagged v1.7.6 source defaults are `model=True`, `flags=False` ([Hourly implementation](https://github.com/meteostat/meteostat-python/blob/v1.7.6/meteostat/interface/hourly.py), [source flag handling](https://github.com/meteostat/meteostat-python/blob/v1.7.6/meteostat/interface/timeseries.py)). Its saved cell 143 reports **6,024 / 6,024 / 6,024 / 6,024 / 3,267** rows for VILD0 / 42099 / 42101 / 42105 / 42096. 6,024 is exactly the hourly-slot count from 2025-03-28 through 2025-12-03 inclusive, consistent with full model-enabled hourly output. Those full series are not in either supplied ZIP. Thus earlier row counts cannot be reconciled row by row, and those results may include model-filled values without retained source flags.
- Phase 00 manifest query window is 2025-03-28 through 2026-03-09. It identifies record counts and retrieval timestamps but omits retrieval library/version, `model`/fill controls, provider/source flags, timezone policy and station metadata. “observed” in its filenames is not proof of direct observations.
- The adjacent `phase01_dataset_integrity_report.csv` describes baseline train/test pipeline checks; it is not a file-level integrity or provenance audit for the five Phase 00 station CSVs.
- Notebook station catalogue output uses Meteostat catalogue labels and coordinates; these are metadata shown by the notebook, not independent verification of the physical station identity/location. Therefore no station distances or zone assignments are calculated. The configured zone boundaries are retained without claiming station membership.
- The station catalogue labels saved for VILD0, 42099, 42101, 42105 and 42096 are captured in `station_identity_crosswalk.csv`. The VILD0 and 42105 labels contain `?` in the notebook's saved output, so their original diacritics are unrecoverable from this artifact; no normalization is inferred.
- Timestamp, completeness, valid-value, overlap, candidate-period and pairwise descriptive statistics are in the CSV outputs. Exact alignment is separated from 15/30/60-minute nearest matching. Valid pairs require nonmissing values at both endpoints; shared indexes alone are not counted as valid pairs.

### Safe claims for an academic report

- The Phase 00 archive contains 2,763 station rows with the per-station distribution and variable completeness shown above and in `station_coverage.csv`.
- The notebook code used a model-enabled default in Meteostat 1.7.6 and did not retain source flags. The earlier notebook retrieval must therefore be described as potentially mixed observed/model output, not direct observations.
- The paired differences can be included only as exploratory comparisons of the supplied exports, with the provenance/identity limitation stated alongside them. They do not establish station corroboration, disagreement, fault status or E3 validation.
- Missing values and timestamps are availability limitations, not evidence against the candidate event.

### Phase 00 coverage observed in the supplied files

The candidate period is defined by the saved 8-of-12 candidate list ({len(candidate_times)} timestamps, {candidate_min} through {candidate_max}). Rows outside that period are retained and counted.

| Station | Rows | Unique timestamps | Missing hourly slots inside observed span | Rows in candidate period | Rows outside candidate period |
|---|---:|---:|---:|---:|---:|
{coverage_table}

| Station | Exact candidate timestamp overlap | Candidate timestamps absent |
|---|---:|---:|
{overlap_table}

Temperature pairwise summary versus VILD0 (raw export values; descriptive only). Bias is neighbor minus VILD0; RMSE uses matched values. Tolerance is the maximum nearest-time offset.

| Station | Tolerance (min) | Valid pairs | Bias (degC) | RMSE (degC) |
|---|---:|---:|---:|---:|
{pair_table}

## Reconciliation / unresolved issues

- The two retrievals are not equivalent artifacts. Phase 00 exported sparse row sets; the notebook explicitly enabled the v1.7.6 model-data default and discarded source flags. The row-count gap is consistent with full hourly model-filled output, but without the notebook's exact downloaded frames or Phase 00's retrieval code/metadata, we cannot identify which individual values are direct, modeled, cleaned, or transformed.
- Phase 00 uses timestamps with local offsets in its CSV exports. Notebook code asks Meteostat to use `Asia/Kolkata`; v1.7.6 converts requested local bounds to UTC and localizes returned indexes. The timestamp values are represented as timezone-aware timestamps, but available evidence cannot prove that Phase 00 export timezone conversion preserved every intended observation. The report preserves file timestamps and reports index gaps; no timezone shift is silently applied beyond parsing/normalizing indexes to the primary index zone for comparison.
- No authoritative station identifier crosswalk, official coordinates, elevation, sensor metadata, or observation provenance/flags were supplied. Therefore no station distance or zone membership is calculated, and the available coordinates cannot support physical-distance interpretation.
- Pairwise statistics describe the provided numeric values only. Wind-direction differences use circular wrapping to [-180, 180). They are not independent corroboration until both stations' direct-observation provenance and station identity are established. No fixed residual thresholds are set; no E3 classification or validation claim is made.
- Missing candidate coverage is reported separately from observed differences. Missing data do not count as support or contradiction.

## E3 readiness

- Added an isolated E3 utility module for configurable distance zoning, great-circle distances, exact/nearest timestamp pairing, and a provenance eligibility gate. Existing E1/E2/E4 and their thresholds remain untouched. The E3 evidence service remains unavailable when provenance and coverage are unverified.
- Zone boundaries A 0–10, B 10–50, C 50–100, D 100–250 and E >250 km are recorded as configurable experiment settings, not validated scientific thresholds. Zone evidence is unassignable until station coordinates are independently verified.
- Synthetic regression tests validate utility behavior and exclusion of unknown/model-filled provenance. Passing these tests validates software behavior only; it does not validate E3 empirically.

## Still required before empirical E3

1. Obtain reproducible retrieval code/configuration and original source flags for Phase 00, plus the full notebook retrieval datasets if those results are to be compared.
2. Establish station identity and coordinates from an authoritative source and record datum/elevation and station history.
3. Obtain direct observation records or provider provenance labels. Exclude modeled/imputed values from independent corroboration.
4. Resolve timezone semantics and demonstrate timestamp integrity across exports.
5. Predefine per-variable allowable temporal mismatch and residual criteria, account for station distance/elevation and weather regime, then report candidate-event support, disagreement and availability separately.

## New outputs

- `retrieval_version_reconciliation.csv`
- `station_coverage.csv`
- `candidate_timestamp_overlap.csv`
- `timestamp_intersections.csv`
- `pairwise_comparisons.csv`
- `candidate_spatial_evidence.csv`
- `candidate_tolerance_pairs.csv`
- `provisional_zone_evidence.csv`
- `distance_zone_configuration.csv`
- `station_identity_crosswalk.csv`
- `zone_level_evidence.csv`
- `missing_data_report.csv`
- `provenance_audit.json`
- `regression_tests.txt`
"""
    (OUT / "E3_DATA_RECONCILIATION_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
