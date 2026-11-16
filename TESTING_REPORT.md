# Testing and Validation Report — Final Targeted Bug-Fix Audit

## Actual results

- **PASS — 31 tests, 0 failures:** `python -B -m unittest discover -s tests -v`.
- **PASS:** Missing configuration/timestamp predictions raise instead of silently counting as normal votes. All configuration test timestamp sets must match.
- **PASS:** Model configuration prediction tests preserve timestamp alignment and metadata.
- **PASS:** Repeated-spike ground truth marks only changed timestamps, while the registry retains all interval timestamps and records exact injected timestamps separately.
- **PASS:** Physical screening gives each available weather variable explicit missing, nonnumeric, infinite, below-range, above-range and cross-variable inconsistency flags; screening is not a sensor-fault label.
- **PASS:** Fault injection requires a calibration boundary; faults cannot cross irregular timestamp gaps or segment boundaries; point spikes are single-timestamp; missing model outputs are not counted as normal.
- **PASS:** The injected observation is excluded from its own shifted rolling reference; pre-fault feature rows are unchanged.
- **PASS:** Matched controls are post-candidate, hourly contiguous, and non-overlapping; block-length sensitivity executes on synthetic episode pairs. These checks do not establish inferential validity.
- **PASS:** Incomplete evidence abstains; exact-time missing-neighbor states remain unavailable.
- **PASS:** Every notebook section has an explicit implementation status.
- **PASS:** Notebook setup cell imports the package from a separate working directory using `WEATHER_RESEARCH_ROOT`.
- **PASS:** All master notebook cells have unique stable IDs under nbformat 4.5. The unchanged archive declares nbformat 4.0, where cell IDs are not required; its original bytes, outputs and execution history remain preserved.
- **PASS:** Master notebook default path ran all 16 code cells sequentially with data, retrieval and model actions disabled.

## Not run / not verified

- **NOT VERIFIED:** Real Pipeline B/VILD0 data, Drive manifest, real Phase 01 audit, or historical prediction reproduction.
- **NOT IMPLEMENTED in this package:** Full Phase 02 station-provenance inventory/readback/candidate-coverage audit. Earlier `decision_log.md` references point to a separate historical working folder, not deliverables in this package.
- **NOT RUN:** Meteostat retrieval, Google Drive persistence/readback, complete 12-model research experiment, or real matched-control/synthetic fault evaluation.
- **NOT VERIFIED:** A hosted Colab runtime. The clean-process import-path check emulates package discovery locally; it cannot verify Drive mounting, Colab package resolution or Meteostat API behavior.
- **NOT IMPLEMENTED:** Ablation runner, complete sensor-behavior evidence, research figures and report export pipeline.

Software tests use synthetic fixtures only and do not establish scientific validity or station-level truth.

## Codex continuation run (2026-11-16)

- python -B -m unittest discover -s tests -v: **31 passed, 0 failed** after the continuation edits.
- python -m compileall -q src/weather_research: passed.
- Parsed the synthetic campaign and station provenance JSON manifests and all nine generated campaign CSVs successfully.
- Controlled temperature campaign executed locally; output-specific parity discrepancy and results are recorded in CODEX_PROJECT_AUDIT.md. No Colab or data retrieval was run.

## WeatherGuard AI application validation — 2026-11-16

- `python -B -m unittest discover -s tests -v`: **35 passed, 0 failed** (31 research tests and 4 application contract/UI tests).
- Streamlit `AppTest` started the Command Center and navigated all five workspaces without script exceptions.
- Verified artifact loader row counts, feature-column parity, manifest state, and the 8,415 × 12 complete prediction grid.
- JSON manifests and literature metadata parsed; `python -m compileall -q app.py services ui src/weather_research tests` passed.
- A local HTTP health request could not be validated because the managed sandbox denied localhost socket access. No screenshot was captured; no fake screenshot was created.
- The optional full model run and UI-triggered synthetic campaign were not invoked during smoke tests to avoid long model fits. The temperature campaign outputs from the prior local execution remain the displayed synthetic results.

## Friday demonstration readiness validation — 2026-11-16

- `python -B -m unittest discover -s tests -v`: **39 passed, 0 failed**. Includes manifest mismatch rejection, missing-only E4 handling, sub-threshold E1 categorization, E2 consensus-dependence handling, synthetic affected-window metric regression, and all-workspace AppTest.
- `python -m compileall -q app.py services ui src/weather_research tests`: passed.
- Fresh Streamlit process command `python -m streamlit run app.py --server.headless true --server.port 8765` started. A direct `/_stcore/health` request could not be made because the managed sandbox denied localhost socket access. AppTest is the successful page-level verification; direct browser rendering remains unverified here.
- Loader checked SHA-256, rows and ordered columns for the three loaded Phase 01 snapshots. Counts: observations 44,879; train 36,434; test 8,415. Saved predictions: 100,980 rows across 8,415 timestamps and 12 configurations, without duplicate pairs or missing labels.
- Saved campaign figures and summary are displayed only when their manifest indicates a passed Phase 01 audit and their source hashes match the currently loaded Phase 01 files.
- Synthetic event table now separately reports all-window changes and changes beyond the feature-propagation window. Existing saved propagation checks were reused; no model refit was run.
- Full optional model fitting, a new campaign, real browser screenshot capture, and notebook execution were not run.
