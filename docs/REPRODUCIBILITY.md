# WeatherGuard AI Reproducibility Guide

## Reproduction levels

Keep these evidence types distinct:

1. **Artifact integrity:** whether local files match hashes, row counts and schemas in manifests.
2. **Historical analysis:** outputs computed or saved from the bundled held-out time series.
3. **Synthetic experiments:** controlled injected values evaluated in selected contexts.
4. **Real-world validation:** comparison with independently sourced observations and adjudicated event/fault labels. This level is not complete.

Integrity does not prove data provenance; historical or synthetic behavior does not establish real-world fault-detection performance.

## Environment and commands

The CI workflow uses Python 3.12. Create an isolated environment, install the project and test dependencies, then run tests:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m compileall -q app.py ui services src tests
```

Run the UI with `python -m streamlit run app.py`. The full test suite checks software contracts; it is not a real-world performance evaluation. The model-evaluation UI has an explicit refit control. Do not use that control when the objective is to inspect saved historical outputs.

## Snapshot and split

Primary local files and declarations are under `verified_phase01/`; Phase 03 saved artifacts and their integrity manifest are under `phase03_model_revalidation/`. The Phase 01 manifest reports:

| Item | Reported value | Interpretation |
| --- | ---: | --- |
| `model_df.csv` rows | 44,879 | Historical primary table in the local snapshot |
| Feature-ready multi-variable rows | 44,849 | Rows represented in model matrices after feature readiness |
| Training rows | 36,434 | Train segment ending 2025-03-14 23:30+05:30 |
| Held-out test rows | 8,415 | Test segment beginning 2025-03-21 23:30+05:30 |
| Temporal separation | 7 days | Gap between the train endpoint and test start |

The overall primary period is reported as 2021-01-05 19:30+05:30 through 2026-03-09 23:30+05:30. Consult `verified_phase01/phase01_manifest.json` for exact hashes and declared metadata. The Phase 03 manifest explicitly describes its audit as `HASHED_INTEGRITY_ONLY_HISTORICAL_PROVENANCE_UNKNOWN`; therefore do not describe these local checks as proof of original acquisition, independent station identity or direct observation status.

## Features and fitted protocol

The ordered model feature set is `temp`, `dwpt`, `rhum`, `prcp`, `wspd`, `pres`, `temp_change_1h`, `temp_rolling_mean_6h`, `temp_deviation_6h`, `month_sin`, and `month_cos`. Feature engineering includes elapsed-time-aware temperature change and segment-aware rolling context. Preprocessing documentation specifies train-only imputation/scaling where used.

The saved protocol has 12 detector configurations:

- Isolation Forest: contamination 0.01, 0.02, 0.03 and 0.05; 200 trees; random seed 42; `n_jobs=-1`.
- Local Outlier Factor: 10, 20, 30 and 50 neighbors; contamination 0.02; novelty mode enabled.
- One-Class SVM: RBF kernel; `gamma=scale`; `nu` 0.01, 0.02, 0.03 and 0.05.

For LOF and One-Class SVM, the standardized path fits `StandardScaler` on the training matrix only. Fitted estimator/scaler objects are not bundled as a serialized deployment model. A clean local refit differs from saved predictions in **42 of 100,980 cells**; the cause remains unresolved. The discrepancy prevents exact prediction reproduction from being claimed. Saved results remain the historical record; do not silently replace them with a new fit.

## Evidence components and outcomes

- **E1:** stability across 12 saved detector configurations. The 8-of-12 candidate threshold is descriptive, not a probability or independently validated cutoff. In the contribution analysis, E1 vote counts match the baseline-derived votes at all 8,415 test timestamps; this indicates dependency rather than an independent added signal.
- **E2:** temporal consistency uses a default six-hour past window, minimum context of three, robust z threshold 3.5 and stuck-run length four. Real-time mode is past-only; retrospective mode may use future observations. These exploratory settings are not validated fault rules. Phase 12 records 1,661 support flags, without independent event adjudication.
- **E3:** neighbor comparisons are descriptive-only, unavailable or insufficient under current lineage and evidence policy. In the Phase 12 held-out summary, 123 records are descriptive-only; 8,292 are unavailable/insufficient; decision-eligible independent coverage is 0%. E3 is not a classifier vote and is not validated.
- **E4:** physical/range/cross-variable checks are broad screens, not calibration tests. Phase 12 records zero positive support flags across 8,415 test timestamps. That result does not show that every sensor was healthy; it says only that this screen supplied no positive flags under the saved setup.

Across Phase 12, 123 test timestamps were baseline-suspicious and 8,292 had insufficient evidence under the documented policy. These are workflow assessment counts, not confusion-matrix metrics. No independent real-fault labels are available to calculate accuracy, precision, recall, F1 or specificity.

## Saved and synthetic experiments

### Historical saved outputs

`research_results/phase12_evidence_contribution/20261119T144632Z/` contains a saved-output structural contribution/dependency analysis. Its report labels the work as operational/structural contribution analysis, not predictive validation. `research_results/e1_e4_ablation_study_20261119T132347Z/` contains an ablation report over saved held-out outputs. These analyses do not require a model fit when read; the ablation runner creates a new output run if executed.

### Temperature-dose synthetic campaign

`outputs/synthetic_fault_campaign/` preserves a single held-out timestamp injection experiment with temperature increments +2, +5, +10 and +15 °C, evaluated alongside clean context. Its recorded votes are 0, 6, 9, 11 and 12 respectively across 12 configurations. It is a one-timestamp controlled injection, not an estimate of field sensitivity, fault prevalence or generalization.

### Multi-context synthetic campaign

`scripts/run_multicontext_fault_matrix.py` selects up to five held-out contexts from pre-injection data, with a minimum separation of 14 days, then applies eight synthetic fault scenarios. It performs a shared local model fit and generates clean predictions before running injections. Re-running it is an experiment and fitting action; use a new run directory, retain the manifest, and do not present the output as real-world validation.

### E1–E4 ablation runner

`scripts/run_e1_e4_ablation.py` consumes saved held-out outputs and does not fit a model, sample random contexts, make a network request or overwrite source artifacts. It writes a unique timestamped directory by default. To run explicitly:

```powershell
python scripts/run_e1_e4_ablation.py
```

To render from an existing output directory without rerunning evidence components:

```powershell
python scripts/run_e1_e4_ablation.py --render-existing --output-dir research_results/e1_e4_ablation_study_20261119T132347Z
```

Phase 12 runner uses saved evidence and can write to an explicit new directory:

```powershell
python scripts/run_phase12_analysis.py --output-dir research_results/phase12_evidence_contribution/my_new_run
```

Choose a previously unused path. Scripts may intentionally refuse a non-empty output directory; preserve all historical runs.

## Files to consult

- `verified_phase01/phase01_manifest.json` — primary snapshot counts, split and declared hashes.
- `phase03_model_revalidation/` — saved predictions and integrity manifest.
- `research_results/phase12_evidence_contribution/20261119T144632Z/phase12_summary.json` and `PHASE12_RESEARCH_REPORT.md` — contribution results and caveats.
- `research_results/e1_e4_ablation_study_20261119T132347Z/ABLATION_STUDY_REPORT.md` — ablation protocol.
- `SYNTHETIC_BASELINE_COMPARISON_REPORT.md` and `MULTICONTEXT_FAULT_MATRIX_REPORT.md` — synthetic campaign protocols and reports.
- `prediction_mismatch_investigation/` (where present) — saved/refit mismatch investigation artifacts.

## Open reproducibility gaps

Independent acquisition lineage and station identity remain uncertain; no direct-observation claim should be made without source evidence. Independent real event/fault adjudication is missing. E3 has no decision-eligible independent observations. The 42/100,980 prediction mismatch is unresolved. Synthetic campaigns do not substitute for these missing sources of validation. Preserve uncertainty in any report and label each claim as historical, synthetic, provisional or unresolved.
