"""Retrieve public IEM archive messages for the eight fixed Phase 10 event dates.

The IEM service is a downstream, multi-source archive. Returned raw METAR text
is preserved as an archive copy and is not asserted to be provider-original.
"""
from __future__ import annotations

import csv
import hashlib
import http.client
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase11_original_observations_event_adjudication"
EVENTS = ROOT / "outputs" / "phase10_independent_reference_data" / "PHASE10_CANDIDATE_EVENT_REGISTER.csv"
BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if not OUT.is_dir():
        raise FileNotFoundError("Phase 11 output directory must be initialized explicitly")
    events = pd.read_csv(EVENTS)
    dates = sorted({pd.Timestamp(x).tz_convert("UTC").strftime("%Y-%m-%d")
                    for x in events.timestamp_utc_reproduction})
    log_path = OUT / "iem_retrieval_log.json"
    if log_path.exists():
        raise FileExistsError(f"Refusing to overwrite acquisition log: {log_path}")
    entries = []
    for index, day in enumerate(dates):
        start = f"{day}T00:00:00Z"
        end = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
        params = {"station": "VILD", "data": "metar", "sts": start, "ets": end,
                  "tz": "UTC", "format": "onlycomma"}
        url = BASE + "?" + urlencode(params)
        target = OUT / f"iem_vild_metar_{day.replace('-', '')}_raw.csv"
        if target.exists():
            body = target.read_bytes()
            entries.append({"requested_date_utc": day, "request_url": url,
                            "retrieved_at_utc": None, "http_status": "PREEXISTING_PHASE11_ATTEMPT",
                            "response_bytes": len(body), "sha256": sha256(body),
                            "saved_file": target.name, "complete_response": True,
                            "observation_rows": max(0, body.count(b"\n") - 1),
                            "note": "Existing Phase 11 attempt preserved; not overwritten."})
            continue
        request = Request(url, headers={"User-Agent": "WeatherGuard-Research/Phase11"})
        retrieved = datetime.now(timezone.utc).isoformat()
        status, content_type, error, body, complete = None, None, None, b"", True
        try:
            with urlopen(request, timeout=45) as response:
                status = response.status
                content_type = response.headers.get("Content-Type")
                try:
                    body = response.read()
                except http.client.IncompleteRead as exc:
                    body = exc.partial
                    complete = False
                    error = f"IncompleteRead: response ended after {len(body)} bytes"
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            complete = False
            error = f"{type(exc).__name__}: {exc}"
        suffix = "_raw.csv" if complete and status == 200 else "_partial_response.bin"
        saved = OUT / f"iem_vild_metar_{day.replace('-', '')}{suffix}"
        if saved.exists():
            raise FileExistsError(f"Refusing to overwrite acquisition response: {saved}")
        saved.write_bytes(body)
        text_rows = 0
        if complete and status == 200:
            text_rows = max(0, body.count(b"\n") - 1)
        entries.append({"requested_date_utc": day, "request_url": url,
                        "retrieved_at_utc": retrieved, "http_status": status,
                        "content_type": content_type, "response_bytes": len(body),
                        "sha256": sha256(body), "saved_file": saved.name,
                        "complete_response": complete, "observation_rows": text_rows,
                        "error": error, "raw_response_preserved": True})
        if index < len(dates) - 1:
            time.sleep(1.1)  # IEM documents a minimum one-second per-IP throttle.
    log = {"source": "Iowa State University Iowa Environmental Mesonet ASOS/METAR archive",
           "source_type": "downstream multi-source archive; raw message field requested",
           "station": "VILD", "date_selection": "One complete UTC calendar day for each of the eight pre-existing Phase 10 candidate dates; no temporal matching window applied.",
           "candidate_source": "outputs/phase10_independent_reference_data/PHASE10_CANDIDATE_EVENT_REGISTER.csv",
           "requested_variables": ["metar"], "timezone": "UTC", "request_entries": entries,
           "provider_report_id_available": False,
           "note": "IEM documents records as an as-is archive sourced from multiple feeds including Unidata IDD, NCEI ISD, and MADIS; no unique provider ID is returned by this request."}
    log_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"requested_dates": len(entries),
                      "complete_days": sum(bool(x["complete_response"]) for x in entries),
                      "observation_rows": sum(int(x["observation_rows"]) for x in entries),
                      "log": log_path.relative_to(ROOT).as_posix()}, indent=2))


if __name__ == "__main__":
    main()
