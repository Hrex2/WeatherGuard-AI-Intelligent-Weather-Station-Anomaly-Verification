# Project Status — Second-Pass Review

**Software refactor:** implemented and regression-tested on synthetic fixtures. **Research validation:** real Pipeline B / Colab data are absent; Phase 01 remains **NOT VERIFIED**. The full Phase 02 provenance audit is **NOT IMPLEMENTED in this delivered package**.

## Section status

| Section | Status | Notes |
|---|---|---|
| 00 Research overview | Implemented | Scope and uncertainty outcomes documented. |
| 01 Environment/configuration | Implemented; local and clean-process path tested | Colab procedure documented; no actual Colab session. |
| 02 Data acquisition/provenance | Partial | Retrieval helper exists; Phase 02 station inventory/readback/candidate coverage audit is absent. |
| 03 Raw validation | Implemented; synthetic tests pass | Real Pipeline B pending. |
| 04 EDA | Partial | Descriptive and missingness tables only; plots not implemented. |
| 05 Feature engineering | Implemented; synthetic tests pass | Strict one-hour change differs from historical previous-row predictions; real parity pending. |
| 06 Split/preprocessing | Implemented; synthetic tests pass | Train-only medians/scaler; real split audit pending. |
| 07 Baseline models | Implemented API; limited synthetic model test | 12 research configurations not run on real data. |
| 08 Stability | Implemented; synthetic tests pass | Missing or unequal configuration timestamps now raise; no real predictions available. |
| 09 Temporal events | Implemented; synthetic tests pass | Real anomaly candidates unavailable. |
| 10 Matched controls | Partial; synthetic tests pass | Matching/inference assumptions and block sensitivity are not scientifically validated. |
| 11 Synthetic faults | Partial; synthetic tests pass | Full independent-reference campaign, event metrics and detection delay analysis absent. |
| 12 Spatial corroboration | Partial; synthetic tests pass | Exact-time availability/tolerance helpers; no Phase 02 audit or station-pair research results. |
| 13 Physical quality | Partial; synthetic tests pass | Broad screening flags include missingness, nonnumeric, infinite, bounds and cross-variable inconsistency; these are not fault labels. Sensor behavior suite incomplete. |
| 14 Integrated evidence | Partial; synthetic tests pass | Abstains on incomplete evidence; thresholds/domain rules are not calibrated. |
| 15 Robustness/ablation | **Not implemented** | Placeholder only; no ablation runner or results. |
| 16 Reporting/export | Partial | Status display only; figures and result export pipeline absent. |

## Verification

- Source/archive byte identity preserved; source hash recorded in `REFACTORING_REPORT.md`.
- Master notebook default path: 16 code cells sequentially executed without real data/retrieval/model training.
- Isolated package import from a non-project working directory: passed with `WEATHER_RESEARCH_ROOT`. This checks local package discovery, not an actual hosted Colab session.
- Test suite: **31 passed, 0 failed**.
- Phase 00/01 real-data retrieval/audit: not run. Phase 01: **NOT VERIFIED**.
- Phase 02 full provenance coverage audit: **NOT IMPLEMENTED in this package**. Historical registry/log references are external historical artifacts and are explicitly annotated.
- Phases 03–13 empirical research: not executed.

## Codex continuation update — 2026-11-16

- Phase 01: stored manifest and four hashes verified locally; independent raw-data reconstruction remains unverified.
- Phase 02: not complete; actual neighbor/raw time series and provenance metadata are not bundled.
- Phase 03: stored outputs structurally verified; local model reproduction differs in 42/100,980 cells.
- Synthetic validation: controlled temperature dose campaign executed locally; other fault groups remain pending.
- E1–E4 integration: partial rule-based outcome logic only; end-to-end evidence assembly remains pending.
- Ablation: not started.
- Final reporting: audit, handoff, changelog and next steps created; full report remains pending.


Phase 02 provenance inventory template/report created from supplied history only; no raw neighbor inputs are present, therefore status remains IN PROGRESS, not verified.

## WeatherGuard AI implementation update — 2026-11-16

- **Application:** Five-workspace Streamlit app implemented in `app.py`, backed by read-only loaders and the existing research package. Command Center and four other workspaces use actual saved artifacts.
- **Dataset:** Phase 01 manifest and hashes verified in the previous checkpoint audit. Dataset served is a processed snapshot, not raw acquisition.
- **Model inference:** Saved predictions are labeled historical. An explicit user control can refit the 12-config protocol. Existing local parity discrepancy remains: 42/100,980 labels.
- **Investigation:** Shared timestamp selection, saved model table, candidate episode lookup, derived spatial comparisons, and physical screening are connected. Overall outcome conservatively abstains pending validated integration.
- **Research Studio:** Five supplied literature candidates have source-linked metadata and scoped summaries. Full systematic/full-text review is incomplete.
- **Experiment Lab:** Controlled temperature spike campaign is runnable from an explicit form and stores unique run outputs. Remaining variable and temporal fault campaign controls are pending.
- **Evaluation:** Configuration counts and stability are shown; synthetic metrics are segregated; ablation is explicitly not evaluated.
- **Phase 02:** Manifest scaffold only; raw station files/metadata absent.
- **Testing:** Added artifact contract and AppTest workspace navigation tests; final suite result is recorded in `TESTING_REPORT.md`.
- **Screenshots:** No browser screenshot was captured in this stage; AppTest was used for actual Streamlit script/workspace smoke validation.

### Final application test result

The expanded suite is 35 passed, 0 failed. `AppTest` navigates all five workspaces without errors. A real localhost health request and browser screenshot were not obtained because the sandbox denied localhost socket access; this is an environment validation limit, not a reported successful HTTP launch. See `TESTING_REPORT.md`.

## Current repository checkpoint — 2026-11-17

PR #2 has merged. The remote main commit `852bc34e76ef4e5de15e48f0f1402f7bf0e9c1d1` contains the completed path-portability, integrity, context-level aggregation, regression-test and documentation remediation. Phase 0 passed 84 tests; after Phase 1A tests were added, the full application/repository suite is **98 passed, 0 failed, 0 skipped**. Compileall and patch whitespace pass; the PR-head hosted Actions run for merged code passed. Phase 01/03 identities and the PR #2 campaign/E2/baseline result sets were verified without regenerating them. The older notebook-package status above describes that notebook deliverable's own validation and must not be used as the current application test count.

The next research dependency is source evidence: raw VILD0 and neighboring-station observations with retrieval metadata, plus independently adjudicated event/fault/normal references. Until those are supplied and verified, E3, real-world metrics and outcome-level ablation remain unavailable.

## Phase 1A station preflight — 2026-11-17

Phase 1A status: **PARTIALLY_COMPLETE_EXTERNAL_DATA_ACCESS_REQUIRED**. The repository contains VILD0 plus four neighbor candidates: 42099, 42101, 42105 and 42096. Public Meteostat pages report station metadata and station-level hourly inventory periods for the first four; 42096 shows daily historical inventory only. Provider inventory is not proof of populated per-parameter rows or direct observation provenance. All seven parameter-level availability statuses remain `NOT_CHECKED`. Candidate suitability, distances, sources, and manual-access requirements are documented in `research_results/phase1a_station_preflight/PHASE1A_STATION_PREFLIGHT_REPORT.md`.

No raw observation files were downloaded. No historical prediction, Phase 01/03 snapshot, spatial comparison, or synthetic result was modified. The Meteostat package is not installed, its parameter inventory API was not called, and IMD Data Service Portal request/access terms remain unverified. E3 is not validated. Phase 1B must wait for source-verified station metadata and controlled, approved raw observation retrieval.

## Phase 1B station identity and acquisition readiness — 2026-11-17

The Phase 1A statements above are retained as a dated checkpoint. Phase 1B queried Meteostat 2.2.3 provider/parameter inventory metadata in a temporary isolated environment (179 records across five stations); project dependencies were not changed. This establishes inventory metadata only, not populated observation rows. VILD0 and 42099 remain IDENTITY_UNRESOLVED. VILD0/42105 METAR inventories share five fields and overlap the original processed period, but row source flags, exact timestamps and neighbor suitability remain unchecked. IMD registration, document, request and possible-charge steps are now documented; station-specific hourly availability remains NOT_CHECKED.

Phase 1B status: PARTIALLY_COMPLETE_EXTERNAL_ACCESS_REQUIRED. No raw observations were retrieved; E3 is not validated; Phase 2 independent event/fault references remain outstanding. A bounded Meteostat METAR proposal for VILD0 + 42105, five variables, hourly, 2021-01-05 through 2026-03-09 awaits explicit user approval. Details are in research_results/phase1b_station_identity/PHASE1B_READINESS_REPORT.md.

## Phase 1C controlled METAR pilot — 2026-11-17

Phase 0 is complete locally; Phase 1A and Phase 1B remain partially complete. Phase 1C's exact two-station, five-variable hourly retrieval workflow is prepared with a dry-run default and an explicit execution gate. Actual observation retrieval was not executed and approval remains pending. The pinned Meteostat 2.2.3 METAR adapter's runtime registry starts on 2026-11-16 and its Aviation Weather Center endpoint is limited to `hours=24`; its provider filter excludes the requested 2025-09-01 through 2025-09-30 interval before any observation request. Therefore Phase 1C readiness is `PILOT_WORKFLOW_BLOCKED_PROVIDER_INTERFACE_UNVERIFIED` for this historical window. RHUM is computed by Meteostat from temperature and dew point. E3 is not scientifically validated, and Phase 2 independent event/fault references remain outstanding. See `research_results/phase1c_metar_pilot/` and `PHASE1C_PILOT_READINESS_REPORT.md`. No push or PR was made.

## Phase 04 provenance-aware collection — 2026-11-18

- Added an isolated Meteostat 2.2.3 retrieval path that retains source-provider IDs, excludes model/analysis/forecast grades, disables filling/cleaning, and records UTC boundaries and SHA-256 hashes. No project dependency was added and no existing model was retrained.
- Official IMD/WIS2 and IMD climatological records support retrieval for WMO 42099 (Ludhiana) and 42101 (Patiala). Meteostat returned 567 `isd_lite` source rows for 42099 and 1,719 rows for 42101 (1,187 `isd_lite`, 532 `ghcnh`). These are Meteostat-returned, source-stratified exports, not original provider payloads; independent sensor lineage remains unverified.
- VILD0, 42105, and 42096 were not retrieved because their exact physical station/site crosswalks remain unverified. No primary-relative distance bands were assigned; E3 is **BLOCKED_BY_METADATA** and not validated.
- Exact timestamp overlap between 42099 and 42101 is 562 timestamps (563 within 60 minutes). Descriptive same-source exact pairs: temperature 560 (bias −0.444 °C, RMSE 1.927 °C); relative humidity 560 (bias +5.211 percentage points, RMSE 10.657); wind speed 561 (bias −1.112 km/h, RMSE 4.433); pressure 562 (bias +1.003 hPa, RMSE 1.177). Dew point and precipitation have no valid pairs. These are neighbor-to-neighbor summaries, not primary-station corroboration.
- Phase 04 and E3 targeted tests: **12 passed**. Full repository suite: **152 passed, 5 subtests passed, 0 failures**. The earlier no-`PYTHONPATH` invocation failed only at import collection; rerunning with `PYTHONPATH=src` succeeded.
- Detailed manifest, raw exports, coverage, candidate-time availability, pairwise results, missingness, interval gaps, station verification and readiness are under `outputs/phase04_provenance_aware_collection/`. Previous derived outputs were preserved in `_superseded_derived/` before regeneration. No push or merge was performed.

## Phase 05 primary station identity verification — 2026-11-18

- **Crosswalk:** `VILD0` is verified at station-record/airport-meteorological-service level as the Meteostat record associated with ICAO `VILD` (Ludhiana Airport). Meteostat metadata links the record to NOAA GHCNh `INI0000VILD`; NOAA's official station-list entry exactly matches the Meteostat coordinates (30.8547, 75.9526) and gives elevation 254.2 m. AAI eAIP identifies VILD as Ludhiana Airport and documents its METAR service.
- **Scope limits:** the NOAA/Meteostat point is a station-record reference coordinate, not a verified sensor coordinate. AAI lists DIWE at the ATC tower but does not document the full variable sensor suite, instrument positions, exposure, calibration or moves. VILD0 is not crosswalked to WMO 42099; keep the station records separate.
- **Historical data provenance:** archived Meteostat 1.7.6 notebook retrieval code omits `model` and `flags`; the library defaults are `model=True`, `flags=False`. Those saved VILD0 rows may include model fills and lack row-level source distinctions, so they are not verified direct-only observations.
- **E3:** readiness is `PARTIALLY_READY`. A geographically identified airport station record is available for future reference, but no source-level VILD0 observations or complete instrument/source lineage are available. No Phase 04 outputs or station zones were changed; E3 remains unvalidated.
- **Protocol:** variable-specific prospective comparison metrics, exact/tolerance timestamp rules, minimum descriptive counts, missing-data handling and specification-based tolerance policy are in `outputs/phase05_primary_station_verification/variable_comparison_protocol.md`.
- **Validation:** relevant station/spatial regression tests **43 passed**; full repository suite **152 passed, 5 subtests passed, 0 failures**. Phase 05 output schema checks and report-builder compile check passed.
- Full Phase 05 source log, crosswalk evidence, timeline and readiness are in `outputs/phase05_primary_station_verification/`. No push or merge was performed.

## Phase 06 controlled E3 spatial validation — 2026-11-18

- Created `feature/phase06-controlled-e3-validation` from the Phase 05 checkpoint (`7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`). A bounded Meteostat 2.2.3 VILD0 hourly retrieval succeeded for 2025-03-28 through 2026-03-09 UTC with model inclusion disabled, filling/cleaning disabled, and provider source IDs retained. It yielded 1,390 source rows (1,021 unique times: 1,002 `metar`, 388 `ghcnh`); SHA-256 `e51795c202efbe287e61aa700d7c310cc4cf159e806cd3e60ee522113f58307e`. These are package-returned source-level rows, not original provider payloads or proof of independent sensors.
- Descriptive neighbor records: WMO 42099 in provisional zone A (~2.27 km) and WMO 42101 in provisional zone C (~76.04 km). Zones B, D and E are unrepresented. Exact sensor locations and independent sensor/feed lineage are unverified; no pair passes the strict lineage gate.
- Exact timestamp valid-pair counts by source pair: VILD0 `metar` vs 42099 `isd_lite`: temperature 65, RH 65, wind speed 65, pressure 65; VILD0 `metar` vs 42101 `isd_lite`: 67 for each of those four; VILD0 `metar` vs 42101 `ghcnh`: temperature/RH/wind speed 3 each and pressure 113; VILD0 `ghcnh` vs 42101 `ghcnh`: temperature/RH/wind speed 117 each. Dewpoint, wind direction and precipitation have no valid exact pairs. Metrics remain descriptive; wind speed is converted to m/s. No measurement tolerances or significance claims are asserted.
- Experiments 1–4 report source-stratified exact, 15/30/60-minute one-to-one matching, represented-zone coverage and variable-specific comparisons. Experiment 5 is simulated random missingness masking. Experiment 6 excludes all pairs under a strict independent-lineage gate. Experiment 7 uses synthetic logic controls only. These do not establish real-world E3 validation or event ground truth; E3 remains `BLOCKED_BY_DATA_PROVENANCE` and isolated from the classifier.
- Phase 00 exports remain provenance-uncertain despite matching timestamp/value fingerprints. Historical notebook retrievals retain their Meteostat 1.7.6 default-model uncertainty. Earlier Phase 06 derived files were preserved under `outputs/phase06_controlled_e3_validation/_superseded_derived/iteration1/` before correcting and regenerating reports. Raw retrieval data and manifest were left in place.
- Phase 06 reports and tables are under `outputs/phase06_controlled_e3_validation/`. Focused Phase 04/E3 tests: **16 passed**; full repository suite: **156 passed, 5 subtests passed, 0 failed**. Compileall and `git diff --check` passed. No push or merge was performed.

## Phase 07 independent lineage and external reference validation — 2026-11-18

- Created `feature/phase07-independent-evidence` from base commit `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`; inherited dirty files were preserved. No push, merge, or commit was made.
- Retrieved and preserved official NOAA NCEI GHCNh station-year PSV files and metadata in `outputs/phase07_independent_evidence/external_reference_data/`. Native row fields resolve Ludhiana ICAO-VILD FM15 METAR and Patiala WMO-42101 FM12 SYNOP report records; they do not identify instrument serials or establish operator independence.
- VILD0 Meteostat METAR and NOAA GHCNh are potentially shared-source products: 981 exact timestamp overlaps; among valid pairs, temperature matched 613/613 and pressure/altimeter 981/981 within 0.11 in their normalized values. Patiala Meteostat GHCNh is an exact mirror/repackaging of the NOAA GHCNh rows (532 exact timestamps; all available temperature, wind, pressure, and RH values matched after unit handling). Patiala ISD-Lite and GHCNh have strong same-station fingerprints and are not independent votes.
- WMO 42101 is a distinct station/report record 76.04 km from VILD0, with separate source identifiers and FM12 versus FM15 report types. This supports **limited report-level** comparison, not proof of separate operators, instruments, calibration, or full organizational independence. WMO 42099 remains `UNKNOWN_LINEAGE`; no authoritative alias to VILD0 or NOAA GHCNh station match was found.
- Eight candidate events were selected mechanically from the Phase 03 8-of-12 table before inspecting neighbor agreement. Three have a QC-good Patiala native comparison within 60 minutes (two temperature rows and one wind-speed row). This is descriptive reference availability only: no tolerance-based support/conflict judgment or event ground truth was registered; historical candidate row lineage is unresolved. Candidate E1/E2/E4 event labels remain unavailable in the selected artifact. No precipitation candidate was selected.
- Decision: `LIMITED_INDEPENDENT_EVIDENCE` for narrowly scoped report-level investigation; E3 remains unvalidated and must stay isolated from the final classifier. No IMD original archive, separate historical AWC/NCEI order, or ERA5 contextual series was obtained. Pressure comparisons remain excluded because candidate `pres`, VILD altimeter, and Patiala sea-level pressure are not demonstrated to be the same quantity.
- Phase 07 code, tests, reports, comparison tables, lineage graph, decision JSON, source manifest and downloaded references are under `src/weather_research/phase07_lineage.py`, `tests/test_phase07_lineage.py`, `scripts/`, and `outputs/phase07_independent_evidence/`. An initial generated attempt was preserved under `_superseded_derived/attempt1/` before correcting the QC normalization and rebuilding; prior Phase 00–06/raw outputs were not changed.
- Validation: Phase 07 focused tests **8 passed**; full repository suite **164 passed, 5 subtests passed, 0 failed**. Phase 07 compile checks and `git diff --check` passed. No model was retrained and E1/E2/E4 implementation/results were not modified.

## Phase 08 E3 evidence policy and validation framework — 2026-11-18

- Created `feature/phase08-e3-evidence-policy` from the verified Phase 07 base commit `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`. All inherited dirty and untracked files were preserved; no reset, clean, stash, or overwrite of earlier phase outputs was performed.
- Added the isolated research policy module `src/weather_research/e3_evidence_policy.py`. It defines six lineage classes, eligibility rules for lineage/duplicates, station/site identity, coordinates, exact/15/30/60-minute UTC alignment, variable/unit compatibility, QC, missingness and imputation; separate variable outcomes; and readiness-gate evaluation. It uses no default numerical tolerance, confidence score, or evidence weight. Precipitation mismatch defaults to `NOT_COMPARABLE` unless a matching accumulation interval and preregistered protocol are supplied.
- Added 16 synthetic policy scenarios and focused regression tests. These test the software rules only; they are not empirical weather validation. Existing `classify_evidence()` behavior and E1/E2/E4 code/results were not modified, and E3 remains outside the classifier.
- Readiness gates: provenance **PARTIAL**; geography **PARTIAL**; temporal validity **PARTIAL**; measurement compatibility **PARTIAL**; event-level validation **FAIL**; reproducibility **PARTIAL**. Decision: **PARTIALLY_READY** for future controlled study design, not empirically ready or validated. Phase 07's `LIMITED_INDEPENDENT_EVIDENCE` conclusion is preserved.
- Remaining blockers include historical candidate-to-original-report lineage, WMO 42099 provenance, exact sensor coordinates/site histories, instrument/operator/calibration metadata, specification-based measurement tolerances, precipitation event windows, independently adjudicated event labels, and complete source-to-candidate reproduction.
- Phase 08 policy, rules tables, scenario matrix, readiness/decision JSON, flowchart, report and manifest are under `outputs/phase08_e3_evidence_policy/`. Focused Phase 08 tests: **20 passed**; focused E3/evidence regression selection: **61 passed**; full repository suite: **184 passed, 5 subtests passed, 0 failed**. Python compile checks and `git diff --check` passed.
- No commit, push, merge, model retraining, primary-station replacement, baseline pipeline change, classifier modification, or E3 classifier integration occurred.

## Phase 09 empirical E3 validation — 2026-11-18

- Created `feature/phase09-e3-empirical-validation` from base `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`; inherited dirty files and research artifacts were preserved. No commit, push, or merge was made.
- Used only preserved Phase 04–08 data. NOAA NCEI GHCNh station-year records were compared at report level: ICAO-VILD FM15 and WMO-42101 FM12, approximately 76.04 km apart by station-record reference coordinates (provisional zone C). The reports are distinct, but instrument, operator, calibration, and organizational independence are unverified. No data was downloaded in Phase 09.
- Deterministically selected 8 candidate events from the Phase 03 8-of-12 candidate table and reproduced the Phase 07 event signature. Zero events were suitable for empirical event validation because the candidate rows lack original report identifiers and may include Meteostat model-filled values; all 8 outcomes remain `UNAVAILABLE`. No anomaly/fault labels or fault probabilities were assigned.
- At exact UTC matching: temperature had 595 available pairs / 435 QC-good metadata-valid pairs (bias +0.044 °C; RMSE 1.508 °C); dewpoint 595 / 456 (bias +2.280 °C; RMSE 3.251 °C); wind speed 594 / 457 (bias −0.409 m/s; RMSE 1.038 m/s); wind direction 465 / 328 valid circular pairs. At 15/30/60 minutes, temperature pairs were 608/623/1,041, dewpoint 608/623/1,041, wind speed 607/622/1,040, and direction 477/490/752. These are descriptive report-level statistics, not event agreement tests; no scientific tolerance was preregistered.
- RH was excluded from independent comparison because it is derived from temperature/dewpoint and direct measurement QC was unavailable. Precipitation was non-comparable because VILD had no valid precipitation values and Patiala accumulation intervals did not match. VILD altimeter/QNH and Patiala sea-level pressure are different elements and were not compared. Potentially shared, duplicate, and unknown-lineage products were excluded from independent votes.
- Decision: `DESCRIPTIVE_ONLY`; Phase 08 remains `PARTIALLY_READY`. Phase 09 reports and hashed artifacts are under `outputs/phase09_e3_empirical_validation/`. Earlier generated attempts were retained under sibling `_superseded_attempt*` directories. The Phase 08 policy limitation around typed measurement semantics and absence of an outcome for valid descriptive pairs with no threshold is documented; Phase 08 code was not altered.
- Validation after implementation: Phase 09 focused tests **9 passed**; focused E3/evidence regression selection **53 passed**; full repository suite **193 passed, 5 subtests passed, 0 failed**. No baseline retraining, primary-station replacement, E1/E2/E4 change, classifier behavior change, or E3 classifier integration occurred.

## Phase 10 independent reference data — 2026-11-19

- Continued on `feature/phase10-independent-reference-data`, based on commit `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`. Existing dirty/untracked research outputs from prior phases were preserved; no commit, push, or merge was made.
- Added an isolated Phase 10 provenance/reference-data module, builder, and regression tests. The builder reuses NOAA NCEI GHCNh station-year inputs already downloaded and preserved in Phase 07; it performs no observation download and leaves all source files untouched. A sanitized public WMO OSCAR/Surface metadata response was captured for WMO 42099 Ludhiana and 42101 Patiala. The metadata identifies IMD as organization for both but provides no sensor deployment, calibration, or historical observation series.
- Constructed a long-format dataset with **173,811 element rows** from **7,557 station/timestamp records** (VILD 2,243; Patiala 5,314) and **7,557 locally derived report-payload fingerprints**. Raw timestamps, value strings, source/report/measurement/QC metadata, REM text, and source-line hashes are retained. Missing values are preserved; no filling, QC filtering, timestamp conversion, or unit conversion was applied.
- Reproduced the eight Phase 09 candidate events deterministically. **Zero** events are independently adjudicated; all eight remain `NOT_ADJUDICATED`. Phase 08 eligibility is applied unchanged: candidate-to-original-report links remain unavailable and shared product copies contribute zero independent votes. No fault inference or classifier integration was made.
- Phase 10 decision: **`INSUFFICIENT_INDEPENDENT_DATA`**. Provenance, geography, temporal coverage, measurement compatibility, and event coverage are partial; adjudication fails. Needed next: original IMD observations and request documentation, historical raw VILD METAR reports, report-to-candidate linkage, instrument/site histories, and independent event adjudication. IMD data requests and NOAA SRRS orders were not submitted.
- Phase 10 reports, registers, decision/sufficiency JSON, transformed dataset, WMO metadata snapshot, and reproducibility manifest are under `outputs/phase10_independent_reference_data/`. Repository `.gitignore` excludes `outputs/*`; output data remain local and are not included by Git unless separately staged by a future task.
- Validation: focused Phase 10 suite **9 passed**; full repository suite **202 passed, 5 subtests passed, 0 failed**; compile checks passed. A pytest-asyncio configuration deprecation warning remains. Prior Phase 00–09 outputs were not modified.

## Phase 11 original-observation acquisition and event adjudication — 2026-11-19

- Created `feature/phase11-original-observations-event-adjudication` from expected base `7baf75a8a9682e611fb8a4b1cd248a1a6144cc65`. Before switching, verified the expected Phase 10 branch and base. Preserved the inherited dirty worktree, untracked report/code artifacts, and ignored Phase 04–10 output directories. Earlier Phase 11 generated outputs were preserved under `outputs/phase11_original_observations_event_adjudication_superseded_attempt1/` and `outputs/phase11_original_observations_event_adjudication_superseded_attempt2/`. No reset, clean, stash, commit, push, or merge was performed.
- No original IMD station observation series were acquired. Official IMD Data Service Portal and Meteorological Centre Chandigarh procedures document historical data access, including hourly elements for selected stations, via registration/request, availability/cost review, undertaking, and possibly payment. No account, request, email, payment, or external message was submitted.
- Investigated AWC's public raw METAR API and NCEI SRRS/AIRS. AWC's documented 30-day window excludes Phase 03 candidate dates. NCEI offers archived text product orders (up to five days per order within a month), but VILD international bulletin/date availability is unverified; no order was submitted.
- Queried Iowa State IEM's public ASOS/METAR archive for a complete UTC calendar day on each of the eight unchanged Phase 10 candidate dates. Preserved eight exact CSV responses: **31 archived raw METAR rows across five dates**; the other three queried dates returned headers with no observations. IEM documents its archive as as-is, multi-source (including Unidata IDD, NOAA NCEI ISD, and MADIS), with very little QC. It returns no unique provider report ID. Thus these are newly retrieved archive copies of raw report text, not direct-provider source files or independent station votes. One initial broad-range request failed with an incomplete chunked response; it was not parsed as data and its failure metadata is recorded.
- Candidate linkage used exact VILD station, UTC timestamp, and consistency of the raw report's embedded DDHHMMZ time; no time tolerance or proximity match was used. Two event links are provisional archive-copy links (2025-12-02 temperature; 2025-12-22 report with RH only implied from equal temperature/dewpoint). Six have no exact match in queried dates. **Confirmed provider-ID links: 0.** All eight Phase 08 outcomes remain `INELIGIBLE / UNAVAILABLE` because lineage is unknown; shared or missing evidence adds zero votes.
- WMO OSCAR metadata reused from Phase 10 identifies WMO 42099 Ludhiana and WMO 42101 Patiala, with IMD listed for both, but does not resolve sensor coordinates/history, instruments, calibration, or operator epochs. VILD0 remains verified only at airport-station identity level; no authoritative VILD0–42099 alias was established. Instrument lineage remains unknown. All eight events are `NOT_ADJUDICATED`; no truth labels or fault probabilities were assigned.
- Phase 11 decision: **`INSUFFICIENT_INDEPENDENT_DATA`**. Primary blocker is source lineage/access; event adjudication and instrument/site history are additional blockers. Phase 08 policy was reused unchanged. The model/baseline, 11 features, primary station, E1/E2/E4, and classifier behavior were not modified; E3 remains isolated.
- Phase 11 report, source access and observation manifests, parsed archive copy, station/instrument lineage, event/linkage/adjudication and policy audit registers, quality audit, blockers, decision, input manifest, raw response files, failed-attempt log, and `SHA256SUMS.txt` are under `outputs/phase11_original_observations_event_adjudication/`. The output directory is ignored by the existing `.gitignore`.
- Validation: Phase 11 focused tests **12 passed**; Phase 11 + Phase 08/09/10 evidence regression tests **50 passed**; full suite **214 passed, 5 subtests passed, 0 failed**. Compile checks, SHA-256 verification, artifact integrity checks, and `git diff --check` passed. Pytest emitted the existing pytest-asyncio fixture-loop-scope deprecation warning.
