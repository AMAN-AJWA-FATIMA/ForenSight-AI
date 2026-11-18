"""Root-cause diagnosis of the weak NETWORK result. Nothing here is used for training or reporting a score.

    python -m src.evaluation.diagnose_network            (reads datasets/network_analysis/cicandmal2017_flows.csv)

It answers, with numbers from YOUR data:
  1. Is class imbalance the problem?          (compare with the static data: same ratio)
  2. Are labels noisy by construction?         (flow label = capture label; identical flows with opposite labels)
  3. Are the features informative?             (single-feature AUC; tiny/degenerate flows)
  4. Is the split too hard / too easy?         (random split vs group split on the same sample)
  5. Is the FLOW the wrong unit?               (flow-level AUC vs capture-level AUC on held-out captures)
Output: reports/network_diagnosis.json
"""
import json
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, roc_curve
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from src import config
from src.preprocessing.loaders import load_network

SEED = config.RANDOM_STATE


def rf():
    return RandomForestClassifier(n_estimators=150, max_depth=14, min_samples_leaf=5, n_jobs=-1,
                                  class_weight="balanced_subsample", random_state=SEED)


def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    return {"f1": round(float(f1_score(y, pred)), 4), "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y, pred)), 4), "roc_auc": round(float(roc_auc_score(y, p)), 4)}


def tpr_at_fpr(y, score, fpr_target=0.05):
    fpr, tpr, _ = roc_curve(y, score)
    return round(float(np.interp(fpr_target, fpr, tpr)), 4)


def main(n_sample=60000):
    b = load_network(config.NETWORK_CSV)
    X, y, g = b.X, b.y, b.groups
    rep = {}

    # 1 + 2: balance, capture structure
    cap = pd.DataFrame({"g": g, "y": y}).groupby("g").agg(flows=("y", "size"), y=("y", "max"))
    rep["balance"] = {"flows": {"benign": int((y == 0).sum()), "malware": int((y == 1).sum())},
                      "imbalance_ratio_flows": round(float((y == 0).sum() / max(1, (y == 1).sum())), 2),
                      "captures": {"benign": int((cap.y == 0).sum()), "malware": int((cap.y == 1).sum())},
                      "flows_per_capture": cap.flows.describe().round(1).to_dict(),
                      "note": "static data ratio is 531:131 (about 4:1) and scores well, so a ~4:1 ratio alone is NOT "
                              "the root cause. The independent units here are CAPTURES, not flows."}
    h = pd.util.hash_pandas_object(X.fillna(-1), index=False)
    d = pd.DataFrame({"h": h.values, "y": y.values})
    conf = d.groupby("h")["y"].nunique()
    conflict = conf[conf > 1].index
    rep["label_noise"] = {"feature_vectors_seen_with_BOTH_labels": int(len(conflict)),
                          "flows_involved": int(d.h.isin(conflict).sum()),
                          "share_of_flows_%": round(100 * float(d.h.isin(conflict).mean()), 2),
                          "note": "every flow inherits its capture's label, so ordinary background traffic inside a "
                                  "malware capture is labelled malware. Identical flows with opposite labels cap the "
                                  "best possible flow-level score."}

    # 3: data quality + informativeness
    s = X.sample(min(n_sample, len(X)), random_state=SEED)
    ys = y.loc[s.index]
    gs = g.loc[s.index]
    filled = s.fillna(s.median())
    dup_cols = int(filled.iloc[:5000].T.duplicated().sum())
    aucs = {}
    for c in filled.columns:
        v = filled[c].to_numpy()
        if np.nanstd(v) > 0:
            aucs[c] = float(roc_auc_score(ys, v))
    strength = pd.Series({c: abs(a - 0.5) * 2 for c, a in aucs.items()}).sort_values(ascending=False)
    small = {}
    if {"Total Fwd Packets", "Total Backward Packets"}.issubset(s.columns):
        tot = s["Total Fwd Packets"].fillna(0) + s["Total Backward Packets"].fillna(0)
        small = {"share_flows_with_<=2_packets_benign_%": round(100 * float((tot[ys == 0] <= 2).mean()), 1),
                 "share_flows_with_<=2_packets_malware_%": round(100 * float((tot[ys == 1] <= 2).mean()), 1)}
    rep["features"] = {"n_features": int(X.shape[1]), "duplicate_columns_in_sample": dup_cols,
                       "missing_cells_%": round(100 * float(X.isna().mean().mean()), 3),
                       "strongest_single_features(|2*AUC-1|)": strength.head(10).round(3).to_dict(),
                       "features_with_|2*AUC-1|<0.1_%": round(100 * float((strength < 0.1).mean()), 1),
                       "tiny_flows": small,
                       "note": "if almost no single feature separates the classes, flow statistics alone are weak "
                               "evidence; tiny flows (DNS, handshakes) look the same for any app."}

    # 4: random split vs group split on the SAME sample
    idx = np.arange(len(s))
    tr, te = train_test_split(idx, test_size=config.TEST_SIZE, stratify=ys, random_state=SEED)
    m = rf().fit(s.iloc[tr].fillna(s.median()), ys.iloc[tr])
    rand = metrics(ys.iloc[te], m.predict_proba(s.iloc[te].fillna(s.median()))[:, 1])
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=config.TEST_SIZE, random_state=SEED).split(s, ys, gs))
    m = rf().fit(s.iloc[tr].fillna(s.median()), ys.iloc[tr])
    pg = m.predict_proba(s.iloc[te].fillna(s.median()))[:, 1]
    grp = metrics(ys.iloc[te], pg)
    rep["split_effect"] = {"random_row_split_(LEAKY, do not report)": rand, "group_split_(honest)": grp,
                           "note": "the gap is how much a random split would have flattered the model by letting "
                                   "near-identical flows of one capture sit on both sides."}

    # 5: flow-level vs capture-level on the held-out captures of the honest split
    te_df = pd.DataFrame({"g": gs.iloc[te].values, "y": ys.iloc[te].values, "p": pg})
    agg = te_df.groupby("g").agg(y=("y", "max"), mean_p=("p", "mean"), flows=("p", "size"))
    rep["unit_of_analysis"] = {
        "flow_level_roc_auc": grp["roc_auc"],
        "capture_level_roc_auc_(mean flow score per capture)": round(float(roc_auc_score(agg.y, agg.mean_p)), 4)
        if agg.y.nunique() == 2 else None,
        "capture_level_TPR_at_5%_FPR": tpr_at_fpr(agg.y, agg.mean_p) if agg.y.nunique() == 2 else None,
        "held_out_captures": {"benign": int((agg.y == 0).sum()), "malware": int((agg.y == 1).sum())},
        "note": "if capture-level AUC is clearly higher, the weak link is classifying ONE flow; classify the whole "
                "capture instead (src/models/train_capture_level.py)."}

    out = config.ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "network_diagnosis.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    print("\nSaved", out / "network_diagnosis.json")


if __name__ == "__main__":
    main()
