# Friday classroom backup plan

## Primary launch

1. Use the tested project checkout and a Python environment with `requirements.txt` installed.
2. From the repository root run `python -m streamlit run app.py`.
3. Open the local address printed by Streamlit.
4. Navigate through Command Center → Model Evaluation → Investigation Studio → Experiment Lab → Research Studio.
5. Avoid the optional full 12-model refit. The demonstration uses saved outputs.

The current environment passed Streamlit AppTest for all five workspaces. Direct browser/HTTP health validation was blocked by localhost socket policy, so do a real launch rehearsal on the classroom machine before Friday.

## If launch fails

1. Confirm PowerShell is in the repository root (the folder containing `app.py`).
2. Check `python --version`; use the Python version selected during rehearsal.
3. Run `python -m pip install -r requirements.txt` while internet/package access is available.
4. Retry `python -m streamlit run app.py`.
5. If the error says an artifact is missing or its SHA-256 differs, do not edit or replace the historical file during class. Use the prepared recording/verified outputs and investigate the checkout after the presentation.
6. If the local port is unavailable, stop the existing Streamlit process and rerun; allow Streamlit to choose/report another port if needed.

## Capture actual screenshots during rehearsal

Capture these views from the real running application on the presentation computer:

1. Command Center showing dataset period and integrity status.
2. Model Evaluation configuration comparison and vote distribution.
3. Investigation Studio with candidate `2026-03-09 13:30 IST` and its E1–E4 availability states.
4. Experiment Lab with the saved `+10 °C` baseline/injected overlay and votes.
5. Research Studio methodology and limitations.

Store them in a clearly named local folder (for example `demo_assets/`). Check that timestamps, labels, and text are readable at presentation resolution. Do not use fabricated or manually altered screenshots. No screenshot is included with this preparation because this managed run could not reach the local Streamlit server over HTTP.

## Backup recording and saved artifacts

During rehearsal, record the same 7–10 minute walkthrough as a backup video, including screen and spoken explanation. Keep the recording local and test playback before class. If the app will not launch, explain using the actual saved repository artifacts:

- `phase03_model_revalidation/model_predictions.csv`, `stability_results_verified.csv`, `configuration_results.csv`, and `episode_profiles_1h.csv`.
- `outputs/synthetic_fault_campaign/experiment_summary.csv`, `observation_level_results.csv`, `event_level_results.csv`, `feature_propagation.csv`, and the campaign manifest.
- The tested UI screenshots and the 11-slide outline.

Present the synthetic dose response as a controlled demonstration only. It is not real-world sensor fault accuracy. If asked about missing spatial evidence or the 42-cell refit discrepancy, explain those limitations directly.
