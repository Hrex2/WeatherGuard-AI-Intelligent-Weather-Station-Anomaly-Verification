# WeatherGuard AI

**Uncertainty-aware review of weather-station anomaly candidates.** WeatherGuard AI is a research prototype for examining unusual weather readings through model stability, temporal context, spatial evidence and physical plausibility. Its governing principle is **ANOMALY ≠ FAULT**: an unusual reading is a candidate for review, not proof that a station or sensor failed.

The project combines a Streamlit research interface, saved historical analysis artifacts, controlled synthetic experiments, and a conservative evidence policy. It is not a live monitoring or operational fault-diagnosis service.

## Research status at a glance

- The local primary snapshot contains 44,879 time-indexed rows; 44,849 have the selected model features. The held-out test segment contains 8,415 rows and is separated from the training segment by a temporal gap. See [`verified_phase01/phase01_manifest.json`](verified_phase01/phase01_manifest.json) and [Reproducibility](docs/REPRODUCIBILITY.md).
- Historical saved predictions have no independently adjudicated real fault labels. Predictive accuracy, precision, recall, F1 and fault-detection claims are therefore not established.
- A clean local refit differs from saved prediction outputs in 42 of 100,980 prediction cells; the cause is unresolved. Exact model-output reproduction is not established.
- E1 is a model-configuration stability signal and is dependent on the baseline model outputs. E2 supplies temporal context. E3 station comparisons remain descriptive or unavailable and are decision-ineligible because independent lineage and event validation are insufficient. E4 is a physical screening layer, not a calibration test.
- Synthetic injections support controlled software/behavioral investigation only; they are not real-world validation.

These are scoped research findings, not performance guarantees. The [Reproducibility Guide](docs/REPRODUCIBILITY.md) identifies source artifacts, definitions, and limitations.

## Start the application

Python 3.12 is used in the repository CI workflow. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the URL printed by Streamlit (normally `http://localhost:8501`). The application reads the committed local snapshot and manifests. Its integrity checks detect changes to selected files; they do not prove historical data provenance or independent station lineage. See [User Guide](docs/USER_GUIDE.md) for workspace navigation and safe interpretation.

## Main workspaces

The application offers Home, Weather Data, Investigate a Reading, Model Evaluation, Experiment Lab, Research and About. Home provides a historical dashboard and synchronized timeline. Investigate a Reading keeps evidence streams visible separately. Model Evaluation describes and can explicitly refit the saved protocol. Experiment Lab and Research expose saved analyses and documents. Detailed workflows are in the [User Guide](docs/USER_GUIDE.md); a short classroom walkthrough is in the [Demo Guide](docs/DEMO_GUIDE.md).

## Architecture and data

The application shell is `app.py`; UI workspaces live in `ui/`, services in `services/`, and feature/preprocessing research code in `src/weather_research/`. Snapshot inputs and manifests are in `verified_phase01/` and `phase03_model_revalidation/`. Historical and synthetic outputs are preserved under `research_results/` and `outputs/`. The [Architecture Guide](docs/ARCHITECTURE.md) describes data flow, component boundaries and output behavior.

The primary feature protocol uses six weather measurements, three prior-temperature features and two cyclic month features. The exact ordered feature list, split and saved-protocol settings are recorded in the [Reproducibility Guide](docs/REPRODUCIBILITY.md). “Verified snapshot” refers to local integrity checks, not an independently reproduced upstream acquisition.

## Tests and checks

Install the test dependencies and run the repository's unittest discovery command:

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m compileall -q app.py ui services src tests
```

The test suite checks software behavior and evidence-policy contracts; passing tests do not validate real-world anomaly detection. The GitHub Actions research-quality workflow installs `requirements-test.txt` before running tests.

## Research records

Useful existing records include:

- `MULTICONTEXT_FAULT_MATRIX_REPORT.md` — five-context synthetic scenario campaign.
- `SYNTHETIC_BASELINE_COMPARISON_REPORT.md` — controlled temperature-dose comparison.
- `research_results/phase12_evidence_contribution/20261119T144632Z/PHASE12_RESEARCH_REPORT.md` — saved-output contribution/dependency analysis.
- `research_results/e1_e4_ablation_study_20261119T132347Z/ABLATION_STUDY_REPORT.md` — structural operational ablation.
- `research_results/phase13_research_synthesis/PHASE13_FINAL_RESEARCH_SYNTHESIS.md` — synthesis and unresolved limitations.
- `research_results/phase15_ieee_paper_v4/WeatherGuard_AI_IEEE_Research_Paper_v5.docx` and `.pdf` — current paper draft artifacts; verify authorship and affiliation details before submission.

Older dated notes, reports and outputs are retained as historical records; consult their manifests and run-specific limitations before reusing figures or claims.

## Project implementation plan

1. **Integrity and provenance:** retain source manifests, hashes and explicit provenance qualifications; do not equate file integrity with verified acquisition.
2. **Evidence isolation:** preserve E1–E4 as distinct evidence views; do not make E3 a classifier vote or treat missing data as agreement.
3. **Validation:** pursue independent station lineage, original observations and blinded/independent event adjudication before estimating real-world fault performance.
4. **Reproducibility:** investigate the 42/100,980 saved-prediction mismatch and archive every new run in a unique output directory.
5. **Product scope:** keep the interface transparent about uncertainty and historical-only inputs; any live use needs a separate data, safety and operational validation effort.

## Contributors

The v5 paper draft lists Harnoor Singh Thiara and Nisha Majumder and gives an affiliation in its author block. Authors should confirm names, order, affiliation, contributions, acknowledgments and funding statements before submission. Listing in a draft is not independent verification of those details.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [User Guide](docs/USER_GUIDE.md)
- [Reproducibility Guide](docs/REPRODUCIBILITY.md)
- [Demo Guide](docs/DEMO_GUIDE.md)
