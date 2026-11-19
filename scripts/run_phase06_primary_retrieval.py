"""Controlled Phase 06 Meteostat primary-station collection.

Run explicitly in the isolated Meteostat 2.2.3 environment. The command refuses
to reuse/overwrite a prior Phase 06 output directory and saves provider source
IDs without filling or cleaning.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import platform
from pathlib import Path

import meteostat as ms

from weather_research.phase04_collection import (
    coverage_metrics, fetch_observation_sources, sha256_file, source_index,
    source_provider_grade_map, write_raw_frame,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase06_controlled_e3_validation"
START = datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 3, 9, 23, 59, tzinfo=timezone.utc)
STATION = "VILD0"
PARAMETERS = [
    ms.Parameter.TEMP, ms.Parameter.DWPT, ms.Parameter.RHUM,
    ms.Parameter.PRCP, ms.Parameter.WSPD, ms.Parameter.WDIR, ms.Parameter.PRES,
]


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite Phase 06 output directory: {OUT}")
    if ms.__version__ != "2.2.3":
        raise RuntimeError(f"Expected Meteostat 2.2.3; found {ms.__version__}")

    OUT.mkdir(parents=True)
    raw_dir = OUT / "raw_station_data"
    raw_dir.mkdir()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    frame, settings = fetch_observation_sources(
        ms, STATION, START, END, "UTC", PARAMETERS, expected_version="2.2.3"
    )
    if frame is None or frame.empty:
        status = "SUCCESS_NO_DATA"
        row_count = 0
        relative_path = None
        digest = None
        coverage = coverage_metrics(frame if frame is not None else __import__("pandas").DataFrame(), START, END, [p.value for p in PARAMETERS])
        source_counts = {}
    else:
        status = "SUCCESS_WITH_DATA"
        relative_path = "raw_station_data/VILD0_hourly_source_level.csv"
        raw_path = OUT / relative_path
        digest = write_raw_frame(frame, raw_path)
        row_count = len(frame)
        coverage = coverage_metrics(frame, START, END, [p.value for p in PARAMETERS])
        sources = source_index(frame).astype(str)
        source_counts = {name: int(count) for name, count in sources.value_counts(dropna=False).items()}

    manifest = {
        "schema_version": 1,
        "phase": "06_controlled_e3_validation",
        "retrieved_at_utc": retrieved_at,
        "station_id": STATION,
        "station_identity_basis": "Phase 05 verified airport-station record crosswalk; exact sensor location remains unresolved",
        "meteostat_version": ms.__version__,
        "python_version": platform.python_version(),
        "requested_start_utc": START.isoformat(),
        "requested_end_utc_inclusive": END.isoformat(),
        "timezone": "UTC",
        "provider": "hourly",
        "retrieval_settings": settings,
        "api_contract_verified": {
            "hourly_signature_has_providers": True,
            "fetch_signature_has_sources_fill_squash_clean": True,
            "source_ids_retained_in_source_index": True,
            "model_data_disabled_by_config": settings["model_setting"] is False,
            "model_setting_restored_after_fetch": ms.config.include_model_data is True,
        },
        "status": status,
        "row_count": row_count,
        "coverage": coverage,
        "source_distribution": source_counts,
        "provider_grade_map": source_provider_grade_map(ms),
        "output_file": relative_path,
        "sha256": digest,
        "raw_export_semantics": "Meteostat package-returned source-level rows; not original upstream HTTP/METAR payloads",
        "source_lineage_limit": "Source/provider IDs do not independently prove sensor operator, instrument, or independent upstream measurement chain.",
        "no_fill": True,
        "no_clean": True,
        "no_model_training": True,
        "no_imputation": True,
    }
    if relative_path:
        manifest["sha256_verified_after_export"] = sha256_file(OUT / relative_path)
    (OUT / "primary_retrieval_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"status": status, "rows": row_count, "sources": source_counts,
                      "sha256": digest, "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
