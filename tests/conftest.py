"""IMPORTANT: the frames below are tiny, randomly generated CODE-PATH FIXTURES used only to check that the
software runs (splits, pipelines, API). They are never saved to datasets/ or artifacts/, and no result in the
project or report comes from them. All reported results come from the real TUANDROMD / CIC-AndMal2017 files."""
import numpy as np, pandas as pd, pytest
from src.preprocessing.loaders import DataBundle


def make_fixture(n=240, n_feat=12, groups=False, seed=0):
    rng = np.random.RandomState(seed)
    y = pd.Series(rng.randint(0, 2, n))
    X = pd.DataFrame(rng.randint(0, 2, (n, n_feat)), columns=[f"feat_{i}" for i in range(n_feat)]).astype(float)
    X["feat_0"] = (y + rng.randint(0, 2, n) > 1).astype(float)     # one informative column
    X["const"] = 1.0                                                # zero-variance column
    g = pd.Series([f"cap_{i // 10}" for i in range(n)]) if groups else None
    log = {"rows_loaded": n, "rows_dropped_missing_label": 0, "duplicate_rows_removed": 0, "rows_final": n,
           "n_features": X.shape[1], "missing_cells_after_coercion": 0, "groups_available": groups,
           "class_counts": {"benign": int((y == 0).sum()), "malware": int((y == 1).sum())}}
    if groups:
        log.update(n_capture_files_final=int(g.nunique()), identifier_columns_removed=[])
    return DataBundle(X, y, g, log)


@pytest.fixture
def static_bundle():
    return make_fixture()


@pytest.fixture
def network_bundle():
    return make_fixture(groups=True, seed=1)
