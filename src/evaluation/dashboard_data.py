"""Collect what the dashboard shows beyond the training metrics, from the REAL files:
raw-vs-processed statistics, previews, one EDA panel and real held-out test records.

    python -m src.evaluation.dashboard_data --experiment both      (run AFTER training)
Output: artifacts/dashboard_data.json
"""
import argparse, json
import numpy as np, pandas as pd
from sklearn.feature_selection import mutual_info_classif
from src import config
from src.models.inference import load_model
from src.models.train import split
from src.preprocessing.loaders import (LABEL_MAP, NETWORK_ID_COLS, STATIC_LABEL_CANDIDATES,
                                       load_network, load_static)

SEED = config.RANDOM_STATE
NET_PREVIEW_COLS = ["Source Port", "Destination Port", "Protocol", "Flow Duration", "Total Fwd Packets",
                    "Total Backward Packets", "Flow Bytes/s", "Flow Packets/s"]   # IP columns are not shown


def _clean(v):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, float)): return None if not np.isfinite(v) else round(float(v), 4)
    return None if (v is None or (isinstance(v, float) and np.isnan(v))) else v


def _records(df, n=5):
    return {"columns": [str(c) for c in df.columns],
            "rows": [[_clean(v) for v in row] for row in df.head(n).itertuples(index=False, name=None)]}


def _hist(values_by_class, bins=20):
    """Per-class histogram on shared bin edges, as % of that class (so imbalance does not hide the shape)."""
    allv = np.concatenate([v for v in values_by_class.values()])
    edges = np.histogram_bin_edges(allv, bins=bins)
    out = {"edges": [round(float(e), 4) for e in edges]}
    for k, v in values_by_class.items():
        c, _ = np.histogram(v, bins=edges)
        out[k] = [round(float(x) * 100 / max(1, len(v)), 3) for x in c]
    return out


def raw_stats(exp, raw: pd.DataFrame):
    if exp == "static":
        label_col = next(c for c in STATIC_LABEL_CANDIDATES if c in raw.columns)
        feats = raw.drop(columns=[label_col])
        lab = raw[label_col].astype(str).str.strip().str.lower().where(raw[label_col].notna())
        y = lab.map(LABEL_MAP)
        dup = int(raw.duplicated().sum())
    else:
        feats = raw.drop(columns=[c for c in NETWORK_ID_COLS + ["label_binary", "source_file"] if c in raw.columns])
        y = raw["label_binary"]
        dup = int(raw.drop(columns=[c for c in NETWORK_ID_COLS + ["source_file"] if c in raw.columns
                                    and c != "label_binary"]).duplicated().sum())
    num = feats.apply(pd.to_numeric, errors="coerce")
    return {"rows": int(len(raw)), "columns": int(raw.shape[1]), "feature_columns": int(feats.shape[1]),
            "missing_cells": int(raw.isna().sum().sum()),
            "invalid_non_numeric_cells": int(num.isna().sum().sum() - feats.isna().sum().sum()),
            "infinite_cells": int(np.isinf(num.to_numpy(dtype=float)).sum()),
            "duplicate_rows": dup,
            "class_counts": {"benign": int((y == 0).sum()), "malware": int((y == 1).sum()), "unlabelled": int(y.isna().sum())}}


def build(exp, raw: pd.DataFrame, bundle, art_dir=config.ARTIFACTS):
    art = load_model(exp, art_dir)
    res = json.loads((art_dir / "evaluation_results.json").read_text())[exp]
    X, y, g = bundle.X, bundle.y, bundle.groups
    feats = art["feature_names"]
    out = {"raw_stats": raw_stats(exp, raw)}

    # ---- previews: raw vs processed ----
    if exp == "static":
        raw_prev = raw.iloc[:, list(range(min(7, raw.shape[1] - 1))) + [raw.shape[1] - 1]]
    else:
        cols = [c for c in NET_PREVIEW_COLS if c in raw.columns] or list(raw.columns[:8])
        raw_prev = raw[cols + ["label_binary"]]
    out["raw_preview"] = _records(raw_prev)
    out["processed_stats"] = {"rows": int(len(X)), "features": int(len(feats)),
                              "missing_cells_before_imputation": int(X[feats].isna().sum().sum()),
                              "duplicate_rows": int(pd.concat([X[feats], y.rename("__y__")], axis=1).duplicated().sum()),
                              "class_counts": {"benign": int((y == 0).sum()), "malware": int((y == 1).sum())}}
    proc = X[feats[:8]].round(3).copy(); proc["label (0=benign,1=malware)"] = y.values
    out["processed_preview"] = _records(proc)

    # ---- what was removed / kept ----
    log = bundle.log
    out["features"] = {"kept": len(feats), "identifier_columns_removed": log.get("identifier_columns_removed", []),
                       "all_nan_removed": log.get("all_nan_columns_dropped", []),
                       "zero_variance_removed": res["zero_variance_features_dropped"],
                       "model_based_selection": False}

    # ---- one EDA panel: static = feature usage by class, network = two most label-related flow features ----
    Xs = X[feats]
    if exp == "static":
        prev = Xs.groupby(y.values).mean().T; prev.columns = ["benign", "malware"]
        top = prev.reindex((prev["malware"] - prev["benign"]).abs().sort_values(ascending=False).index).head(10)
        out["feature_frequency"] = {f: {"benign": round(float(r.benign) * 100, 2), "malware": round(float(r.malware) * 100, 2)} for f, r in top.iterrows()}
    else:
        samp = Xs.sample(min(20000, len(Xs)), random_state=SEED)
        ys = y.loc[samp.index]; filled = samp.fillna(samp.median())
        mi = pd.Series(mutual_info_classif(filled, ys, random_state=SEED), index=samp.columns).sort_values(ascending=False)
        out["histograms"] = {}
        for c in mi.index[:2]:
            v = np.log1p(filled[c].clip(lower=0))
            out["histograms"][f"log(1 + {c})"] = _hist({"benign": v[ys == 0].to_numpy(), "malware": v[ys == 1].to_numpy()}, 20)

    # ---- real held-out test rows the user can run through the model ----
    tr, te, _ = split(X, y, g)
    Xte, yte = Xs.iloc[te], y.iloc[te]
    rng = np.random.RandomState(SEED); samples = []
    for lab, name in ((0, "benign"), (1, "malware")):
        idx = np.where(yte.values == lab)[0]
        for i in rng.choice(idx, min(6, len(idx)), replace=False):
            samples.append({"id": f"test-{int(te[i])}", "true_label": name, "features": {c: _clean(v) for c, v in Xte.iloc[i].items()}})
    out["samples"] = samples
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--experiment", choices=["static", "network", "both"], default="both")
    a = ap.parse_args()
    path = config.ARTIFACTS / "dashboard_data.json"
    allv = json.loads(path.read_text()) if path.exists() else {}
    if a.experiment in ("static", "both"):
        allv["static"] = build("static", pd.read_csv(config.STATIC_CSV), load_static(config.STATIC_CSV))
    if a.experiment in ("network", "both"):
        allv["network"] = build("network", pd.read_csv(config.NETWORK_CSV, low_memory=False), load_network(config.NETWORK_CSV))
    path.write_text(json.dumps(allv))
    print("dashboard data ->", path, f"({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
