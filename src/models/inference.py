"""Load a saved pipeline and predict. Feature order always comes from the training schema."""
import joblib
import pandas as pd
from src import config
from src.evaluation.explain import local_explanation

_CACHE = {}


class ModelNotReady(Exception):
    pass


def _model_path(name, artifacts_dir):
    """Resolve the model artifact, preferring the improved network model."""
    if name == "network":
        improved_path = artifacts_dir / "improved" / "network_model.joblib"
        if improved_path.exists():
            return improved_path

    return artifacts_dir / f"{name}_model.joblib"


def load_model(name, artifacts_dir=config.ARTIFACTS):
    path = _model_path(name, artifacts_dir)
    key = str(path.resolve())

    if key not in _CACHE:
        if not path.exists():
            raise ModelNotReady(
                f"{path.name} not found. "
                f"Train first: python -m src.models.train --experiment {name}"
            )
        _CACHE[key] = joblib.load(path)

    return _CACHE[key]


def predict_frame(
    name,
    df: pd.DataFrame,
    allow_partial=False,
    explain_rows=3,
    artifacts_dir=config.ARTIFACTS,
):
    """Validate columns, coerce to numbers, predict, explain the first few rows.
    allow_partial=True fills absent columns with training medians (used by the manual form only).
    """
    art = load_model(name, artifacts_dir)
    feats = art["feature_names"]
    missing = [f for f in feats if f not in df.columns]

    if missing and not allow_partial:
        raise ValueError(
            f"CSV is missing {len(missing)} required column(s), e.g. {missing[:8]}"
        )

    df = df.copy()
    for f in missing:
        df[f] = art["background"][f]

    X = df[feats].apply(pd.to_numeric, errors="coerce")
    bad = int(X.isna().all(axis=1).sum())

    if bad == len(X):
        raise ValueError("No usable numeric rows found in the input.")

    X = X.fillna(pd.Series(art["background"]))
    probs = art["pipeline"].predict_proba(X)[:, 1]
    thr = float(art.get("threshold", 0.5))

    out = []
    for i, p in enumerate(probs):
        rec = {
            "row": i,
            "malware_probability": float(p),
            "label": (
                "potentially malicious"
                if p >= thr
                else "likely benign"
            ),
        }

        if i < explain_rows:
            rec["explanation"] = local_explanation(
                art["pipeline"], X.iloc[i], art["background"], feats
            )

        out.append(rec)

    return {
        "model": art["model_name"],
        "n_rows": len(out),
        "partial_input": bool(missing),
        "n_features_filled_with_median": len(missing),
        "predictions": out,
        "disclaimer": (
            "Triage score only: it does not prove malicious intent or execution."
        ),
    }
