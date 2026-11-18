# Submission notes (CT-264 CCA, C3 rubric)

## Rubric alignment (target: Level 2)
| Criterion | Evidence | Where |
|---|---|---|
| 1. Problem identification | Binary triage task, inputs/outputs, scope and limits | Report sec. 1-4, `docs/DATASETS.md` |
| 2. Problem-solving | Verified datasets, cleaning log, EDA, 3 algorithms, stratified / group-aware split, CV tuning, single test evaluation | `notebooks/`, `src/models/train.py` |
| 3. Implementation | Reproducible pipelines, saved Joblib models, Flask API with validation, vanilla JS dashboard, tests | `src/`, `backend/`, `frontend/`, `tests/` |
| 4. Deliverables | Code, dataset instructions, EDA figures, models, results JSON, dashboard, report (>= 10 pages) | README, `artifacts/`, `reports/` |
| 5. Depth of knowledge | Viva questions below | this file |

Before submitting: both datasets downloaded, `scripts/run_all.sh` finished, notebook interpretations written, report cover page and
*Student interpretation* paragraphs filled in, screenshots of the app added, report page count checked.

## Tests (`python -m pytest -q`)
Tiny in-memory fixtures check code paths only. They are never written to `datasets/` or `artifacts/`, and no reported result comes from them.
They cover metrics, label cleaning, group-aware splitting, training output (curves, specificity, FNR), dashboard data, the API
(form, records, CSV, invalid input, missing model) and the page.

## Viva questions
1. **Why split before preprocessing?** Imputers and scalers learn statistics. Fitting them on all data leaks test information into training.
2. **Why a group-aware split for network flows?** Flows from one capture are near-copies. Splitting them across train and test grades the model on data it has effectively seen.
3. **Why is accuracy not enough?** With imbalance a model can be accurate yet miss malware. Read recall, precision, F1, FPR and the confusion matrix.
4. **Recall vs false-positive rate?** Recall is the share of malware caught; FPR is the share of benign items wrongly flagged. Missing malware is costlier; too many false alarms waste analyst time.
5. **How do the algorithms work?** Logistic regression: weighted sum to probability. Random forest: many decorrelated trees vote. Gradient boosting: trees added one by one to fix earlier errors.
6. **How did tuning avoid cheating?** Cross-validation inside the training split only; the test set was used once, after the model was chosen.
7. **Importance vs causation?** Importance says what the model used, not that a feature causes malware.
8. **What can the system not do?** Prove intent, reliably detect unseen families, or combine static and network evidence for one app (different datasets).
9. **Static dataset limitation?** No app identifiers, so near-duplicates may sit in both splits.
10. **Why reject the Kaggle competition?** Unverifiable provenance and likely hidden test labels.
