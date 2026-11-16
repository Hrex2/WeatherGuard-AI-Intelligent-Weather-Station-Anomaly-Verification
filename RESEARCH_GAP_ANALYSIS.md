# Research Gap Analysis — 2026-11-16

| Area | Evidence in repository | Classification | Remaining gap |
|---|---|---|---|
| Baseline data | Passed Phase 01 manifest; loader verifies hashes, counts and column order | Already completed and validated (artifact integrity) | Independent reconstruction from raw acquisition not possible with bundled files |
| Model grid | 12 configurations and 100,980 saved labels; E1 family and threshold tables generated | Completed but needs interpretation | Assess sensitivity; no truth labels for accuracy/calibration |
| Prediction parity | Targeted reproduction: 42 differences, all Isolation Forest; LOF and SVM match | Completed but needs causal explanation | Historical estimator/scaler objects and full fit environment are absent |
| E2 | Segment-aware real-time/retrospective screen; six-variable, 22,140-row E1-selected sensitivity; missing/irregular-value run boundaries corrected | Implementation and descriptive sensitivity complete; thresholds not validated | Evaluate on independent injected faults and matched unmodified contexts; E2 temporal departure is not regional-event support or fault diagnosis |
| E3 | Derived spatial summaries and provenance scaffold; no bundled raw neighbor time series or verified coordinates | Blocked by unavailable data | Traceable observations, source metadata, units, time coverage and valid coordinates |
| E4 | Broad physical screening helper and selected-reading integration; synthetic matrix compares clean/faulted screens | Implemented; synthetic screening behavior exercised | Single synthetic context; operational limits and real station calibration remain unvalidated; screening is not diagnosis |
| Synthetic faults | Reproducible temperature point-spike campaign plus one eight-scenario matrix using the existing injectors | Initial synthetic experiments executed and documented | One context per scenario; repeat across intervals, formalize uncertainty and do not treat as real-world validation |
| Integrated evidence | E1/E2/E3/E4 are represented separately; selected-reading interpretation abstains | Partially implemented | Evidence thresholds and three-outcome rules cannot be validated without truth/coverage |
| Baselines / ablation / robustness | Helpers exist for matched episodes and synthetic controls; no complete study | Not implemented as final studies | Prespecified evaluation units and defensible available-data comparisons |
| Application | Six workspaces, selected-variable E2, saved eight-scenario matrix shown in Experiment Lab, isolated CSV run | Implemented and AppTest-verified | Add multi-context result comparison after campaign; preserve synthetic/historical separation |
| Manuscript | Literature summaries, methods and status documents | Not implemented as full manuscript | Chapter draft tied to verified outputs, references and disclosed limitations |

## Decision

Continue with independent E2 validation, repeated synthetic contexts, E1 interpretation and robustness work. E3 remains explicitly unavailable until source observations and provenance are supplied. Do not call the research complete based on application readiness.

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

Phase 1 audit validation: 66 tests passed, compilation and Phase 03 integrity checks passed. CI was added because no suitable workflow existed.
