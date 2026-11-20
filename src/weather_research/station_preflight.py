"""Conservative helpers for the Phase 1A station availability preflight."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PARAMETERS = ("temperature", "dew_point", "relative_humidity", "precipitation",
              "wind_speed", "wind_direction", "pressure")
STATUSES = {"VERIFIED_AVAILABLE", "PARTIALLY_AVAILABLE", "UNAVAILABLE", "METADATA_ONLY",
            "NOT_CHECKED", "ACCESS_RESTRICTED", "CONFLICTING_SOURCE_INFORMATION"}


def parse_station_inventory(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return station candidates exactly as reported by repository inventory."""
    result = []
    for item in payload.get("stations", []):
        result.append({"station_id": str(item.get("station_id", "")).strip(),
                       "role": item.get("role", "unknown"),
                       "reported_location": item.get("reported_location"),
                       "reported_period": item.get("reported_period"),
                       "reported_count": item.get("reported_observation_count", item.get("observation_count")),
                       "latitude": None, "longitude": None, "elevation_m": None,
                       "verification_status": "METADATA_ONLY",
                       "confidence": item.get("provenance_confidence", "LOW"),
                       "source": "outputs/station_provenance/station_manifest.json"})
    return result


def valid_coordinates(latitude: Any, longitude: Any) -> bool:
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return False
    return math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if not all(valid_coordinates(a, b) for a, b in ((lat1, lon1), (lat2, lon2))):
        raise ValueError("Haversine requires finite latitude/longitude pairs in geographic bounds")
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 6371.0088 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def classify_data_source(source: Any) -> str:
    if source is None or str(source).strip() == "":
        return "UNKNOWN_ORIGIN"
    value = str(source).strip().lower()
    if any(token in value for token in ("model", "interpol", "reanalysis", "grid")):
        return "MODEL_GENERATED_OR_INTERPOLATED"
    if any(token in value for token in ("synop", "metar", "observation", "station")):
        return "OBSERVATION_SOURCE_INDICATED_NOT_INDEPENDENTLY_VERIFIED"
    return "PROVIDER_SOURCE_INDICATED_UNCLASSIFIED"


def classify_suitability(*, primary_coordinates: bool, neighbor_coordinates: bool,
                         elevation_known: bool, parameter_overlap: bool,
                         observed_overlap: bool, direct_source: bool) -> tuple[str, str]:
    if not (primary_coordinates and neighbor_coordinates):
        return "INSUFFICIENT_METADATA", "Verified coordinates are missing; distance cannot be calculated."
    if not direct_source:
        return "CONDITIONAL_CANDIDATE", "Source is not verified as direct station observations."
    if not parameter_overlap or not observed_overlap:
        return "CONDITIONAL_CANDIDATE", "Parameter or observed temporal overlap has not been established."
    if not elevation_known:
        return "CONDITIONAL_CANDIDATE", "Elevation difference is unknown."
    return "SUITABLE_CANDIDATE", "Metadata and observed overlap checks passed; scientific inclusion criteria remain to be defined."


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_preflight_manifest(output_dir: Path, *, commit: str, inputs: list[Path], summary: dict,
                             network_status: str, environment: dict,
                             repo_root: Path | None = None) -> dict:
    output_dir = Path(output_dir)
    outputs = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "preflight_manifest.json":
            outputs.append({"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    manifest = {"schema_version": 1, "git_commit": commit,
                "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "environment": environment,
                "inputs": [{"path": p.relative_to(repo_root).as_posix() if repo_root else str(p),
                            "sha256": sha256(p)} for p in inputs],
                "outputs": outputs, "summary": summary, "network_access_status": network_status,
                "limitations": ["Inventory metadata does not prove populated observations.",
                                "No raw hourly observations were downloaded.",
                                "Manifest hash is not self-referential."]}
    (output_dir / "preflight_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    return manifest


def verify_preflight_manifest(output_dir: Path, *, repo_root: Path | None = None) -> bool:
    output_dir = Path(output_dir)
    manifest = json.loads((output_dir / "preflight_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["inputs"]:
        path = (Path(repo_root) / record["path"]) if repo_root else Path(record["path"])
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise ValueError(f"Preflight input integrity failure: {record['path']}")
    for record in manifest["outputs"]:
        path = output_dir / record["path"]
        if not path.is_file() or path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"Preflight output integrity failure: {record['path']}")
    return True


def inventory_parameter_records(station_id: str, inventory: Any, *, provider: str = "Meteostat",
                                retrieved_at: str | None = None) -> list[dict[str, Any]]:
    """Represent station inventory metadata without claiming parameter observations exist."""
    start = str(getattr(inventory, "start", "") or "")
    end = str(getattr(inventory, "end", "") or "")
    params = set(getattr(inventory, "parameters", []) or [])
    records = []
    for parameter in PARAMETERS:
        available = parameter in params
        records.append({"station_id": station_id, "provider": provider, "parameter": parameter,
                        "availability_status": "METADATA_ONLY" if available else "NOT_CHECKED",
                        "frequency": "hourly inventory" if start or end else "",
                        "start_date": start, "end_date": end,
                        "data_type": "inventory metadata; not observation rows",
                        "source_indicator_available": "NOT_QUERIED",
                        "retrieval_timestamp_utc": retrieved_at or datetime.now(timezone.utc).isoformat(),
                        "notes": "Inventory does not verify populated timestamps or direct/model source."})
    return records
