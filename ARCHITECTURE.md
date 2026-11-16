# WeatherGuard application architecture

## Current application slice

- `app.py`: Streamlit shell, workspace navigation, page composition, UI-only filtering and charts.
- `services/data_service.py`: read-only discovery/loading, timestamp and pair integrity checks, snapshot hashes.
- `services/model_service.py`: explicit, manual execution of the existing 12-model train/test protocol; never called at startup.
- `services/evidence_service.py`: selected-time view assembly from saved artifacts and physical screening; preserves unavailable evidence and defaults to uncertain.
- `ui/theme.py`: shared visual tokens and evidence/metric components.
- `services/model_metadata.py` and `research_content/model_profiles.json`: data-backed estimator settings, train/test facts and user-facing model explanations.
- `research_content/literature.json` and `references.bib`: literature summaries, metadata and citations.
- `src/weather_research/`: preserved scientific backend, including the previous synthetic campaign runner.

## Data modes

The default Research Dataset mode reads only the included processed Phase 01 snapshots and saved Phase 03 outputs. It makes no retrieval calls and labels saved predictions as historical. The synthetic demonstration mode runs only after an explicit button press and writes a unique run directory.

## Known integration boundaries

- Fitted scikit-learn model objects are absent; a user-triggered protocol run refits from the verified training matrix.
- Neighbor raw time series, verified coordinates, source provenance, and independent-provider metadata are absent. The UI displays derived comparisons when available and does not assign a spatial support/conflict verdict.
- Integrated three-way outcome logic is not yet validated end to end. The current observation view abstains to uncertain.
- Streamlit is 1.56 in the inspected runtime. The skill's version-matched reference discovery requires 1.57 or newer; the app uses the installed Streamlit API and was smoke-tested through AppTest.

## User-facing navigation

The six workspaces are Home, Weather Data, Investigate a Reading, Model Evaluation, Experiment Lab and Research. Model Evaluation has two main sections: Experiments & Results and How the Models Work. Its model education service uses the shared estimator factory and the same saved train/test/result artifacts shown elsewhere in the project.
