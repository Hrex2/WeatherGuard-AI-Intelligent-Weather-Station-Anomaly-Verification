# Model Evaluation design

## Primary structure

Model Evaluation has two top-level sections and no third evaluation tab:

### A. Experiments & Results

1. **Compare the tested configurations** — all 12 saved algorithm/parameter combinations and actual held-out anomaly counts/rates. Counts are model outputs, not accuracy.
2. **Do the models agree?** — saved vote-count distribution, 8/12 candidate total, per-family vote distributions, and the saved verified Jaccard similarity heatmap. Agreement is not probability or correctness.
3. **Controlled temperature experiment** — only shown as verified when its manifest source hashes match the loaded Phase 01 snapshots. Displays clean/+2/+5/+10/+15 °C target votes; any-model and 8/12 criteria; expected feature-propagation window; changes beyond that window. All results are synthetic.
4. **Configuration sensitivity** — saved anomaly counts against each family’s predefined varied parameter, without claiming formal optimization.
5. **Contribution tests (ablation)** — “Not evaluated yet”; no sample metrics or chart.

### B. How the Models Work

Selectable profiles for Isolation Forest, Local Outlier Factor, and One-Class SVM provide a plain-language summary, technical explanation, use/difference, actual train/test dates and row counts, feature groups/order, scaling policy, applied parameters, saved configuration counts, installed estimator defaults, limitations, and prediction workflow. A chronological range chart distinguishes train and test periods.

The optional full local refit is nested under an advanced expander and requires an explicit button. It is not invoked by opening Model Evaluation. Archived Phase 03 predictions are distinct from any fresh local refit.

## Data and source-of-truth boundaries

`services/model_metadata.py` binds UI values to real project structures. Estimator parameter overrides are generated through `weather_research.models.build_estimator()`, the same constructor used by the standard and synthetic campaign fit paths. Defaults come from the installed scikit-learn constructors and are labeled with the installed version. Saved anomaly counts come from `configuration_results.csv`; predictions and family vote distributions come from saved Phase 03 tables; Jaccard values come from `jaccard_similarity_verified.csv`.

The feature pipeline provides 11 ordered inputs: six current weather variables, three recent-temperature features, and two month encodings. StandardScaler is fit only to training data for LOF and One-Class SVM. Isolation Forest uses unscaled input. The optional local protocol refit generates month encodings through the existing service. No saved continuous decision scores or feature importance are shown.

The preset grid is not GridSearchCV or exhaustive hyperparameter search. No fitted estimator files are present. The 8/12 cutoff is a descriptive operating threshold and has not been calibrated or established as optimal. A saved/local prediction mismatch of 42/100,980 cells remains documented.
