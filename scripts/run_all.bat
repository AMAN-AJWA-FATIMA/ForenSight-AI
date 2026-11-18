@echo off
REM One-shot pipeline on Windows AFTER both datasets are in place (README steps 3-4).
REM Run from the project folder with the virtual environment activated.
cd /d "%~dp0.."
python -m src.preprocessing.build_network_dataset --max-rows-per-file 100 || exit /b 1
python -m src.evaluation.eda --experiment both || exit /b 1
python -m src.models.train --experiment both || exit /b 1
python -m src.evaluation.dashboard_data || exit /b 1
python reports\build_report.py || exit /b 1
echo Done. Start the app with:  python -m backend.app
