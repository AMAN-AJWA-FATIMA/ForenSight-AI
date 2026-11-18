"""Evaluation helpers. Convention: label 1 = malware (positive class), 0 = benign."""
import numpy as np
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, roc_auc_score, classification_report,
                             average_precision_score)

CLASS_NAMES = ["benign", "malware"]


def evaluate(y_true, y_pred, y_score=None):
    """Return a JSON-serialisable dict of all metrics required by the CCA."""
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        # false-positive rate = benign items wrongly flagged / all benign items
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else None,
        "specificity": float(tn / (tn + fp)) if (tn + fp) else None,          # benign correctly cleared
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else None,  # malware missed
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],  # rows=true, cols=pred
        "classification_report": classification_report(
            y_true, y_pred, labels=[0, 1], target_names=CLASS_NAMES,
            output_dict=True, zero_division=0),
    }
    # ROC-AUC needs both classes present in the test labels
    if y_score is not None and len(np.unique(y_true)) == 2:
        out["roc_auc"] = float(roc_auc_score(y_true, y_score))
    else:
        out["roc_auc"] = None
    out["pr_auc"] = float(average_precision_score(y_true, y_score)) if (y_score is not None and len(np.unique(y_true)) == 2) else None
    return out
