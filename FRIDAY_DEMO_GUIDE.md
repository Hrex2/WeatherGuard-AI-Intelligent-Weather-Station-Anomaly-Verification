# WeatherGuard AI — Friday demonstration guide

**Target:** 7–10 minutes · **Date:** Friday, 20 November 2026  
**Run from the repository root.** This is Historical Weather Anomaly Monitoring over saved data, not a live station feed.

## Setup before class

In PowerShell:

```powershell
cd "C:\path\to\WeatherGuard-AI-Intelligent-Weather-Station-Anomaly-Verification"
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. A prepared Python environment is preferable; install dependencies and launch once before class. Do not click the optional 12-model refit. It refits all 12 configurations and is unnecessary for this demonstration.

## Rehearsed walkthrough

### 0:00–1:00 · Command Center

Show the project name and explain: “An anomaly detector can find unusual values, but unusual weather and a broken sensor can look similar. This prototype gathers evidence and can abstain when evidence is missing.” Point out the 44,879-row processed historical snapshot, its time span, saved predictions, and verified Phase 01 hash status. It is not a live feed and the station-source provenance remains incomplete.

### 1:00–2:15 · Model Evaluation

Open **Model Evaluation → Configuration comparison**. Explain the three unsupervised methods and four parameter settings per method. These 12 configurations show sensitivity to modeling choices; anomaly counts are not accuracy scores because no real fault labels are available. In **Stability**, show the saved vote distribution and the 8/12 cutoff. Say explicitly: “Eight votes is a strict two-thirds operating threshold in this analysis, not a calibrated probability or a demonstrated optimal cutoff.”

### 2:15–3:30 · Investigate a candidate

Open **Investigation Studio**. The default latest candidate is **2026-03-09 13:30 IST**, with 8/12 saved configuration votes. Show the weather values and the 12 individual predictions. The app’s default date window includes this timestamp. Explain that model agreement makes it a candidate for review, not a sensor-fault finding.

### 3:30–4:45 · E1–E4 and cautious interpretation

Walk through the evidence cards:

- **E1:** saved model vote count is available.
- **E2:** episode context is visible, but independent temporal evidence is unavailable because saved episodes were built from E1 consensus timestamps.
- **E3:** unavailable for verification; derived comparisons do not include sufficient raw series/provenance and a validated comparison rule.
- **E4:** broad screening flags can be shown; missing values alone do not count as fault evidence.

Point to the uncertain interpretation. Missing evidence is not a negative result, and agreement is not a probability.

### 4:45–6:45 · Experiment Lab

Open **Experiment Lab** and show the saved dose series before running anything. Choose **+10 °C** under “Saved dose to visualize.” The chart overlays the original historical series and an explicitly synthetic injected series at **2025-09-02 07:30 IST**. Saved target votes were 0 clean and 11 after +10 °C. The saved dose campaign reports votes 0, 6, 9, 11, and 12 for clean, +2, +5, +10, and +15 °C.

Clarify the metrics: any-model detection is true for all four injected doses; only +5 °C and above meet the 8/12 threshold. These are controlled synthetic observations, not real sensor-fault accuracy. The “outside” change count excludes the injected timestamp and its expected six-following-hour feature window; all saved doses report zero changes beyond that window. The historical source CSV is unchanged.

Do not run a new campaign during the short demo unless rehearsal established that the machine can tolerate model fitting time. A new run is explicit and is not needed to show these saved results.

### 6:45–8:15 · Research Studio and close

Open **Research Studio** and show the research question, method, references, findings and limitations. Close with: “The prototype demonstrates saved model stability and a controlled synthetic experiment. It does not yet distinguish real regional weather from a faulty station. Verified neighbors, provenance, and independent validation are future research steps.”

## Useful answers to keep precise

- Historical processed snapshot; not live monitoring.
- No verified real fault labels; therefore no precision/recall/F1 or real-world accuracy.
- Synthetic injection establishes controlled behavior only.
- 8/12 is a transparent heuristic threshold, not a probability.
- The local refit has a documented 42-cell mismatch with the saved grid; avoid refitting during the demonstration.

## If something goes wrong

Use [FRIDAY_BACKUP_PLAN.md](FRIDAY_BACKUP_PLAN.md). Saved tables and the recorded dose series can be explained without running any models.
