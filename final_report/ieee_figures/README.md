# WeatherGuard AI paper figures

These figures accompany `WeatherGuard_AI_Complete_IEEE_Research_Paper.docx` and its PDF. Empirical plots were generated from saved repository artifacts using `final_report/create_ieee_figures.py`; the two framework diagrams are schematic summaries of the audited design and evidence policy. No model was run and no weather observations were downloaded to create these figures.

| File | Paper figure | Data/source | Interpretation limit |
|---|---:|---|---|
| `fig01_system_architecture.png` | Fig. 1 | Audited application, model, and evidence-service architecture | Schematic; not performance evidence. E3 remains outside classifier voting. |
| `fig02_e1_e4_framework.png` | Fig. 2 | E1–E4 definitions and Phase 8 evidence policy | Schematic; spatial/event validation is insufficient. |
| `fig03_dataset_coverage_missingness.png` | Fig. 3 | `verified_phase01/model_df.csv` | Processed historical series, not raw-provider coverage. |
| `fig04_station_distribution_coverage.png` | Fig. 4 | `outputs/phase06_controlled_e3_validation/station_zone_assignment.csv`; Phase 4/6 source-level station CSVs | Record coordinates are not surveyed sensor sites; row counts do not establish independent instruments. |
| `fig05_model_family_candidate_counts.png` | Fig. 5 | `research_results/e1_family_comparison.csv` | Saved candidate counts; families overlap; no independent truth labels. |
| `fig06_e1_e2_sensitivity.png` | Fig. 6 | `research_results/e1_threshold_sensitivity.csv`; `research_results/e2_candidate_sensitivity.csv` | E1 thresholds are sensitivity settings; E2 status frequencies are not accuracy. |
| `fig07_monthly_candidate_distribution.png` | Fig. 7 | `phase03_model_revalidation/candidate_observations_8of12.csv` | Candidate frequency is not anomaly prevalence or fault prevalence. |
| `fig09_synthetic_e1_e4_response.png` | Fig. 8 | `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/synthetic_baseline_response_summary.csv` | Five selected contexts/eight injected scenarios; fractions are not field recall. |
| `fig08_e3_pair_coverage_heatmap.png` | Fig. 9 | `outputs/phase06_controlled_e3_validation/variable_comparison_results.csv` filtered to `ALL_SERIES`, exact UTC (`tolerance_minutes=0`) | Cell counts are valid-value pairs, not common-index totals; none passes the strict independent-lineage gate. |
| `fig10_event_reference_status.png` | Fig. 10 | Phase 11 event/reference outputs under `outputs/phase11_original_observations_event_adjudication/` | Eight candidate events; none independently adjudicated; outcome is `INSUFFICIENT_INDEPENDENT_DATA`. |

The PNG names retain the generation order; paper numbering reflects the order in which figures appear in the manuscript.

## Unresolved research gaps

- The legacy Meteostat 1.7.6 retrieval that reported 6,024 rows per station has no matching saved raw export and used defaults that enabled model data. It cannot be treated as a direct-observation dataset or reconciled definitively with the later source-stratified exports.
- VILD0 station-record identity is associated with Ludhiana Airport, but exact sensor location, instrument, exposure, and site history are not verified. No VILD0–WMO 42099 alias is confirmed.
- Cross-source fingerprints indicate likely mirrored or repackaged records; independent sensor/provider lineage has not passed the E3 eligibility gate.
- The eight event candidates have no provider-ID-confirmed original-observation linkage and no independent fault/clean adjudication. E3 is descriptive only; the event validation outcome is `INSUFFICIENT_INDEPENDENT_DATA`.
- Provisional distance zones (0–10, 10–50, 50–100, 100–250, and >250 km) are not validated scientific thresholds; zones B, D, and E have no comparison observations in the current investigation.
- The saved prediction parity discrepancy remains 42 of 100,980 cells, all associated with Isolation Forest; the cause remains unresolved.
- Local `outputs/` research artifacts are ignored by Git and are not all present in a clean clone. Figure regeneration requires the audited local artifacts listed above.

No figure should be interpreted as establishing fault-detection accuracy, field performance, or validated E3 corroboration.
