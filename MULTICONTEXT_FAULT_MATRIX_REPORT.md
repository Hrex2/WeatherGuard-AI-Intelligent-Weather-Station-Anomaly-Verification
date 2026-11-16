# Five-Context Synthetic Fault Matrix — 2026-11-16

## Status and objective

**Executed local synthetic experiment; exploratory detector-behavior study only.** The campaign reused the existing eight fault definitions and asked whether their model responses vary with background temperature and six-hour variability. It does not estimate field accuracy or identify real sensor failures.

## Selection and model protocol

Five contexts were selected before examining detector outputs, from the original held-out test split. Each has 24 continuous hourly observations before injection and a continuous six-observation interval, satisfies the existing eight-scenario preflight, and is separated from every other selected context by at least 14 days. The selection used the 24-hour temperature median and prior six-hour temperature standard deviation. Thresholds were Q1/Q3 = 15.35/28.60 °C for temperature and 0.770/2.216 °C for six-hour standard deviation.

| Context | Local timestamp | Quarter | 24h median temp (°C) | Prior 6h SD (°C) |
|---|---|---:|---:|---:|
| TEMP_HIGH_VAR_LOW | 2025-04-09 17:30 +05:30 | 2 | 29.75 | 0.547 |
| TEMP_HIGH_VAR_HIGH | 2025-05-27 12:30 +05:30 | 2 | 30.10 | 3.041 |
| TEMP_MIDLEVEL_MIDVAR | 2025-09-04 22:30 +05:30 | 3 | 25.40 | 1.451 |
| TEMP_LOW_VAR_HIGH | 2025-11-30 20:30 +05:30 | 4 | 12.80 | 3.103 |
| TEMP_LOW_VAR_LOW | 2026-02-06 09:30 +05:30 | 1 | 11.80 | 0.588 |

The existing twelve configurations were fitted once on the unchanged training matrix. The same fitted objects and clean held-out predictions were reused for all 40 context/scenario combinations. Features were recomputed after injection; the saved historical predictions and original single-context outputs were not changed. Run ID: `fault_matrix_multicontext_46ae5d119d`. Code revision: `c55b90a`.

## Results

The values below are fractions of **configuration × synthetically modified timestamp** decisions flagged, aggregated over each context. They are synthetic-label response fractions, not estimates of real-world recall. Unmodified held-out rows are not independently verified clean.

| Existing scenario | Variable / fault | Mean across contexts | Range across contexts |
|---|---|---:|---:|
| TEMP_POINT_SPIKE | Temp +10 °C, one timestamp | 0.850 | 0.667–1.000 |
| TEMP_POINT_DROP | Temp −10 °C, one timestamp | 0.800 | 0.667–0.917 |
| TEMP_PERSISTENT_OFFSET | Temp +5 °C, six observations | 0.231 | 0.042–0.361 |
| TEMP_STUCK_SENSOR | Temp held constant, six observations | 0.081 | 0.000–0.319 |
| TEMP_GRADUAL_DRIFT | Temp drift 0→+5 °C, six observations | 0.019 | 0.000–0.056 |
| TEMP_MISSING_BLOCK | Temp missing, three observations | 0.167 | 0.000–0.333 |
| TEMP_INTERMITTENT_NOISE | Temp Gaussian noise, σ=2 °C, six observations | 0.164 | 0.000–0.292 |
| DEWPOINT_TEMP_INCONSISTENCY | Dew point +20 °C, three observations | 0.717 | 0.667–0.806 |

Responses differed by model family. For point drops, LOF and One-Class SVM each flagged all injected labels in every context under this local fit, while Isolation Forest averaged 0.40 across contexts. For point spikes, LOF and SVM also averaged 1.00; Isolation Forest ranged from 0 to 1.00 by context. For missing-temperature blocks, mean family fractions were 0.00 (Isolation Forest), 0.50 (LOF), and 0.00 (One-Class SVM). These results describe this one shared fitted model protocol and these selected synthetic conditions.

Across all context/scenario/configuration comparisons, no prediction-label changes occurred outside the declared expected feature-propagation window: through six following hourly readings for temperature injections and the injection interval for dew-point-only changes. Per-configuration changed-prediction and detection-delay counts remain in each context run's `configuration_metrics.csv`. The same-run unmodified observation flag rate ranged about 3.93%–3.97%; it is a comparator statistic, not a validated real-world false-positive rate.

Broad E4 screening flags changed on **36 injected timestamp-variable rows** across contexts: 15 dropout, 4 noise, 3 point-drop, 13 positive-offset (including dew point), and 1 stuck. No changed E4 rows were recorded for drift or point spikes. These are rule-response counts, not hardware diagnoses or validation of meteorological/operational bounds.

## Interpretation and limitations

The main observed pattern is context sensitivity: persistent offsets, stuck runs, drift, missing blocks, noise, and even point faults produced different synthetic-label response fractions across backgrounds. The model-family responses also differed. These are not population estimates. The same fitted models were shared across contexts, the station identity/provenance remains unverified, and neither held-out unmodified observations nor injected observations provide real-field fault adjudication. The 42 Isolation Forest historical parity differences remain unexplained; this experiment compares each faulted series only with its same-fit clean comparator.

## Traceability

- Campaign manifest and preselected contexts: `research_results/fault_matrix_multicontext_46ae5d119d/campaign_manifest.json`, `context_selection.csv`.
- Five per-context run directories are listed in the campaign manifest; each contains exact injection values, source hashes, model/family metrics, E4 screens and run metadata.
- Aggregate scenario/family results: `context_scenario_summary.csv`, `context_family_summary.csv`.
- Reproduction: `python scripts/run_multicontext_fault_matrix.py` (fits once; writes a new unique campaign directory).

Independent E2 evaluation against these injections and matched unmodified windows is tracked separately and remains pending.
