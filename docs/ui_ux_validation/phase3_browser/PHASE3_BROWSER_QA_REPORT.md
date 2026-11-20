# Phase 3 Browser QA and UI Refinement

Date: 2026-11-20

## Scope and setup

Browser checks used Microsoft Edge through Playwright against the locally running Streamlit app at `http://localhost:8768`. Playwright was installed into a temporary directory; no browser automation dependency was added to the project. The existing test suite was run before and after the UI changes.

The seven destinations checked were Home, Weather Data, Investigate a Reading, Model Evaluation, Experiment Lab, Research, and About. Each was visited at 1440×900, 1366×768, 768×1024, and 390×844 (28 workspace/viewport checks). Seventeen screenshots are stored in this directory: one desktop image per destination and laptop/tablet/mobile images for Home, Weather Data, and Investigate.

## Browser-verified behavior

- All seven navigation choices remained available and the selected radio state matched the opened workspace.
- No document or body horizontal overflow was found in the 28 viewport checks.
- At 390 px, Streamlit's `auto` sidebar state opens the dashboard with the analytics sidebar collapsed; the drawer toggle remains available.
- Weather measurement selection changed from air temperature to dew point and the chart remained present.
- The Weather Data date range changed from 2025-03-09–2026-03-09 to 2026-02-01–2026-02-05. A Plotly hover layer appeared on pointer hover.
- Investigation timestamp selection changed from 2026-03-09 23:30 to 22:30 (Asia/Kolkata) and the selected timestamp readout updated.
- Experiment Lab's E3 page displayed its decision-ineligible state for insufficient independent provider lineage and event adjudication.
- Model Evaluation opened Results without triggering the optional 12-configuration refit.
- Keyboard focus styling computed to a solid 3 px outline. The reduced-motion media rule was present.
- The Home map's Carto basemap and station markers rendered after the initial load settled. Clicking the Patiala marker (station 42101) updated the Station details selector to 42101.
- Timeline controls were regression-checked with AppTest, including 2× playback speed, next, play, and pause. The playback timer now runs only while playback is active, avoiding continuous idle redraws.

## Refinements made

- Changed the initial sidebar behavior from forced-expanded to responsive `auto`; this fixes the phone-width overlay observed in a fresh mobile session.
- Improved widget label contrast, dark-themed expander headers, and button styling after computed-color and screenshot inspection.
- Changed Home's historical coverage KPI to a concise year span and its validation status to “Prototype”; exact dates remain available in the metric help text.
- Aligned the Model Evaluation page heading with its navigation label.
- Made the Home fragment playback timer conditional on active playback and preserved the selected speed across play/pause reruns.

## Verification and limitations

- Full suite: **170 passed, 0 failed, 0 skipped**. The 168-test baseline remains passing; two regression tests cover idle/active timeline refresh policy.
- Python compilation, targeted `git diff --check`, and live HTTP/health checks pass. The repository-wide staged diff check still reports trailing whitespace in the pre-existing staged `research_results/phase14_ieee_paper_revision/qa/final_text.txt`; it was left unchanged.
- The browser recorded one transient 404 for a Streamlit in-memory PNG while navigating between workspaces. No failed network requests or JavaScript page exceptions were recorded. The image source was not identified conclusively, so this remains an unresolved browser-only warning.
- Map tiles and marker rendering required a longer initial wait; the focused canvas capture and marker click were verified after settling. The first-pass desktop screenshots can capture the map before its asynchronous load completes.
- A genuinely empty date range was not reproduced with the supplied bounded historical time index. Empty-state handling remains covered by existing code/tests rather than this browser session.
- Contrast was reviewed visually and with computed colors for representative text; no formal WCAG scanner or full screen-reader audit was run.

## Screenshot index

- `Home_desktop.png`, `Home_laptop.png`, `Home_tablet.png`, `Home_mobile.png`
- `Weather_Data_desktop.png`, `Weather_Data_laptop.png`, `Weather_Data_tablet.png`, `Weather_Data_mobile.png`
- `Investigate_a_Reading_desktop.png`, `Investigate_a_Reading_laptop.png`, `Investigate_a_Reading_tablet.png`, `Investigate_a_Reading_mobile.png`
- `Model_Evaluation_desktop.png`, `Experiment_Lab_desktop.png`, `Research_desktop.png`, `About_desktop.png`
- `home_map_canvas.png` shows the loaded map and station markers. `browser_qa_results.json` contains workspace/viewport measurements and interaction assertions.
- `interaction_qa_results.json` contains the focused date-range and chart-hover results.

## Run locally

From the repository root:

```powershell
python -m streamlit run app.py
```



