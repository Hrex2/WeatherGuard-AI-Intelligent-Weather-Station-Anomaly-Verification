# WeatherGuard E1–E4 Demonstration

## Start the application

From the project root, run:

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit and leave the main navigation on **Home**.

## Walkthrough

1. Use the historical date range and bottom timeline to select an observation. Try **Reset**, **Next**, **Play**, and **Pause**.
2. Select **VILD0** in the station detail panel. Review its saved weather measurements and the expanded **View E1–E4 assessment** panel.
3. Expand the component details to inspect exact baseline prediction rows, temporal screen output, physical flags, and any available descriptive spatial rows.
4. Select **42099** or **42101** to see neighbor source rows where an exact timestamp is present. The app marks the primary model/temporal/physical screens as not applicable to those station exports; it does not treat them as independent E3 validation.
5. Point out the final triage label. A baseline 8/12 candidate appears as **Suspicious** for review. Other cases remain **Insufficient evidence**. The page explicitly does not label a sensor fault.

## What to say about E3

E3 can show existing time-aligned exploratory comparison rows as descriptive context. It remains decision-ineligible because independent station lineage and adjudicated event evidence are insufficient. Empty E3 results mean missing evidence, not normal regional conditions.

## Demonstration boundaries

The baseline is loaded from saved Phase 03 predictions; the historical model is not refit. The E2 screen runs in prior-only real-time mode. E4 applies the repository's broad physical-quality rules. The integrated output is not an accuracy claim or validated combined classifier. The map uses station-record coordinates, not verified sensor locations.
