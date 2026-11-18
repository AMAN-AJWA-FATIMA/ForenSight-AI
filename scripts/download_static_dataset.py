"""Download TUANDROMD from the official UCI Machine Learning Repository (CC BY 4.0).
Page: https://archive.ics.uci.edu/dataset/855/tuandromd+(tezpur+university+android+malware+dataset)
Run:  python scripts/download_static_dataset.py
If this fails (no internet / UCI down) download manually and place the CSV at datasets/static_analysis/TUANDROMD.csv"""
import io, sys, zipfile, urllib.request
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/855/tuandromd+tezpur+university+android+malware+dataset.zip"
OUT = Path(__file__).resolve().parents[1] / "datasets" / "static_analysis"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        data = urllib.request.urlopen(URL, timeout=60).read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(OUT)
    except Exception as e:
        print(f"Direct zip download failed ({e}); trying the ucimlrepo package (pip install ucimlrepo) ...")
        try:
            from ucimlrepo import fetch_ucirepo
            ds = fetch_ucirepo(id=855)
            df = ds.data.features.copy()
            df["Label"] = ds.data.targets.iloc[:, 0].values
            df.to_csv(OUT / "TUANDROMD.csv", index=False)
        except Exception as e2:
            sys.exit(f"Also failed ({e2}). Download manually from the UCI page above and put the CSV in {OUT}")
    print("Extracted:", [p.name for p in OUT.iterdir()])
    print("Expected file: TUANDROMD.csv  (rename if the extracted CSV has a different name)")


if __name__ == "__main__":
    main()
