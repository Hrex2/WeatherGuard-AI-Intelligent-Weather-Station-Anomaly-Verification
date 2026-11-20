# WeatherGuard AI User Guide

## Purpose and safe interpretation

Use this research prototype to explore historical weather readings, detector behavior and separate evidence views. It does not provide live warnings or establish that a station has failed. Keep the governing distinction visible: **ANOMALY ≠ FAULT**. A candidate reading calls for investigation; missing or insufficient evidence means the system cannot resolve it.

The bundled snapshot is historical, its upstream provenance is not fully established, and it has no independently adjudicated real fault labels. The application’s local integrity checks do not independently validate source lineage. See [Reproducibility](REPRODUCIBILITY.md) before interpreting or citing results.

## Launch

From the repository root, install `requirements.txt` in your Python environment and run:

```powershell
python -m streamlit run app.py
```

Open the local address shown by Streamlit. The application loads bundled artifacts; opening a page does not train a model. If required snapshots are missing or fail their declared integrity checks, the application may not load.

## Navigation

### Home

The dashboard summarizes the selected historical time range. Use the date controls to filter the displayed period. The analytics sidebar presents measurements and candidate summaries; the map supports selecting a station marker and opening its details. The timeline slider and previous, play, pause, reset, next and speed controls keep the selected time synchronized with the historical view. A data-upload dialog is available from the dashboard.

Treat marker and candidate styling as a display of saved historical analysis, not a live sensor alert. Verify the selected timestamp and period before interpreting a chart.

### Weather Data

Explore measurements and candidate markers for a chosen date interval. Metrics and plots describe available snapshot values. An empty selection can simply mean the chosen range has no rows. The `New Data Analysis` uploader is a separate exploratory path for user-provided files; it does not replace the bundled research dataset or authenticate the upload’s provenance.

### Investigate a Reading

Filter by date interval and variable, then choose a timestamp. Review the selected value, model family/configuration signals, distribution and time-context plots, data-quality information, and the separate E1–E4 evidence panels. E2 offers real-time-style (past-only) and retrospective context modes; these modes answer different questions. The E3 panel can report descriptive-only, insufficient or unavailable evidence. That status is not agreement and must not be interpreted as an E3 validation result.

The overall interpretation is intentionally cautious. `SUSPICIOUS` means a candidate merits review; `INSUFFICIENT_EVIDENCE` means the available evidence does not support a stronger assessment. Neither is an independently adjudicated fault label.

### Model Evaluation

Browse the documented data acquisition, preprocessing, model selection, training protocol, evaluation, results and conclusion sections. Saved outputs are shown without fitting on page load. An advanced control can explicitly initiate a new 12-configuration refit. A refit may not match saved predictions exactly: the known discrepancy is 42 / 100,980 prediction cells, with cause unresolved. Do not overwrite or substitute saved outputs when reproducing the historical analysis.

### Experiment Lab

Review saved E1/E2/E3/E4 evidence analyses, contribution/ablation results, research synthesis, paper materials and synthetic campaigns. The synthetic campaign results use injected values and controlled contexts; they explain behavior under those scenarios, not field detection performance. Read the report and manifest attached to the selected result before using its figures.

### Research

Browse the paper’s overview, literature review, research gap, methods/results and references, along with available figures and downloads. The current IEEE Word/PDF files are research drafts. Confirm author metadata and verify citations before formal submission.

### About

Read project scope and limitations. This prototype is for research exploration and classroom demonstration, not operational weather-station monitoring.

## Evidence glossary

| Component | What is shown | What it does not establish |
| --- | --- | --- |
| E1 — model stability | Agreement/disagreement among configured detector outputs | Independent evidence, calibrated probability, or accuracy against fault labels |
| E2 — temporal consistency | Whether a measurement fits its selected temporal context | Sensor failure; retrospective context may include later observations |
| E3 — spatial corroboration | Descriptive neighbor comparisons when records exist | Validated independent corroboration; current decision-eligible coverage is zero |
| E4 — physical plausibility | Broad range and cross-variable screening | Calibration, sensor health, or fault diagnosis |

## Data and privacy

The bundled analysis uses local snapshot files. External station data retrieval is not performed merely by browsing the application. Uploaded files are handled by the app’s analysis path; do not upload sensitive data. For dataset row counts, feature definitions, and experiment limits, consult [Reproducibility](REPRODUCIBILITY.md).
