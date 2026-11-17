"""Conservative station identity checks for research preflight workflows."""
from __future__ import annotations

from typing import Any

IDENTITY_CLASSES = {
    "SAME_PHYSICAL_STATION_CONFIRMED", "POSSIBLE_ALIAS", "DISTINCT_STATIONS_CONFIRMED",
    "POSSIBLE_RELOCATION", "IDENTITY_UNRESOLVED", "CONFLICTING_METADATA",
}


def classify_identity(left: dict[str, Any], right: dict[str, Any], *,
                      independent_evidence: bool = False,
                      shared_official_id: bool = False,
                      history_evidence: bool = False,
                      coordinate_tolerance_km: float = 0.25) -> str:
    """Classify a pair without treating proximity/name similarity as identity proof."""
    lcoord, rcoord = left.get("coordinates"), right.get("coordinates")
    if lcoord and rcoord:
        distance = haversine_km(*lcoord, *rcoord)
        lelev, relev = left.get("elevation_m"), right.get("elevation_m")
        if distance <= coordinate_tolerance_km and lelev is not None and relev is not None and abs(lelev-relev) > 100:
            return "CONFLICTING_METADATA"
        if distance > coordinate_tolerance_km and shared_official_id and history_evidence:
            return "POSSIBLE_RELOCATION"
        if distance > coordinate_tolerance_km and independent_evidence and history_evidence:
            return "DISTINCT_STATIONS_CONFIRMED"
        if distance <= coordinate_tolerance_km and shared_official_id and independent_evidence:
            return "SAME_PHYSICAL_STATION_CONFIRMED"
        if shared_official_id and distance <= 5:
            return "POSSIBLE_ALIAS"
    return "IDENTITY_UNRESOLVED"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import atan2, cos, radians, sin, sqrt
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi, dlambda = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
    return 6371.0088 * 2 * atan2(sqrt(a), sqrt(1-a))


def same_identifier(left: Any, right: Any) -> bool:
    return bool(left and right and str(left).strip().casefold() == str(right).strip().casefold())
