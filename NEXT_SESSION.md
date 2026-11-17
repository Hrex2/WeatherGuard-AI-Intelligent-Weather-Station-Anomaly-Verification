# Next Session Handoff — 2026-11-16

## Repository checkpoint

- Latest `main`: `0a27959` (merge commit for PR #1; includes the earlier research branch through `69a5fe5`).
- Active branch: `codex/research-validation-v2`, created from refreshed `origin/main` at `0a27959`.
- Continuation branch `codex/research-validation-v2`; latest confirmed remote commit `e5ad7d2`. Commits `4276aec`, `68df516`, `6486c1e`, `c55b90a`, `f1b08d1`, and `e5ad7d2` are pushed. Draft PR #2 is open to `main`, unmerged. Local commits `8d4deaf` (baseline comparison) and `c3c5b01` (coverage ablation) plus generated output/UI/docs changes are not yet pushed.
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
- Committed and pushed the E2 results and hash-gated Experiment Lab view at `e5ad7d2`.
- Ran E2 once: 6,840 screen evaluations, 10 matched controls and 2,880 paired injection/same-time comparisons. Status changed in 1,008/2,880 comparisons, including 270 missing blocks becoming `UNAVAILABLE`. Faulted series were `SUPPORTING` in 961/2,610 available comparisons; same-time unmodified series were `SUPPORTING` in 691/2,880. Matched controls were `SUPPORTING` in 272/1,080 rows. Controls are unadjudicated; these are not accuracy estimates.
- Added synthetic baseline response and E1/E2/E4 setting comparisons for 160 context × scenario × labelled-timestamp units. At 8/12, point spike/drop/dew-point labels were all flagged; offset/noise were 0.067; missing/drift/stuck 0. E4 direct-variable broad rules flagged missing blocks only. No real accuracy estimates.
- Added coverage-only ablation: E1 160/160; E1+E2 145/160 per setting; E1+E4 160/160; E1+E2+E4 145/160; E3 combinations blocked at 0/160. This is evidence availability, not an outcome utility study.
- Experiment Lab now shows multi-context, E2 pair/status, baseline, setting sensitivity and coverage tables after dataset hash checks. Full suite passes 69/69; compileall and `git diff --check` pass. AppTest navigates all six workspaces and checks the new view content.

## Exact next actions

1. Commit and push the baseline/coverage outputs, final Experiment Lab update and synchronized docs; verify the remote head and update the draft PR description.
2. Continue robustness sensitivity and E4 rule review; keep sensitivity statements tied to these synthetic contexts and existing broad rules.
3. Continue manuscript/reference verification. E3 waits on traceable neighboring-station data; real E2 validation and outcome-level ablation wait on adjudicated labels.

## Remaining research limits

No real-observation fault labels; no verified neighboring-station series/coordinates; no persisted historical estimators; no causal resolution of the 42-label refit mismatch. E2 cutoffs remain exploratory. Synthetic baseline results and availability-only ablation do not establish field accuracy or evidence utility. Robustness beyond the current E1/E2 synthetic settings, E4 operational limits and full manuscript/reference verification remain incomplete.

## PR #2 audit remediation checkpoint — 2026-11-17

The prior baseline section above records the first-generation timestamp-level summaries. Corrected, reviewable outputs are now written separately under `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`; the historical files and campaign manifest remain unchanged. The corrected analysis reuses saved predictions, injection registries, E4 results and reviewed E2 outputs; it performs no estimator fitting, new synthetic campaign, or prediction regeneration.

The analysis separates configuration/timestamp observations, context × scenario responses, and across-context summaries. Across-context minimum and maximum values now range over five context responses, not individual timestamps. It verified 5 contexts, 8 scenarios and 160 context × scenario × timestamp units; the response detail has 3,360 rows and the across-context summary has 168 rows. For the existing 8/12 E1 threshold, the across-context mean/minimum/maximum responses are: dew-point inconsistency 1.000/1.000/1.000 (15 units); gradual drift 0/0/0 (30); intermittent noise 0.0667/0/0.1667 (30); missing block 0/0/0 (15); persistent offset 0.0667/0/0.1667 (30); point drop 1/1/1 (5); point spike 1/1/1 (5); stuck sensor 0/0/0 (30). These are synthetic-label response fractions, not event detection accuracy.

The review manifest records 29 input artifacts and all 6 outputs with hashes, sizes and applicable row/column metadata; the manifest’s own final SHA-256 is stored in a separate integrity sidecar. Reviewed E2 artifacts were verified before use (6,840 detail rows, 2,880 pairs, 813 summaries and 10 controls). Experiment Lab hides the reviewed outputs and displays an integrity warning if required manifests or files are missing or fail checks. The historical campaign manifest and first-generation baseline outputs are preserved.

Implementation revision: `1712e1289e961211538277cc2f8285ef9f1dbce8`. Final full-suite result and hosted Actions result are recorded in `TESTING_REPORT.md` and `NEXT_SESSION.md` after completion of the push verification.

## Current PR #2 handoff — 2026-11-17

- Branch: `codex/research-validation-v2`; base: `main` at `0a279597c3d6cc0eed6088150bfe59ec13e7c99d`.
- Implementation commit: `1712e1289e961211538277cc2f8285ef9f1dbce8`; documentation/artifact commit `db97633` is pushed to the PR branch.
- Full local validation: **84 tests passed**, compileall passed, and `git diff --check` passed. Baseline results are in `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`; 29 inputs and six outputs are hash/shape verified.
- No refit, new campaign, or prediction regeneration was performed. PR #2 remains draft and must receive human review; do not merge automatically.
- Hosted Actions was started for the pushed head; verify the latest run before treating CI as complete. Scientific blockers remain E3 station data/provenance, adjudicated real fault/clean labels, outcome-level ablation, broader robustness, the unexplained 42 Isolation Forest mismatches, and full reference verification.

- Documentation and saved review-artifact commit `db97633` is pushed to the existing draft PR branch. The final PR head and hosted Actions status are available in PR #2.
