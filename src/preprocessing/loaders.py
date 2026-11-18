"""Load the two REAL datasets and document every cleaning step (nothing is invented)."""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

LABEL_MAP = {"malware": 1, "goodware": 0, "benign": 0, "malicious": 1, "1": 1, "0": 0}
STATIC_LABEL_CANDIDATES = ["Label", "label", "Class", "class", "target"]


@dataclass
class DataBundle:
    X: pd.DataFrame
    y: pd.Series
    groups: pd.Series | None
    log: dict = field(default_factory=dict)


def _encode_labels(series: pd.Series, log: dict) -> pd.Series:
    raw = series.astype(str).str.strip().str.lower()
    raw[series.isna()] = np.nan
    log["raw_label_values"] = {str(k): int(v) for k, v in series.value_counts(dropna=False).items()}
    unknown = sorted(set(raw.dropna().unique()) - set(LABEL_MAP))
    if unknown:  # inconsistent labels -> stop instead of guessing
        raise ValueError(f"Unrecognised label values {unknown}. Inspect the file and extend LABEL_MAP.")
    return raw.map(LABEL_MAP)


def _clean_common(df, y_raw, groups, log, id_like_cols=()):
    """Shared cleaning: bad labels, numeric coercion, inf->NaN, duplicates, empty columns."""
    y = _encode_labels(y_raw, log)
    log["rows_loaded"] = int(len(df))
    keep = y.notna()
    log["rows_dropped_missing_label"] = int((~keep).sum())
    df, y = df[keep], y[keep].astype(int)
    groups = groups[keep] if groups is not None else None

    df = df.drop(columns=[c for c in id_like_cols if c in df.columns])
    before_types = df.dtypes.astype(str).value_counts().to_dict()
    log["dtypes_before"] = {k: int(v) for k, v in before_types.items()}
    df = df.apply(pd.to_numeric, errors="coerce")           # invalid strings -> NaN
    df = df.replace([np.inf, -np.inf], np.nan)              # CICFlowMeter writes inf for some rates
    log["missing_cells_after_coercion"] = int(df.isna().sum().sum())

    empty = [c for c in df.columns if df[c].isna().all()]
    log["all_nan_columns_dropped"] = empty
    df = df.drop(columns=empty)

    # exact duplicates (features + label) are removed BEFORE splitting so copies cannot leak
    combined = df.copy()
    combined["__y__"] = y.values
    dup = combined.duplicated(keep="first").values
    log["duplicate_rows_removed"] = int(dup.sum())
    df, y = df[~dup], y[~dup]
    groups = groups[~dup] if groups is not None else None

    log["rows_final"] = int(len(df))
    log["n_features"] = int(df.shape[1])
    log["class_counts"] = {"benign": int((y == 0).sum()), "malware": int((y == 1).sum())}
    return df.reset_index(drop=True), y.reset_index(drop=True), \
        (groups.reset_index(drop=True) if groups is not None else None)


def load_static(path) -> DataBundle:
    df = pd.read_csv(path)
    label_col = next((c for c in STATIC_LABEL_CANDIDATES if c in df.columns), None)
    if label_col is None:
        raise ValueError(f"No label column found. Columns start with {list(df.columns[:5])}")
    log = {"source_file": str(path), "label_column": label_col, "groups_available": False}
    y_raw = df.pop(label_col)
    X, y, _ = _clean_common(df, y_raw, None, log)
    return DataBundle(X, y, None, log)


NETWORK_ID_COLS = ["Flow ID", "Source IP", "Src IP", "Destination IP", "Dst IP",
                   "Timestamp", "Source Port", "Src Port", "Unnamed: 0", "Label",
                   "source_file", "label_binary"]


def load_network(path) -> DataBundle:
    df = pd.read_csv(path, low_memory=False)
    for col in ("label_binary", "source_file"):
        if col not in df.columns:
            raise ValueError("Network CSV must be built with src/preprocessing/build_network_dataset.py "
                             f"(missing column '{col}').")
    groups = df["source_file"].astype(str)
    log = {"source_file": str(path), "label_column": "label_binary (from capture folder / Label)",
           "groups_available": True, "n_capture_files": int(groups.nunique()),
           "identifier_columns_removed": [c for c in NETWORK_ID_COLS if c in df.columns]}
    y_raw = df["label_binary"].map({0: "benign", 1: "malware"})
    X, y, g = _clean_common(df.drop(columns=["label_binary"]), y_raw, groups, log, NETWORK_ID_COLS)
    log["n_capture_files_final"] = int(g.nunique())
    return DataBundle(X, y, g, log)
