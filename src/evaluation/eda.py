"""EDA figures computed from the REAL data. Run:  python -m src.evaluation.eda --experiment static|network|both
Figures go to reports/figures/ ; factual captions (numbers computed from the data) go to
artifacts/eda_summary.json. Interpretation of the patterns is written by the student in the notebooks/report."""
import argparse, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd, seaborn as sns
from sklearn.feature_selection import mutual_info_classif
from src import config
from src.preprocessing.loaders import load_network, load_static

PAL = {0: "#168C83", 1: "#C2410C"}


def _save(fig, name):
    config.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(config.FIGURES / name, dpi=140)
    plt.close(fig)
    return f"figures/{name}"


def class_distribution(y, tag, title):
    counts = y.map({0: "Benign", 1: "Malware"}).value_counts()
    fig, ax = plt.subplots(figsize=(5, 3.6))
    sns.barplot(x=counts.index, y=counts.values, hue=counts.index, ax=ax, legend=False,
                palette={"Benign": PAL[0], "Malware": PAL[1]})
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom")
    ax.set(title=title, xlabel="Class", ylabel="Number of records")
    return _save(fig, f"{tag}_class_distribution.png"), {k: int(v) for k, v in counts.items()}


def missing_values(df_raw_missing, tag, title):
    m = df_raw_missing[df_raw_missing > 0].sort_values(ascending=False).head(15)
    if m.empty:
        return None
    fig, ax = plt.subplots(figsize=(6.5, 4))
    sns.barplot(x=m.values, y=m.index, ax=ax, color="#243B53")
    ax.set(title=title, xlabel="Missing / invalid cells", ylabel="Feature")
    return _save(fig, f"{tag}_missing_values.png")


def correlation_heatmap(X, cols, tag, title):
    fig, ax = plt.subplots(figsize=(7, 5.8))
    sns.heatmap(X[cols].corr(), cmap="vlag", center=0, ax=ax, square=True,
                cbar_kws={"label": "Pearson correlation"})
    ax.set(title=title)
    return _save(fig, f"{tag}_correlation.png")


def eda_static(bundle):
    X, y, out = bundle.X, bundle.y, {}
    out["class_distribution"] = class_distribution(y, "static", "Static dataset: class distribution")
    prev = X.groupby(y.values).mean().T                      # share of apps using each feature, per class
    prev.columns = ["benign", "malware"]
    prev["diff"] = prev["malware"] - prev["benign"]
    top = prev.reindex(prev["diff"].abs().sort_values(ascending=False).index).head(15)
    fig, ax = plt.subplots(figsize=(7, 5.2))
    top[["benign", "malware"]].iloc[::-1].plot.barh(ax=ax, color=[PAL[0], PAL[1]])
    ax.set(title="Static: features whose usage differs most between classes",
           xlabel="Share of apps that have the feature", ylabel="Feature")
    out["prevalence_figure"] = _save(fig, "static_feature_prevalence.png")
    out["prevalence_top"] = {f: {"benign": float(r.benign), "malware": float(r.malware)} for f, r in top.iterrows()}
    cols = X.var().sort_values(ascending=False).head(15).index.tolist()
    out["correlation_figure"] = correlation_heatmap(X, cols, "static", "Static: correlation of the 15 highest-variance features")
    ft = X.sum(axis=1)
    fig, ax = plt.subplots(figsize=(6, 3.8))
    sns.histplot(x=ft, hue=y.map({0: "Benign", 1: "Malware"}), bins=30, ax=ax, element="step",
                 palette={"Benign": PAL[0], "Malware": PAL[1]})
    ax.set(title="Static: number of permissions/APIs requested per app", xlabel="Features present (count)", ylabel="Apps")
    out["count_figure"] = _save(fig, "static_feature_count.png")
    out["mean_features_per_app"] = {"benign": float(ft[y == 0].mean()), "malware": float(ft[y == 1].mean())}
    return out


def eda_network(bundle):
    X, y, g, out = bundle.X, bundle.y, bundle.groups, {}
    out["class_distribution"] = class_distribution(y, "network", "Network dataset: class distribution (flows)")
    sample = X.sample(min(20000, len(X)), random_state=config.RANDOM_STATE)
    ys = y.loc[sample.index]
    sample_f = sample.fillna(sample.median())
    mi = pd.Series(mutual_info_classif(sample_f, ys, random_state=config.RANDOM_STATE), index=sample.columns)
    top = mi.sort_values(ascending=False).head(6).index.tolist()
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.6))
    for ax, c in zip(axes.ravel(), top):
        sns.boxplot(x=ys.map({0: "Benign", 1: "Malware"}), y=np.log1p(sample[c].clip(lower=0)), hue=ys.map({0: "Benign", 1: "Malware"}),
                    palette={"Benign": PAL[0], "Malware": PAL[1]}, ax=ax, legend=False, showfliers=False)
        ax.set(title=c, xlabel="", ylabel="log(1 + value)")
    fig.suptitle("Network: six features most associated with the label (mutual information)")
    out["feature_figure"] = _save(fig, "network_top_features.png")
    out["top_mi_features"] = {c: float(mi[c]) for c in top}
    out["correlation_figure"] = correlation_heatmap(sample_f, top + mi.sort_values(ascending=False).index[6:15].tolist(),
                                                   "network", "Network: correlation of the 15 most label-related features")
    per = pd.DataFrame({"g": g, "y": y}).groupby("g").agg(n=("y", "size"), mal=("y", "max"))
    fig, ax = plt.subplots(figsize=(6, 3.8))
    sns.histplot(x=per["n"], hue=per["mal"].map({0: "Benign capture", 1: "Malware capture"}), bins=30, log_scale=True, ax=ax,
                 palette={"Benign capture": PAL[0], "Malware capture": PAL[1]}, element="step")
    ax.set(title="Network: flows per capture file", xlabel="Flows in capture file (log scale)", ylabel="Capture files")
    out["flows_per_capture_figure"] = _save(fig, "network_flows_per_capture.png")
    out["n_capture_files"] = int(len(per))
    out["flows_per_capture"] = {"median": float(per["n"].median()), "max": int(per["n"].max())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", choices=["static", "network", "both"], default="both")
    a = ap.parse_args()
    path = config.ARTIFACTS / "eda_summary.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    if a.experiment in ("static", "both"):
        res["static"] = eda_static(load_static(config.STATIC_CSV))
    if a.experiment in ("network", "both"):
        res["network"] = eda_network(load_network(config.NETWORK_CSV))
    config.ARTIFACTS.mkdir(exist_ok=True)
    path.write_text(json.dumps(res, indent=2))
    print("EDA figures ->", config.FIGURES)


if __name__ == "__main__":
    main()
