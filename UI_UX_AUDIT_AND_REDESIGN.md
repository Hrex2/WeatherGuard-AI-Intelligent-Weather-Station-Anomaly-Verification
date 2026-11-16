# UI/UX audit and redesign

## Audit baseline

Inspected baseline `d1280a6f86a5bf89fe69e127a1159e2356f3e6bf`, Streamlit `app.py`, `ui/theme.py`, `services/`, `src/weather_research/models.py`, data and prediction manifests, model results, saved synthetic experiment artifacts, and existing AppTest coverage.

The baseline had five workspace names, technical-first labels, a single Model Evaluation page with four tabs, investigation data browsing mixed with evidence review, and no reusable model profile source. Backend snapshots and saved analysis were already present and working; this redesign keeps them and changes their presentation.

## Navigation

The main navigation now contains six task-oriented destinations:

1. **Home** — what the system does, dataset coverage, model count, consensus candidates and validation status.
2. **Weather Data** — date-filtered temperature, dew point, humidity, precipitation, wind and pressure charts with units.
3. **Investigate a Reading** — five-step review of measurements, votes, E1–E4 evidence, cautious conclusion and expandable details.
4. **Model Evaluation** — exactly two primary learning sections: **Experiments & Results** and **How the Models Work**.
5. **Experiment Lab** — historical saved synthetic dose results and explicit new experiment controls.
6. **Research** — research context, methods, results, literature and limitations.

The selected timestamp is stored in Streamlit session state and highlighted in the Weather Data view. Technical terms remain available in secondary labels and expanded sections.

## Progressive disclosure and evidence language

- Main screens lead with a brief explanation and a result or action.
- Long configuration tables, full estimator defaults, prediction rows, screening flags and experiment metadata are in expanders.
- Evidence labels use direct questions: **Do the models agree? (E1)**, **Does it make sense over time? (E2)**, **Do nearby stations show something similar? (E3)**, and **Is the measurement physically reasonable? (E4)**.
- E2 remains unavailable as independent evidence because saved episodes derive from E1 consensus. E3 remains unavailable for corroboration due to insufficient verified neighbor inputs. E4 flags are screening observations, not fault labels. Missingness alone is not positive fault evidence. Overall interpretation remains uncertain.
- No model scores, feature importance, probabilities or accuracy figures are manufactured.

## Model education data flow

`services/model_metadata.py` composes education material from:

- `weather_research.models.default_model_configs()` for the four actual settings per family.
- `weather_research.models.build_estimator()` for protocol overrides.
- Installed scikit-learn estimator constructors for non-overridden defaults.
- Loaded train/test frames for counts, timestamp coverage and available columns.
- Saved configuration results for anomaly counts and rates.
- `services/model_service.FEATURE_ORDER` for the actual 11-feature order.
- `research_content/model_profiles.json` for reviewed plain-language explanations.

No fitted estimator objects are claimed to exist. Opening Model Evaluation does not fit models. The optional refit remains inside an advanced expander and only runs after an explicit button press.

## Visual system and accessibility

The dark scientific theme remains. Visualizations use actual Plotly-backed artifacts with readable labels, units, hover details and explicit historical or synthetic framing. Illustrations in the model profiles are conceptual and labeled as such. Status is also conveyed in text, not color alone. Dense details remain reachable through expanders.

## Verification

The updated AppTest suite checks all six navigation destinations, both Model Evaluation section labels, all three profile selections, profile configuration values, actual training/test counts and feature order, no automatic refit state, and existing evidence safeguards. Direct local browser rendering may remain unavailable in restricted environments; AppTest is the executable page-level check.
