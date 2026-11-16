# Friday demonstration audit — 16 November 2026

## Scope and starting point

Audited the clean `main` checkout at `6497f1c` before edits. Inspected `README.md`, dependencies, the Streamlit app and UI/services, `src/weather_research/`, existing tests, both notebooks, Phase 01 and Phase 03 saved artifacts, synthetic campaign outputs, literature sources, manifests and current research/status documentation. No historical notebook, source observation snapshot, prediction artifact, or fitted model was overwritten.

## Repository and working parts

- `app.py`, `services/`, and `ui/` implement five workspaces: Command Center, Research Studio, Investigation Studio, Experiment Lab, and Model Evaluation.
- `verified_phase01/` contains processed VILD0 observations and model matrices; the data are historical and processed, not raw retrieval or live measurements.
- `phase03_model_revalidation/` contains predictions, stability, similarity, configuration, episode, and derived spatial tables.
- `src/weather_research/` contains the preserved feature, model, temporal, spatial, quality, fault, evidence, audit and synthetic campaign logic.
- `outputs/synthetic_fault_campaign/` contains the executed temperature-spike dose campaign and its manifest; `outputs/station_provenance/` is an explicitly incomplete inventory.
- The master and exploratory notebooks are retained. Full notebook execution was outside this focused demo audit.

## Current artifact facts

- Phase 01 manifest reports audit passed. Loader now checks SHA-256, row count and ordered columns for `model_df.csv`, `X_train_multi.csv`, and `X_test_multi.csv` before returning data.
- Processed observations: 44,879 rows, 10 columns; train: 36,434 × 9; test: 8,415 × 9. Processed observation window: 2021-01-05 19:30 IST to 2026-03-09 23:30 IST.
- Saved prediction grid: 100,980 rows, 8,415 timestamps, 12 configurations, no duplicate timestamp/configuration pairs, and no missing labels.
- Configurations: four Isolation Forest (`IF_0.01`, `.02`, `.03`, `.05`), four LOF (`LOF_10`, `_20`, `_30`, `_50`), and four One-Class SVM (`SVM_0.01`, `.02`, `.03`, `.05`).
- The saved 8/12 consensus table has 123 candidate timestamps and 81 one-hour episodes. This is a research operating threshold, not an optimized or calibrated probability cutoff.
- Campaign dose results at the injected timestamp: clean 0 votes; +2 °C 6; +5 °C 9; +10 °C 11; +15 °C 12. Detection here means at least one configuration flagged the synthetic injected row. Changed configuration predictions anywhere were 10, 15, 20, and 21 respectively; corrected counts beyond the expected feature-propagation window are 0 for all four. These are synthetic results only.

## Issues corrected for the demo

1. Enforced Phase 01 manifest hash, row-count and column-order checks; mismatches fail closed with the affected filename.
2. Changed sub-threshold E1 votes from “conflicting” to “no detected evidence.”
3. E2 is now explicitly unavailable as independent evidence because saved episodes derive from the E1 consensus selection; episode context remains visible.
4. E4 missingness alone no longer supports a sensor-fault interpretation; missing values are separately counted. Only non-missing screening flags (including nonnumeric/infinite, broad-range, and cross-variable flags) can support a screening signal, which is still not a fault label.
5. Corrected the synthetic event table’s “unaffected window” count using the already saved propagation audit and retained an “anywhere” total as a separate column. No models were rerun.
6. Experiment Lab now displays the real baseline series beside a selected synthetic dose, clean/faulted votes, baseline option, and result provenance checks against the current Phase 01 hashes.

## Testing and launch status

- Before editing, the previous testing report records 35 passing tests; the final current suite after edits: **39 passed, 0 failed**.
- `python -m compileall -q app.py services ui src/weather_research tests`: passed.
- Data loader verification: passed; counts above confirmed, and prediction grid reconciling at 8,415 × 12.
- Streamlit `AppTest`: all five workspaces opened without script exceptions.
- Fresh `python -m streamlit run app.py --server.headless true --server.port 8765` started as a process, but external HTTP health check was blocked by the managed environment’s localhost socket restriction. Thus browser/HTTP rendering and real screenshots were not verified here. No screenshots were fabricated.

## Remaining risks for Friday

- Start and rehearse on the classroom computer before the session; network/browser restrictions or dependency differences may affect launch.
- There are no raw observation files, verified provider metadata, neighbor coordinates/series, or fault labels. E3 stays unavailable; outcome remains uncertain.
- E2 is contextual only, not an independent temporal model. E1–E4 have no validated integrated rule or real-world calibration.
- The local clean refit differs from saved predictions at 42/100,980 cells. The parity discrepancy remains unresolved and is not part of the live demo.
- Full research validation, ablation, station provenance, real-world fault evaluation, and expanded synthetic fault campaigns remain after-Friday work.
