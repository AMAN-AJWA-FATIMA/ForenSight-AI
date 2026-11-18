"""EXTRA experiment (does NOT change the submitted pipeline): classify a whole CAPTURE, not a single flow.

    python -m src.models.train_capture_level
    python -m src.models.train_capture_level --min-flows 5 --repeats 3

Why: one flow is a tiny, noisy piece of an app's behaviour (malware apps also make normal traffic), so
flow-level F1 is low. Here every capture file (= one app run) becomes ONE row: for each CICFlowMeter
statistic we keep mean, std, median and max over all flows of that capture. The label is the capture's label.

Honest-evaluation rules kept from the main project:
  * split FIRST (stratified, 20% test, seed from config), tuning/selection with CV on TRAIN only,
  * the test set is used ONCE, after choosing the model,
  * identifier columns (Flow ID, IPs, ports, timestamp) are never used,
  * the number of flows in a capture is NOT used (it depends on capture length / sampling, not behaviour).

Results are saved to artifacts/capture_level_results.json. The submitted model and evaluation_results.json
are never touched. NOTE: a capture-level score is a different task from the flow-level score, so the two
must not be compared as if they were the same experiment.
"""
import argparse, json, time
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src import config
from src.evaluation.metrics import evaluate
from src.preprocessing.build_network_dataset import label_from

SEED = config.RANDOM_STATE
# identifier / label columns that must never be features (compared in lower case)
DROP = {"flow id", "source ip", "src ip", "destination ip", "dst ip", "timestamp", "source port", "src port",
        "destination port", "dst port", "label", "label_binary", "source_file"}
STATS = ("mean", "std", "median", "max")


def capture_row(df):
    cols = [c for c in df.columns if c.lower() not in DROP]
    num = df[cols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    row = {}
    for stat in STATS:
        for col, val in getattr(num, stat)().items():
            row[f"{col}__{stat}"] = float(val) if pd.notna(val) else np.nan
    return row


def build_capture_table(raw_dir, min_flows):
    files = sorted(raw_dir.rglob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files under {raw_dir}")
    rows, labels, names, skipped = [], [], [], {"no_label": 0, "too_few_flows": 0}
    for i, f in enumerate(files, 1):
        df = pd.read_csv(f, low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        lab, _ = label_from(f.relative_to(raw_dir), df)
        if lab is None:
            skipped["no_label"] += 1
            continue
        if len(df) < min_flows:
            skipped["too_few_flows"] += 1
            continue
        rows.append(capture_row(df))
        labels.append(int(lab.max()))        # label is constant inside a capture file
        names.append(str(f.relative_to(raw_dir)))
        if i % 200 == 0:
            print(f"  processed {i}/{len(files)} files ...")
    X = pd.DataFrame(rows)
    X = X.loc[:, X.nunique(dropna=True) > 1]   # drop constant columns (no information)
    return X, pd.Series(labels, name="y"), names, skipped


def make_models():
    imp = ("impute", SimpleImputer(strategy="median"))
    return {
        "Logistic Regression": Pipeline([imp, ("scale", StandardScaler()),
                                         ("model", LogisticRegression(max_iter=3000, C=0.1, class_weight="balanced",
                                                                      random_state=SEED))]),
        "Random Forest": Pipeline([imp, ("model", RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2, class_weight="balanced_subsample", n_jobs=-1, random_state=SEED))]),
        "Hist Gradient Boosting": Pipeline([imp, ("model", HistGradientBoostingClassifier(
            learning_rate=0.05, max_depth=4, class_weight="balanced", random_state=SEED))]),
    }


def main(min_flows=5, repeats=3):
    t0 = time.time()
    print("Building one row per capture file (this reads every raw CSV once) ...")
    X, y, names, skipped = build_capture_table(config.NETWORK_RAW_DIR, min_flows)
    print(f"{len(X)} captures x {X.shape[1]} features | malware {int(y.sum())} benign {int((y == 0).sum())} | skipped {skipped}")

    idx = np.arange(len(X))
    tr, te = train_test_split(idx, test_size=config.TEST_SIZE, stratify=y, random_state=SEED)
    X_tr, X_te, y_tr, y_te = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]

    cv = RepeatedStratifiedKFold(n_splits=config.CV_FOLDS, n_repeats=repeats, random_state=SEED)
    cv_scores = {}
    for name, pipe in make_models().items():
        s = cross_val_score(pipe, X_tr, y_tr, scoring="f1", cv=cv, n_jobs=-1)
        cv_scores[name] = (float(s.mean()), float(s.std()))
        print(f"  CV F1 on TRAIN only  {name:24s} {s.mean():.3f} +/- {s.std():.3f}")

    best = max(cv_scores, key=lambda n: cv_scores[n][0])
    final = make_models()[best].fit(X_tr, y_tr)
    pred, proba = final.predict(X_te), final.predict_proba(X_te)[:, 1]
    m = evaluate(y_te, pred, proba)               # same metric function as the main project
    tn, fp, fn, tp = confusion_matrix(y_te, pred, labels=[0, 1]).ravel()

    print(f"\nChosen by CV F1 (train only): {best}")
    print(f"TEST ({len(y_te)} captures, {int(y_te.sum())} malware) -> "
          f"accuracy {m['accuracy']:.3f} precision {m['precision']:.3f} recall {m['recall']:.3f} "
          f"F1 {m['f1']:.3f} ROC-AUC {m['roc_auc']:.3f}")
    print(f"Confusion matrix: TN={tn} FP={fp} FN={fn} TP={tp}")
    print("Always-benign baseline accuracy:", round(float((y_te == 0).mean()), 3), "(recall 0)")

    top = []
    if best == "Random Forest":
        imp = final.named_steps["model"].feature_importances_
        order = np.argsort(imp)[::-1][:10]
        top = [(X.columns[i], round(float(imp[i]), 4)) for i in order]
        print("Top features:", top)

    out = config.ARTIFACTS
    out.mkdir(parents=True, exist_ok=True)
    (out / "capture_level_results.json").write_text(json.dumps({
        "task": "capture-level (one row per capture file); NOT comparable to the flow-level experiment",
        "n_captures": int(len(X)), "n_features": int(X.shape[1]), "skipped": skipped,
        "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
        "cv_f1_train": {k: {"mean": v[0], "std": v[1]} for k, v in cv_scores.items()},
        "chosen": best, "test": {k: float(v) for k, v in m.items() if isinstance(v, (int, float, np.floating))},
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "top_features": top, "seconds": round(time.time() - t0, 1)}, indent=2))
    print(f"Saved {out / 'capture_level_results.json'}  ({round(time.time() - t0, 1)} s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-flows", type=int, default=5)
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    main(a.min_flows, a.repeats)
