# Research limitations and next work

## Evidence limits

1. The analyzed weather series is a processed historical snapshot. Independent raw-data reconstruction, direct instrument provenance and row-level provider indicators are unavailable.
2. Station identity remains unresolved for VILD0 and 42099. Candidate inventories do not prove populated, comparable hourly observations; 42105 is conditional and 42101 is an alternative.
3. The inspected Meteostat METAR adapter did not cover the proposed September 2025 period: its historical horizon began on 16 November 2026 and the inspected Aviation Weather Center integration exposed a 24-hour window. The pilot did not retrieve observations.
4. There are no independently adjudicated field fault labels or independently verified clean operational labels. No real-world precision, recall, false alarm rate, calibration or operational utility can be estimated.
5. E3 spatial corroboration is not empirically evaluated. Missing neighboring evidence must remain unavailable, never interpreted as negative evidence.
6. E2 `SUPPORTING` denotes a temporal departure under a selected screen setting. Matched controls are not adjudicated clean truth, and repeated screen settings are dependent.
7. Synthetic injections cover eight selected patterns, five preselected contexts and particular variables/magnitudes. They do not establish coverage of field failure modes or representativeness of weather regimes.
8. The corrected baseline contains 160 experimental units. Its evidence ablation measures availability only, not outcome correctness or decision value.
9. Forty-two of 100,980 saved prediction cells differ in the Isolation Forest parity investigation. Missing historical estimator/scaler artifacts and fit provenance leave the cause unresolved; historical labels were retained.
10. Historical model artifacts and scaler provenance are incomplete; the notebook includes exploratory legacy material, and full Colab verification is not demonstrated.
11. The literature review is a focused narrative synthesis, not a systematic review or exhaustive search.
12. Physical bounds are broad screening limits and cross-variable checks; they do not diagnose hardware or establish local climatological validity.

## Next work, in order

1. Resolve station identifiers and instrument/provider provenance.
2. Identify and retrieve traceable historical observations with row-level source and quality metadata.
3. Validate temporal alignment, missingness, units and common coverage before any spatial comparison.
4. Independently adjudicate regional events, station faults and operationally acceptable readings.
5. Evaluate E3 on matched, time-aligned observations and characterize spatial representativeness.
6. Measure outcome-level utility for evidence combinations, including abstention, with uncertainty intervals and leakage controls.
7. Conduct broader robustness analyses across stations, seasons, variables, scenarios and acquisition sources.
8. Resolve or bound the Isolation Forest parity discrepancy and preserve estimator/scaler provenance.
9. Reassess integrated interpretation only after the independent reference set is available.
