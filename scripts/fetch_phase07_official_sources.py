"""Fetch small NOAA NCEI source files for Phase 07 without replacing files."""
from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "outputs" / "phase07_independent_evidence" / "external_reference_data"
BASE = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly"
SOURCES = {
    "ghcnh-station-list.csv": f"{BASE}/doc/ghcnh-station-list.csv",
    "ghcnh-source-list.pdf": f"{BASE}/doc/ghcnh-source-list.pdf",
    **{
        f"GHCNh_{station}_{year}.psv":
            f"{BASE}/access/by-year/{year}/psv/GHCNh_{station}_{year}.psv"
        for station in ("INI0000VILD", "INM00042101")
        for year in ("2025", "2026")
    },
}


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        path = DEST / name
        if path.exists():
            print(f"PRESERVED {name} ({path.stat().st_size} bytes)")
            continue
        request = Request(url, headers={"User-Agent": "WeatherGuard-Research/Phase07"})
        try:
            with urlopen(request, timeout=90) as response:
                payload = response.read()
        except HTTPError as exc:
            print(f"UNAVAILABLE {name}: HTTP {exc.code}")
            continue
        with path.open("xb") as stream:
            stream.write(payload)
        print(f"FETCHED {name} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
