# WeatherGuard AI Final Academic Submission Audit

**Audit date:** 21 November 2026
**Repository branch:** `codex/ui-ux-redesign`
**Audited commit:** `aec543b755903b7fbdb1dc1ddefb1dc3ac68660d`

## 1. Executive summary

The repository contains a technically coherent research prototype, substantial historical and synthetic evidence, a working Streamlit application, and a current seven-page IEEE-style paper candidate. The numerical claims checked in the latest paper draft agree with the principal local manifests and results. The paper appropriately avoids real-world fault-performance metrics and repeatedly distinguishes unusual readings from confirmed sensor failures.

**The project is not ready for final academic submission yet.** The main blockers are unresolved author/affiliation confirmation, multiple competing paper files with inconsistent title and author metadata, and the absence of the actual presentation slides or Gamma export. The public GitHub README and the live Research workspace contain stale project-status text. The slide talk and viva therefore cannot be audited, and the repository currently exposed on GitHub does not reflect all local documentation.

No existing file was modified by this audit. This report is the only new repository file. Tests, compilation, app startup/health, local artifacts, and read-only GitHub inspection were used; no branch, staging, commit, push, reset, cleanup, or data retrieval was performed.

## 2. Audit scope and source inventory

### Research papers and report material

- Latest-by-file-date candidate: `research_results/phase15_ieee_paper_v4/WeatherGuard_AI_IEEE_Research_Paper_v5.docx` and matching `.pdf` (seven pages; two-column A4 rendering). Its title is **“Provenance-Based Review of Weather-Station Anomalies.”** The author block lists Harnoor Singh Thiara and Nisha Majumder with a Lovely Professional University affiliation.
- Earlier corrected candidate: `research_results/phase14_1_final_corrections/WeatherGuard_AI_IEEE_Final_Corrected_v3.docx` and `.pdf`. It contains `[Institution]` and `[City, Country]` placeholders. Its `AUTHOR_CONFIRMATION_REQUIRED.md` says affiliation/location have not been confirmed.
- Other paper variants: `research_results/phase14_ieee_paper_revision/WeatherGuard_AI_IEEE_Revised.docx/.pdf`; `final_report/WeatherGuard_AI_Complete_IEEE_Research_Paper.docx/.pdf`; and preliminary IEEE and preliminary research reports. The preliminary complete paper uses a different title and a single-column layout.
- Supporting records include the Phase 14 revision/correction notes and figure audit, Phase 12 report and manifest, Phase 13 synthesis, Phase 1A–1C provenance reports, E1 analysis, synthetic campaign reports, prediction mismatch investigation, and ablation reports.
- The repository contains historical page renders and figure PNGs. These are report/QA images, not presentation slides.

### Code, data, tests, and documentation

- Application: `app.py`; user interface modules in `ui/`; evidence, data, temporal, model and ablation modules in `services/`; research methods in `src/weather_research/`; execution scripts in `scripts/`.
- Main local inputs: `verified_phase01/` and `phase03_model_revalidation/`, with CSV manifests and saved prediction outputs. Phase 12, synthetic, station-provenance and Phase 10 artifacts exist under `research_results/` and `outputs/`.
- Tests: `tests/`, including policy, app, data-integrity, spatial, temporal, synthetic-campaign and phase-specific tests. CI configuration is in `.github/workflows/`.
- Local README and the four Phase 4 guides exist in the working tree. The four guides are untracked; the README is modified and unstaged. They are not present at the audited GitHub commit.
- Text-only presentation materials include `FRIDAY_PRESENTATION_OUTLINE.md`, `FRIDAY_DEMO_GUIDE.md`, `INTEGRATION_DEMO_GUIDE.md`, `FRIDAY_DEMO_AUDIT.md`, and `docs/DEMO_GUIDE.md`.

### Presentation inventory

No `.pptx`, `.ppt`, Keynote, Gamma export, or slide PDF was found in the repository. The checked-in Markdown outline is not a slide deck and cannot be used to assess slide readability, density, visuals, transitions, or the four-minute delivery. **Presentation audit: BLOCKED pending the actual deck/export.**

The separate IEEE template DOCX referenced in earlier project work was not found in this repository inventory. Exact conformance to a particular conference template cannot be certified without the target venue/template and its submission requirements.

## 3. Research paper audit

### Structure

The v5 candidate includes title and abstract, index terms, introduction, related work, dataset/provenance, framework, methodology, experimental results, discussion, limitations/threats, conclusion/future work, acknowledgment, and references. It contains figures and tables with captions and in-text discussion. Its structure is suitable for a research article, subject to the correction and confirmation items below.

### Technical and scientific content

The v5 paper accurately characterizes the local Phase 12 assessment as a saved-output analysis, not a retraining or predictive-validation study. It correctly says that E1 duplicates the baseline signal, that E2 has no independent outcome validation, that E3 is decision-ineligible, that E4 is broad screening, and that no independently adjudicated fault labels support classification metrics. It does not claim measured accuracy, precision, recall, F1, specificity, or calibrated fault probabilities.

The synthetic results are described as injections and coverage/response analyses, not observations from faulty stations. “160” is supported by the campaign’s context × scenario × injected-time unit; it should continue to be described as such, not as 160 independent field cases. The 8/12 threshold is explicitly descriptive rather than selected or calibrated against fault truth.

### Numerical consistency cross-check

| Claim | Result checked against local artifact | Audit finding and limitation |
| --- | --- | --- |
| Processed primary dataset and date span | `model_df.csv`: 44,879 rows, 2021-01-05 19:30 to 2026-03-09 23:30 (+05:30) | Matches Phase 01 manifest. It is a processed snapshot; its manifest does not establish raw-source provenance. |
| Feature-ready rows and temporal split | 44,849 feature-ready rows; 36,434 train; 8,415 held-out; train ends 2025-03-14 23:30 and test starts 2025-03-21 23:30 (+05:30) | Matches manifest. The endpoint gap is exactly seven days. |
| Prediction grid | 8,415 × 12 = 100,980 cells | Matches model prediction grid and mismatch analysis. |
| Missing precipitation values | Six missing `prcp` values in `model_df.csv` | Confirmed. The feature-ready matrices have their own derived-feature readiness filtering; do not conflate those missingness counts. |
| Models and configurations | 4 Isolation Forest, 4 LOF and 4 One-Class SVM configurations | Matches `model_service.py` and saved configuration artifacts: IF contamination .01/.02/.03/.05, 200 trees and seed 42; LOF neighbors 10/20/30/50; OCSVM RBF with nu .01/.02/.03/.05. LOF/OCSVM standardization is fit on training data only. |
| E1 threshold counts | 4/12: 432; 6/12: 214; 8/12: 123; 10/12: 51; 12/12: 15 | Matches `research_results/e1_analysis_summary.json`. Counts describe saved flags, not sensitivity or fault prevalence. |
| E2 held-out support and overlap | 1,661 E2 flags; 47 overlap E1 8/12 candidates; 1,614 E2-only; 79.9168% paired agreement; Jaccard 0.02706; phi 0.0565 | Matches Phase 12 summary. Agreement is dominated by 6,678 joint negatives; it is descriptive association, not predictive validation. |
| E3 coverage and alignment | 123 candidates with neighbor-indexed descriptions; 246 neighbor rows: 32 exact, 61 nonzero-offset, 153 missing offsets; median absolute available offset 60 min; 0 decision-eligible observations | Matches Phase 12 report/summary. Exact time matches do not prove independent instruments or sources; source lineage remains unverified. |
| E4 | Zero positive E4 flags in 8,415 Phase 12 held-out rows; no missing measurement values in that held-out window | Matches Phase 12. A zero-flag screen does not prove station/sensor health or calibration. |
| Saved/refit prediction mismatch | 42 / 100,980; all 42 in Isolation Forest; LOF and OCSVM have no mismatch rows | Confirmed by `research_results/prediction_mismatch_investigation.csv`. Historical estimator/scaler provenance is unavailable, so cause remains unresolved. |
| Multi-context synthetic campaign | Five selected contexts × eight scenarios = 40 context/scenario combinations and 160 context × scenario × injected-time units; one shared local model fit for the contexts | Matches `campaign_manifest.json`. Scenarios are point spike, point drop, persistent offset, stuck sensor, gradual drift, missing block, intermittent noise, and dew-point inconsistency. Results are synthetic-only. |
| Temperature-dose experiment | 2025-09-02 07:30 (+05:30); baseline 0 votes; +2 °C: 6; +5 °C: 9; +10 °C: 11; +15 °C: 12 | Matches campaign registry/results for one injected timestamp and 12 configurations. It is not a field sensitivity estimate. |
| Synthetic evidence-coverage ablation | E1 160/160; E1+E2 145/160; E1+E4 160/160; E1+E2+E4 145/160; E1+E3 and full E1+E2+E3+E4 0/160 | Matches `evidence_coverage_ablation_summary.csv`. This is evidence availability/coverage, not outcome utility, accuracy, or a performance ablation. |
| Phase 12 policy counts | 123 `SUSPICIOUS`; 8,292 `INSUFFICIENT_EVIDENCE`; no `NORMAL` or `ANOMALOUS` assignments | Matches the summary and paper. These are policy outcomes, not adjudicated labels. |

No checkpoint contradiction was found in the v5 numerical values listed above. Historical evidence and synthetic evidence remain distinct. Paper variants differ, however, and should not be treated as interchangeable.

### Paper issues

- V5 is the newest candidate by modification time, but the repository does not identify it as the sole submission master. V5, corrected v3, revised, and `final_report` versions contain different titles and author blocks. The v5 affiliation appears in its author block, while the Phase 14.1 author-confirmation record says the affiliation is unconfirmed and another final paper retains placeholders.
- The final paper title in v5 differs from the earlier explicitly requested research title, “Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence.” Project materials also use “Provenance-based review of weather station anomalies.” Faculty/authors must approve one title and one canonical Word/PDF pair.
- The v5 acknowledgement asks authors to confirm institutional/funding details; author order, affiliation, contribution statement, funding, and acknowledgments need written author approval.
- Spot checks of core scholarly DOI metadata matched the citation title/venue/page details for the meteorological QA and core detector references. This was not a full 13-reference citation-to-claim audit. The data-provider web references should be checked for stable URLs, access dates, and the exact package/API version described.
- Visual review of rendered v5 pages 1–7 found a readable two-column layout with no obvious clipped body text. Figure 1 labels are small, and page 7 is mostly blank below the references. These are presentation-quality concerns, not numerical errors. The chosen IEEE template/target venue was unavailable for an exact formatting comparison.

## 4. Software implementation audit

### Functionality observed in code and tests

Navigation presents Home, Weather Data, Investigate a Reading, Model Evaluation, Experiment Lab, Research, and About. The data loader checks required local files and declared integrity metadata; integrity checks do not establish original acquisition or sensor lineage. The saved workspaces filter historical dates/variables, show reading/model context, and expose separate evidence status. E3 is descriptive-only or unavailable under the policy and cannot change the overall assessment. Model Evaluation states that opening the page does not fit a model; its 12-configuration refit is behind an explicit user control. Synthetic injection execution also requires the explicit campaign form/button; saved results can be browsed without launching a new experiment.

The repository’s Phase 3 browser-QA artifacts record navigation and visible content for all seven destinations across desktop, laptop, tablet and mobile sizes; the archived interaction results record date, variable, investigation timestamp, station marker and timeline interactions. These are prior-run artifacts, not a browser run performed during this Phase 5 audit. They record no page exceptions or failed requests, but do record one transient Streamlit `/media/...png` 404 whose source was not identified. Treat that as an unresolved visual/demo risk.

One substantive app-copy inconsistency remains: `app.py` contains a local `render_research_workspace` definition that shadows the imported `ui.research_workspace.render_research_workspace`. The rendered Research page therefore uses older text that says the current implementation is incomplete and describes E1–E4 evidence states, other synthetic scenarios and ablation as still proposed/incomplete, despite their implementation and saved outputs elsewhere in the repository. The claim that calibrated/validated outcome logic is incomplete is still correct; the broader feature-status statement is stale and misleading for faculty evaluation.

### Current validation

- `python -m unittest discover -s tests -v`: **170 tests passed**.
- `python -m compileall -q app.py ui services src tests`: passed.
- Streamlit startup and `/_stcore/health`: **HTTP 200**.
- The full unittest run emits expected Streamlit bare-mode/deprecation warnings and the METAR pilot dry-run reports blocked provider access; no test failed. The deprecation warning concerns `use_container_width` and is not an audit failure.
- No new browser interaction run was performed in this audit; only existing browser results were inspected.

## 5. README and documentation audit

The local README now explains installation, workspaces, methods, limits and tests, and it links the local Phase 4 guides. However, those local changes are unstaged and the guides are untracked, so they are not visible on GitHub. The README on the public `codex/ui-ux-redesign` branch at the audited commit remains a long November 16 checkpoint that reports stale test counts and says full E1–E4 integration and ablation are incomplete. It also directs readers through older Colab/notebook setup material. This public entry point does not currently describe the reviewed app and saved evidence accurately.

The local dependency files are understandable: `requirements.txt` lists core packages; `requirements-test.txt` adds pytest; CI installs test requirements. There is no dependency lockfile. `.gitignore` ignores most of `outputs/` with specific allowlisted subfolders. Two 221,327,931-byte Phase 10 reference CSV copies exist locally and are ignored; neither is tracked in Git. This preserves the large files locally but means repository readers cannot assume those reference tables are available from GitHub. The files should not be uploaded without confirming provenance, licensing, necessity, and an artifact-delivery plan.

No `LICENSE`, `COPYING`, or `NOTICE` file was found. The repo is public but has no license declaration in the checked GitHub repository view. No `.env` file or matches for common high-confidence credential patterns were found in the limited text scan; this is not a substitute for GitHub secret scanning. Dataset and external-source reuse terms still need explicit review.

GitHub read-only inspection found the public repository description is empty. The public `main` commit is `852bc34e76ef4e5de15e48f0f1402f7bf0e9c1d1`; `codex/ui-ux-redesign` is at `aec543b755903b7fbdb1dc1ddefb1dc3ac68660d`. The local branch matches its upstream commit (0 ahead/0 behind), but its working tree is not clean. No changes were uploaded.

## 6. Scientific integrity audit

The v5 draft and evidence policy maintain the critical distinctions:

- Anomaly candidates are not confirmed sensor faults.
- E1 configuration agreement is dependent on the saved baseline labels, not independent confirmation or a calibrated confidence measure.
- E2, E3 and E4 are evidence/context streams, not model votes.
- Missing or unavailable evidence is not negative or normal evidence.
- E3 remains decision-ineligible because independent source and sensor lineage are unverified; a timestamp match alone does not create independence.
- Synthetic injections do not estimate real-world accuracy or fault prevalence.
- No independently adjudicated real fault labels exist; standard predictive performance metrics cannot be estimated.
- The 42/100,980 mismatch is openly reported, with its cause unresolved.

The paper’s strongest scientifically defensible contribution is an uncertainty-preserving evidence review and provenance audit workflow. Claims of validated event-level fault detection, independent spatial corroboration, classifier accuracy, or operational readiness would not be defensible on the available evidence.

## 7. Presentation audit

**Blocked:** no slide deck, Gamma export, or slide PDF was available. Markdown outlines can guide a future review but do not establish that the content fits a four-minute talk and two-minute viva. Once supplied, check slide-by-slide alignment with the paper, density, visual legibility, separation of historical and synthetic evidence, metric wording, and timing. Ensure the presentation uses the same title, author details and canonical result tables as the selected paper.

## 8. Demonstration readiness

The local six-minute `docs/DEMO_GUIDE.md` is technically plausible and uses saved campaign artifacts, explicitly avoids model refitting, and explains missing evidence and synthetic limits. The code supports its main path: date selection, marker details, timeline interaction, reading investigation, separate E1–E4 display, and saved synthetic results. It remains a six-minute app demonstration guide, not a four-minute slide talk. Its main operational risks are: required local snapshots/manifests must be present and pass integrity checks; the selected date range must contain observations; the Phase 3 browser record includes one unidentified transient image 404; and an optional refit button must not be activated unless a new run is intended. No live browser demonstration was conducted during this audit.

## 9. Prioritized issue register

| ID | Severity | File/component | Finding and evidence | Recommended correction | Blocks submission? |
| --- | --- | --- | --- | --- | --- |
| SUB-01 | **High** | Paper variants under `research_results/` and `final_report/` | Multiple final-looking DOCX/PDF pairs differ in title, author block, and revision. The newest timestamp suggests v5 but no authoritative master is designated. | Author/faculty select one paper title and canonical DOCX/PDF pair; retire nothing until selection, then mark other files as archived drafts. | **Yes** |
| SUB-02 | **High** | `AUTHOR_CONFIRMATION_REQUIRED.md`; v5 author block and acknowledgment | Author order, affiliation, contribution, funding and acknowledgment details are not author-confirmed; one paper contains placeholders. | Obtain written author approval and update only the selected final paper in a later correction phase. | **Yes** |
| SUB-03 | **High** | `app.py` Research workspace | Local function shadows imported UI module and displays obsolete claims that implemented evidence states, synthetic scenarios and ablation remain incomplete. | Align the active Research workspace copy and dispatch with current code and evidence status; preserve the accurate limitation that validated outcomes remain incomplete. | No for paper alone; **yes for a consistent software/research evaluation** |
| SUB-04 | **High** | Public GitHub README and local working tree | Public branch README is a stale November checkpoint; local replacement/docs are not committed or published. Root GitHub view also has no project description. | In a separate authorized release phase, publish the reviewed README/docs to the intended branch and update the repository description after content and artifact selection. | **Yes for repository-based evaluation** |
| SUB-05 | **Blocked** | Presentation materials | No Gamma export, PPTX/PPT, Keynote or slide PDF found. | Upload the actual presentation source/export for review; align title, authors, claims and timing with the selected paper. | **Yes for oral/presentation submission** |
| SUB-06 | **Medium** | `docs/DEMO_GUIDE.md` and browser QA | Six-minute walkthrough is safe and plausible, but it does not prove four-minute talk/two-minute viva timing. Archived browser QA records one unidentified transient image 404. | Prepare a timed talk/viva script and rehearse; resolve or confirm the image warning before a live demo. | No, if presentation is assessed separately |
| SUB-07 | **Medium** | IEEE paper DOCX/PDF | Readable two-column A4 output, but exact target venue/template is absent; Figure 1 is small and final page is underfilled. | Compare the chosen final paper against the actual target IEEE template and venue checklist; inspect figure minimum-size/readability requirements. | Potentially, depending on venue rules |
| SUB-08 | **Medium** | References in v5 | Core reference metadata spot checks matched, but the complete bibliography and citation-to-claim mapping were not exhaustively verified; data-provider URLs/version/access details need a final pass. | Verify every reference against publisher/provider records, check every in-text citation, and use stable DOI/official URLs where available. | No, but should be completed before submission |
| SUB-09 | **Medium** | Repository root / `.gitignore` | No license or explicit dataset/source reuse notice found. Two ignored local Phase 10 CSV copies are about 221 MB each and are not available from GitHub. | Confirm reuse rights and attribution; decide which research artifacts belong in GitHub or a separate archival repository without uploading raw data by default. | Potentially, depending on faculty/repository requirements |
| SUB-10 | **Low** | UI/browser QA | Current tests pass; UI code still emits a Streamlit `use_container_width` deprecation warning, and one historical browser run recorded an image 404. | Address the deprecation and retest the image request in a later UI maintenance phase. | No |

## 10. Submission readiness scorecard

| Area | Status | Reason |
| --- | --- | --- |
| Research paper | **Requires correction** | Numerically defensible v5 candidate, but canonical version and author details are not confirmed; exact venue template not supplied. |
| Software and core tests | **Requires correction** | All 170 tests pass, compilation passes, health endpoint is 200; the active Research workspace contains materially stale feature-status copy and old browser artifact has one 404. |
| Local README and guides | **Ready with minor corrections** | Useful locally, but not published to GitHub and app Research copy remains inconsistent. |
| GitHub repository | **Requires correction** | Public README/status are stale, no repo description or license declaration, large ignored evidence files are not remotely available, local changes are unpublished. |
| Presentation slides | **Blocked** | No actual slide deck or Gamma export available to inspect. |
| Live demonstration | **Ready with minor corrections** | Guide is feasible and cautious; browser 404 is unresolved and no Phase 5 live interaction run was performed. |
| Final submission package | **Blocked** | Requires author/faculty confirmation, a canonical paper pair, the actual presentation and venue requirements. |

## 11. Recommended correction sequence

1. Authors/faculty choose the paper title, canonical DOCX/PDF revision, author order and approved affiliation/contribution/funding/acknowledgment text.
2. Supply the actual slide deck/Gamma export and target venue template/rules; audit the four-minute talk and two-minute viva against the chosen paper.
3. Correct the active Research workspace copy and its dispatch so it describes implemented evidence components accurately while retaining the unresolved validation limits.
4. Complete citation-to-claim and reuse/licensing review; decide how to reference large Phase 10 files without pushing unsupported or unnecessary raw artifacts.
5. Publish a consistent README and documentation set on the selected GitHub branch only after review and explicit release authorization; rerun tests and browser interaction checks then.
6. Rehearse the live demo with local artifact hashes checked, saved experiments selected, and the refit control avoided unless intentionally demonstrating a new run.

## 12. Missing materials to provide

- The actual Gamma presentation export or source deck (`.pptx`, `.ppt`, Keynote, or slide PDF), including speaker notes if available.
- Author-approved author order, affiliation/location, contributions, funding statement and acknowledgments.
- The target IEEE conference/journal name, its current author instructions/template, and the institution/faculty submission rubric if those govern acceptance.
- Any external submission files not stored in this repository (cover sheet, declaration, ethics/data statement, or signed forms), if required by the faculty or venue.

## 13. Git safety record

Before creating this audit report, status was `codex/ui-ux-redesign...origin/codex/ui-ux-redesign` at commit `aec543b755903b7fbdb1dc1ddefb1dc3ac68660d`, with **279 staged paths, 10 unstaged tracked paths, and 46 pre-existing untracked paths**. Staged work is primarily accumulated final-paper QA images and Phase 14 paper artifacts. Unstaged tracked changes included `README.md`, `app.py`, tests and UI modules. Untracked items included the Phase 4 guides, browser-QA artifacts, Phase 15 paper files, and UI files. The new audit report adds one untracked path. All existing staged, unstaged and untracked work has been preserved. No stage/commit/push/branch/reset/clean/stash operation was performed.

### External read-only checks

- Public repository: [WeatherGuard AI on GitHub](https://github.com/Hrex2/WeatherGuard-AI-Intelligent-Weather-Station-Anomaly-Verification)
- Current public branch README: [codex/ui-ux-redesign README](https://github.com/Hrex2/WeatherGuard-AI-Intelligent-Weather-Station-Anomaly-Verification/blob/codex/ui-ux-redesign/README.md)
- Spot-checked bibliographic metadata: [Fiebrich et al. 2010](https://doi.org/10.1175/2010JTECHA1433.1), [Fiebrich et al. 2020](https://doi.org/10.1175/JTECH-D-20-0078.1), [Faybishenko et al. 2022](https://doi.org/10.1007/s00477-021-02106-w), [Isolation Forest](https://doi.org/10.1109/ICDM.2008.17), and [Schölkopf et al. 2001](https://doi.org/10.1162/089976601750264965).
