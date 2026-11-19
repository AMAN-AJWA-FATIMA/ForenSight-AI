"""Train + evaluate one experiment (static OR network) independently.

    python -m src.models.train --experiment static
    python -m src.models.train --experiment network
    python -m src.models.train --experiment both

Steps: load real data -> split (group-aware if capture ids exist) -> baseline LR/RF/GB ->
tune each with CV on TRAIN only -> pick best by CV F1 -> evaluate ONCE on the untouched test set ->
explain -> save pipeline (joblib) + metrics (JSON).
"""
import argparse, json, time
import joblib, numpy as np, pandas as pd
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (GridSearchCV, GroupShuffleSplit, RandomizedSearchCV,
                                     StratifiedGroupKFold, StratifiedKFold, cross_val_predict, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

from src import config
from src.evaluation.explain import native_importance, permutation_top
from sklearn.metrics import f1_score, matthews_corrcoef, precision_recall_curve, roc_curve
from src.evaluation.metrics import evaluate
from src.preprocessing.loaders import load_network, load_static

SEED = config.RANDOM_STATE



def make_models(improved=False):
    """
    Return model pipelines, hyperparameter grids, and search strategies.

    Random Forest:
        Pre-pruning: max_depth, min_samples_split, min_samples_leaf,
                     max_features.
        Post-pruning: ccp_alpha.

    Gradient Boosting:
        Pre-pruning: max_depth, min_samples_split, min_samples_leaf.
        Post-pruning: ccp_alpha.

    Logistic Regression:
        Regularized using C and balanced class weights.

    HistGradientBoosting:
        Regularized using max_leaf_nodes, min_samples_leaf,
        and l2_regularization.
    """

    imp = ("impute", SimpleImputer(strategy="median"))

    # Parameters shared by both experiment configurations.
    rf_grid = {
        "model__n_estimators": [100, 200, 300],
        "model__max_depth": [8, 12, 20, 30, None],
        "model__min_samples_split": [2, 5, 10, 20],
        "model__min_samples_leaf": [1, 2, 5, 10],
        "model__max_features": ["sqrt", 0.3],
        "model__ccp_alpha": [0.0, 0.00001, 0.0001, 0.001],
    }

    gb_grid = {
        "model__n_estimators": [100, 200],
        "model__learning_rate": [0.05, 0.1],
        "model__max_depth": [1, 2, 3],
        "model__min_samples_split": [2, 5, 10],
        "model__min_samples_leaf": [2, 5, 10],
        "model__ccp_alpha": [0.0, 0.00001, 0.0001, 0.001],
    }

    if improved:
        return {
            "Logistic Regression": (
                Pipeline([
                    imp,
                    ("scale", StandardScaler()),
                    ("model", LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=SEED,
                    )),
                ]),
                {"model__C": [0.01, 0.1, 1, 10]},
                "grid",
            ),

            "Random Forest": (
                Pipeline([
                    imp,
                    ("model", RandomForestClassifier(
                        class_weight="balanced_subsample",
                        n_jobs=-1,
                        random_state=SEED,
                    )),
                ]),
                rf_grid,
                "random",
            ),

            "Gradient Boosting": (
                Pipeline([
                    imp,
                    ("model", GradientBoostingClassifier(
                        random_state=SEED,
                    )),
                ]),
                gb_grid,
                "random",
            ),

            "Hist Gradient Boosting": (
                Pipeline([
                    imp,
                    ("model", HistGradientBoostingClassifier(
                        class_weight="balanced",
                        early_stopping=False,
                        random_state=SEED,
                    )),
                ]),
                {
                    "model__learning_rate": [0.03, 0.06, 0.1],
                    "model__max_iter": [150, 300],
                    "model__max_leaf_nodes": [15, 31, 63],
                    "model__min_samples_leaf": [20, 50, 100],
                    "model__l2_regularization": [0.0, 1.0, 10.0],
                },
                "random",
            ),
            "Extra Trees": (
                Pipeline([
                        imp,
                        ("model", ExtraTreesClassifier(
                            class_weight="balanced",
                            n_jobs=-1,
                            random_state=SEED,
                        )),
                    ]),
                    {
                        "model__n_estimators": [200, 300],
                        "model__max_depth": [8, 12, 16],
                        "model__min_samples_split": [10, 20],
                        "model__min_samples_leaf": [5, 10, 20],
                        "model__max_features": ["sqrt", 0.5],
                        "model__ccp_alpha": [0.0, 0.0001, 0.001],
                    },
                    "random",
                ),
        }

    return {
        "Logistic Regression": (
            Pipeline([
                imp,
                ("scale", StandardScaler()),
                ("model", LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    random_state=SEED,
                )),
            ]),
            {"model__C": [0.01, 0.1, 1, 10]},
            "grid",
        ),

        "Random Forest": (
            Pipeline([
                imp,
                ("model", RandomForestClassifier(
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=SEED,
                )),
            ]),
            rf_grid,
            "random",
        ),

        "Gradient Boosting": (
            Pipeline([
                imp,
                ("model", GradientBoostingClassifier(
                    random_state=SEED,
                )),
            ]),
            gb_grid,
            "random",
        ),
    }




def fit_kwargs(name, y):
    # Gradient Boosting has no class_weight option -> use balanced sample weights instead
    return {"model__sample_weight": compute_sample_weight("balanced", y)} if name == "Gradient Boosting" else {}


def split(X, y, groups):
    if groups is not None:   # keep every capture file entirely in train OR test
        gss = GroupShuffleSplit(n_splits=1, test_size=config.TEST_SIZE, random_state=SEED)
        tr, te = next(gss.split(X, y, groups))
        return tr, te, "GroupShuffleSplit (capture files never shared between train and test)"
    idx = np.arange(len(X))
    tr, te = train_test_split(idx, test_size=config.TEST_SIZE, stratify=y, random_state=SEED)
    return tr, te, "Stratified train_test_split (no group ids exist -> near-duplicate leakage cannot be ruled out)"


def make_cv(groups_train):
    if groups_train is not None:
        return StratifiedGroupKFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=SEED)
    return StratifiedKFold(n_splits=config.CV_FOLDS, shuffle=True, random_state=SEED)


def score_model(pipe, X, y, threshold=None):
    """threshold=None -> the model's own 0.5 decision (submitted behaviour); otherwise a tuned threshold."""
    proba = pipe.predict_proba(X)[:, 1]
    pred = pipe.predict(X) if threshold is None else (proba >= threshold).astype(int)
    return evaluate(y, pred, proba)


def best_threshold(pipe, model_name, Xs, ys, gs, cv, objective="f1"):
    """Decision threshold that maximises F1 (or MCC) on OUT-OF-FOLD predictions of the TRAINING subsample only.

    objective="mcc" (Matthews correlation) uses all four confusion-matrix cells, so it cannot be won by simply
    flagging everything; use it if the F1-optimal threshold costs too much accuracy.

    Every training row is scored by a model that never saw it (group-aware CV), so the threshold is not fitted
    to the test set and not to the model's own training fit. Returns (threshold, oof_f1)."""
    params = fit_kwargs(model_name, ys) or None
    proba = cross_val_predict(clone(pipe), Xs, ys, groups=gs, cv=cv, method="predict_proba",
                              n_jobs=-1, params=params)[:, 1]
    grid = np.linspace(0.05, 0.95, 91)
    score = (lambda t: matthews_corrcoef(ys, proba >= t)) if objective == "mcc" else \
            (lambda t: f1_score(ys, proba >= t, zero_division=0))
    vals = [score(t) for t in grid]
    i = int(np.argmax(vals))
    return float(grid[i]), float(f1_score(ys, proba >= grid[i], zero_division=0))


def _thin(a, n=150):
    """Keep at most n evenly spaced points of a curve (keeps the JSON small, shape unchanged)."""
    idx = np.unique(np.linspace(0, len(a[0]) - 1, min(n, len(a[0]))).astype(int))
    return [[round(float(v), 5) for v in arr[idx]] for arr in a]


def curves(pipe, X, y):
    score = pipe.predict_proba(X)[:, 1]
    fpr, tpr, _ = roc_curve(y, score)
    prec, rec, _ = precision_recall_curve(y, score)
    (f, t), (r, p) = _thin([fpr, tpr]), _thin([rec, prec])
    return {"roc": {"fpr": f, "tpr": t}, "pr": {"recall": r, "precision": p}}


def run_experiment(name, bundle, out_dir=config.ARTIFACTS, max_tune_rows=20000, n_iter=8, fast=False, improved=False,
                   threshold_objective="f1"):
    t0 = time.time()
    X, y, groups = bundle.X, bundle.y, bundle.groups
    tr, te, split_desc = split(X, y, groups)
    X_tr, X_te, y_tr, y_te = X.iloc[tr], X.iloc[te], y.iloc[tr], y.iloc[te]
    g_tr = groups.iloc[tr] if groups is not None else None

    # zero-variance columns are found on TRAIN only (no information from the test set)
    keep = [c for c in X_tr.columns if X_tr[c].nunique(dropna=True) > 1]
    dropped_const = sorted(set(X.columns) - set(keep))
    X_tr, X_te = X_tr[keep], X_te[keep]
    feature_names = list(keep)
    cv = make_cv(g_tr)

    # smaller subsample for hyper-parameter search keeps big flow tables fast
    if len(X_tr) > max_tune_rows:
        sub = np.random.RandomState(SEED).choice(len(X_tr), max_tune_rows, replace=False)
    else:
        sub = np.arange(len(X_tr))
    Xs, ys = X_tr.iloc[sub], y_tr.iloc[sub]
    gs = g_tr.iloc[sub] if g_tr is not None else None

    results, fitted = {}, {}
    for model_name, (pipe, grid, kind) in make_models(improved).items():
        print(f"[{name}] {model_name}: baseline ...")
        base = clone(pipe).fit(X_tr, y_tr, **fit_kwargs(model_name, y_tr))
        base_metrics = score_model(base, X_te, y_te)

        if fast:
            grid = {k: v[:1] for k, v in grid.items()}
        search_cls = GridSearchCV if kind == "grid" else RandomizedSearchCV
        kw = {} if kind == "grid" else {"n_iter": min(n_iter, int(np.prod([len(v) for v in grid.values()]))),
                                         "random_state": SEED}
        print(f"[{name}] {model_name}: tuning ({config.CV_FOLDS}-fold CV on train only) ...")
        search = search_cls(pipe, grid, scoring="f1", cv=cv, n_jobs=-1, **kw)
        search.fit(Xs, ys, groups=gs, **fit_kwargs(model_name, ys))
        tuned = clone(pipe).set_params(**search.best_params_).fit(X_tr, y_tr, **fit_kwargs(model_name, y_tr))
        thr, oof_f1 = None, None
        if improved:   # threshold chosen from out-of-fold TRAIN predictions only (never from the test set)
            thr, oof_f1 = best_threshold(clone(pipe).set_params(**search.best_params_), model_name, Xs, ys, gs, cv,
                                         threshold_objective)
        tuned_metrics = score_model(tuned, X_te, y_te, thr)

        # training-set performance (subsample for speed) to show the train-vs-test gap
        tsub = np.random.RandomState(SEED).choice(len(X_tr), min(len(X_tr), 30000), replace=False)
        tr_m = score_model(tuned, X_tr.iloc[tsub], y_tr.iloc[tsub], thr)
        results[model_name] = {
            "baseline": base_metrics, "tuned": tuned_metrics,
            "train": {k: tr_m[k] for k in ("accuracy", "precision", "recall", "f1", "roc_auc", "false_positive_rate")},
            **curves(tuned, X_te, y_te),
            "best_params": {k.replace("model__", ""): v for k, v in search.best_params_.items()},
            "cv_f1_train": float(oof_f1 if improved else search.best_score_),
        }
        if improved:
            results[model_name]["threshold"] = thr
            results[model_name]["tuned_at_default_threshold"] = score_model(tuned, X_te, y_te)   # for transparency
        fitted[model_name] = tuned

    # model selection uses CV score on TRAIN data only - never the test set
    best_name = max(results, key=lambda n: results[n]["cv_f1_train"])
    best_pipe = fitted[best_name]

    importance = {"native": native_importance(best_pipe, feature_names),
                  "permutation": permutation_top(best_pipe, X_te, y_te)}

    background = {c: float(X_tr[c].median()) for c in feature_names}
    top_features = [i["feature"] for i in importance["permutation"]["items"][:12]]
    stats = {c: {"min": float(X_tr[c].min()), "max": float(X_tr[c].max())} for c in feature_names}

    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": best_pipe, "model_name": best_name, "feature_names": feature_names,
                 "background": background, "top_features": top_features, "feature_stats": stats,
                 "label_names": ["benign", "malware"],
                 "threshold": results[best_name].get("threshold") or 0.5}, out_dir / f"{name}_model.joblib")

    summary = {
        "experiment": name, "data_log": bundle.log, "split": split_desc,
        "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
        "test_class_counts": {"benign": int((y_te == 0).sum()), "malware": int((y_te == 1).sum())},
        "imbalance_ratio_majority_to_minority": float(max(np.bincount(y)) / max(1, min(np.bincount(y)))),
        "zero_variance_features_dropped": dropped_const,
        "tuning_rows_used": int(len(Xs)), "models": results, "best_model": best_name,
        "selection_rule": ("highest out-of-fold F1 (at its tuned threshold) on the training split" if improved
                           else "highest mean 5-fold CV F1 on the training split"),
        "improved": bool(improved), "threshold_objective": threshold_objective if improved else None,
        # F1 you would get by flagging EVERY flow as malware: a weak model must beat this to be worth anything
        "flag_all_baseline_f1": round(2 * float(y_te.mean()) / (1 + float(y_te.mean())), 4),
        "importance": importance, "seconds": round(time.time() - t0, 1),
    }
    path = out_dir / "evaluation_results.json"
    allres = json.loads(path.read_text()) if path.exists() else {}
    allres[name] = summary
    path.write_text(json.dumps(allres, indent=2))
    print(f"[{name}] best = {best_name}  -> saved {out_dir}/{name}_model.joblib")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", choices=["static", "network", "both"], default="both")
    ap.add_argument("--fast", action="store_true", help="tiny grids, for a quick code check only")
    ap.add_argument("--improved", action="store_true",
                    help="network only: upgraded models + threshold tuning; writes to artifacts/improved/ "
                         "so the submitted artifacts/ (and the dashboard) are not touched")
    ap.add_argument("--threshold-objective", choices=["f1", "mcc"], default="f1",
                    help="with --improved: what the decision threshold maximises on out-of-fold training predictions")
    a = ap.parse_args()
    if a.improved and a.experiment != "network":
        ap.error("--improved applies to the network experiment only: use --experiment network --improved")
    if a.experiment in ("static", "both"):
        run_experiment("static", load_static(config.STATIC_CSV), fast=a.fast)
    if a.experiment in ("network", "both"):
        if a.improved:
            run_experiment("network", load_network(config.NETWORK_CSV), out_dir=config.ARTIFACTS / "improved",
                           max_tune_rows=40000, n_iter=12, fast=a.fast, improved=True,
                           threshold_objective=a.threshold_objective)
        else:
            run_experiment("network", load_network(config.NETWORK_CSV), fast=a.fast)


if __name__ == "__main__":
    main()
