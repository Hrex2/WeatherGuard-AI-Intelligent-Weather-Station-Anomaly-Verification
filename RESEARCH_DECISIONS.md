# Research Decisions

## 2026-11-16 — Resume without regenerating historical artifacts

**Decision:** Treat commit `830d315` as the recovery baseline and continue on `codex/autonomous-research-loop`. Reuse existing Phase 01 snapshots, Phase 03 prediction grid, and controlled point-spike outputs.
**Reason:** Their hashes/counts and internal structures are already checked; broad regeneration adds cost and can obscure historical provenance. The exact 42-cell mismatch is a specific unresolved issue and warrants a targeted reproduction.
**Limit:** Current refit environment cannot explain historical differences without saved estimator/scaler provenance and original run environment details.

## 2026-11-16 — Agreement and uncertainty labels

**Decision:** Keep model agreement as a fraction of available binary predictions, never as a probability. Show an 8/12 label only for a complete twelve-configuration grid.
**Reason:** Partial availability must not be treated as if all 12 configurations voted. Independent evidence availability remains a separate measure.

## 2026-11-16 — Station geography

**Decision:** Render no marker unless the station manifest has valid verified coordinates.
**Reason:** VILD0 coordinates are null; reported locality is not a station coordinate. E3 remains unavailable without validated neighbor observations.

## 2026-11-16 — Independent temporal screen

**Decision:** E2 uses measured-variable history, estimates local cadence, and stops context across gaps larger than 1.5× the median interval. Real-time mode uses prior observations and the selected value only; retrospective mode is separately labelled and may inspect following observations.
**Exploratory defaults:** six-hour prior context, three non-missing context rows, 3.5 scaled-MAD departure threshold, and a stuck run of four equal measurements.
**Limit:** These are screening defaults, not validated meteorological criteria. E2 describes temporal behavior and cannot diagnose hardware failure.

## 2026-11-16 — Uploaded data

**Decision:** Keep uploads isolated; validate six mapped variables, units, timestamps, uniqueness, hourly cadence and causal features before any fit. Fit only after an explicit user action; never mutate historical snapshots or persist raw uploads/estimators.
**Limit:** Current protocol is hourly and fixed to its 11-feature order; other cadence/feature schemas are rejected instead of silently adapted.
