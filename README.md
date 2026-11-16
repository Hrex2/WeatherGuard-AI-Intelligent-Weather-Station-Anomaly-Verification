# WeatherGuard AI — Intelligent Weather Station Anomaly Verification

## Codex continuation checkpoint (2026-11-16)

The extracted November 15 checkpoint is audited in [CODEX_PROJECT_AUDIT.md](CODEX_PROJECT_AUDIT.md). Stored Phase 01 hashes/counts and Phase 03 table structure were checked locally. The reusable controlled temperature campaign is in `src/weather_research/synthetic_campaign.py`; its executed synthetic-only outputs are in `outputs/synthetic_fault_campaign/`. Run it explicitly with `PYTHONPATH=src` and `run_temperature_spike_campaign('.')`. The campaign performs no retrieval. Local clean-model reproduction differs from saved Phase 03 labels at 42/100,980 cells; see `outputs/synthetic_fault_campaign/clean_baseline_reproduction.csv` and the handoff before interpreting these outputs.

Phase 02 provenance, the other synthetic fault groups, complete E1–E4 wiring, and ablation remain incomplete. See [NEXT_STEPS.md](NEXT_STEPS.md). The current output is not a complete or Colab-verified research pipeline.
## Research package and Colab setup

This package contains a 17-section master notebook, reusable Python modules, a complete source-cell inventory/migration manifest, and the unmodified exploratory archive. The original selected source notebook and exploratory archive remain byte-identical. The master notebook has unique cell IDs for nbformat 4.5; the archive remains unchanged because its declared nbformat 4.0 does not require IDs.

## Colab setup

1. Upload/copy the whole `weather_anomaly_research_cleaned` folder to Google Drive.
2. In Colab, mount Drive and set the package root before the notebook setup cell:

```python
from google.colab import drive
drive.mount('/content/drive')
import os
os.environ['WEATHER_RESEARCH_ROOT'] = '/content/drive/MyDrive/weather_anomaly_research_cleaned'
%pip install -r /content/drive/MyDrive/weather_anomaly_research_cleaned/requirements.txt
```

If the folder is elsewhere, change the path. Alternatively, change the working directory to the package folder. The setup cell also searches the two common Colab Drive mount paths. It fails with a clear error if `src/weather_research` cannot be found. Meteostat is optional and is not installed by the base requirements; install/verify the recorded Meteostat version only when explicitly running data acquisition. No cell downloads weather data automatically.

For raw Pipeline B CSV loading, set `WEATHER_RAW_CSV` to a timezone-aware CSV with the six required weather columns. Do not point it at a substitute or gridded dataset. Set `HISTORICAL_PIPELINE_B` explicitly in Colab only when auditing the exact historical objects. `run_models` and `run_retrieval` default to false.

## Deliverables

- `Weather_Station_Anomaly_Detection_Master.ipynb` — sections 00–16 with a second-pass implementation status for every section. Section 15 ablation and some visual/reporting analyses remain unimplemented.
- `Weather_Station_Anomaly_Detection_Exploratory_Archive.ipynb` — original cells and saved outputs.
- `src/weather_research/` — feature, preprocessing, audit, model, event, fault, spatial, physical and evidence helpers.
- `tests/` — deterministic regression suite: **31 passed, 0 failed** on `python -B -m unittest discover -s tests -v`.
- `FINAL_BUGFIX_REPORT.md`, `SECOND_PASS_AUDIT.md`, `PROJECT_STATUS.md`, `REFACTORING_REPORT.md`, `TESTING_REPORT.md`, `DEPENDENCY_MAP.md`, `cell_audit_inventory.csv`, `cell_migration_manifest.csv`, `experiment_registry.csv`, `record.md`.

**Research status:** this package does not include the Phase 02 station-provenance audit cell/validator/report described in earlier workspace history. Its retrieval and spatial helper functions are not a substitute for that phase audit. Phase 01 real-data verification and all real-station empirical conclusions remain pending.


Phase 02 currently has an explicitly incomplete [provenance report](PHASE02_PROVENANCE_REPORT.md) and a machine-readable inventory at outputs/station_provenance/station_manifest.json; the report records known history fields and leaves unavailable metadata null. No source data were fetched.

# WeatherGuard AI application

**WeatherGuard AI — Intelligent Weather Station Anomaly Verification** is a Streamlit interface over the existing research package and archived experiment artifacts. The interface uses the included VILD0 processed snapshots and Phase 03 saved outputs. Phase 01 manifest hashes, row counts and column order are enforced before the app presents those snapshots as verified. It does not fetch data on startup and does not present the snapshots as raw acquisition or a live feed.

## Friday classroom demonstration

- [Audit and implementation notes](FRIDAY_DEMO_AUDIT.md)
- [7–10 minute walkthrough and setup](FRIDAY_DEMO_GUIDE.md)
- [11-slide presentation outline](FRIDAY_PRESENTATION_OUTLINE.md)
- [Teacher Q&A preparation](FRIDAY_QA_PREPARATION.md)
- [Backup plan](FRIDAY_BACKUP_PLAN.md)

## Research framing

The research separates model anomaly flags from event-level interpretation. It organizes candidate evidence as E1 model stability, E2 temporal consistency, E3 spatial corroboration, and E4 physical screening. Possible interpretation outcomes are regionally supported unusual event, station-specific suspicious observation, and uncertain/insufficient evidence. Current end-to-end evidence integration is incomplete; the application therefore displays uncertainty when it cannot justify a conclusion.

## Workspaces

- **Home** — plain-language purpose, historical coverage, agreement summary, candidate count, and validation status.
- **Weather Data** — date-filtered measurements with units and historical candidate markers.
- **Investigate a Reading** — guided review of measurements, votes, E1–E4 evidence availability, and technical details.
- **Model Evaluation** — exactly two primary sections: **Experiments & Results** and **How the Models Work**. The model selector explains Isolation Forest, LOF and One-Class SVM using saved data and actual protocol settings.
- **Experiment Lab** — saved and explicitly triggered temperature point-spike experiments.
- **Research** — methods, literature summaries, research gap, findings and limitations.

Model metadata is served through `services/model_metadata.py`, sourced from `weather_research.models.build_estimator`, `default_model_configs`, the loaded dataset, and saved configuration results. Plain-language profile copy is maintained in `research_content/model_profiles.json`.

See the implementation notes in [UI_UX_AUDIT_AND_REDESIGN.md](UI_UX_AUDIT_AND_REDESIGN.md), the [Model Evaluation design](MODEL_EVALUATION_DESIGN.md), and [UI redesign changelog](UI_REDESIGN_CHANGELOG.md).

The interactive investigation, independent temporal screening, upload limitations and parity audit are documented in [ANOMALY_INVESTIGATION_DESIGN.md](ANOMALY_INVESTIGATION_DESIGN.md). `scripts/analyze_saved_e1.py` produces E1 agreement and threshold sensitivity tables from saved predictions without refitting. `scripts/investigate_prediction_mismatches.py` reproduces the specific local-vs-saved comparison and records per-row feature vectors; the known 42 differences are all Isolation Forest and remain unexplained without the original estimator/scaler provenance.

Saved-label E1 threshold counts are 432 (4/12), 214 (6/12), 123 (8/12), 51 (10/12), and 15 (12/12) of 8,415 test timestamps. At least one configuration flags 521 timestamps for Isolation Forest, 635 for LOF and 575 for One-Class SVM. These describe model outputs, not labeled performance or probabilities. See [RESEARCH_MASTER_PLAN.md](RESEARCH_MASTER_PLAN.md), [RESEARCH_GAP_ANALYSIS.md](RESEARCH_GAP_ANALYSIS.md), [EXPERIMENT_TRACKER.md](EXPERIMENT_TRACKER.md), [RESEARCH_DECISIONS.md](RESEARCH_DECISIONS.md), [GIT_CHANGELOG.md](GIT_CHANGELOG.md), and [NEXT_SESSION.md](NEXT_SESSION.md) for continuation state.

The initial E2 candidate sensitivity table evaluates 123 saved model candidates across five prior windows and three robust-deviation cutoffs in real-time and retrospective modes. See `research_results/e2_candidate_sensitivity_summary.csv`; this selected sample does not provide independent temporal accuracy validation.

## Run locally

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

Model refitting and synthetic campaigns run only after the user activates their controls. The twelve-model refit can take several minutes and uses the saved training matrix. It is labelled as a new local execution and compared with the historical predictions.

## Tests

```powershell
python -B -m unittest discover -s tests -v
```

## Artifacts and scientific limits

See `ARCHITECTURE.md`, `RESEARCH_METHODOLOGY.md`, `NEXT_STAGE_IMPLEMENTATION_PLAN.md`, and `CODEX_PROJECT_AUDIT.md`. There are no fitted model objects, raw neighbor observation exports, verified neighbor coordinates, or real-observation fault labels in this archive. The stored Phase 03 outputs and fresh local refit differ at 42 of 100,980 prediction cells. The application does not claim real-world anomaly accuracy or treat synthetic labels as real-world fault truth.
