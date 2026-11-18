import pandas as pd
from pathlib import Path

ROOT = Path(".")
OUTPUT_DIR = Path("reports/dataset_inspection")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDED = {".venv", "venv", ".git", "__pycache__", "node_modules"}

csv_files = [
    p for p in ROOT.rglob("*.csv")
    if not any(part in EXCLUDED for part in p.parts)
    and "dataset_inspection" not in p.parts
]

if not csv_files:
    print("No CSV files found anywhere in the project.")
    raise SystemExit(1)

for file in csv_files:
    print(f"\nInspecting: {file}")

    try:
        df = pd.read_csv(file, nrows=200000, low_memory=False)

        report = [
            f"Dataset: {file}",
            f"Rows inspected: {len(df)}",
            f"Columns: {len(df.columns)}",
            f"Shape inspected: {df.shape}",
            "\nCOLUMN NAMES AND DATA TYPES:",
            df.dtypes.to_string(),
            "\nMISSING VALUES:",
            df.isnull().sum().to_string(),
            "\nUNIQUE VALUES:",
            df.nunique().to_string(),
            "\nNUMERIC STATISTICS:",
            df.describe().to_string(),
            "\nSAMPLE ROWS:",
            df.head(5).to_string(),
        ]

        # Class distribution for likely label columns
        label_cols = [
            c for c in df.columns
            if any(x in c.lower() for x in
                   ["label", "class", "target", "category"])
        ]

        for col in label_cols:
            report.extend([
                f"\nDISTRIBUTION OF {col}:",
                df[col].value_counts(dropna=False).to_string()
            ])

        output_name = str(file).replace("/", "_").replace("\\", "_")
        output_file = OUTPUT_DIR / f"{output_name}_schema.txt"

        output_file.write_text("\n".join(report))

        print(f"Saved: {output_file}")

    except Exception as e:
        print(f"ERROR: {file}: {e}")

print(f"\nInspection completed. Reports: {OUTPUT_DIR}")
print(f"Total CSV files inspected: {len(csv_files)}")
