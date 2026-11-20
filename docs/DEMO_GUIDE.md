# WeatherGuard AI Classroom Demo Guide

## Goal and setup

This short demonstration shows how the interface helps inspect an unusual historical reading while keeping uncertainty visible. It does not demonstrate fault diagnosis. Repeat the principle: **ANOMALY ≠ FAULT**.

Before class, install `requirements.txt` and start the app from the repository root:

```powershell
python -m streamlit run app.py
```

Confirm that the bundled snapshots load. Use the existing saved results; do not trigger a new model refit during the walkthrough. Allow about 6 minutes, plus questions.

## Walkthrough

| Time | Action | Explain |
| --- | --- | --- |
| 0:00–0:40 | Open **Home** and identify the historical date range and dashboard | The app explores a local historical snapshot. Integrity checks do not independently prove upstream provenance, and the app is not a live station monitor. |
| 0:40–1:35 | Adjust the date range; select a station marker and inspect its detail popup | The map and measurement context help orient the reading. A marker or candidate style is not a fault alert. |
| 1:35–2:15 | Move the timeline slider; use next, previous, pause and reset | The timeline synchronizes the selected historical time across views. |
| 2:15–3:20 | Open **Investigate a Reading**, select a reading and review model signals and time context | E1 and E2 are different views. Show the past-only and retrospective distinction if useful; retrospective context may use later readings. |
| 3:20–4:15 | Expand E1–E4 and point out each status separately | E3 is descriptive-only/unavailable under current evidence rules and has zero decision-eligible independent coverage. E4 is a broad physical screen. Missing evidence is not agreement. |
| 4:15–5:15 | Open **Experiment Lab** → **Synthetic Campaigns** and show a saved campaign result/report | Injected scenarios are controlled software experiments, not real station events or field-performance metrics. Do not claim they estimate accuracy or fault detection. |
| 5:15–6:00 | Open **Research** or **About**, then recap limits | The test suite and saved analyses support software/research inspection, not independently adjudicated real-world performance. |

## Suggested closing

“WeatherGuard AI organizes evidence around unusual readings. Its output supports investigation, not a declaration of sensor failure. Independent station lineage, decision-eligible spatial evidence and adjudicated real fault events are still needed before real-world performance can be claimed.”

## Avoid during the demo

- Do not call a candidate a confirmed fault or the absence of a flag proof of normal operation.
- Do not call E1 agreement independent confirmation or a calibrated probability.
- Do not present synthetic injections as observations from actual stations.
- Do not report accuracy, precision, recall, F1 or specificity without independent labels.
- Do not say a local refit exactly reproduces saved predictions; 42 of 100,980 cells currently differ for an unresolved reason.
- Do not start the optional Model Evaluation refit unless explicitly demonstrating a new experiment and explaining that it does not replace the saved record.
