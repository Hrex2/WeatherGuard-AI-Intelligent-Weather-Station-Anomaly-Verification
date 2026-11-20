"""Normalize provider inventory evidence while keeping it separate from observations."""
from __future__ import annotations

from typing import Any

PARAMETERS = ("temperature", "dew_point", "relative_humidity", "precipitation",
              "wind_speed", "wind_direction", "pressure")
AVAILABILITY_STATUSES = {"OBSERVATION_AVAILABILITY_VERIFIED", "INVENTORY_ONLY",
                         "PARTIAL_AVAILABILITY", "UNAVAILABLE", "ACCESS_RESTRICTED",
                         "NOT_CHECKED", "SOURCE_UNKNOWN"}


def parameter_inventory_records(station_id: str, provider: str, inventory: dict[str, Any] | None,
                                *, frequency: str = "hourly") -> list[dict[str, Any]]:
    """Expand documented provider/parameter inventory into explicit, conservative records."""
    inventory = inventory or {}
    params = set(inventory.get("parameters", []))
    provider_params = set(inventory.get("provider_parameters", []))
    records = []
    for parameter in PARAMETERS:
        present = parameter in params or parameter in provider_params
        records.append({"station_id": station_id, "provider": provider, "parameter": parameter,
                        "potential_inventory": "PRESENT" if present else "NOT_ESTABLISHED",
                        "verification_status": "INVENTORY_ONLY" if present else "NOT_CHECKED",
                        "frequency": frequency if present else "",
                        "start_date": inventory.get("start_date", "") if present else "",
                        "end_date": inventory.get("end_date", "") if present else "",
                        "direct_observation_evidence": "NOT_CHECKED",
                        "source_indicator_availability": "NOT_QUERIED"})
    return records


def classify_meteostat_source(code: Any) -> str:
    """Only classify known textual descriptions; undocumented numeric codes stay unknown."""
    if code is None or str(code).strip() == "":
        return "SOURCE_UNKNOWN"
    value = str(code).strip().casefold()
    if any(token in value for token in ("model", "interpol", "reanalysis", "grid")):
        return "MODEL_OR_INTERPOLATED_INDICATED"
    if any(token in value for token in ("synop", "metar", "observation", "station")):
        return "OBSERVATION_SOURCE_INDICATED_NOT_INDEPENDENTLY_VERIFIED"
    return "SOURCE_UNKNOWN"


def intersect_windows(windows: list[tuple[str | None, str | None]]) -> tuple[str | None, str | None]:
    valid = [(start, end) for start, end in windows if start and end]
    if len(valid) != len(windows) or not valid:
        return None, None
    start, end = max(x[0] for x in valid), min(x[1] for x in valid)
    return (start, end) if start <= end else (None, None)


def frequencies_compatible(frequencies: list[str]) -> bool:
    return bool(frequencies) and len(set(frequencies)) == 1 and frequencies[0] in {"hourly", "daily"}


def classify_provider_response(status_code: int | None, *, exception: str | None = None) -> str:
    if exception:
        return "NOT_CHECKED"
    if status_code == 200:
        return "INVENTORY_ONLY"
    if status_code in {401, 403, 429}:
        return "ACCESS_RESTRICTED"
    if status_code in {404, 204}:
        return "UNAVAILABLE"
    return "NOT_CHECKED"


def build_retrieval_proposal(*, stations: list[str], variables: list[str],
                             start_date: str | None, end_date: str | None,
                             providers: list[str], frequency: str,
                             availability_verified: bool) -> dict[str, Any]:
    return {"stations": stations, "variables": variables, "start_date": start_date,
            "end_date": end_date, "providers": providers, "frequency": frequency,
            "retrieval_authorized": False,
            "availability_verified": availability_verified,
            "expected_record_count": None,
            "expected_file_size": None,
            "status": "READY_FOR_REVIEW" if availability_verified else "PROVISIONAL_AVAILABILITY_UNVERIFIED"}


def require_approval(*, approved: bool, stations: list[str], variables: list[str],
                     start_date: str | None, end_date: str | None, providers: list[str]) -> None:
    """Fail closed for any operation that could retrieve observations."""
    if not approved or not all((stations, variables, start_date, end_date, providers)):
        raise PermissionError("Raw historical retrieval requires explicit approval of providers, stations, variables, and dates")
