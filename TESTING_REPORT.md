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

## User-friendly UI and model education redesign — 2026-11-16

- `python -B -m unittest discover -s tests -v`: **40 passed, 0 failed**.
- Streamlit AppTest visited Home, Weather Data, Investigate a Reading, Model Evaluation, Experiment Lab, and Research with no script exceptions. Weather Data and Model Evaluation each rendered Plotly charts.
- AppTest confirmed Model Evaluation has exactly two primary sections, all three model-profile selections render, and no new model-run state is created on page load.
- Model metadata tests checked the 11-feature order; actual train/test counts; all configurations; Isolation Forest settings; LOF neighbor values/novelty/contamination; and One-Class SVM kernel/gamma/nu.
- `python -m compileall -q app.py services ui src/weather_research tests`: passed.
- No estimator refit or synthetic campaign was run as part of the UI redesign.

## Autonomous research continuation and investigation workspace — 2026-11-16

- `python -B -m unittest discover -s tests -v`: **55 passed, 0 failed**.
- `python -m compileall -q app.py services ui src/weather_research tests scripts`: passed.
- Streamlit AppTest visited all six workspaces with no script exceptions; confirmed the investigation charts/variable selector, upload expander, and two-section Model Evaluation view.
- Temporal service tests cover causal no-future behavior, retrospective persistence/return, stable and gradual series, stuck patterns, missing values, insufficient context, irregular gaps and segment boundaries.
- Heatmap/upload tests cover date/family filtering, unavailable cells, complete-grid consensus, observed-variable discovery, verified-coordinate refusal, unit conversion, immutable input, duplicate/invalid timestamps, hourly cadence, and chronological training-only imputation.
- `scripts/analyze_saved_e1.py` ran on saved labels only. Sensitivity counts: 432 (4/12), 214 (6/12), 123 (8/12), 51 (10/12), 15 (12/12); no model refit for this analysis.
- `scripts/investigate_prediction_mismatches.py` locally refit the existing 12 configurations once to investigate the specific parity issue. It reproduced 42 differences, all in Isolation Forest; cause remains unresolved because historical estimators/scalers and complete historical fit provenance are absent. Saved prediction files were not changed.
- No CSV model fit, spatial retrieval or real-label performance study was run in this checkpoint. The separately documented synthetic fault matrix was run afterward. Direct browser rendering, raw-data reconstruction and external source/repository contact are not verified here.

## E2 temporal sensitivity — 2026-11-16

- `python scripts/evaluate_e2_sensitivity.py`: passed; evaluated 123 saved 8/12 candidate timestamps across five prior windows, three robust-deviation thresholds, and real-time/retrospective modes (3,690 result rows).
- At the six-hour/3.5 scaled-MAD default: real-time returned 47 supporting and 76 no-detected-departure statuses. Retrospective returned 43 supporting, 76 no-detected-evidence, and 4 return-to-baseline conflicts.
- The one-hour window returned unavailable for all 123 candidates because the configured minimum is three prior observations. This is a data/context availability result, not a negative temporal finding.
- Candidate timestamps were selected by E1 consensus, so the analysis is not independent evidence validation. It is descriptive sensitivity only and does not establish a calibrated threshold or real-world accuracy.

## Additional synthetic fault matrix — 2026-11-16

- `python scripts/run_synthetic_fault_matrix.py` completed one shared local 12-configuration fit and eight held-out synthetic scenarios. Run ID: `fault_matrix_02bd147f5cce`.
- Scenario preflight validated held-out intervals and broad bounds before model fitting. The full suite passed **57/57**, including scenario preflight, immutable input and neutral metric-label tests; Python compilation passed.
- The run recorded exact original/injected values, labels, seeds, feature order, training/test spans, data hashes, package versions and model settings. Full duplicate holdout prediction grids were compacted to injected and changed rows only.
- Results are single-context synthetic screening observations. No verified clean labels or real-world fault labels exist; do not interpret unmodified-row flags as false positives or synthetic label recall as real-world accuracy.

## Research validation master loop — Phase 1 audit (2026-11-16)

- Refreshed GitHub state: `main` is `0a27959`, merge PR #1; the prior `codex/autonomous-research-loop` remains preserved. Started `codex/research-validation-v2` from the latest main with a clean worktree.
- `python -B -m unittest discover -s tests -v`: **66 passed, 0 failed**. Includes regression cases for missing/irregular/segment-separated stuck runs, cadence changes, timezone-aware indexes, same-segment stuck injection, unavailable spatial evidence, strict CSV interval validation, selected-variable E2 and the Experiment Lab matrix.
- `python -m compileall -q app.py services ui src/weather_research tests scripts`: passed.
- `git diff --check`: passed.
- Phase 03 integrity manifest verified **11 CSV artifacts** against SHA-256, ordered columns, row counts, available timestamp/configuration counts, and Phase 01 reference hashes. Manifest explicitly says `HASHED_INTEGRITY_ONLY_HISTORICAL_PROVENANCE_UNKNOWN`.
- Streamlit AppTest visited all six workspaces without page exceptions and confirmed the saved eight-scenario matrix appears in Experiment Lab.
- Dataset snapshots, saved predictions, and the old synthetic matrix were not regenerated or overwritten. No model campaign was fit during this phase.
- CI was added in `.github/workflows/research-quality.yml`; hosted Actions status has not yet been observed.

The eight audit findings AUD-01 through AUD-08 are corrected. AUD-09 remains a documented selection-dependence limit; AUD-10 remains blocked by the absence of verified neighboring-station raw data; AUD-11 status records have been synchronized. Software verification does not establish scientific validity.

## Multi-context synthetic campaign preparation (2026-11-16)

- Added a deterministic pre-injection selector requiring a regular hourly 24-hour history, a continuous six-observation injection interval, adequate core-variable coverage and successful preflight of all eight existing scenarios.
- Selected five held-out contexts without inspecting model responses: 2025-04-09 (high temperature/low variability), 2025-05-27 (high/high), 2025-09-04 (middle/middle), 2025-11-30 (low/high), and 2026-02-06 (low/low). The contexts cover calendar quarters 1–4 and are at least 14 days apart. Preflight only; no model fitting or fault predictions have run.
- Added orchestration to fit the 12-configuration protocol once and reuse the clean holdout comparator across all contexts. Each context retains its own exact injection registry and output manifest; the campaign writes aggregate context and family summaries and records failure status if fitting/evaluation errors occur.
- Added changes outside the declared feature-propagation window and synthetic-label detection-delay fields, with a regression for aggregate preservation.
- `python -m compileall -q app.py services ui src/weather_research tests scripts`: passed. `python -B -m unittest discover -s tests -v`: **68 passed, 0 failed**.
- Runner and tests are not yet committed/pushed; next step is commit and push the validated runner before executing the campaign.

## Five-context synthetic matrix execution — 2026-11-16

- Campaign `fault_matrix_multicontext_46ae5d119d` completed with five preselected contexts across quarters 1–4 and all eight existing fault scenarios. One train-only fit and clean holdout comparator were reused across all 40 context/scenario combinations.
- Scenario fractions across configuration × injected-timestamp decisions varied by context: point spike 0.667–1.000, point drop 0.667–0.917, persistent offset 0.042–0.361, stuck 0–0.319, drift 0–0.056, missing block 0–0.333, noise 0–0.292, and dew-point offset 0.667–0.806. These are synthetic responses, not real-world accuracy.
- No model label changes occurred outside the declared feature-propagation window across the campaign. E4 broad screening changed on 36 injected timestamp-variable rows. The same-run unmodified observation flag rate is not a validated false-positive rate.
- Context/run artifacts and interpretation are in `MULTICONTEXT_FAULT_MATRIX_REPORT.md` and `research_results/fault_matrix_multicontext_46ae5d119d/`; original single-context outputs remain intact.
- Added E2 injection/control paired evaluator and selected 10 matched unmodified controls by calendar quarter, time-of-day, recent temperature level/variability and missingness, with 14-day separation from injection contexts.
- E2 evaluation completed: **6,840** screen evaluations, **10** matched controls, **2,880** same-time paired comparisons and **813** summary rows. Paired statuses changed in 1,008/2,880 comparisons; 270 missing-block cases became `UNAVAILABLE`. `SUPPORTING` occurred in 961/2,610 available faulted comparisons, 691/2,880 same-time unmodified rows and 272/1,080 matched-control rows. These are repeated exploratory screen outcomes, not adjudicated accuracy metrics.
- Added hash-gated five-context and E2 summary views in Experiment Lab, including per-fault status changes and status counts across injection, same-time and matched-control conditions. AppTest visits the Experiment Lab and checks both new views. `python -B -m unittest discover -s tests -v`: **69 passed, 0 failed** in 51.8 seconds; compileall and `git diff --check` passed.

## PR #2 pre-merge review — 2026-11-17

- Rechecked the five-context manifests, 40 context/scenario combinations, 12 shared configurations, 96 configuration rows and 24 family rows per context. Selection is pre-injection and separated across four calendar quarters; Phase 03's 11 source CSVs pass the recorded hash/shape checks. These integrity checks do not establish historical provenance.
- Corrected E2 pairing so each pair must contain exactly one unlabeled same-time comparator and one synthetically labeled fault row; duplicate or incomplete pairs fail closed. Corrected outputs are versioned under `e2_validation_review_1/`, preserving the original outputs. The new manifest verifies 4 files: 6,840 detail rows, 2,880 pairs, 813 summaries and 10 matched controls. Paired status counts remain 1,008 changes and 270 faulted missing-block rows marked `UNAVAILABLE`.
- Added end-to-end regressions for missing selected observations and history, a missing value inside a repeated series, and a sampling gap at the selected boundary. They verify no stuck-pattern bridge, reduced evidence completeness, E3/E4 unavailable behavior and an uncertain outcome.
- Current validation: `python -B -m unittest discover -s tests -v` — **74 passed**; compileall passed; `git diff --check` passed. Synthetic baseline response and coverage-only ablation outputs are descriptive and partial; outcome-level ablation and robustness analysis remain incomplete. No field accuracy or fault diagnosis claim is supported.

## Synthetic baseline and coverage ablation integration (2026-11-16)

- `python scripts/analyze_synthetic_baseline_comparison.py`: completed at code revision `c3c5b014e2fd26ee4ceb182363486438d9e1b588`; 160 context × scenario × synthetic-label timestamp units; 1,440 model/E4 response detail rows; 72 response summary rows; 144 E2 setting/scenario rows; coverage-only ablation detail and summary written with dataset hashes and source-artifact hashes.
- At the 8/12 E1 threshold, response was 100% on point spike, point drop and dew-point inconsistency labels, 6.7% on persistent offset/noise, and 0% on missing blocks/drift/stuck. Existing direct-variable E4 broad screening flagged missing blocks only. E2 setting fractions and detailed caveats are in `SYNTHETIC_BASELINE_COMPARISON_REPORT.md`.
- Coverage-only ablation per setting: E1 160/160; E1+E2 145/160; E1+E4 160/160; E1+E2+E4 145/160; E3 combinations 0/160. This is availability coverage, not an evidence-utility or event-outcome ablation.
- Experiment Lab renders the new tables behind dataset-hash checks. Final full run after these changes: `python -B -m unittest discover -s tests -v` — **69 passed, 0 failed** in 44.3 seconds; `python -m compileall -q app.py services ui src/weather_research tests scripts` and `git diff --check` passed.

## PR #2 audit remediation checkpoint — 2026-11-17

The prior baseline section above records the first-generation timestamp-level summaries. Corrected, reviewable outputs are now written separately under `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`; the historical files and campaign manifest remain unchanged. The corrected analysis reuses saved predictions, injection registries, E4 results and reviewed E2 outputs; it performs no estimator fitting, new synthetic campaign, or prediction regeneration.

The analysis separates configuration/timestamp observations, context × scenario responses, and across-context summaries. Across-context minimum and maximum values now range over five context responses, not individual timestamps. It verified 5 contexts, 8 scenarios and 160 context × scenario × timestamp units; the response detail has 3,360 rows and the across-context summary has 168 rows. For the existing 8/12 E1 threshold, the across-context mean/minimum/maximum responses are: dew-point inconsistency 1.000/1.000/1.000 (15 units); gradual drift 0/0/0 (30); intermittent noise 0.0667/0/0.1667 (30); missing block 0/0/0 (15); persistent offset 0.0667/0/0.1667 (30); point drop 1/1/1 (5); point spike 1/1/1 (5); stuck sensor 0/0/0 (30). These are synthetic-label response fractions, not event detection accuracy.

The review manifest records 29 input artifacts and all 6 outputs with hashes, sizes and applicable row/column metadata; the manifest’s own final SHA-256 is stored in a separate integrity sidecar. Reviewed E2 artifacts were verified before use (6,840 detail rows, 2,880 pairs, 813 summaries and 10 controls). Experiment Lab hides the reviewed outputs and displays an integrity warning if required manifests or files are missing or fail checks. The historical campaign manifest and first-generation baseline outputs are preserved.

Implementation revision: `1712e1289e961211538277cc2f8285ef9f1dbce8`. Final full-suite result and hosted Actions result are recorded in `TESTING_REPORT.md` and `NEXT_SESSION.md` after completion of the push verification.

## PR #2 audit remediation — validation result (2026-11-17)

- `python -B -m unittest discover -s tests -v`: **84 passed, 0 failed** in 125.448 seconds. This includes the Streamlit AppTest across all six workspaces and 10 new baseline/path/integrity regressions.
- `python -m compileall -q app.py services ui src/weather_research tests scripts`: passed.
- `git diff --check`: passed.
- Saved-data baseline review completed without model fitting or campaign/prediction regeneration. The versioned review manifest verifies 29 input artifacts and 6 CSV outputs; the manifest SHA-256 is in `synthetic_baseline_comparison_manifest.integrity.json`. The reviewed E2 set and Phase 01 sources passed their integrity checks.
- New Actions workflow run for the pushed final commit is pending verification; see `NEXT_SESSION.md` once observed.
