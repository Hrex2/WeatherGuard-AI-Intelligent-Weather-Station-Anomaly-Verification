# WeatherGuard AI UI/UX Test Report

## Automated checks

- `python -m compileall -q app.py ui tests` — passed.
- `python -m pytest -q` — **241 passed, 5 subtests passed**.
- Existing evidence-integration, E3 policy, data-integrity, upload-preprocessing, and research tests passed with the rest of the suite.
- Streamlit AppTest exercised all five main destinations and the Home data/investigation subviews. It also visited every Model, Research, and Experiments section without Streamlit exceptions.
- Timeline interaction test covered slider selection, Next, Play/Pause, selected-station changes, and marker-status language.
- Upload-mode test confirmed that existing-model inference reports unavailable when no fitted estimator is persisted, and that the explicit retraining/refitting path is separate.
- Coordinate checks validated saved station-record latitude/longitude ranges and presence of the neighbor source export; UI status checks verified that non-primary stations remain unknown and E1 candidates are explicitly not fault labels.
- Timeline slider, previous/next, play/pause, and the station detail selector were exercised through AppTest. PyDeck zoom controls were visible in the browser capture; the test harness did not synthesize a map-marker click event, so that exact browser gesture remains unautomated.

## Manual browser review

The app was launched locally and captured in headless Microsoft Edge at 1600 × 1200. Screenshots are in `docs/ui_ux_screenshots/`. The Home map and details, Model section navigation, Research reader/results, Experiments E1/E3, and About view were inspected.

The headless review confirmed the five-item navigation, dark design system, map/data context, station detail panel, section readers, Phase 12 values, and visible E3 restriction. No layout clipping was seen in the captured desktop views.

## Not run

- No upload-driven model fitting or retraining was executed. The upload form's explicit run action is available for a user-selected dataset, but training was outside this UI verification run.
- Upload schema mapping was covered by the existing service tests; the browser run did not upload a separate user CSV end to end.
- No live weather retrieval was attempted.
- No independent real-world station-fault validation is available in the repository, so it cannot be tested here.
- A mobile viewport screenshot audit was not performed.

The direct `pytest -q` console entry point initially failed collection because `services` was not on its import path. Running the repository suite as `python -m pytest -q` correctly placed the project root on the import path and completed successfully.
