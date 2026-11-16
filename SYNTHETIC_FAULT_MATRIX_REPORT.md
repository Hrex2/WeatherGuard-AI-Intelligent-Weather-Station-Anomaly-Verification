# Synthetic Fault Matrix — Local Held-out Experiment

**Run:** `fault_matrix_02bd147f5cce`
**Status:** Executed local synthetic experiment; not real-world validation.
**Code revisions:** initial run `01f9ede`; compaction/metric labeling `f09b9cd`; injection provenance `4b85329`; E4 output generation `9caecaa`.

## Protocol

The experiment reused the manifest-verified processed observations, training matrix and held-out matrix. It fitted the existing twelve configurations once on the original training data, then evaluated eight injected held-out scenarios against predictions from that same local clean fit. Scenarios began at 2025-09-02 07:30 +05:30. The training scaler was fit on training rows only for LOF and One-Class SVM; Isolation Forest used unscaled features. Data hashes, configuration, feature order, environment, seed, exact original/injected values and timestamps are in `research_results/fault_matrix_02bd147f5cce/`.

The table reports the share of injected observation/configuration labels flagged by the models. Denominators are duration × 12 configurations. “New flags outside labels” means faulted-run flags that were not present in the same-run clean prediction at unmodified timestamps. It is not a validated false-positive count: the historical observations have no verified normal/anomaly labels, and synthetic truth labels only identify injected rows.

| Scenario | Injection | Injected labels flagged | New flags outside injected labels |
|---|---|---:|---:|
| Temperature point spike | +10 °C, 1 observation | 11/12 (91.7%) | 8 |
| Temperature point drop | −10 °C, 1 observation | 11/12 (91.7%) | 22 |
| Persistent temperature offset | +5 °C, 6 observations | 23/72 (31.9%) | 13 |
| Stuck temperature | Previous value held for 6 observations | 5/72 (6.9%) | 21 |
| Gradual temperature drift | Linear 0 to +5 °C over 6 observations | 16/72 (22.2%) | 12 |
| Missing temperature block | 3 observations | 0/36 (0%) | 4 |
| Intermittent temperature noise | Gaussian noise, σ=2 °C over 6 observations | 26/72 (36.1%) | 11 |
| Dew point / temperature inconsistency | Dew point +20 °C over 3 observations | 24/36 (66.7%) | 0 |

## Family detail

Across the single injected interval for each scenario, LOF and One-Class SVM flagged all four configuration labels for the +10 °C spike and drop. Isolation Forest flagged 3/4 in each. For the dew-point inconsistency, LOF and One-Class SVM each flagged 12/12 injected labels; Isolation Forest flagged 0/12. The missing block was not flagged by any configuration. Full family and per-configuration results are saved alongside the report.

The independent broad E4 screen changed on 11 injected timestamp-variable rows: three missing-temperature rows, one point-drop, two stuck-temperature, two noise, and three dew-point/temperature-inconsistency rows. The latter were cross-variable screening flags; they do not establish hardware failure. Baseline and faulted flags are both retained in `physical_screening_results.csv`.

## Interpretation limits

- Each scenario was tested once at one selected historical interval. Results do not estimate performance across weather regimes or stations.
- The 12 configurations are correlated model variants; configuration counts are not independent trials.
- The model was locally refitted. Historical-vs-local parity differs at 42 Isolation Forest labels; within-run comparisons here use the same local clean fit.
- “Unmodified” observations are not verified normal readings. Their model flags cannot be labeled false alarms without independent truth.
- Synthetic injections do not establish field accuracy, sensor diagnosis, or generalization. E3 spatial evidence was not available or used.

## Files

- `run_metadata.json` — reproducibility, hashes, package versions, code revisions and limitations.
- `injection_registry.csv` — exact intervals, original/injected values, labels and seeds.
- `physical_screening_results.csv` — broad physical screens before and after each injection.
- `configuration_metrics.csv` — all model-configuration metrics with neutral unmodified-row terminology.
- `family_scenario_summary.csv` — family-level injected-label counts and changes.
- `scenario_summary.csv` — aggregate scenario results.
- `changed_and_injected_predictions.csv` — only injected timestamps and changed configuration/timestamp predictions; the redundant full grid is not duplicated.
