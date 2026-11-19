#  (ForenSight AI)
**A Machine Learning-Based System for Android Malware Detection**

Two independent binary classifiers (benign vs potentially malicious) behind one Flask app with a clean one-page dashboard.
A score is a triage aid; it does not prove malicious intent.

| Experiment | Dataset (real, public) | Evidence | Split |
|---|---|---|---|
| A. Static | TUANDROMD, UCI #855 (CC BY 4.0) | permissions + API calls | stratified |
| B. Network | CIC-AndMal2017, UNB/CIC | CICFlowMeter flow statistics | group-aware (by capture file) |

No data is generated or invented. The repository ships **no datasets and no trained models**: you download the real data and every number
comes from training on it (provenance and known issues: `docs/DATASETS.md`).

## Layout
```
src/        preprocessing/ (loaders, network builder)  models/ (train, inference)  evaluation/ (metrics, eda, explain, dashboard_data)
backend/    app.py, routes.py (Flask)          frontend/  templates/ (index + partials), static/css, static/js (core, one file per view)
notebooks/  01-04 EDA and modelling            reports/   build_report.py (+ figures/ after EDA)
artifacts/  models and results (created by training)       tests/  docs/  scripts/
```

## 1. Setup (Ubuntu)
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
cd ForenSight-AI
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # code check on tiny fixtures (not your data)
```

## 2. Static dataset (TUANDROMD)
```bash
python scripts/download_static_dataset.py     # expect datasets/static_analysis/TUANDROMD.csv
```
If it fails, download from https://archive.ics.uci.edu/dataset/855/tuandromd+(tezpur+university+android+malware+dataset) and put the CSV at that path.

## 3. Network dataset (CIC-AndMal2017)
1. Open https://www.unb.ca/cic/datasets/andmal2017.html and download the five `*-CSVs.zip` files (Benign, Adware, Ransomware, Scareware, SMSmalware) from the CSVs folder.
2. Unzip each into `datasets/network_analysis/raw/<Name>-CSVs/` (keep the folder names; they give the labels).
3. Build the flow table (100 flows per capture file keeps training fast; raise it for more data):
```bash
python -m src.preprocessing.build_network_dataset --max-rows-per-file 100
```

## 4. EDA, training, dashboard data
```bash
python -m src.evaluation.eda --experiment both       # matplotlib figures -> reports/figures
python -m src.models.train --experiment both         # baseline + tuned LR / RF / GB -> artifacts/
python -m src.evaluation.dashboard_data              # previews, samples, EDA numbers for the dashboard
# or all of it, plus the report:   bash scripts/run_all.sh
```
Network training on a few hundred thousand flows can take a while (`--experiment static` or `network` trains one at a time).

## 5. Run the dashboard
```bash
python -m backend.app        # open http://127.0.0.1:5000
```
Dashboard (landing) · Dataset · Models · Explainability · Detect. The switch in the banner changes between static and network evidence.

## 6. Report
```bash
python reports/build_report.py     # -> reports/ForenSight_AI_Technical_Report.docx
```
Fill in the cover page, write your own interpretation where marked, add screenshots, and check it is at least 10 pages.

## 7. Put it on GitHub
```bash
git config --global user.name "Your Name" && git config --global user.email "you@example.com"
cd ForenSight-AI
git init -b main && git add . && git status     # datasets/*.csv and *.joblib are git-ignored
git commit -m "FORENSIC AI: A Machine Learning-Based System for Android Malware Detection (CT-264 CCA)"
```
Create an empty repository `ForenSight-AI` on github.com (no README or licence), then:
```bash
git remote add origin https://github.com/AMAN-AJWA-FATIMA/ForenSight-AI.git
git push -u origin main
```
Use a personal access token (Settings → Developer settings) as the password, or SSH keys / `gh auth login`.
Anyone cloning the repo repeats steps 1-4. Commit `artifacts/evaluation_results.json` after training if you want the results visible.
GitHub Pages cannot run Flask; running locally is enough for the CCA (Render or PythonAnywhere can host it later).

## Limitations
Triage only. Static data has no app ids, so near-duplicate leakage cannot be excluded. Models reflect the data's collection period.
The two datasets contain different apps, so their results are never merged. Details and viva notes: `docs/`.
