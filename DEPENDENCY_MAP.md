# Canonical Dependency Map — audited

```text
Explicitly configured Pipeline B source / explicit retrieval call
                         |
                         v
Raw schema, timezone, ordering, duplicate and cadence checks
                         |
                         v
Timestamp-gap segmentation (> configured gap starts a new segment)
                         |
                         v
Causal features: previous-row change; strict exact-hour change; shifted prior-6-observation mean
                         |
                         v
Chronological cutoff -> remove engineered warm-up rows -> train-only imputation/scaler
                         |
                +--------+-------------------+
                |                            |
                v                            v
12-config model API                 Exact-time neighbor availability helpers
(common timestamp set enforced)     (not a complete Phase 02 audit)
                |                            |
                v                            v
E1 stability -> E2 segment/gap episodes -> E3 spatial comparison -> E4 broad quality flags
                                                   |
                                                   v
Abstaining rule scaffold: regional support / station-specific suspicion / uncertain
```

## Module roles and limits

- `validation.py`: schema, order, duplicate, cadence validation.
- `features.py`: segment construction, previous-row temperature change, exact-hour change, shifted previous-six-observation mean and month-cycle features.
- `preprocessing.py`: chronological split, training-only medians and optional train-fitted scaler.
- `audit.py`: explicit-input Phase 01 audit with parity, exact row reasons, precipitation and split value checks, duplicates, physical screening, lag-1 and monthly descriptions. Synthetic tested; real execution pending.
- `retrieval.py`: explicit Meteostat observation-only call with version/API metadata. It is not the absent full Phase 02 coverage audit.
- `models.py`: 12 historical configurations and strict complete timestamp-aligned prediction/stability summaries. Unequal/missing test rows raise; no NA-to-normal conversion.
- `temporal.py`: segment/gap-aware episode construction and gap sensitivity.
- `experiments.py`: month/hour/minute/length matched exact-hour controls and block resampling. The inferential method is exploratory; assumptions and block lengths require sensitivity review and sufficient independent episodes.
- `faults.py`: held-out-only injection after a required calibration boundary, contiguous-interval check, clean/fault feature recomputation and synthetic-label metrics. Earlier injected values can affect later causal history, but never enter their own shifted reference.
- `spatial.py`: exact-time coverage categories and comparison against a caller-declared tolerance; no interpolation or distance model.
- `quality.py`: explicit missing, nonnumeric, infinite, below/above screening and cross-variable inconsistency flags; broad screening only, not sensor-fault labels.
- `evidence.py`: three outcome scaffold. Incomplete/conflicting inputs remain uncertain; thresholds have not been empirically calibrated.

Model votes require every configuration to cover identical test timestamps. Fault labels/metrics apply only to synthetic injections. Missing spatial evidence is unavailable, not disagreement.
