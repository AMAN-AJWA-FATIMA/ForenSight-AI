"""Simple, model-agnostic explanations.

Global:  model-native importance (RF/GB importances, LR coefficients) + permutation importance.
Local:   occlusion - replace one feature at a time by its training background value and
         measure how the malware probability changes.

IMPORTANT: these describe what the MODEL uses, not what causes malware (association != causation).
"""
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


def native_importance(pipeline, feature_names, top_k=20):
    model = pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        vals, kind = model.feature_importances_, "impurity importance (higher = used more)"
    elif hasattr(model, "coef_"):
        vals, kind = model.coef_.ravel(), "coefficient on standardised feature (+ pushes to malware)"
    else:
        return {"kind": "unavailable", "items": []}
    order = np.argsort(-np.abs(vals))[:top_k]
    return {"kind": kind,
            "items": [{"feature": feature_names[i], "value": float(vals[i])} for i in order]}


def permutation_top(pipeline, X_test, y_test, top_k=20, max_rows=5000, seed=42):
    if len(X_test) > max_rows:
        idx = np.random.RandomState(seed).choice(len(X_test), max_rows, replace=False)
        X_test, y_test = X_test.iloc[idx], np.asarray(y_test)[idx]
    r = permutation_importance(pipeline, X_test, y_test, scoring="f1",
                               n_repeats=5, random_state=seed, n_jobs=-1)
    order = np.argsort(-r.importances_mean)[:top_k]
    return {"kind": "drop in F1 when the feature is shuffled (test set)",
            "items": [{"feature": X_test.columns[i], "value": float(r.importances_mean[i]),
                       "std": float(r.importances_std[i])} for i in order]}


def local_explanation(pipeline, row: pd.Series, background: dict, feature_names, top_k=8):
    """Occlusion explanation for ONE row. Positive contribution = pushes towards malware."""
    base = float(pipeline.predict_proba(row[feature_names].to_frame().T.astype(float))[0, 1])
    block = pd.DataFrame([row[feature_names].astype(float).values] * len(feature_names),
                         columns=feature_names)
    for i, f in enumerate(feature_names):
        block.iat[i, i] = background[f]
    probs = pipeline.predict_proba(block)[:, 1]
    contrib = base - probs
    order = np.argsort(-np.abs(contrib))[:top_k]
    return [{"feature": feature_names[i], "value": float(row[feature_names[i]]),
             "contribution": float(contrib[i])} for i in order if abs(contrib[i]) > 1e-9]
