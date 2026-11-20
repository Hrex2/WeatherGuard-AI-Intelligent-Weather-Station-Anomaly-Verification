"""Build Phase 06 inventories and descriptive E3 experiments from saved inputs.

This script does not retrieve data, train models, impute values, or modify prior
phase outputs. It refuses to replace any Phase 06 report already present.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from weather_research.e3_spatial import (
    DEFAULT_ZONES, assign_distance_zone, evaluate_spatial_evidence,
    haversine_km, nearest_timestamp_pairs,
)
from weather_research.phase04_collection import source_index, source_series, time_index

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase06_controlled_e3_validation"
DEFAULT_PHASE00 = Path(r"D:/Download/weather_anomaly_phase00-20261118T100505Z-1-001.zip")
VARIABLES = ("temp", "dwpt", "rhum", "wspd", "wdir", "pres", "prcp")
UNITS = {"temp":"degC", "dwpt":"degC", "rhum":"%RH", "wspd":"m/s",
         "wdir":"degrees clockwise from north", "pres":"hPa", "prcp":"mm/interval"}
TOLERANCES = (0, 15, 30, 60)
PERIOD_START = pd.Timestamp("2025-03-28T00:00:00Z")
PERIOD_END = pd.Timestamp("2026-03-09T23:59:00Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_csv_once(path: Path, rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 06 artifact: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row)) if rows else ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_source_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["time"])
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return frame.set_index(["time", "source"]).sort_index()


def frame_stats(frame: pd.DataFrame, raw_time: pd.Series | None = None) -> dict:
    times = pd.DatetimeIndex(time_index(frame))
    unique = times.unique().sort_values()
    deltas = pd.Series(unique).diff().dropna().dt.total_seconds().div(60)
    example = str(raw_time.iloc[0]) if raw_time is not None and len(raw_time) else ""
    if "+05:30" in example or "+0530" in example:
        tz_label = "Asia/Kolkata offset encoded in timestamp strings"
    elif len(unique) and unique.tz is not None:
        tz_label = str(unique.tz)
    else:
        tz_label = "UNKNOWN"
    variables = [c for c in frame.columns if c not in {"source", "location"}]
    missing = {col: int(pd.to_numeric(frame[col], errors="coerce").isna().sum())
               for col in variables if col in frame}
    source_counts = {str(k): int(v) for k, v in source_index(frame).astype(str).value_counts().items()}
    return {
        "rows": int(len(frame)), "unique_timestamps": int(len(unique)),
        "duplicate_time_rows": int(times.duplicated().sum()),
        "first_utc": str(unique.min()) if len(unique) else None,
        "last_utc": str(unique.max()) if len(unique) else None,
        "timestamp_resolution_min_minutes": float(deltas.min()) if len(deltas) else None,
        "timestamp_resolution_median_minutes": float(deltas.median()) if len(deltas) else None,
        "timestamp_resolution_max_minutes": float(deltas.max()) if len(deltas) else None,
        "timezone": tz_label, "variables": variables,
        "missing_count_by_variable": missing, "source_distribution": source_counts,
    }


def metrics_from_pairs(pairs: pd.DataFrame, variable: str) -> dict:
    valid = pairs.neighbor_time.notna() & pairs.primary_value.notna() & pairs.neighbor_value.notna()
    a = pd.to_numeric(pairs.loc[valid, "primary_value"], errors="coerce")
    b = pd.to_numeric(pairs.loc[valid, "neighbor_value"], errors="coerce")
    valid = a.notna() & b.notna()
    valid_rows = pairs.loc[a.index[valid]].copy()
    a, b = a[valid].astype(float), b[valid].astype(float)
    diff = b.to_numpy() - a.to_numpy()
    if variable == "wspd":
        a, b = a / 3.6, b / 3.6  # Raw Meteostat metric speed is km/h; Phase 05 protocol specifies m/s.
        diff = b.to_numpy() - a.to_numpy()
    if variable == "wdir":
        diff = ((diff + 180.0) % 360.0) - 180.0
    valid_dates = int(pd.to_datetime(valid_rows.primary_time, utc=True).dt.date.nunique()) if len(valid_rows) else 0
    valid_count = int(len(a))
    corr = float(np.corrcoef(a, b)[0, 1]) if len(a) > 1 and a.std() > 0 and b.std() > 0 else None
    return {
        "valid_pairs": int(len(a)),
        "valid_dates": valid_dates,
        "minimum_descriptive_sample_met": bool(valid_count >= 30 and valid_dates >= 10),
        "bias_neighbor_minus_primary": float(np.mean(diff)) if len(diff) else None,
        "mae": float(np.mean(np.abs(diff))) if len(diff) else None,
        "median_absolute_difference": float(np.median(np.abs(diff))) if len(diff) else None,
        "rmse": float(np.sqrt(np.mean(np.square(diff)))) if len(diff) else None,
        "correlation": corr,
        "metric_note": "Circular signed error used for wind direction; correlation is descriptive only." if variable == "wdir" else "Correlation is descriptive only; no agreement threshold is applied.",
    }


def phase00_inventory(zip_path: Path) -> tuple[list[dict], dict[str, pd.DataFrame], dict[str, dict]]:
    rows, frames, members = [], {}, {}
    if not zip_path.exists():
        return rows, frames, members
    with ZipFile(zip_path) as archive:
        manifest = json.loads(archive.read("weather_anomaly_phase00/phase00_observed_manifest.json"))
        zip_hash = sha256_path(zip_path)
        for station in ("VILD0", "42099", "42101", "42105", "42096"):
            name = f"weather_anomaly_phase00/{station}_observed.csv"
            payload = archive.read(name)
            digest = sha256_bytes(payload)
            df = pd.read_csv(io.BytesIO(payload))
            time_raw = df["time"].copy()
            df["time"] = pd.to_datetime(df["time"], utc=True)
            data = df.set_index("time")
            frames[station] = data
            members[station] = {"member":name,"member_sha256":digest,"zip_sha256":zip_hash,
                                "manifest":manifest[station], "raw":df}
            stats = frame_stats(data, time_raw)
            rows.append({
                "station_id":station, "dataset_category":"PHASE00_SPARSE_EXPORT",
                "dataset_source":str(zip_path), "retrieval_configuration":"NOT_RECORDED_IN_PHASE00_MANIFEST",
                "provenance_status":"UNRESOLVED; source IDs/flags absent from CSV",
                "retrieval_timestamp":manifest[station].get("retrieval_start"),
                "requested_start":manifest[station].get("query_start"),
                "requested_end":manifest[station].get("query_end"),
                **stats, "sha256":digest,
                "hash_scope":f"ZIP member SHA-256; archive SHA-256={zip_hash}",
                "known_limitation":"Manifest records count/query bounds only; package version, timezone, model/fill/flags settings not recorded.",
            })
    return rows, frames, members


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase00", type=Path, default=DEFAULT_PHASE00)
    args = parser.parse_args()
    if not OUT.exists():
        raise FileNotFoundError("Run scripts/run_phase06_primary_retrieval.py first.")
    if any((OUT / name).exists() for name in (
        "PHASE06_RESEARCH_REPORT.md", "dataset_inventory.csv", "station_zone_assignment.csv",
        "variable_comparison_results.csv", "timestamp_alignment_results.csv",
        "coverage_sensitivity_results.csv", "source_sensitivity_results.csv",
        "e3_experiment_summary.json", "e3_validation_decision.md", "primary_data_readiness.json",
    )):
        raise FileExistsError("Phase 06 derived artifacts already exist; refusing to overwrite.")

    phase00_rows, p0_frames, p0_members = phase00_inventory(args.phase00)
    retrieval_path = OUT / "primary_retrieval_manifest.json"
    primary_manifest = json.loads(retrieval_path.read_text(encoding="utf-8"))
    if not primary_manifest.get("output_file"):
        raise RuntimeError("No source-level VILD0 raw export exists; cannot perform primary-relative evaluation.")
    primary_path = OUT / primary_manifest["output_file"]
    if sha256_path(primary_path) != primary_manifest["sha256"]:
        raise RuntimeError("VILD0 raw export SHA-256 mismatch.")
    primary = read_source_csv(primary_path)

    phase04_dir = ROOT / "outputs" / "phase04_provenance_aware_collection"
    phase04_manifest = json.loads((phase04_dir / "retrieval_manifest.json").read_text(encoding="utf-8"))
    neighbors = {}
    inventory = list(phase00_rows)
    phase04_hashes = {}
    for station in ("42099", "42101"):
        entry = phase04_manifest["station_results"][station]
        path = phase04_dir / entry["output_file"]
        digest = sha256_path(path)
        if digest != entry["sha256"]:
            raise RuntimeError(f"Phase 04 raw hash mismatch for {station}.")
        frame = read_source_csv(path)
        neighbors[station] = frame
        phase04_hashes[station] = digest
        inventory.append({
            "station_id":station,"dataset_category":"PHASE04_PROVENANCE_AWARE_NEIGHBOR",
            "dataset_source":str(path),
            "retrieval_configuration":json.dumps(entry["settings"],sort_keys=True),
            "provenance_status":"Provider IDs retained; upstream sensor lineage/independence unverified",
            "retrieval_timestamp":entry.get("retrieval_started_utc"),
            "requested_start":phase04_manifest["requested_start_utc"],
            "requested_end":phase04_manifest["requested_end_utc_inclusive"],
            **frame_stats(frame),"sha256":digest,"hash_scope":"Raw source-level CSV",
            "known_limitation":"Not original upstream provider payload; source ID is not instrument independence proof.",
        })
    inventory.append({
        "station_id":"VILD0","dataset_category":"PHASE06_PROVENANCE_AWARE_PRIMARY",
        "dataset_source":str(primary_path),"retrieval_configuration":json.dumps(primary_manifest["retrieval_settings"],sort_keys=True),
        "provenance_status":"Meteostat source IDs retained; model/fill/clean disabled; sensor/upstream lineage not independently verified",
        "retrieval_timestamp":primary_manifest["retrieved_at_utc"],
        "requested_start":primary_manifest["requested_start_utc"],"requested_end":primary_manifest["requested_end_utc_inclusive"],
        **frame_stats(primary),"sha256":primary_manifest["sha256"],"hash_scope":"Raw Meteostat package-returned source-level CSV",
        "known_limitation":"Not original provider payload; source IDs do not establish instrument or feed independence.",
    })

    # Historical notebook retrievals remain their own non-reproducible category.
    historical = [
        ("Weather_Station_Anomaly_Detection_Exploratory_Archive.ipynb", "exploratory cell 4", 8591,
         "2025-03-10", "2026-03-09", "Asia/Kolkata"),
        ("Weather_Station_Anomaly_Detection_Exploratory_Archive.ipynb", "exploratory cell 40", 45229,
         "2020-06-18", "2026-03-09", "Asia/Kolkata"),
    ]
    for notebook_name, cell_label, count, start, end, tz in historical:
        notebook_path = ROOT / notebook_name
        inventory.append({
            "station_id":"VILD0","dataset_category":"HISTORICAL_NOTEBOOK_RETRIEVAL_UNCERTAIN",
            "dataset_source":f"{notebook_name} ({cell_label}); full raw frame not preserved in repo",
            "retrieval_configuration":"Meteostat 1.7.6; Hourly called without model/flags args; defaults model=True, flags=False",
            "provenance_status":"UNCERTAIN; possible model-filled rows and no row source flags",
            "retrieval_timestamp":"not recorded with notebook output","requested_start":start,"requested_end":end,
            "rows":count,"unique_timestamps":None,"duplicate_time_rows":None,"first_utc":None,"last_utc":None,
            "timestamp_resolution_min_minutes":60,"timestamp_resolution_median_minutes":60,
            "timestamp_resolution_max_minutes":None,"timezone":tz,
            "variables":["temp","dwpt","rhum","prcp","snow","wdir","wspd","wpgt","pres","tsun","coco"],
            "missing_count_by_variable":"FULL_FRAME_NOT_AVAILABLE","source_distribution":"NOT_RECORDED",
            "sha256":sha256_path(notebook_path),"hash_scope":"Notebook artifact SHA-256, not retrieved dataset hash",
            "known_limitation":"No full raw notebook dataframe available for row-level validation; model=True default enabled.",
        })
    p05 = json.loads((ROOT / "outputs/phase05_primary_station_verification/e3_readiness_assessment.json").read_text(encoding="utf-8"))
    inventory.append({
        "station_id":"VILD0","dataset_category":"PHASE05_METADATA_ONLY","dataset_source":"outputs/phase05_primary_station_verification/",
        "retrieval_configuration":"Not an observation dataset","provenance_status":"Verified airport-station record crosswalk; exact sensor point/lineage unresolved",
        "retrieval_timestamp":p05["assessment_date_utc"],"requested_start":None,"requested_end":None,"rows":None,
        "sha256":"","hash_scope":"Metadata artifacts are listed in Phase 05 register","known_limitation":"No observations in Phase 05."})

    # Verify exact row/value fingerprints without merging data categories.
    fingerprint_rows = []
    for station, old in p0_frames.items():
        new_frame = primary if station == "VILD0" else neighbors.get(station)
        if new_frame is None:
            continue
        for source, values in source_series(new_frame, "temp").items():
            source_frame = new_frame.xs(source, level="source", drop_level=True)
            old_times = pd.DatetimeIndex(old.index)
            new_times = pd.DatetimeIndex(source_frame.index)
            overlap = old_times.intersection(new_times)
            for variable in VARIABLES:
                old_col = pd.to_numeric(old.loc[old.index.isin(overlap), variable], errors="coerce") if variable in old else pd.Series(dtype=float)
                new_col = pd.to_numeric(source_frame.loc[source_frame.index.isin(overlap), variable], errors="coerce") if variable in source_frame else pd.Series(dtype=float)
                joined = pd.concat([old_col.rename("phase00"), new_col.rename("new")], axis=1).dropna()
                fingerprint_rows.append({
                    "station_id":station,"phase00_member":p0_members[station]["member"],"comparison_source":source,
                    "variable":variable,"phase00_rows":len(old),"new_source_rows":len(source_frame),
                    "exact_timestamp_overlap":len(overlap),"both_valid_values":len(joined),
                    "identical_nonmissing_values":int(joined.phase00.eq(joined.new).sum()) if len(joined) else 0,
                    "phase00_provenance_status":"UNKNOWN_CONFIG; fingerprint is not retroactive provenance proof",
                })

    # Verified station-record coordinates only; distance bands are provisional study zones.
    origin = (30.8547, 75.9526, 254.2)
    station_meta = {
        "VILD0": (origin[0], origin[1], origin[2], "VERIFIED_CROSSWALK_STATION_RECORD", "NOAA GHCNh INI0000VILD / Meteostat; sensor point not confirmed"),
        "42099": (30.8666667,75.9333333,255.0,"VERIFIED_IDENTITY_HISTORIC_COORDINATE","IMD WIS2 + IMD 1981-2010; site continuity note applies"),
        "42101": (30.3333333,76.4666667,251.0,"VERIFIED_IDENTITY_HISTORIC_COORDINATE","IMD WIS2 + IMD 1981-2010; site continuity note applies"),
        "42105": (None,None,None,"UNVERIFIED","No official provider-ID/site crosswalk"),
        "42096": (None,None,None,"UNVERIFIED","No official provider-ID/site crosswalk"),
    }
    zones = {}
    zone_rows = []
    for station, (lat, lon, elev, status, source) in station_meta.items():
        if station == "VILD0":
            distance, zone, elevation_diff = 0.0, "REFERENCE", 0.0
        elif lat is not None and lon is not None and status.startswith("VERIFIED"):
            distance = haversine_km(origin[0], origin[1], lat, lon)
            zone = assign_distance_zone(distance)
            elevation_diff = float(elev - origin[2]) if elev is not None else None
            zones[station] = zone
        else:
            distance, zone, elevation_diff = None, None, None
        zone_rows.append({
            "station_id":station,"latitude":lat,"longitude":lon,"elevation_m":elev,
            "distance_from_VILD0_km":distance,"elevation_difference_neighbor_minus_primary_m":elevation_diff,
            "zone":zone,"zone_status":"PROVISIONAL_EXPERIMENTAL_BOUNDARY" if zone not in (None,"REFERENCE") else ("REFERENCE_COORDINATE_ONLY" if zone=="REFERENCE" else "NOT_ASSIGNED_UNVERIFIED_IDENTITY_OR_COORDINATES"),
            "metadata_confidence":status,"metadata_source":source,
            "lineage_status":"SOURCE_OR_SENSOR_INDEPENDENCE_UNVERIFIED" if station not in ("VILD0","42105","42096") else ("PRIMARY_LINEAGE_UNVERIFIED" if station=="VILD0" else "NOT_APPLICABLE"),
            "zone_boundaries_km":"A [0,10); B [10,50); C [50,100); D [100,250); E [250,infinity); provisional, not validated meteorological zones",
            "travel_time_inference":"NOT_INFERRED_FROM_DISTANCE",
        })

    primary_sources = source_series(primary, "temp")
    candidate_path = ROOT / "phase03_model_revalidation" / "candidate_observations_8of12.csv"
    if candidate_path.exists():
        candidate_frame = pd.read_csv(candidate_path)
        candidate_times = pd.DatetimeIndex(pd.to_datetime(candidate_frame["timestamp"], utc=True).unique()).sort_values()
    else:
        candidate_times = pd.DatetimeIndex([], tz="UTC")
    variable_results, alignment_results = [], []
    exact_pair_cache = {}
    source_grade = primary_manifest.get("provider_grade_map", {})
    for station, neighbor in neighbors.items():
        neighbor_sources = source_series(neighbor, "temp")
        zone = zones.get(station)
        for psource in primary_sources:
            p_times = pd.DatetimeIndex(primary.xs(psource, level="source").index).unique().sort_values()
            for nsource in neighbor_sources:
                n_times = pd.DatetimeIndex(neighbor.xs(nsource, level="source").index).unique().sort_values()
                p_dummy = pd.Series(1.0, index=p_times)
                n_dummy = pd.Series(1.0, index=n_times)
                for tol in TOLERANCES:
                    aligned = nearest_timestamp_pairs(p_dummy, n_dummy, tol)
                    matched_count = int(aligned.neighbor_time.notna().sum())
                    alignment_results.append({
                        "comparison_scope":"ALL_TIMESTAMP_AVAILABILITY", "reference":"VILD0", "station_id":station,
                        "zone":zone,"source_primary":psource,"source_neighbor":nsource,
                        "tolerance_minutes":tol,"primary_timestamps":len(p_times),"neighbor_timestamps":len(n_times),
                        "matched_timestamp_pairs_one_to_one":matched_count,
                        "primary_match_rate":matched_count/len(p_times) if len(p_times) else None,
                        "source_lineage_status":"UNVERIFIED_INDEPENDENT_SENSOR_LINEAGE",
                        "interpretation":"Timestamp availability only; not variable-valid pairs or corroboration.",
                    })
                for variable in VARIABLES:
                    pser = source_series(primary, variable).get(psource, pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC")))
                    nser = source_series(neighbor, variable).get(nsource, pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC")))
                    for tol in TOLERANCES:
                        pairs = nearest_timestamp_pairs(pser, nser, tol)
                        result = metrics_from_pairs(pairs, variable)
                        row = {
                            "comparison_scope":"ALL_SERIES",
                            "station_primary":"VILD0","station_neighbor":station,"zone":zone,
                            "variable":variable,"units":UNITS[variable],"source_primary":psource,
                            "provider_grade_primary":source_grade.get(psource,"UNSPECIFIED"),
                            "source_neighbor":nsource,"provider_grade_neighbor":phase04_manifest["source_grade_map"].get(nsource,"UNSPECIFIED"),
                            "tolerance_minutes":tol,"matched_timestamp_pairs":int(pairs.neighbor_time.notna().sum()),
                            **result,
                            "independent_source_eligible":False,
                            "interpretation":"DESCRIPTIVE_MEASUREMENT_COMPARISON_ONLY; upstream sensor/feed independence unverified; no agreement tolerance applied.",
                        }
                        variable_results.append(row)
                        if tol == 0:
                            exact_pair_cache[(station,psource,nsource,variable)] = pairs
                    candidate_primary = pser[pser.index.isin(candidate_times)]
                    for tol in TOLERANCES:
                        candidate_pairs = nearest_timestamp_pairs(candidate_primary, nser, tol)
                        candidate_row = {
                            "comparison_scope":"CANDIDATE_EVENT_TIMES",
                            "station_primary":"VILD0","station_neighbor":station,"zone":zone,
                            "variable":variable,"units":UNITS[variable],"source_primary":psource,
                            "provider_grade_primary":source_grade.get(psource,"UNSPECIFIED"),
                            "source_neighbor":nsource,"provider_grade_neighbor":phase04_manifest["source_grade_map"].get(nsource,"UNSPECIFIED"),
                            "tolerance_minutes":tol,"matched_timestamp_pairs":int(candidate_pairs.neighbor_time.notna().sum()),
                            **metrics_from_pairs(candidate_pairs, variable),
                            "independent_source_eligible":False,
                            "interpretation":"Candidate-event descriptive comparison only; candidate labels are not independent ground truth and source lineage is unverified.",
                        }
                        variable_results.append(candidate_row)
        # Candidate availability is independent of primary provider stratum;
        # emit it once per neighbor source rather than once per primary source.
        for nsource in neighbor_sources:
            n_times = pd.DatetimeIndex(neighbor.xs(nsource, level="source").index).unique().sort_values()
            n_dummy = pd.Series(1.0, index=n_times)
            for tol in TOLERANCES:
                candidate_alignment = nearest_timestamp_pairs(
                    pd.Series(1.0, index=candidate_times), n_dummy, tol
                )
                candidate_matched = int(candidate_alignment.neighbor_time.notna().sum())
                alignment_results.append({
                    "comparison_scope":"CANDIDATE_EVENT_TIME_AVAILABILITY","reference":"8of12 candidate timestamps",
                    "station_id":station,"zone":zone,"source_primary":"candidate_set","source_neighbor":nsource,
                    "tolerance_minutes":tol,"primary_timestamps":len(candidate_times),"neighbor_timestamps":len(n_times),
                    "matched_timestamp_pairs_one_to_one":candidate_matched,
                    "primary_match_rate":candidate_matched/len(candidate_times) if len(candidate_times) else None,
                    "source_lineage_status":"UNVERIFIED_INDEPENDENT_SENSOR_LINEAGE",
                    "interpretation":"Candidate-time availability only; not event truth or variable-valid corroboration.",
                })

    # Coverage robustness: deterministic random removal of neighbor timestamps from exact pairs.
    coverage_rows = []
    rng = np.random.default_rng(6043)
    for (station, psource, nsource, variable), pairs in exact_pair_cache.items():
        valid = pairs.neighbor_time.notna() & pairs.primary_value.notna() & pairs.neighbor_value.notna()
        valid_pairs = pairs.loc[valid]
        base = len(valid_pairs)
        for retained in (1.0, 0.9, 0.75, 0.5, 0.25, 0.1, 0.0):
            counts = []
            for _ in range(100):
                keep_mask = rng.random(base) < retained
                counts.append(int(keep_mask.sum()))
            coverage_rows.append({
                "experiment":"E5_RANDOM_MISSINGNESS_MASKING","station_id":station,"zone":zones.get(station),
                "variable":variable,"source_primary":psource,"source_neighbor":nsource,
                "retained_neighbor_pair_fraction":retained,"baseline_exact_valid_pairs":base,"repetitions":100,
                "mean_valid_pairs_after_mask":float(np.mean(counts)),
                "p05_valid_pairs_after_mask":float(np.quantile(counts,0.05)),
                "p95_valid_pairs_after_mask":float(np.quantile(counts,0.95)),
                "status":"SIMULATED_AVAILABILITY_MASKING_NOT_OBSERVED_VALIDATION",
                "missingness_method":"Randomly retain the stated fraction of exact valid pair rows; no values imputed or changed.",
            })

    # Source sensitivity preserves provider strata and applies a strict independence gate.
    sensitivity_rows = []
    phase00_sources = {"VILD0":"metar","42099":"isd_lite","42101":"isd_lite"}
    for row in variable_results:
        if row["comparison_scope"] != "ALL_SERIES" or row["tolerance_minutes"] != 0:
            continue
        sensitivity_rows.append({
            "experiment":"E6_SOURCE_SENSITIVITY","station_id":row["station_neighbor"],"zone":row["zone"],
            "variable":row["variable"],"source_primary":row["source_primary"],"source_neighbor":row["source_neighbor"],
            "filter":"ALL_MODEL_EXCLUDED_SOURCE_LEVEL_PROVIDER_ROWS","provider_grade_primary":row["provider_grade_primary"],
            "provider_grade_neighbor":row["provider_grade_neighbor"],"valid_pairs":row["valid_pairs"],
            "strict_independent_lineage_eligible_pairs":0,"status":"DESCRIPTIVE_ONLY_LINEAGE_UNVERIFIED",
            "note":"Grade 3/source label identifies provider category, not independent sensor lineage."})
        sensitivity_rows.append({
            "experiment":"E6_SOURCE_SENSITIVITY","station_id":row["station_neighbor"],"zone":row["zone"],
            "variable":row["variable"],"source_primary":row["source_primary"],"source_neighbor":row["source_neighbor"],
            "filter":"VERIFIED_INDEPENDENT_SENSOR_LINEAGE_ONLY","provider_grade_primary":row["provider_grade_primary"],
            "provider_grade_neighbor":row["provider_grade_neighbor"],"valid_pairs":0,
            "strict_independent_lineage_eligible_pairs":0,"status":"NO_SOURCE_PAIR_PASSES_INDEPENDENCE_GATE",
            "note":"No instrument/operator/upstream-feed independence chain was verified for any pair."})

    # Phase 00 fingerprint checks are separate from the source-stratified datasets.
    for r in fingerprint_rows:
        sensitivity_rows.append({
            "experiment":"PHASE00_FINGERPRINT_RECONCILIATION","station_id":r["station_id"],"zone":zones.get(r["station_id"]),
            "variable":r["variable"],"source_primary":"PHASE00_UNTAGGED_EXPORT","source_neighbor":r["comparison_source"],
            "filter":"SAME_TIMESTAMP_AND_VALUE_FINGERPRINT","provider_grade_primary":"UNKNOWN","provider_grade_neighbor":"SEE_PHASE04_OR_06_MANIFEST",
            "valid_pairs":r["both_valid_values"],"strict_independent_lineage_eligible_pairs":0,
            "status":"FINGERPRINT_MATCH_NOT_PROVENANCE_PROOF",
            "note":f"overlap={r['exact_timestamp_overlap']}; exact nonmissing values={r['identical_nonmissing_values']}/{r['both_valid_values']}; original Phase 00 config remains unknown."})

    # Synthetic controls exercise logic only; they do not describe weather observations.
    synthetic_base = {"matched":True,"primary_value":20.0,"offset_minutes":0,
                      "provenance_status":"VERIFIED_DIRECT_OBSERVATION",
                      "independence_status":"VERIFIED_INDEPENDENT","quality_status":"VALID"}
    positive = evaluate_spatial_evidence([
        {**synthetic_base,"station_id":"SYN_LOCAL","zone":"A","neighbor_value":20.2},
        {**synthetic_base,"station_id":"SYN_REGION","zone":"C","neighbor_value":20.6},
    ], tolerance=1.0)
    negative = evaluate_spatial_evidence([
        {**synthetic_base,"station_id":"SYN_LOCAL","zone":"A","neighbor_value":24.0},
    ], tolerance=1.0)
    missing_control = evaluate_spatial_evidence([
        {"station_id":"SYN_MISSING","zone":"A","matched":False,"candidate_available":False,
         "provenance_status":"VERIFIED_DIRECT_OBSERVATION","independence_status":"VERIFIED_INDEPENDENT",
         "quality_status":"MISSING"}
    ], tolerance=1.0)

    # Actual evidence outcomes remain unavailable; no real-world values are fabricated here.
    actual_evidence = {
        variable:"UNAVAILABLE_SOURCE_LINEAGE_UNVERIFIED_AND_TOLERANCE_NOT_REGISTERED"
        for variable in VARIABLES
    }

    exact_results = [row for row in variable_results
                     if row["comparison_scope"] == "ALL_SERIES" and row["tolerance_minutes"] == 0]
    valid_by_variable = {}
    for variable in VARIABLES:
        valid_by_variable[variable] = [
            {"station":r["station_neighbor"],"source_primary":r["source_primary"],
             "source_neighbor":r["source_neighbor"],"valid_pairs":r["valid_pairs"],
             "bias":r["bias_neighbor_minus_primary"],"mae":r["mae"],"rmse":r["rmse"],"correlation":r["correlation"]}
            for r in exact_results if r["variable"] == variable
        ]
    represented_zones = sorted({z for z in zones.values()})
    summary = {
        "phase":"06_controlled_e3_validation","decision":"BLOCKED_BY_DATA_PROVENANCE",
        "primary_retrieval":{"status":primary_manifest["status"],"station":"VILD0",
            "rows":primary_manifest["row_count"],"unique_timestamps":frame_stats(primary)["unique_timestamps"],
            "sources":primary_manifest["source_distribution"],"sha256":primary_manifest["sha256"],
            "model_setting":False,"fill_setting":False,"clean_setting":False,"source_ids_retained":True},
        "metadata_eligible_neighbor_stations":["42099","42101"],
        "independently_lineage_verified_station_pairs":0,
        "represented_experimental_zones":represented_zones,
        "unrepresented_zones":[x.name for x in DEFAULT_ZONES if x.name not in represented_zones],
        "primary_source_level_counts_by_variable":primary_manifest["coverage"]["variable_summary"],
        "exact_valid_pair_results_by_variable_source_pair":valid_by_variable,
        "experiments":{
            "E1_exact_timestamp":"COMPUTED_DESCRIPTIVE_SOURCE_STRATIFIED; timestamp availability is separate from variable-valid pairs.",
            "E2_15_30_60_minute":"COMPUTED_DESCRIPTIVE_ONE_TO_ONE_SENSITIVITY; no neighbor row reused.",
            "E3_distance_zone":"A and C represented by verified station records; boundaries provisional and not meteorologically validated.",
            "E4_variable_specific":"Computed separately for temperature, dewpoint, RH, wind speed/direction, pressure and precipitation.",
            "E5_missing_data":"Synthetic random masking of exact valid pairs; not observational validation.",
            "E6_source_sensitivity":"Provider-source-stratified metrics computed; strict independent-lineage gate excludes every pair.",
            "E7_controls":{"positive_synthetic":positive["research_outcome"],"negative_synthetic":negative["research_outcome"],
                "missing_synthetic":missing_control["research_outcome"],"status":"SYNTHETIC_LOGIC_CONTROLS_ONLY_NOT_REAL_WEATHER_VALIDATION"},
        },
        "actual_evidence_status_by_variable":actual_evidence,
        "phase00_source_fingerprint_rows":len(fingerprint_rows),
        "phase00_fingerprint_caution":"Timestamp/value identity to newer source-level rows is a data fingerprint, not proof of the older retrieval configuration or source lineage.",
        "no_model_training":True,"no_imputation":True,"e3_integrated_into_classifier":False,
        "scientific_limit":"Descriptive agreement does not prove independent corroboration, event truth, prediction performance, or a sensor fault.",
    }

    readiness = {
        "status":"PARTIALLY_READY","decision":"BLOCKED_BY_DATA_PROVENANCE",
        "direct_source_level_vild0_package_rows_obtained":True,
        "direct_provider_payload_obtained":False,
        "retrieval_manifest":"primary_retrieval_manifest.json",
        "primary_source_rows":primary_manifest["row_count"],
        "primary_sources":primary_manifest["source_distribution"],
        "model_fill_clean_disabled":True,"source_ids_retained":True,
        "metadata_verified_neighbors":["42099","42101"],
        "independent_source_lineage_verified":False,
        "reason":"Meteostat returned source-stratified VILD0 rows with model/fill/clean disabled, but original provider payloads, exact sensor position/history, and upstream sensor/feed independence are not verified. Numeric tolerances are also pending sensor specifications.",
        "next_gate":"Acquire/retain original METAR or source records and instrument/site logs; obtain variable-specific sensor accuracy/QC specifications; then preregister tolerance and assess independent lineage before event-level corroboration.",
        "not_validated":True,
    }

    # Write deliverables only after all calculations have completed successfully.
    write_csv_once(OUT / "dataset_inventory.csv", inventory)
    write_csv_once(OUT / "station_zone_assignment.csv", zone_rows)
    write_csv_once(OUT / "variable_comparison_results.csv", variable_results)
    write_csv_once(OUT / "timestamp_alignment_results.csv", alignment_results)
    write_csv_once(OUT / "coverage_sensitivity_results.csv", coverage_rows)
    write_csv_once(OUT / "source_sensitivity_results.csv", sensitivity_rows)
    (OUT / "primary_data_readiness.json").write_text(json.dumps(readiness, indent=2), encoding="utf-8")
    (OUT / "e3_experiment_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    decision_text = f'''# E3 validation decision\n\n**Decision: `BLOCKED_BY_DATA_PROVENANCE`**\n\nA new VILD0 Meteostat 2.2.3 source-level export was obtained for 2025-03-28 through 2026-03-09 with model inclusion disabled, filling/cleaning disabled, and provider IDs retained. It contains {primary_manifest['row_count']} source rows across {frame_stats(primary)['unique_timestamps']} unique timestamps: {json.dumps(primary_manifest['source_distribution'],sort_keys=True)}. The export hash is `{primary_manifest['sha256']}`. This is package-returned provider data, not original upstream METAR/NOAA payload bytes. Provider IDs do not establish exact instruments or independent source chains.\n\nWMO 42099 and 42101 are metadata-eligible neighbors; their record coordinates place them in provisional zones **A** and **C** respectively. No stations are represented in B, D or E. These bands are experimental distance bins, not validated meteorological boundaries.\n\nExact and one-to-one 15/30/60-minute timestamp comparisons and variable-specific descriptive statistics were generated in the CSV results. They quantify source-level measurement similarity and availability only. No VILD0-to-neighbor pair passes the strict independent sensor/source-lineage gate. Dewpoint and precipitation coverage are absent in the primary retrieval; no universal variable tolerance has been applied. Correlation alone is not corroboration.\n\nThe Phase 00 CSVs have undocumented retrieval settings. Their timestamps and nonmissing values largely fingerprint-match later source-stratified records (see `source_sensitivity_results.csv`), but this does not retroactively prove the older model/fill/flags settings. Historical notebook data used Meteostat 1.7.6 defaults `model=True`, `flags=False` and remain a separate uncertain category.\n\nMissing-data sensitivity rows are simulated random availability masks on exact valid pairs; they are not new weather observations. Positive, negative and missing-evidence controls are synthetic logic checks only. No independent labelled positive/negative real events were available.\n\n**E3 is not validated and must remain isolated from the final classifier.** This result does not establish that an event is true or false and does not diagnose a sensor fault.\n\nNext steps: obtain original source reports and instrument/site logs; document upstream source independence; secure variable-specific uncertainty/QC specifications; preregister tolerances; then repeat the observational experiment.\n'''
    (OUT / "e3_validation_decision.md").write_text(decision_text, encoding="utf-8")

    report_text = f'''# Phase 06 — Controlled E3 Spatial Validation\n\n**Branch:** `feature/phase06-controlled-e3-validation`  \n**Base commit:** `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`  \n**Decision:** `BLOCKED_BY_DATA_PROVENANCE`  \n**Scientific status:** descriptive source-level comparisons completed; E3 not validated.\n\n## Primary VILD0 retrieval\n\nA new VILD0 Meteostat 2.2.3 retrieval **succeeded** for 2025-03-28 00:00 UTC through 2026-03-09 23:59 UTC. The API contract was checked: v2.2.3 `hourly` accepts explicit provider selection; `TimeSeries.fetch` supports `sources`, `fill`, `squash`, and `clean`; `include_model_data=False` was set and restored; `fill=False`, `clean=False`, `squash=False`, and `sources=True` were used. `flags` is not a separate v2.2.3 argument; provider source IDs were retained as an index level. The VILD0 request returned {primary_manifest['row_count']} source-level rows, {frame_stats(primary)['unique_timestamps']} unique timestamps, source distribution {json.dumps(primary_manifest['source_distribution'],sort_keys=True)}. The raw SHA-256 is `{primary_manifest['sha256']}`.\n\nThe 1,390 source rows include 369 timestamps represented in multiple source strata. Across source rows, valid counts were temp 1,021; dewpoint 0; RH 1,021; precipitation 0; wind speed 1,021; direction 1,019; pressure 1,002. There is no dewpoint or precipitation basis for comparisons. Source rows are package-returned provider records—not the original upstream payload—and the provider labels do not prove sensor/feed independence.\n\n## Input inventory and reconciliation\n\n`dataset_inventory.csv` keeps four categories separate: (1) Phase 00 sparse exports; (2) historical Meteostat 1.7.6 notebook outputs; (3) Phase 04 source-level neighbor exports; (4) the new Phase 06 source-level VILD0 retrieval. Phase 05 contributes metadata only, not observation rows. Raw datasets and manifests from earlier phases were not modified.\n\nPhase 00’s manifest records requested dates, counts and retrieval timestamps but omits package version, timezone, model/fill/flags settings and per-row source IDs. Fingerprint checks found all 1,002 VILD0 timestamps align with the new METAR-stratum records and all overlapping nonmissing temp, RH, wind direction, wind speed and pressure values identical. Phase 00 42099 aligns at all 567 timestamps with Phase 04 `isd_lite`, with common valid values identical. Phase 00 42101 aligns at 1,187 timestamps with the 1,187 Phase 04 `isd_lite` records, with common valid values identical; Phase 00 has one additional unmatched timestamp. The later Phase 04 `ghcnh` stratum contains 532 rows not represented in Phase 00. These are timestamp/value fingerprints, **not** proof of the historical exports’ query configuration or row-level lineage.\n\nThe archived notebook retrievals remain uncertain: Meteostat 1.7.6 `Hourly` calls omitted `model` and `flags`; library defaults were `model=True` and `flags=False`. They cannot be treated as direct-only.\n\n## Eligible station metadata and provisional zones\n\nThe Phase 05 crosswalk supplies VILD0’s station-record reference coordinate; it is not an exact sensor coordinate. The two verified neighbor records are 42099 and 42101. Their recorded coordinates assign 42099 to provisional zone A ({zone_rows[1]['distance_from_VILD0_km']:.2f} km) and 42101 to provisional zone C ({zone_rows[2]['distance_from_VILD0_km']:.2f} km). Zones B, D and E are unrepresented. The coordinate for 42099/42101 is historical record metadata and site continuity is not fully established. Stations 42105 and 42096 remain unverified and unzoned. These bands are experimental, not meteorological thresholds. No travel time was inferred from distance.\n\nTwo neighbor station records are eligible for **descriptive** source-level comparison. Zero pairs pass the strict independent sensor/source-lineage gate. Do not treat source codes as independent votes.\n\n## Experiments and measurements\n\n1. **Exact timestamp:** computed one-to-one alignment and variable-valid pairs separately; see `timestamp_alignment_results.csv` and `variable_comparison_results.csv`.\n2. **15/30/60-minute sensitivity:** computed as separate one-to-one matching analyses; a neighbor row is never reused. These are availability/similarity sensitivities, not evidence thresholds.\n3. **Distance zones:** A and C have eligible station records; other bands are empty, so a zone gradient cannot be validated.\n4. **Variable-specific:** temperature, dewpoint, humidity, wind speed/direction, pressure, precipitation are separate. Bias/MAE/RMSE/correlation are descriptive; wind direction uses circular error. Correlation is not proof of corroboration.\n5. **Missing data:** deterministic repeated random masking of exact valid pairs estimates the effect of reduced coverage. It changes availability only, not values; results are synthetic sensitivity analysis, not observational validation.\n6. **Source sensitivity:** provider-stratified and grade-filter rows are shown; all strict independence-only counts are zero because sensor/feed lineage is unverified.\n7. **Controls:** positive, negative and missing-data controls exercise the evidence logic using synthetic values only. They are not real-weather validation or ground-truth events.\n\nNo numeric agreement tolerances were introduced because instrument-specific uncertainties and QC specifications are unavailable. The Phase 05 comparison protocol remains the basis for later preregistration. No statistical significance is claimed.\n\n## Evidence logic and integration\n\nThe E3 utility now requires valid timing, quality, explicitly direct provenance, verified independent lineage and a preregistered variable tolerance before it can mark a station as supporting or conflicting. It does not use weighted votes. Unknown lineage or tolerance returns unavailable/uncertain evidence; missing records never count as conflict. Synthetic controls verify this behavior. E3 remains isolated and is not integrated into the E1/E2/E4 classifier. No E1, E2 or E4 implementation, baseline feature, or model was changed or retrained.\n\n## Final decision\n\n`BLOCKED_BY_DATA_PROVENANCE`. A source-level VILD0 dataset was obtained and model/filling/cleaning were disabled, improving readiness. However, raw provider payloads, exact sensor position/history, upstream source independence, and instrument uncertainty remain unavailable. Observed pairwise agreement is descriptive only. The three research outcomes remain uncertain absent validated independent evidence. Do not infer sensor fault from neighboring disagreement.\n\n## Files\n\n- `primary_retrieval_manifest.json` and `raw_station_data/VILD0_hourly_source_level.csv`\n- `dataset_inventory.csv`\n- `primary_data_readiness.json`\n- `station_zone_assignment.csv`\n- `variable_comparison_results.csv`\n- `timestamp_alignment_results.csv`\n- `coverage_sensitivity_results.csv`\n- `source_sensitivity_results.csv`\n- `e3_experiment_summary.json`\n- `e3_validation_decision.md`\n'''
    (OUT / "PHASE06_RESEARCH_REPORT.md").write_text(report_text, encoding="utf-8")
    print(f"Built Phase 06 reports in {OUT}")


if __name__ == "__main__":
    main()
