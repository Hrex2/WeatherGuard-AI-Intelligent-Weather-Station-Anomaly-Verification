# E1–E4 Integration Verification Report

**Verification date:** 2026-11-19  
**Branch:** `feature/phase11-original-observations-event-adjudication`  
**Scope:** E1–E4 adapters, conservative integration engine, Home dashboard integration, and existing regression suite. No model retraining, data downloads, push, or merge was performed.

## Results

| Check | Result |
|---|---|
| New E1–E4 integration tests | 12 passed |
| Complete unittest discovery | 152 passed, 0 failed, 0 errors |
| Streamlit AppTest workspaces and Home evidence panel | Passed; no Streamlit exceptions |
| Live Streamlit startup | Passed; `http://localhost:8501` returned HTTP 200 |
| `git diff --check` | Passed; Git emitted only its existing LF-to-CRLF normalization notice for `ui/theme.py` |
| Read-only assessment smoke check | Passed on the latest saved VILD0 row: 7/12 baseline votes, E1 below 8/12, E2 no detected screen, E3 insufficient data, E4 no broad screen; final result `INSUFFICIENT_EVIDENCE` |

Commands run:

```powershell
python -X utf8 -m unittest tests.test_evidence_integration
python -X utf8 -m unittest discover -s tests -v
python -m streamlit run app.py --server.headless true --server.port 8501 --browser.gatherUsageStats false
```

The existing Phase 1B dry-run tests printed their expected dry-run metadata. They did not make a network request or download observations.

## Integration cases covered

- All four adapters connected to their existing calculation or saved-output source.
- E3 descriptive-only and E3 insufficient-data states.
- One and multiple unavailable components.
- Contradictory temporal evidence kept separate from the baseline.
- Invalid component schema converted to visible `ERROR`.
- Adapter execution failure isolated from other components.
- Insufficient evidence remains distinct from `NORMAL`.
- Saved baseline vote count and configuration rows are preserved.
- E3 descriptive content cannot change the final assessment.
- Response includes the component schema and explanatory dashboard fields.

## Scope of verification

The dashboard was exercised with the bundled historical dataset through Streamlit AppTest, and the server returned a successful HTTP response. Automated tests do not emulate browser mouse clicks on the PyDeck map. E3 remains unvalidated and decision-ineligible; the current integrated result is a conservative review/insufficiency assessment, not a validated combined classifier.

The latest-row smoke result is a demonstration of actual artifact wiring, not a claim that the timestamp is meteorologically normal. The E3 absence is missing evidence.
