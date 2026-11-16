# Codex handoff — 2026-11-16

## Current location

This handoff describes the extracted archive copy in `weather_anomaly_checkpoint_20261115/weather_anomaly_research_cleaned`. The original Desktop project folder and source ZIP were not edited.

## Reproduce the executed controlled campaign

From the project root, install `requirements.txt` if needed, then run:

```powershell
$env:PYTHONPATH = 'src'
python -c "from weather_research.synthetic_campaign import run_temperature_spike_campaign; run_temperature_spike_campaign('.')"
```

This runs four same-timestamp held-out temperature point injections at +2, +5, +10, and +15 °C. It uses the stored `model_df`, `X_train_multi`, `X_test_multi`, and saved Phase 03 clean predictions. The training scaler and 12 model configurations use only the saved training matrix. No data download occurs.

## Interpretation of the current campaign

The same local clean refit reproduces 100,938 of 100,980 stored configuration/timestamp labels; 42 labels differ across 42 timestamps. This discrepancy is saved in `clean_baseline_reproduction.csv`. Dose effects compare each faulted fit to the matching local clean fit so that those saved-baseline mismatches do not inflate fault changes. At the target timestamp, local votes rise from 0 to 6, 9, 11, and 12 across the four magnitudes. These are model votes on synthetic test injections, not probabilities or real sensor-fault accuracy.

## Remaining work

1. Diagnose saved/local model prediction parity (software versions, model matrix reproduction, estimator details) before using deltas for research conclusions.
2. Extend the campaign to other variable-specific point faults and segment-safe temporal faults; add event-level and affected-window assertions.
3. Obtain the actual neighbor and raw primary series as read-back artifacts. Do not fetch automatically. Complete Phase 02 provenance from those files and retrieval metadata.
4. Expand evidence integration to produce the requested E1–E4 evidence states and full explanations from actual source tables. Current classifier changes are rule-level scaffolding only.
5. Implement ablation and robustness only after evidence inputs and synthetic truth labels are wired end-to-end.
6. Run the full tests, package syntax checks, and controlled campaign after all future edits. Do not claim a phase is verified until execution outputs and review exist.
7. In Colab, upload this folder, verify the four manifest hashes before running, and use the explicit no-download workflow. There is no need to execute any Meteostat retrieval for the saved-data synthetic campaign.

Phase 02 scaffolding is available at PHASE02_PROVENANCE_REPORT.md and outputs/station_provenance/station_manifest.json. It does not replace retrieval/read-back verification.

Runtime and results: Python 3.12.9, pandas 3.0.2, NumPy 2.4.4, scikit-learn 1.8.0. The campaign found 0/6/9/11/12 target votes for clean/+2/+5/+10/+15 C. Fault-vs-local-clean changes were 10/15/20/21 configuration/timestamp predictions. Each experiment caused one changed timestamp outside the synthetic target label, but zero changed predictions beyond the computed 7-timestamp causal feature window. The output calls these outside-label changes false alarms only relative to the exact synthetic labels; they do not denote observed faults.

## WeatherGuard AI application

Start from the project root with `python -m pip install -r requirements.txt` followed by `streamlit run app.py`. The app exposes Command Center, Research Studio, Investigation Studio, Experiment Lab, and Model Evaluation. The included dataset and saved predictions are read-only until a user explicitly starts a local model run or synthetic experiment. The local refit parity discrepancy (42/100,980) is shown in the app. Neighbor raw-data provenance is unavailable, so investigation remains conservative. See `ARCHITECTURE.md` and `NEXT_STAGE_IMPLEMENTATION_PLAN.md`.

The final expanded tests report **35 passed, 0 failed**, including Streamlit AppTest across all five workspaces. The sandbox denied local socket access, so there is no real browser screenshot or external HTTP health-check evidence. Fitted model execution and the UI-triggered campaign remain manual, potentially long-running user actions.
