# Model Card — ModelServe AI

> Phase 1 training was run against IBM's public source CSV on 2026-10-28. Values below are from the held-out test split and are recorded in the ignored local manifest `artifacts/telco-models/telco-churn-20261028T120929Z/manifest.json`.

## Model identity
- Model name: Telco customer churn classifier (fictional demonstration data)
- Version: `telco-churn-20261028T120929Z`
- Artifact checksum: `44142441ad133b5749452d90244c1d9f6c64bb4a51a9ca15721b927099863b99`
- Training date: 2026-10-28 UTC
- Dataset fingerprint: `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`

## Intended use
Demonstration of an end-to-end classification inference workflow using IBM's fictional telecommunications sample data. This is not a validated customer-retention decision system and must not be used to make consequential decisions about real people.

## Dataset
- Dataset/source: IBM Telco Customer Churn sample, [`Telco-Customer-Churn.csv`](https://github.com/IBM/telco-customer-churn-on-icp4d/blob/master/data/Telco-Customer-Churn.csv)
- License: Apache License 2.0 as included in the [source repository](https://github.com/IBM/telco-customer-churn-on-icp4d/blob/master/LICENSE).
- Rows: 7,043; source schema: 20 inputs plus target `Churn` (21 columns total); 19 model features after excluding `customerID`.
- Target: `Churn`, `Yes` or `No`.
- Exclusions: `customerID` is a record identifier and is not a model feature.
- Missing values: source contains blank `TotalCharges` for some records; training pipeline median-imputes numeric values based on training data only. Other required columns cannot be missing.
- Limitations: fictional sample, historical/static labels, one source population, no evidence of validity for real telco customers.

## Training methodology
- Split: stratified 60% train, 20% validation, 20% test; seed 42.
- Preprocessing: numeric median imputation and standard scaling; categorical most-frequent imputation and one-hot encoding with unknown-category handling.
- Candidates: prior dummy baseline, class-weighted logistic regression, class-weighted random forest.
- Selection: highest validation average precision, then validation F1. Test split evaluated once after candidate selection.
- Threshold: fixed 0.5; not tuned using test data.
- Leakage controls: preprocessing is fitted within each training pipeline; `customerID` excluded.
- Package versions: Python 3.12.6, NumPy 2.1.3, Pandas 2.3.2, scikit-learn 1.5.2 for the recorded run.

## Evaluation
Held-out test set, 1,409 rows:
- Precision: 0.5084
- Recall: 0.8102
- F1: 0.6247
- ROC-AUC: 0.8321
- PR-AUC (average precision): 0.6232
- Confusion matrix, true rows and predicted columns ordered `[No, Yes]`: `[[742, 293], [71, 303]]`

The generated artifact manifest and `evaluation.json` are the source of truth for a specific run. Model scores are uncalibrated probability estimates; calibration was not evaluated. These metrics describe only this fixed random split of this fictional dataset.

## Limitations and risks
- The sample does not represent a real service provider or population.
- Random stratification does not establish generalization to future cohorts or another operator.
- Discrimination, fairness, calibration, and operational intervention effects have not been assessed.
- Drift is not proof of accuracy decline; live performance evaluation requires genuine aligned labels.

## Version history
| Version | Date | Change | Evaluation evidence | Status |
|---|---|---|---|---|
| `telco-churn-20261028T120929Z` | 2026-10-28 | Initial fixed-split training run; logistic regression selected by validation average precision | Manifest and `evaluation.json` under ignored `artifacts/telco-models/<version>/` | Demonstration candidate |
