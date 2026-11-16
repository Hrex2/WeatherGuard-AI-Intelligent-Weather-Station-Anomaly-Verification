# Codex changelog — 2026-11-16

- Added `src/weather_research/synthetic_campaign.py` for reproducible controlled temperature point-spike experiments on saved Phase 01/03 artifacts.
- Generated the controlled +2, +5, +10, +15 °C campaign outputs and machine-readable manifest under `outputs/synthetic_fault_campaign/`.
- Added a local-versus-saved clean prediction parity table. The discrepancy is preserved and surfaced rather than hidden.
- Updated `src/weather_research/evidence.py` to use the requested outcome identifiers and return evidence explanation fields, including missing/conflicting states and an uncalibrated uncertainty statement.
- Updated evidence outcome expectations in `tests/test_research.py`.
- Added `CODEX_PROJECT_AUDIT.md`, `CODEX_HANDOFF.md`, and `NEXT_STEPS.md`.
- Existing notebooks, saved outputs, verified snapshots, prior reports, migration history, and registry history were preserved.

- Added a Phase 02 provenance report and machine-readable station manifest that explicitly preserve unavailable metadata as null; no retrieval was performed.
- Updated the experiment registry with the executed local temperature dose series and its baseline parity limitation.

## WeatherGuard AI application stage

See `CHANGELOG_RESEARCH.md` for the app, services, literature content, and tests added on 2026-11-16.

Final application validation: 35 tests passed; AppTest covered all five workspaces. Local socket denial prevented browser screenshot/HTTP health validation.
