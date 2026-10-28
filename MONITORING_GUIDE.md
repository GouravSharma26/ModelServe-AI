# Monitoring Guide

## Release A signals
- Request count over time.
- Successful and failed predictions.
- Error rate.
- Latency summaries with a documented percentile calculation.
- Prediction-label distribution.
- Score/probability distribution, if applicable.
- Active model version.
- Database persistence status.
- Model evaluation metrics from the recorded test evaluation.

All dashboard data must be sourced from real API metrics or persisted database records.

## Release B drift
### Reference window
Define the reference dataset/window, preprocessing, binning, and refresh policy. Store the reference metadata and fingerprint.

### PSI
For each selected numeric feature or model score:
1. Define stable bins from the reference distribution.
2. Calculate reference and current proportions per bin.
3. Apply a small documented epsilon to avoid logarithm of zero.
4. Calculate PSI using the documented formula.
5. Record window size, missingness, score, threshold, and method version.

Document that thresholds are heuristic and feature-dependent. Test expected behavior on unchanged, mildly shifted, and strongly shifted synthetic distributions. Categorical features need a defined category mapping and an explicit unseen-category policy.

### Ground-truth evaluation
Only compute live precision, recall, F1, ROC-AUC, PR-AUC, or calibration when genuine outcome labels are available and aligned with prediction IDs/time windows. Account for delayed labels and selection bias.

## Alerting
Start with dashboard indicators and persisted reports. Add Prometheus alert rules in Release B. Define severity, threshold, duration, owner/action, and false-positive considerations. Drift alert does not mean automatic retraining or proof of model failure.

## Privacy
Do not store raw input payloads for convenience. Prefer aggregate histograms and approved non-sensitive feature summaries. Set retention limits for prediction events and logs.
