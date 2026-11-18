"""Build the technical report (Word) from the REAL results produced by training/EDA.

    python reports/build_report.py                 # -> reports/ForenSight_AI_Technical_Report.docx

Numbers, tables and figures are read from artifacts/*.json and reports/figures/. Fixed text
(background, method, ethics) is written once here. Replace the cover-page placeholders and add your own
interpretation paragraphs (marked 'Student interpretation') before submitting."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
ART = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts"
IMG = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "reports" / "figures"
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "reports" / "ForenSight_AI_Technical_Report.docx"
pc = lambda v: "n/a" if v is None else f"{v * 100:.2f}%"


def boxes(path, labels, title, cols=None):
    """Simple labelled-box diagram (architecture / methodology). Not data - a drawing of the design."""
    n = len(labels); cols = cols or n
    rows = -(-n // cols)
    fig, ax = plt.subplots(figsize=(8.5, 1.5 * rows + .6)); ax.axis("off"); ax.set_xlim(0, cols); ax.set_ylim(0, rows)
    for i, t in enumerate(labels):
        r, c = divmod(i, cols); x, y = c + .06, rows - r - .85
        ax.add_patch(FancyBboxPatch((x, y), .88, .65, boxstyle="round,pad=0.02", fc="#EEF2F6", ec="#243B53"))
        ax.text(x + .44, y + .325, t, ha="center", va="center", fontsize=8.5, wrap=True)
        if c < cols - 1 and i < n - 1:
            ax.annotate("", xy=(x + 1.04, y + .325), xytext=(x + .92, y + .325), arrowprops=dict(arrowstyle="->", color="#243B53"))
    ax.set_title(title, fontsize=10, color="#243B53"); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def main():
    res = json.loads((ART / "evaluation_results.json").read_text())
    eda = json.loads((ART / "eda_summary.json").read_text()) if (ART / "eda_summary.json").exists() else {}
    tmp = OUT.parent / "_diagrams"; tmp.mkdir(parents=True, exist_ok=True)
    boxes(tmp / "arch.png", ["Browser\nHTML + CSS + JS\n(Chart.js)", "Flask backend\nroutes, validation,\nJSON APIs", "Saved pipelines\n(Joblib):\nstatic / network", "Results\nprediction + metrics\n+ explanations"],
          "System architecture (two independent pipelines behind one Flask app)")
    boxes(tmp / "method.png", ["Load real\ndataset", "Inspect + clean\n(labels, duplicates,\ninf/NaN)", "Split first\n(stratified / group-aware)", "Baseline\nLR, RF, GB", "Tune: CV on\ntrain only", "Select by\nCV F1", "Single test\nevaluation", "Explain +\nsave pipeline"],
          "Methodology flowchart (applied separately to each experiment)", cols=4)

    d = Document()
    d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)
    H = lambda t, l=1: d.add_heading(t, level=l)
    P = lambda t: d.add_paragraph(t)
    B = lambda items: [d.add_paragraph(i, style="List Bullet") for i in items]
    def FIG(path, caption, w=5.8):
        if Path(path).exists():
            d.add_picture(str(path), width=Inches(w)); d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c = d.add_paragraph(caption); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.runs[0].italic = True
    def TABLE(header, rows):
        t = d.add_table(rows=1, cols=len(header)); t.style = "Light Grid Accent 1"
        for i, h in enumerate(header): t.rows[0].cells[i].text = h
        for r in rows:
            cells = t.add_row().cells
            for i, v in enumerate(r): cells[i].text = str(v)
        d.add_paragraph()
    def NOTE(): P("Student interpretation: [write 3-4 sentences in your own words explaining what the figure/table shows and why it matters for classification.]")

    # ---- title + abstract ----
    d.add_heading("ForenSight AI", 0)
    P("Explainable Android Malware Triage Using Static and Network Features")
    P("CT-264 Programming for Artificial Intelligence - Complex Computing Activity (CLO3 / C3)\nDepartment of Computer Science and Information Technology, NED University of Engineering & Technology\n"
      "BS Computer Science (Cyber Security)\nStudent: [name, roll number]   Instructor: [name]   Date: [date]")
    d.add_page_break()
    H("Abstract")
    s, n = res.get("static"), res.get("network")
    ab = "This project builds two independent binary classifiers that help a security analyst prioritise Android evidence: one on static application features (permissions and API calls) and one on network-flow features. "
    if s: ab += f"On the static experiment the selected model ({s['best_model']}) reached F1 = {pc(s['models'][s['best_model']]['tuned']['f1'])} and recall = {pc(s['models'][s['best_model']]['tuned']['recall'])} on a held-out test set. "
    if n: ab += f"On the network experiment, evaluated with capture-aware splitting, the selected model ({n['best_model']}) reached F1 = {pc(n['models'][n['best_model']]['tuned']['f1'])} and recall = {pc(n['models'][n['best_model']]['tuned']['recall'])}. "
    ab += "Three scikit-learn classifiers were compared, tuned with cross-validation, and explained with feature importance and per-prediction contributions. A Flask application with a vanilla HTML/CSS/JavaScript interface serves the saved models."
    P(ab)

    H("1. Introduction")
    P("Android is the most widely used mobile operating system and therefore a constant target for malicious applications. Security teams receive far more suspicious applications than they can inspect by hand. A triage tool that ranks applications by risk lets analysts spend their time on the most suspicious cases first. This report describes ForenSight AI, an academic prototype that applies supervised machine learning to two kinds of evidence: what an application declares and contains (static analysis) and how it behaves on the network (flow statistics).")
    H("2. Problem Statement")
    P("Given a record describing an Android application (static features) or a network flow generated while an application was running (flow features), predict whether it is benign or potentially malicious. The task is binary classification. The output is a probability of malware, a label (likely benign / potentially malicious) and the features that most influenced the prediction. A prediction is a triage signal. It does not prove malicious intent, and it does not prove that malware executed.")
    P("Manual investigation does not scale: reverse engineering a single application can take hours, malware authors obfuscate code and repackage popular applications, and signature-based tools miss unseen variants. A learned model generalises from labelled examples and can score thousands of records in seconds, which motivates the machine-learning approach.")
    H("3. Project Objectives")
    B(["Select and verify two authentic public datasets (one static, one network).", "Preprocess and explore both datasets without data leakage.",
       "Train and compare Logistic Regression, Random Forest and Gradient Boosting independently on each dataset.", "Improve performance with cross-validated hyper-parameter search.",
       "Evaluate with accuracy, precision, recall, F1, ROC-AUC, confusion matrices and false-positive rate.", "Explain predictions and discuss the difference between importance and causation.",
       "Deliver a working Flask + HTML/CSS/JavaScript application backed by the saved models."])
    H("4. Background and Motivation")
    P("Static analysis inspects an application without running it. Permissions declared in the manifest (for example reading SMS or accessing location) and API calls found in the code are cheap to extract and are widely used as features. Network analysis observes traffic produced while an application runs; statistics such as flow duration, packet counts and inter-arrival times can reveal command-and-control or data-exfiltration behaviour. Muzaffar et al. (2022) re-implemented many published studies and found that API calls and TCP network-traffic features were among the most predictive feature families, with Random Forests generally the strongest models. The two evidence types are complementary, but they come from different datasets and applications, so this project treats them as two separate experiments and does not merge them.")

    H("5. Dataset Description and Authentic Sources")
    TABLE(["Item", "Static (Experiment A)", "Network (Experiment B)"], [
        ["Dataset", "TUANDROMD (Tezpur University Android Malware Dataset)", "CIC-AndMal2017"],
        ["Creators", "P. Borah, D. K. Bhattacharyya, J. K. Kalita (Tezpur University)", "A. H. Lashkari, A. F. A. Kadir, L. Taheri, A. A. Ghorbani (Canadian Institute for Cybersecurity, UNB)"],
        ["Repository", "UCI Machine Learning Repository, dataset 855 (preprocessed version also listed as dataset 813)", "https://www.unb.ca/cic/datasets/andmal2017.html"],
        ["Licence", "CC BY 4.0 (stated on the UCI page)", "Free for research; cite the paper (check the terms on the download page)"],
        ["Evidence", "214 permission features + 27 API features (binary)", "~80 CICFlowMeter-V3 flow statistics per network flow"],
        ["Target", "Label: malware / goodware", "Benign vs malware (adware, ransomware, scareware, SMS malware) taken from the capture folder / Label column"],
        ["Collection", "Static analysis of applications; features extracted per APK", "Apps installed and run on real smartphones; traffic captured as PCAP and converted to flows"],
        ["Identifiers", "None (no app id, no family)", "Capture file of each flow (used for group-aware splitting)"]])
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if not r: continue
        L = r["data_log"]
        P(f"{name} dataset as used: {L['rows_loaded']:,} rows loaded, {L['rows_final']:,} after cleaning, {L['n_features']} numeric features. Class counts after cleaning: benign {L['class_counts']['benign']:,}, malware {L['class_counts']['malware']:,}.")

    H("6. Data Preprocessing")
    P("The same cleaning code (src/preprocessing/loaders.py) is applied to both datasets and every step is counted in the preprocessing log shown in the application and reproduced here.")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if not r: continue
        L = r["data_log"]
        H(f"6.{1 if key == 'static' else 2} {name} experiment", 2)
        B([f"Rows without a valid label removed: {L['rows_dropped_missing_label']}.", f"Exact duplicate rows removed before splitting: {L['duplicate_rows_removed']:,}.",
           f"Missing or invalid cells after numeric conversion: {L['missing_cells_after_coercion']:,} (imputed with the training median inside the pipeline).",
           f"Zero-variance features dropped using the training split only: {len(r['zero_variance_features_dropped'])}.",
           ("Identifier columns removed to avoid leakage: " + ", ".join(L.get("identifier_columns_removed", [])) + ".") if L.get("groups_available") else "No identifier columns existed.",
           "Standardisation is used only inside the Logistic Regression pipeline, because tree ensembles do not need scaled inputs."])
    P("Leakage prevention: the data is split first; imputers, scalers and the variance filter are fitted on the training portion only; hyper-parameters are chosen by cross-validation inside the training portion; the test set is used once at the end.")

    H("7. Exploratory Data Analysis")
    for key, name in (("static", "Static"), ("network", "Network")):
        e = eda.get(key)
        if not e: continue
        H(f"7.{1 if key == 'static' else 2} {name} dataset", 2)
        for k, v in e.items():
            if isinstance(v, str) and v.startswith("figures/"):
                FIG(IMG / Path(v).name, f"Figure: {name.lower()} EDA - {Path(v).stem.replace('_', ' ')}")
        if key == "static" and "mean_features_per_app" in e:
            m = e["mean_features_per_app"]; P(f"Observation (computed): the average number of permissions/APIs present per app is {m['benign']:.1f} for benign apps and {m['malware']:.1f} for malware.")
        if key == "static" and e.get("prevalence_top"):
            f0, v0 = next(iter(e["prevalence_top"].items())); P(f"Observation (computed): the feature with the largest usage gap is {f0} (benign {pc(v0['benign'])}, malware {pc(v0['malware'])}).")
        if key == "network" and e.get("top_mi_features"):
            P("Observation (computed): the flow features most associated with the label by mutual information are " + ", ".join(e["top_mi_features"]) + ".")
        NOTE()

    H("8. Class Imbalance Analysis")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if r:
            P(f"{name}: majority-to-minority ratio {r['imbalance_ratio_majority_to_minority']:.2f}. Test split class counts: benign {r['test_class_counts']['benign']:,}, malware {r['test_class_counts']['malware']:,}.")
    P("Implications: with imbalance, accuracy alone can look high while the minority class is missed, so recall, precision, F1 and the false-positive rate are reported. Stratified splitting keeps class proportions in both splits and in each cross-validation fold. Class weights ('balanced') are used for Logistic Regression and Random Forest and balanced sample weights for Gradient Boosting. SMOTE was not used: it requires the imbalanced-learn library outside the prescribed stack, and class weighting addresses the same problem without creating artificial records.")

    H("9. Proposed Methodology")
    FIG(tmp / "method.png", "Figure: methodology flowchart")
    P("Each experiment follows the same steps with its own preprocessing pipeline, models, evaluation results and feature schema. The final model is chosen by mean 5-fold cross-validated F1 on the training split, never by test-set performance.")
    H("10. System Architecture")
    FIG(tmp / "arch.png", "Figure: system architecture")
    P("The Flask application loads the saved Joblib pipelines once, validates every request (column names, numeric values, file type, row limit) and returns JSON. The front end is plain HTML, CSS and JavaScript with Chart.js and shows only values read from the backend; nothing is hard-coded.")
    H("11. Machine-Learning Algorithms")
    P("Logistic Regression models the log-odds of malware as a weighted sum of (standardised) features. It is fast, a natural baseline and directly interpretable through its coefficients; regularisation strength C is tuned.")
    P("Random Forest averages many decision trees trained on bootstrap samples and random feature subsets. It captures non-linear interactions, is robust to scale and gives impurity-based feature importance. Tuned: number of trees, maximum depth, minimum samples per leaf.")
    P("Gradient Boosting builds shallow trees sequentially, each correcting the errors of the previous ones. It is often very accurate but more sensitive to its settings. Tuned: number of trees, learning rate, tree depth.")
    H("12. Implementation")
    B(["src/preprocessing: loaders and the CIC-AndMal2017 flow builder.", "src/models: training/tuning script and inference helper.", "src/evaluation: metrics, EDA figures and explanation functions.",
       "backend: Flask app and routes. frontend: templates, CSS, JavaScript. tests: pytest suite.", "Random seed 42 is used everywhere so results are reproducible."])
    H("13. Model Optimisation")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if not r: continue
        P(f"{name}: hyper-parameters were searched with 5-fold cross-validation on the training split (GridSearchCV for Logistic Regression, RandomizedSearchCV for the tree ensembles, scoring = F1)" + (f"; tuning used a {r['tuning_rows_used']:,}-row training subsample to keep run time reasonable, and the best settings were then refitted on the full training split." if r["tuning_rows_used"] < r["n_train"] else "."))
        TABLE(["Model", "Selected parameters", "CV F1 (train)", "Baseline F1 (test)", "Tuned F1 (test)"],
              [[m, json.dumps(v["best_params"]), pc(v["cv_f1_train"]), pc(v["baseline"]["f1"]), pc(v["tuned"]["f1"])] for m, v in r["models"].items()])

    H("14. Experimental Setup and Evaluation Metrics")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if r: P(f"{name}: {r['split']}. Training rows {r['n_train']:,}; test rows {r['n_test']:,}.")
    P("Metrics (positive class = malware): accuracy, precision (flagged items that are malware), recall (malware that was caught), F1 (harmonic mean of precision and recall), false-positive rate = FP / (FP + TN), ROC-AUC (ranking quality across thresholds) and the confusion matrix. A false negative (missed malware) is usually more costly than a false positive (extra manual review), so recall and FPR are read together.")
    H("15. Experimental Results")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if not r: continue
        H(f"15.{1 if key == 'static' else 2} {name} experiment", 2)
        rows = []
        for m, v in r["models"].items():
            for ver in ("baseline", "tuned"):
                x = v[ver]; rows.append([m, ver, pc(x["accuracy"]), pc(x["precision"]), pc(x["recall"]), pc(x["f1"]), pc(x["false_positive_rate"]), pc(x["roc_auc"])])
        TABLE(["Model", "Version", "Acc.", "Prec.", "Recall", "F1", "FPR", "ROC-AUC"], rows)
        for m, v in r["models"].items():
            (tn, fp), (fn, tp) = v["tuned"]["confusion_matrix"]
            P(f"Confusion matrix, {m} (tuned): TN={tn:,}, FP={fp:,}, FN={fn:,}, TP={tp:,}.")
        b = r["models"][r["best_model"]]["tuned"]
        P(f"Selected model: {r['best_model']} (highest cross-validated F1 on the training split). Test-set results: F1 {pc(b['f1'])}, recall {pc(b['recall'])}, precision {pc(b['precision'])}, false-positive rate {pc(b['false_positive_rate'])}, ROC-AUC {pc(b['roc_auc'])}.")
        gap = r["models"][r["best_model"]]["cv_f1_train"] - b["f1"]
        P(f"Overfitting check (computed): cross-validated F1 on training data minus test F1 = {gap * 100:+.2f} percentage points" + (" - a positive gap suggests the model is slightly more optimistic on data it was tuned on." if gap > 0 else " - the test result is not lower than the cross-validation estimate."))
        NOTE()
    H("16. Model Comparison")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if not r: continue
        top = max(r["models"], key=lambda m: r["models"][m]["tuned"]["recall"]); low = min(r["models"], key=lambda m: r["models"][m]["tuned"]["false_positive_rate"] or 1)
        P(f"{name}: highest tuned recall = {top} ({pc(r['models'][top]['tuned']['recall'])}); lowest false-positive rate = {low} ({pc(r['models'][low]['tuned']['false_positive_rate'])}). Differences of a few tenths of a percentage point may not be meaningful with a single split.")
    NOTE()
    H("17. Explainability")
    for key, name in (("static", "Static"), ("network", "Network")):
        r = res.get(key)
        if not r: continue
        H(f"17.{1 if key == 'static' else 2} {name}", 2)
        P(f"Model-native view ({r['importance']['native']['kind']}) and permutation importance ({r['importance']['permutation']['kind']}), top 10:")
        TABLE(["Rank", "Model-native feature", "Value", "Permutation feature", "Drop in F1"],
              [[i + 1, a["feature"], f"{a['value']:.4f}", b["feature"], f"{b['value']:.4f}"] for i, (a, b) in enumerate(zip(r["importance"]["native"]["items"][:10], r["importance"]["permutation"]["items"][:10]))])
    P("Per-prediction explanations use occlusion: each feature is replaced by its training median and the change in malware probability is shown. Importance describes the model's behaviour, not causation: a permission can be informative because malware and benign apps use it at different rates (association), not because the permission makes an app malicious. Correlated features split credit, and importance depends on the data and the model.")
    H("18. Challenges and Limitations")
    B(["Static data has no application identifiers, so near-duplicate applications or families could appear in both train and test; the reported score may be optimistic and is not claimed to be leakage-free.",
       "Network flows from the same capture are strongly related; group-aware splitting was used so a capture is never shared between train and test, but different captures of the same malware family may still be similar.",
       "Datasets reflect their collection period; new malware families and obfuscation can reduce real-world accuracy (concept drift).",
       "The two datasets contain different applications, so the experiments cannot be combined or compared as if they were the same samples.",
       "Network flow rows may be sub-sampled per capture to keep the table manageable (recorded in datasets/network_analysis/cicandmal2017_flows.meta.json).",
       "Labels come from the dataset creators' collection process and may contain errors."])
    H("19. Ethical Considerations")
    P("The system outputs a risk score, not a verdict. Wrongly flagging a legitimate app (false positive) can harm developers and users, and missing malware (false negative) can harm victims; a human analyst must review high-risk cases. No malware was executed in this project; only existing labelled public datasets were analysed. The datasets contain feature statistics, not personal user content. The tool must not be used to accuse individuals or as sole evidence in an investigation.")
    H("20. Conclusion")
    c = "ForenSight AI shows that simple, explainable scikit-learn models can triage Android applications from static and network features when evaluated carefully. "
    if s and n: c += f"The static experiment selected {s['best_model']} and the network experiment selected {n['best_model']}; the exact scores are given in Section 15. "
    c += "Future work: multi-class family classification, newer datasets for drift testing, combining evidence for the same applications when a shared-application dataset is available, and calibrated thresholds chosen for an analyst's cost of errors."
    P(c)
    H("21. References")
    for r_ in [
        "Borah, P., Bhattacharyya, D. K., & Kalita, J. K. (2020). TUANDROMD / Tezpur University Android Malware Dataset paper. IEEE CICT 2020. DOI: 10.1109/CICT51604.2020.9312053 (add the exact paper title from the DOI page).",
        "Borah, P., & Bhattacharyya, D. K. (2020). TUANDROMD (Tezpur University Android Malware Dataset) [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5560H",
        "Lashkari, A. H., Kadir, A. F. A., Taheri, L., & Ghorbani, A. A. (2018). Toward Developing a Systematic Approach to Generate Benchmark Android Malware Datasets and Classification. 2018 International Carnahan Conference on Security Technology (ICCST). IEEE.",
        "Canadian Institute for Cybersecurity. Android Malware Dataset (CIC-AndMal2017). https://www.unb.ca/cic/datasets/andmal2017.html",
        "Muzaffar, A., Ragab Hassen, H., Zantout, H., & Lones, M. A. Reassessing feature-based Android malware detection in a contemporary context. arXiv:2301.12778.",
        "Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825-2830.",
        "Breiman, L. (2001). Random Forests. Machine Learning, 45(1), 5-32.",
        "Friedman, J. H. (2001). Greedy function approximation: a gradient boosting machine. Annals of Statistics, 29(5), 1189-1232."]:
        d.add_paragraph(r_, style="List Number")
    d.save(OUT); print("Report written:", OUT)


if __name__ == "__main__":
    main()
