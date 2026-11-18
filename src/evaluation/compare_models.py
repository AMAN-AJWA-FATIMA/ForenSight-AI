"""Compare the trained models of one experiment: accuracy, precision, recall, F1, FPR, ROC-AUC + confusion matrices.

    python -m src.evaluation.compare_models --experiment network
    python -m src.evaluation.compare_models --experiment network --dir artifacts/improved --vs artifacts

Reads evaluation_results.json (written by src.models.train), so every number is the one measured on the held-out
test set. --vs puts the CHOSEN model of a second folder (e.g. the submitted artifacts/) next to the first.
Writes reports/model_comparison_<experiment>.csv
"""
import argparse, json
from pathlib import Path
import pandas as pd
from src import config

COLS = ["accuracy", "precision", "recall", "f1", "false_positive_rate", "roc_auc", "pr_auc"]


def load(dir_, exp):
    return json.loads((Path(dir_) / "evaluation_results.json").read_text())[exp]


def table(res):
    rows = []
    for name, m in res["models"].items():
        for kind in ("baseline", "tuned"):
            r = {"model": name, "version": kind, **{c: m[kind].get(c) for c in COLS}}
            r["threshold"] = m.get("threshold") if kind == "tuned" else None
            r["chosen"] = "*" if (kind == "tuned" and name == res["best_model"]) else ""
            rows.append(r)
    return pd.DataFrame(rows)


def show_confusions(res, title):
    print(f"\nConfusion matrices ({title}; rows = true, columns = predicted; [[TN, FP], [FN, TP]])")
    for name, m in res["models"].items():
        (tn, fp), (fn, tp) = m["tuned"]["confusion_matrix"]
        print(f"  {name:24s} TN={tn:<8} FP={fp:<8} FN={fn:<8} TP={tp:<8}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", choices=["static", "network"], default="network")
    ap.add_argument("--dir", default=str(config.ARTIFACTS))
    ap.add_argument("--vs", default=None, help="second artifacts folder to compare the chosen model against")
    a = ap.parse_args()
    res = load(a.dir, a.experiment)
    t = table(res)
    pd.set_option("display.width", 200, "display.max_columns", 20)
    print(f"\n{a.experiment.upper()} experiment | folder: {a.dir} | test rows: {res['n_test']} | "
          f"test class counts: {res['test_class_counts']}")
    print(t.round(4).to_string(index=False))
    base = res.get("flag_all_baseline_f1")
    if base is not None:
        best_f1 = res["models"][res["best_model"]]["tuned"]["f1"]
        print(f"\nSanity check: flagging EVERY flow as malware would already give F1 = {base:.3f}. "
              f"Chosen model F1 = {best_f1:.3f}" + ("  -> barely above that baseline: the features carry little "
              "flow-level signal." if best_f1 < base + 0.05 else "  -> clearly above the baseline."))
    show_confusions(res, a.dir)
    out = config.ROOT / "reports"
    out.mkdir(exist_ok=True)
    t.to_csv(out / f"model_comparison_{a.experiment}.csv", index=False)
    if a.vs:
        other = load(a.vs, a.experiment)
        rows = []
        for label, r in ((f"{a.vs}", other), (f"{a.dir}", res)):
            m = r["models"][r["best_model"]]["tuned"]
            rows.append({"folder": label, "chosen model": r["best_model"], **{c: m.get(c) for c in COLS[:5]}})
        print("\nChosen model: before vs after")
        print(pd.DataFrame(rows).round(4).to_string(index=False))
    print(f"\nSaved {out / f'model_comparison_{a.experiment}.csv'}")


if __name__ == "__main__":
    main()
