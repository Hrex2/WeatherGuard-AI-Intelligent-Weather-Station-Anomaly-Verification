"""Dry-run the bounded METAR pilot; execution is gated and currently blocked."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from weather_research.metar_pilot import (  # noqa: E402
    PILOT_SPEC, PilotBlockedError, dry_run_payload, execute_pilot,
)

SPEC_PATH = ROOT / "research_results" / "phase1c_metar_pilot" / "PILOT_RETRIEVAL_SPEC.json"
OUTPUT_ROOT = ROOT / "research_results" / "phase1c_metar_pilot"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Request the gated observation retrieval")
    parser.add_argument("--confirm-pilot-retrieval", action="store_true", help="Confirm the exact spec was explicitly approved by the user")
    args = parser.parse_args(argv)
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

    if not args.execute and not args.confirm_pilot_retrieval:
        print(json.dumps(dry_run_payload(spec), indent=2))
        print("Dry run only: no provider call, network request, or observation download was performed.")
        return 0
    if not (args.execute and args.confirm_pilot_retrieval):
        print("Refused: both --execute and --confirm-pilot-retrieval are required; no data request was made.", file=sys.stderr)
        return 2

    try:
        run_dir = execute_pilot(spec=spec, execute=True, confirm=True, output_root=OUTPUT_ROOT)
    except (PermissionError, PilotBlockedError, RuntimeError, ValueError) as exc:
        print(f"Retrieval refused: {exc}", file=sys.stderr)
        return 2
    print(f"Pilot run saved to {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
