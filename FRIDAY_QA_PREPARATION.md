# Friday teacher Q&A preparation

### Why unsupervised learning?

The archive does not contain verified real-observation fault labels. Unsupervised models let us explore observations that differ from the training distribution without pretending we have ground truth. This supports candidate generation, not accuracy measurement or diagnosis.

### Why Isolation Forest, LOF, and One-Class SVM?

They are three established unsupervised anomaly-detection approaches with different decision mechanisms: isolation by random partitions, local density comparison, and a one-class boundary. Comparing them shows how candidate flags depend on model family. Their use here is exploratory, not a claim that they are the best possible models.

### Why 12 configurations?

The saved protocol has four parameter settings for each of the three families, so the comparison exposes parameter sensitivity as well as family differences. These are 12 related configurations, not 12 independent experts.

### What is model consensus?

It is a count of configurations flagging the same timestamp. It is not a probability, confidence score, or independent vote from 12 unrelated models.

### Why an 8/12 threshold?

It is the saved analysis’ strict two-thirds consensus operating cutoff. It selects a conservative candidate subset (123 timestamps in the saved grid), but it has not been calibrated or proven optimal. The project should evaluate threshold sensitivity rather than call 8/12 a scientific truth.

### What are E1–E4?

E1 model stability; E2 temporal consistency; E3 spatial corroboration; E4 physical sensor-quality screening. The UI labels unavailable inputs explicitly. The complete evidence combination is not validated end to end.

### What does E2 currently demonstrate?

Saved one-hour episodes provide useful context, but their membership is built from E1 consensus timestamps. Counting that as independent temporal confirmation would double-count E1. Independent temporal evidence is therefore marked unavailable in the selected-observation evidence card.

### What is synthetic fault injection?

It copies the held-out observations, adds a controlled temperature change at a recorded timestamp, recomputes the declared features, and checks the existing model configurations. It tests controlled software behavior on a known artificial perturbation. It does not estimate real-world sensor-fault accuracy.

### Why is spatial evidence unavailable?

The repository lacks raw neighboring-station time series and verified source/coordinate provenance. Derived comparison tables alone do not establish independent corroboration, coverage, or a validated residual threshold.

### What is the difference between an anomaly and a sensor fault?

An anomaly is unusual relative to a model’s learned patterns. A sensor fault is a causal interpretation that needs other evidence, such as instrument metadata, physical checks, temporal behavior, neighboring observations, or maintenance records. An anomaly prediction alone cannot prove a fault.

### What are the current limitations?

No real fault labels or accuracy metrics; incomplete station provenance and spatial evidence; no independent E2 component yet; incomplete integrated E1–E4 rules; no ablation; and a 42/100,980 mismatch between the saved grid and a local clean refit. The data are historical, not live.

### What makes it research-oriented?

The work preserves manifests and saved outputs, checks dataset integrity, records reproducible synthetic experiment settings, compares model configurations, states evidence availability, and documents uncertainty and limits. Research orientation does not mean all hypotheses have been validated.

### Did +10 °C get detected?

At the synthetic target, 11 of 12 configurations flagged the +10 °C injection. The saved clean target had zero votes. This is a controlled result at one selected historical timestamp; it is not a general accuracy rate.

### Does every synthetic dose meet consensus?

No. +2 °C reached 6/12 and +5 °C reached 9/12; all four injected magnitudes were detected by at least one configuration. “Any model” and “8/12 consensus” are different criteria.

### What happens next?

Verify station/provider provenance and neighbor coverage, develop independent temporal evidence, validate conservative evidence rules, investigate saved/refit parity, and run planned ablations and broader synthetic campaigns.
