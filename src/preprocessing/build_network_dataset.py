"""Build ONE flow table from the official CICAndMal2017 CICFlowMeter CSV files.

Usage:  python -m src.preprocessing.build_network_dataset [--max-rows-per-file 3000]

Put the extracted official CSVs anywhere under datasets/network_analysis/raw/ .
Binary label: path contains 'benign' -> 0 ; path contains adware/ransomware/scareware/sms -> 1 ;
otherwise the file's own 'Label' column is used (BENIGN -> 0, anything else -> 1).
Every flow keeps 'source_file' (the capture it came from) so the model can use GROUP-AWARE splits.
Rows are only SAMPLED if --max-rows-per-file is set (seeded, logged in the .meta.json file).
"""
import argparse, json
import pandas as pd
from src.config import NETWORK_RAW_DIR, NETWORK_CSV, RANDOM_STATE

MALWARE_HINTS = ("adware", "ransomware", "scareware", "sms")


def label_from(path, df):
    parts = [p.lower() for p in path.parts]
    if any("benign" in p for p in parts):
        return pd.Series(0, index=df.index), "path"
    if any(h in p for p in parts for h in MALWARE_HINTS):
        return pd.Series(1, index=df.index), "path"
    for col in df.columns:
        if col.strip().lower() == "label":
            return (~df[col].astype(str).str.strip().str.lower().str.contains("benign")).astype(int), "Label column"
    return None, None


def main(raw_dir=NETWORK_RAW_DIR, out=NETWORK_CSV, max_rows=None):
    files = sorted(raw_dir.rglob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files under {raw_dir}. See README step 'Download the network dataset'.")
    frames, meta = [], {"max_rows_per_file": max_rows, "files": {}, "skipped": []}
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        df.columns = [c.strip() for c in df.columns]
        lab, how = label_from(f.relative_to(raw_dir), df)
        if lab is None:
            meta["skipped"].append(str(f.relative_to(raw_dir)))
            continue
        n_all = len(df)
        if max_rows and n_all > max_rows:
            df = df.sample(max_rows, random_state=RANDOM_STATE)
            lab = lab.loc[df.index]
        df["label_binary"] = lab
        df["source_file"] = str(f.relative_to(raw_dir))
        meta["files"][df["source_file"].iat[0]] = {"rows_in_file": n_all, "rows_kept": len(df), "label_from": how}
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    full.to_csv(out, index=False)
    meta["total_rows"] = len(full)
    meta["class_counts"] = {"benign": int((full.label_binary == 0).sum()), "malware": int((full.label_binary == 1).sum())}
    (out.with_suffix(".meta.json")).write_text(json.dumps(meta, indent=2))
    print(f"Wrote {out} ({len(full)} flows from {len(frames)} files). Skipped (no label): {len(meta['skipped'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-rows-per-file", type=int, default=None)
    a = ap.parse_args()
    main(max_rows=a.max_rows_per_file)
