#!/usr/bin/env bash
# One-shot pipeline AFTER both datasets are in place (README steps 3-4).
set -euo pipefail
cd "$(dirname "$0")/.."
python -m src.preprocessing.build_network_dataset --max-rows-per-file 100   # merge CICAndMal2017 CSVs into one flow table
python -m src.evaluation.eda --experiment both                              # matplotlib figures -> reports/figures
python -m src.models.train --experiment both                                # train, tune, evaluate, save models
python -m src.evaluation.dashboard_data                                     # data for the dashboard
python reports/build_report.py                                              # Word report from the real results
echo "Done. Start the app with:  python -m backend.app"
