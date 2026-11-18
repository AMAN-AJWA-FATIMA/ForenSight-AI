"""Flask routes: the single dashboard page and the JSON APIs behind it.
Every number on the page comes from artifacts/ (real training results), never from the front end."""
import io, json
import pandas as pd
from flask import Blueprint, current_app, jsonify, render_template, request
from src.models.inference import ModelNotReady, load_model, predict_frame

bp = Blueprint("main", __name__)
EXPERIMENTS = ("static", "network")
MAX_ROWS = 5000


def _artifacts():
    return current_app.config["ARTIFACTS_DIR"]


def _read_json(name, hint):
    path = _artifacts() / name
    if not path.exists():
        return jsonify(error=f"{name} not found. {hint}"), 404
    return jsonify(json.loads(path.read_text()))


@bp.route("/")
def landing():
    return render_template("landing.html")


@bp.route("/app")
def dashboard():
    return render_template("index.html")


@bp.route("/api/health")
def health():
    status = {}
    for exp in EXPERIMENTS:
        try:
            load_model(exp, _artifacts()); status[exp] = "ready"
        except ModelNotReady as e:
            status[exp] = str(e)
        except Exception as e:                      # corrupted or incompatible model file
            status[exp] = f"model failed to load: {e}"
    return jsonify(status)


@bp.route("/api/results")
def results():
    return _read_json("evaluation_results.json", "Run: python -m src.models.train --experiment both")


@bp.route("/api/dashboard-data")
def dashboard_data():
    return _read_json("dashboard_data.json", "Run: python -m src.evaluation.dashboard_data")


@bp.route("/api/<exp>/schema")
def schema(exp):
    if exp not in EXPERIMENTS:
        return jsonify(error="Unknown experiment"), 404
    try:
        art = load_model(exp, _artifacts())
    except ModelNotReady as e:
        return jsonify(error=str(e)), 404
    top = art["top_features"]
    return jsonify(model=art["model_name"], feature_names=art["feature_names"], top_features=top,
                   feature_stats={f: art["feature_stats"][f] for f in top}, background={f: art["background"][f] for f in top})


def _frame_from_request(art):
    """Return (DataFrame, allow_partial) from a CSV upload, a list of records or one feature dict."""
    if "file" in request.files:
        upload = request.files["file"]
        if not upload.filename.lower().endswith(".csv"):
            raise ValueError("Please upload a .csv file.")
        df = pd.read_csv(io.BytesIO(upload.read()))
        if df.empty:
            raise ValueError("The CSV has no rows.")
        return df, False
    body = request.get_json(silent=True) or {}
    if isinstance(body.get("records"), list) and body["records"]:      # several full records at once
        return pd.DataFrame(body["records"]), False
    feats = body.get("features")
    if not isinstance(feats, dict) or not feats:
        raise ValueError('Send {"features": {...}}, {"records": [...]} or upload a CSV.')
    unknown = [k for k in feats if k not in art["feature_names"]]
    if unknown:
        raise ValueError(f"Unknown feature name(s): {unknown[:5]}")
    try:
        return pd.DataFrame([{k: float(v) for k, v in feats.items()}]), True   # missing features use training medians
    except (TypeError, ValueError):
        raise ValueError("All feature values must be numbers.")


@bp.route("/api/<exp>/predict", methods=["POST"])
def predict(exp):
    if exp not in EXPERIMENTS:
        return jsonify(error="Unknown experiment"), 404
    try:
        art = load_model(exp, _artifacts())
        df, partial = _frame_from_request(art)
        if len(df) > MAX_ROWS:
            raise ValueError(f"Too many rows ({len(df)}). Limit is {MAX_ROWS}.")
        return jsonify(predict_frame(exp, df, allow_partial=partial, artifacts_dir=_artifacts()))
    except ModelNotReady as e:
        return jsonify(error=str(e)), 503
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except pd.errors.ParserError:
        return jsonify(error="The file could not be parsed as CSV."), 400
    except Exception as e:                           # never crash the UI
        current_app.logger.exception("prediction failed")
        return jsonify(error=f"Prediction failed: {e}"), 500
