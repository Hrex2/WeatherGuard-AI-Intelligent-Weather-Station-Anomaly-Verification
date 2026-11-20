# Research Gap Analysis — 2026-11-16

| Area | Evidence in repository | Classification | Remaining gap |
|---|---|---|---|
| Baseline data | Passed Phase 01 manifest; loader verifies hashes, counts and column order | Already completed and validated (artifact integrity) | Independent reconstruction from raw acquisition not possible with bundled files |
| Model grid | 12 configurations and 100,980 saved labels; E1 family and threshold tables generated | Completed but needs interpretation | Assess sensitivity; no truth labels for accuracy/calibration |
| Prediction parity | Targeted reproduction: 42 differences, all Isolation Forest; LOF and SVM match | Completed but needs causal explanation | Historical estimator/scaler objects and full fit environment are absent |
| E2 | Segment-aware screen; E1-selected sensitivity plus exploratory synthetic injection comparison across five contexts and 10 matched controls | 6,840 evaluations; 1,008/2,880 paired status changes, including 270 missing-value `UNAVAILABLE`; thresholds not validated | Controls are not adjudicated clean and temporal support is not fault diagnosis; obtain independent real labels |
| E3 | Derived spatial summaries and provenance scaffold; no bundled raw neighbor time series or verified coordinates | Blocked by unavailable data | Traceable observations, source metadata, units, time coverage and valid coordinates |
| E4 | Broad physical screening helper and selected-reading integration; synthetic matrix compares clean/faulted screens | Implemented; synthetic screening behavior exercised | Single synthetic context; operational limits and real station calibration remain unvalidated; screening is not diagnosis |
| Synthetic faults | Eight existing scenarios run at five preselected held-out contexts with one shared model fit; scenario/family/context summaries, exact injection registries and E4 screens saved | Multi-context synthetic experiment executed; descriptive response varies by scenario and context | Synthetic labels only; unmodified held-out rows are not verified clean truth; shared fit does not measure fit uncertainty or field accuracy |
| Integrated evidence | E1/E2/E3/E4 are represented separately; selected-reading interpretation abstains | Partially implemented | Evidence thresholds and three-outcome rules cannot be validated without truth/coverage |
| Baselines / ablation / robustness | Synthetic family/E1/E2/E4 response comparison and E1/E2/E4 setting sensitivity; availability-only ablation across 160 synthetic timestamp units | Partial descriptive synthetic evaluation; outcome-level ablation is not validated | Real labels and verified E3 needed for event-level utility comparisons; do not interpret availability coverage as benefit |
| Application | Six workspaces, selected-variable E2, saved single/multi-context matrices, E2 paired screens, synthetic baseline and coverage tables in Experiment Lab | Implemented; final full-suite rerun pending | Preserve synthetic/historical separation and confirm hash gates |
| Manuscript | Literature summaries, methods and status documents | Not implemented as full manuscript | Chapter draft tied to verified outputs, references and disclosed limitations |

## Decision

Continue with baselines, available-evidence ablation, robustness and E1 interpretation. E3 remains explicitly unavailable until source observations and provenance are supplied. Real-world E2 validation remains blocked by absent adjudicated fault/event labels; do not call the research complete based on application readiness.

## Validation & implementation audit

| Finding | Current status | Evidence / limitation |
|---|---|---|
| AUD-01 stuck run crossed missing observations | Fixed | E2 counts original ordered values and stops at missing values; regression test passes |
| AUD-02 irregular cadence, long gaps, cadence changes and timezone handling | Corrected for local screen | Local cadence is causal in real-time mode; long gaps and explicit segment changes split context; irregular intervals stop stuck runs; timezone-aware UTC test passes. |
| AUD-03 stuck injection referenced another segment | Fixed | Uses only a contiguous same-segment prior reading; if separated, uses the first finite injection value and records that source |
| AUD-04 UNAVAILABLE counted as complete spatial evidence | Fixed | Completeness requires a recognized spatial status and station counts; unavailable remains incomplete |
| AUD-05 median cadence accepted irregular uploads | Fixed | Upload workflow rejects any non-hourly adjacent interval and implied missing hours; no interpolation is performed |
| AUD-06 saved Phase 03 artifacts had no hash contract | Fixed | New manifest hashes 11 CSV outputs and records ordered columns/counts plus Phase 01 references; historical generation provenance remains unknown |
| AUD-07 Experiment Lab omitted eight-scenario matrix | Fixed | Saved matrix is shown with summaries, injection registry and provenance after data-hash match |
| AUD-08 shared E2 ignored selected variable | Fixed | Evidence service accepts the selected variable; UI and regression use dew point explicitly |
| AUD-09 E1-selected E2 sweep was misread as independent validation | Documented | Manuscript, JSON manifest and tracker identify the selection dependence |
| AUD-10 E3 lacks verified station series/provenance | Blocked by data | No verified neighboring station raw time series or coordinates were found; E3 stays unavailable |
| AUD-11 stale research records | Corrected in this milestone | Tracker, handoff, gap analysis, testing report, changelog and README are synchronized |

Phase 1 audit validation: 66 tests passed, compilation and Phase 03 integrity checks passed. CI was added because no suitable workflow existed. The five-context campaign and exploratory E2 injection/control analysis have run and are integrated into Experiment Lab; latest full-suite validation after UI updates is recorded in `TESTING_REPORT.md`.

## PR #2 audit remediation checkpoint — 2026-11-17

The prior baseline section above records the first-generation timestamp-level summaries. Corrected, reviewable outputs are now written separately under `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`; the historical files and campaign manifest remain unchanged. The corrected analysis reuses saved predictions, injection registries, E4 results and reviewed E2 outputs; it performs no estimator fitting, new synthetic campaign, or prediction regeneration.

The analysis separates configuration/timestamp observations, context × scenario responses, and across-context summaries. Across-context minimum and maximum values now range over five context responses, not individual timestamps. It verified 5 contexts, 8 scenarios and 160 context × scenario × timestamp units; the response detail has 3,360 rows and the across-context summary has 168 rows. For the existing 8/12 E1 threshold, the across-context mean/minimum/maximum responses are: dew-point inconsistency 1.000/1.000/1.000 (15 units); gradual drift 0/0/0 (30); intermittent noise 0.0667/0/0.1667 (30); missing block 0/0/0 (15); persistent offset 0.0667/0/0.1667 (30); point drop 1/1/1 (5); point spike 1/1/1 (5); stuck sensor 0/0/0 (30). These are synthetic-label response fractions, not event detection accuracy.

The review manifest records 29 input artifacts and all 6 outputs with hashes, sizes and applicable row/column metadata; the manifest’s own final SHA-256 is stored in a separate integrity sidecar. Reviewed E2 artifacts were verified before use (6,840 detail rows, 2,880 pairs, 813 summaries and 10 controls). Experiment Lab hides the reviewed outputs and displays an integrity warning if required manifests or files are missing or fail checks. The historical campaign manifest and first-generation baseline outputs are preserved.

Implementation revision: `1712e1289e961211538277cc2f8285ef9f1dbce8`. Final full-suite result and hosted Actions result are recorded in `TESTING_REPORT.md` and `NEXT_SESSION.md` after completion of the push verification.

## Phase 1A station preflight — 2026-11-17

Phase 1A status: **PARTIALLY_COMPLETE_EXTERNAL_DATA_ACCESS_REQUIRED**. The repository contains VILD0 plus four neighbor candidates: 42099, 42101, 42105 and 42096. Public Meteostat pages report station metadata and station-level hourly inventory periods for the first four; 42096 shows daily historical inventory only. Provider inventory is not proof of populated per-parameter rows or direct observation provenance. All seven parameter-level availability statuses remain `NOT_CHECKED`. Candidate suitability, distances, sources, and manual-access requirements are documented in `research_results/phase1a_station_preflight/PHASE1A_STATION_PREFLIGHT_REPORT.md`.

No raw observation files were downloaded. No historical prediction, Phase 01/03 snapshot, spatial comparison, or synthetic result was modified. The Meteostat package is not installed, its parameter inventory API was not called, and IMD Data Service Portal request/access terms remain unverified. E3 is not validated. Phase 1B must wait for source-verified station metadata and controlled, approved raw observation retrieval.

## Phase 1B update — 2026-11-17

Phase 1B queried 179 parameter/provider inventory metadata records from Meteostat 2.2.3 in a temporary isolated environment. This establishes provider inventory bounds only; no weather rows were fetched. Five METAR variables have overlapping inventory bounds for VILD0 and 42105 across the original project period, although reported completeness is low/modest and exact shared observation timestamps/source flags remain unknown. VILD0 and 42099 physical identity remains unresolved; 42105 is only a conditional regional candidate. IMD registration/document/request steps are documented, but station-specific hourly coverage remains unchecked. Status is PARTIALLY_COMPLETE_EXTERNAL_ACCESS_REQUIRED; no raw download is approved or started, E3 is not validated, and Phase 2 independent references remain outstanding. See research_results/phase1b_station_identity/.

## Phase 1C controlled METAR pilot — 2026-11-17

Phase 0 is complete locally; Phase 1A and Phase 1B remain partially complete. Phase 1C's exact two-station, five-variable hourly retrieval workflow is prepared with a dry-run default and an explicit execution gate. Actual observation retrieval was not executed and approval remains pending. The pinned Meteostat 2.2.3 METAR adapter's runtime registry starts on 2026-11-16 and its Aviation Weather Center endpoint is limited to `hours=24`; its provider filter excludes the requested 2025-09-01 through 2025-09-30 interval before any observation request. Therefore Phase 1C readiness is `PILOT_WORKFLOW_BLOCKED_PROVIDER_INTERFACE_UNVERIFIED` for this historical window. RHUM is computed by Meteostat from temperature and dew point. E3 is not scientifically validated, and Phase 2 independent event/fault references remain outstanding. See `research_results/phase1c_metar_pilot/` and `PHASE1C_PILOT_READINESS_REPORT.md`. No push or PR was made.
