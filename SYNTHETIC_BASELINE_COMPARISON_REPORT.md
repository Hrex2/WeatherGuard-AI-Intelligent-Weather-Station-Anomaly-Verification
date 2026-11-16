# Synthetic Baseline and Setting Comparison — 2026-11-16

## Scope

This comparison reuses campaign `fault_matrix_multicontext_46ae5d119d`; it does not refit the 12 existing models or repeat the injections. The experimental unit is a context × scenario × synthetically labelled timestamp. The 160 injected timestamp units were evaluated with individual family votes, E1 consensus thresholds, the existing direct-variable E4 rule, and E2 temporal settings. E2 rows reuse the same events under repeated window/mode/cutoff settings and are not independent observations.

Code revision: `8d4deaf047fe25d76654590894e10e7b55f004dd`. The machine-readable manifest and three output tables are in `research_results/fault_matrix_multicontext_46ae5d119d/`. Dataset hashes are inherited from and checked against the multi-context campaign manifest.

## E1 consensus threshold response

Fractions below are the mean of injected timestamp flags within each fault scenario, across the five selected contexts. They describe response to known synthetic shifts only.

| Scenario | 4/12 | 6/12 | 8/12 | 10/12 | 12/12 |
|---|---:|---:|---:|---:|---:|
| Point spike | 1.000 | 1.000 | 1.000 | 0.600 | 0.400 |
| Point drop | 1.000 | 1.000 | 1.000 | 0.600 | 0.000 |
| Dew-point inconsistency | 1.000 | 1.000 | 1.000 | 0.200 | 0.000 |
| Persistent offset | 0.500 | 0.133 | 0.067 | 0.067 | 0.033 |
| Intermittent noise | 0.233 | 0.100 | 0.067 | 0.000 | 0.000 |
| Missing block | 0.400 | 0.000 | 0.000 | 0.000 | 0.000 |
| Gradual drift | 0.033 | 0.000 | 0.000 | 0.000 | 0.000 |
| Stuck sensor | 0.200 | 0.000 | 0.000 | 0.000 | 0.000 |

Point faults and the dew-point perturbation were consistently detected at the 8/12 threshold in these contexts, while gradual drift, stuck runs, and missing blocks were not. Raising the threshold reduced or preserved the response fraction; it did not improve a validated metric because no real fault outcomes or verified clean negative sample exists.

## Model-family and E4 comparisons

Across scenarios, LOF and One-Class SVM each flagged all injected point spike, point drop and dew-point-inconsistency timestamp labels in the saved shared fit. Their responses to persistent offset, noise, stuck, drift and missing blocks varied substantially by fault and context. Isolation Forest generally had lower injected-label response fractions for those conditions. This is a descriptive comparison of the existing parameterizations; it does not show that one family is superior overall.

The existing broad E4 rule flagged the directly modified variable on all missing-block labels and on none of the other direct-variable injection labels. That behavior reflects the current E4 rule set: missing/non-finite and very broad range/cross-variable checks. It does not mean the other synthetic shifts were physically acceptable, and the broad rules were not calibrated against station specifications.

## E2 sensitivity

Across all 145 available injected timestamp × setting rows per setting (15 missing-temperature rows are `UNAVAILABLE`), the real-time `SUPPORTING` fraction ranged from 0.331 to 0.545 as window and cutoff changed. At a six-hour window it was 0.434, 0.400 and 0.359 for cutoffs 2.5, 3.5 and 4.5. Retrospective fractions ranged from 0.228 to 0.434; at six hours they were 0.297, 0.276 and 0.262. `SUPPORTING` means a temporal departure/pattern only. Matched-control screens also returned support, and no outcomes identify sensor faults.

These setting changes materially affect output coverage, so the chosen 3.5/six-hour setting should remain explicitly exploratory. The same injections are repeated over settings, and the selected contexts are not a random sample of station operation.

## Available-evidence coverage ablation

A coverage-only ablation was computed over the 160 known injection timestamp units. For each E2 setting, the available-only combinations E1, E1+E2, E1+E4, and E1+E2+E4 had coverage of 160/160 (100%), 145/160 (90.6%), 160/160 (100%), and 145/160 (90.6%), respectively. The 15 unavailable E2 units are the injected missing-temperature readings. E1+E3 and E1+E2+E3+E4 were blocked at 0/160 because verified station corroboration is absent.

This is strictly a measurement-availability comparison. It does not evaluate whether removing or adding an evidence group improves an interpretation, because E2 departure and E4 screening statuses do not alone define event/fault truth, E3 is absent, and no adjudicated outcomes exist. The saved `evidence_coverage_ablation.csv` retains unit-level detail and `evidence_coverage_ablation_summary.csv` provides setting-level counts.

## Limitations

- No real-world fault labels or independently adjudicated normal observations are available; no field accuracy, specificity or false-positive rate is estimated.
- The synthetic scenarios directly perturb temperature or dew point, not all six weather variables.
- The same 12 configurations and their shared fit are reused across five contexts; model-fit uncertainty is not measured.
- E3 spatial evidence is unavailable. E1/E2/E4 response comparisons do not validate integrated three-outcome decisions.
- Results are fixed to the selected historical dataset and the declared synthetic magnitudes/durations.
