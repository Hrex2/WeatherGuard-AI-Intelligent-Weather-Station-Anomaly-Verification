# Next Session Handoff — 2026-11-16

## Repository checkpoint

- Latest `main`: `0a27959` (merge commit for PR #1; includes the earlier research branch through `69a5fe5`).
- Active branch: `codex/research-validation-v2`, created from refreshed `origin/main` at `0a27959`.
- Continuation branch `codex/research-validation-v2`; latest pushed commit before current UI integration: `f1b08d1`. Commits `4276aec`, `68df516`, `6486c1e`, `c55b90a`, and `f1b08d1` are pushed to origin. The E2 output files and current UI/docs updates are local and pending commit/push.
- Existing development branch `codex/autonomous-research-loop` is preserved; PR #1 is closed and merged.

## Verified work reused

- Phase 01 data hashes and row/column contracts remain unchanged.
- Historical Phase 03 prediction grid remains unchanged (100,980 labels; 8,415 timestamps × 12 configurations); current local refit mismatch remains 42 Isolation Forest labels and unexplained without saved estimators/scaler provenance.
- E1 threshold counts remain 432/214/123/51/15 for 4/6/8/10/12 of 12.
- The earlier eight-scenario matrix and 22,140-row E2 variable sensitivity were reused, not rerun.
- No raw verified neighbor time series or verified station coordinates are available; E3 remains unavailable.

## Completed in this continuation

- Corrected E2 stuck-run counting so missing values, irregular intervals, large gaps and explicit `segment_id` changes break continuity. Real-time cadence uses timestamps through the selected reading; retrospective mode may use the declared look-ahead.
- Corrected stuck-fault injection to use a same-segment contiguous reference; after a boundary, it falls back to the first finite value inside the injection interval and records the source.
- Changed uploaded CSV validation to require every adjacent timestamp interval to be exactly one elapsed hour. It reports irregular intervals/implied missing hours and never interpolates. Successful validation records usable/excluded row counts.
- Added a Phase 03 integrity manifest for 11 saved CSV outputs, linked to Phase 01 hashes. Status explicitly states hash identity only; historical generation provenance is unknown.
- Corrected evidence completeness so `UNAVAILABLE` spatial evidence is not counted as available. Clarified that E2 temporal departures do not establish regional weather or diagnose a fault.
- Wired the selected variable through the shared evidence service and surfaced the saved eight-scenario matrix in Experiment Lab after hash checks.
- Added CI workflow `.github/workflows/research-quality.yml`.
- Regression suite: 66 passed; `compileall`, `git diff --check`, and Phase 03 manifest checks passed.
- Phase 1 commits `4276aec` and `68df516` were pushed to `origin/codex/research-validation-v2`.
- The new data-only context selector preflighted five contexts: 2025-04-09, 2025-05-27, 2025-09-04, 2025-11-30 and 2026-02-06. They cover calendar quarters 1–4, are at least 14 days apart, and passed all eight scenario validations. No model fit has run for this campaign.
- Added shared-fit campaign orchestration, exact context manifests, expected feature-propagation change counts and detection-delay summaries in commits `6486c1e` and `c55b90a`, both pushed to origin. Validation at runner preparation: 68 tests passed and compileall passed.
- Executed the five-context campaign `fault_matrix_multicontext_46ae5d119d`. Scenario response fractions varied strongly by scenario/context; no changed predictions were outside expected feature-propagation windows; E4 screening changed on 36 injected timestamp-variable rows. See `MULTICONTEXT_FAULT_MATRIX_REPORT.md`. Full suite after E2 matched-control preparation: 69 passed.
- Committed and pushed the five-context outputs, report and E2 evaluator at `f1b08d1`.
- Ran E2 once: 6,840 screen evaluations, 10 matched controls and 2,880 paired injection/same-time comparisons. Status changed in 1,008/2,880 comparisons, including 270 missing blocks becoming `UNAVAILABLE`. Faulted series were `SUPPORTING` in 961/2,610 available comparisons; same-time unmodified series were `SUPPORTING` in 691/2,880. Matched controls were `SUPPORTING` in 272/1,080 rows. Controls are unadjudicated; these are not accuracy estimates.
- Integrated the five-context and E2 summaries into Experiment Lab with dataset-hash checks. AppTest assertion and full-suite rerun are pending.

## Exact next actions

1. Run the full suite, compile checks and diff checks after UI integration; update docs with actual results.
2. Commit and push E2 outputs, UI integration and synchronized research records.
3. Continue baseline, available-evidence ablation and robustness analyses. E3 waits on traceable neighboring-station data; real E2 validity waits on adjudicated labels.

## Remaining research limits

No real-observation fault labels; no verified neighboring-station series/coordinates; no persisted historical estimators; no causal resolution of the 42-label refit mismatch. E2 cutoffs remain exploratory. Synthetic label metrics do not establish field accuracy. Ablation, baseline comparison, robustness and full manuscript/reference verification are incomplete.
