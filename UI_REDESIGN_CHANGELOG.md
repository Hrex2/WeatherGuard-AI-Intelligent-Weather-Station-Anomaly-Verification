# UI redesign changelog

## 2026-11-16 — plain-language navigation and model education

- Replaced the five technical-first workspace labels with Home, Weather Data, Investigate a Reading, Model Evaluation, Experiment Lab, and Research.
- Reworked Home to introduce the research problem plainly and foreground historical coverage, model configuration count, consensus candidates, and validation status.
- Added unit-labeled, date-filtered weather charts and reused the selected observation marker across data and investigation views.
- Turned investigation into a five-step guided layout. Kept full model configuration predictions, screening flags and exploratory spatial tables in technical expanders.
- Restructured Model Evaluation into exactly two primary tabs: Experiments & Results and How the Models Work.
- Added actual model comparison, vote distribution, family vote distributions, verified Jaccard heatmap, synthetic dose/consensus outcomes, feature-window changes, sensitivity chart, and honest not-evaluated ablation status.
- Added model profile selection with explanatory text, conceptual labeled diagrams, train/test timeline, actual feature names/grouping, preprocessing, parameter comparison, estimator defaults, saved counts and limitations.
- Added `services/model_metadata.py`, `research_content/model_profiles.json`, and a shared estimator constructor used by research fitting, synthetic campaign fitting and model education.
- Kept expensive training behind an explicit advanced control. Saved predictions remain separate from new local refits.
- Updated README and Friday demo guide terminology and sequence.

## Scientific safeguards retained

No anomaly scores, model accuracy, probabilities, feature importance, station metadata, or ablation results were invented. E2 and E3 remain unavailable as independent evidence, missing values alone do not support fault interpretation, and the overall event interpretation stays uncertain.
