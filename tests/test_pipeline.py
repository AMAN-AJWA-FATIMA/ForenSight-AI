import io, json
import numpy as np, pandas as pd, pytest
from src.evaluation.metrics import evaluate
from src.models import inference
from src.models.train import run_experiment, split
from src.preprocessing.loaders import load_static


def test_metrics_known_values():
    m = evaluate([0, 0, 1, 1], [0, 1, 1, 1], [0.1, 0.6, 0.7, 0.9])
    assert m["confusion_matrix"] == [[1, 1], [0, 2]]
    assert m["recall"] == 1.0 and m["false_positive_rate"] == 0.5 and m["roc_auc"] == 1.0


def test_loader_cleans_and_maps(tmp_path):
    p = tmp_path / "s.csv"
    pd.DataFrame({"a": [1, 1, 0, 1], "b": [0, 0, 1, 1], "Label": ["malware", "malware", "goodware", None]}).to_csv(p, index=False)
    b = load_static(p)
    assert b.log["rows_dropped_missing_label"] == 1 and b.log["duplicate_rows_removed"] == 1
    assert set(b.y) == {0, 1}


def test_loader_rejects_unknown_label(tmp_path):
    p = tmp_path / "s.csv"
    pd.DataFrame({"a": [1, 0], "Label": ["malware", "weird"]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        load_static(p)


def test_group_split_has_no_overlap(network_bundle):
    b = network_bundle
    tr, te, _ = split(b.X, b.y, b.groups)
    assert not set(b.groups.iloc[tr]) & set(b.groups.iloc[te])


@pytest.fixture
def trained(tmp_path, static_bundle, network_bundle):
    run_experiment("static", static_bundle, out_dir=tmp_path, fast=True)
    run_experiment("network", network_bundle, out_dir=tmp_path, fast=True)
    inference._CACHE.clear()
    return tmp_path


def test_results_file_and_test_set_not_used_for_selection(trained):
    res = json.loads((trained / "evaluation_results.json").read_text())
    for exp in ("static", "network"):
        assert res[exp]["selection_rule"].startswith("highest mean 5-fold CV F1 on the training")
        assert set(res[exp]["models"]) == {"Logistic Regression", "Random Forest", "Gradient Boosting"}
        assert "const" in res[exp]["zero_variance_features_dropped"]


@pytest.fixture
def client(trained):
    from backend.app import create_app
    return create_app(trained).test_client()


def test_api_flow(client):
    assert client.get("/api/health").get_json() == {"static": "ready", "network": "ready"}
    sch = client.get("/api/static/schema").get_json()
    assert "const" not in sch["feature_names"]
    r = client.post("/api/static/predict", json={"features": {sch["top_features"][0]: 1}})
    assert r.status_code == 200 and 0 <= r.get_json()["predictions"][0]["malware_probability"] <= 1
    assert r.get_json()["partial_input"] is True
    # full CSV
    df = pd.DataFrame([{f: 0 for f in sch["feature_names"]}] * 3)
    r = client.post("/api/static/predict", data={"file": (io.BytesIO(df.to_csv(index=False).encode()), "x.csv")})
    assert r.status_code == 200 and r.get_json()["n_rows"] == 3


def test_api_rejects_bad_input(client):
    sch = client.get("/api/static/schema").get_json()
    assert client.post("/api/static/predict", json={}).status_code == 400
    assert client.post("/api/static/predict", json={"features": {"nope": 1}}).status_code == 400
    assert client.post("/api/static/predict", json={"features": {sch["feature_names"][0]: "abc"}}).status_code == 400
    bad = pd.DataFrame({"only_col": [1]}).to_csv(index=False).encode()
    r = client.post("/api/static/predict", data={"file": (io.BytesIO(bad), "x.csv")})
    assert r.status_code == 400 and "missing" in r.get_json()["error"]
    r = client.post("/api/static/predict", data={"file": (io.BytesIO(b"x"), "x.txt")})
    assert r.status_code == 400
    assert client.get("/api/unknown/schema").status_code == 404


def test_landing_and_dashboard_pages(client):
    home = client.get("/")
    assert home.status_code == 200 and b"ForenSight-AI" in home.data and b"/app" in home.data
    page = client.get("/app")
    assert (
    page.status_code == 200
    and b"ForenSight-AI" in page.data
    and b"Dashboard" in page.data
    and b"Dataset" in page.data
)
    for asset in ("js/core.js", "js/dashboard.js", "js/data.js", "js/models.js", "js/explain.js", "js/detect.js", "js/app.js",
                  "js/landing.js", "css/style.css", "css/landing.css", "img/logo.svg"):
        assert client.get(f"/static/{asset}").status_code == 200


def test_results_contain_curves_and_new_metrics(trained):
    res = json.loads((trained / "evaluation_results.json").read_text())
    for exp in ("static", "network"):
        for m in res[exp]["models"].values():
            assert len(m["roc"]["fpr"]) == len(m["roc"]["tpr"]) > 2 and len(m["pr"]["recall"]) == len(m["pr"]["precision"]) > 2
            t = m["tuned"]
            assert t["specificity"] is not None and t["false_negative_rate"] is not None and t["pr_auc"] is not None
            assert abs(t["specificity"] + t["false_positive_rate"] - 1) < 1e-9 and "f1" in m["train"]


def test_dashboard_data_from_real_code_path(trained, static_bundle, network_bundle):
    from src.evaluation.dashboard_data import build
    for name, b in (("static", static_bundle), ("network", network_bundle)):
        raw = b.X.copy(); raw["Label" if name == "static" else "label_binary"] = (b.y.map({0: "goodware", 1: "malware"}) if name == "static" else b.y)
        if name == "network": raw["source_file"] = b.groups
        out = build(name, raw, b, trained)
        assert out["raw_stats"]["rows"] == len(raw)
        assert out["processed_stats"]["rows"] == len(b.X) and out["features"]["kept"] == out["processed_stats"]["features"]
        assert "const" in out["features"]["zero_variance_removed"]
        assert ("feature_frequency" in out) if name == "static" else (len(out["histograms"]) == 2)
        assert {s["true_label"] for s in out["samples"]} == {"benign", "malware"}


def test_predict_accepts_many_records(client):
    sch = client.get("/api/static/schema").get_json()
    rec = {f: 0 for f in sch["feature_names"]}
    r = client.post("/api/static/predict", json={"records": [rec, rec, rec]})
    assert r.status_code == 200 and r.get_json()["n_rows"] == 3 and not r.get_json()["partial_input"]


def test_dashboard_api_missing_file_is_a_clear_404(client):
    r = client.get("/api/dashboard-data")
    assert r.status_code == 404 and "dashboard_data" in r.get_json()["error"]


def test_missing_model_is_handled(tmp_path):
    from backend.app import create_app
    inference._CACHE.clear()
    c = create_app(tmp_path).test_client()
    assert c.get("/api/results").status_code == 404
    assert c.post("/api/static/predict", json={"features": {"a": 1}}).status_code in (400, 503)

def test_network_model_prefers_improved_artifact(tmp_path):
    from src.models.inference import _model_path

    improved_dir = tmp_path / "improved"
    improved_dir.mkdir()

    original_model = tmp_path / "network_model.joblib"
    improved_model = improved_dir / "network_model.joblib"

    original_model.touch()
    improved_model.touch()

    assert _model_path("network", tmp_path) == improved_model
    assert _model_path("static", tmp_path) == tmp_path / "static_model.joblib"


def test_results_api_prefers_improved_network_results(tmp_path):
    from backend.app import create_app

    original_results = {
        "static": {"best_model": "Static Original"},
        "network": {"best_model": "Network Original"},
    }

    improved_results = {
        "network": {"best_model": "Hist Gradient Boosting"},
    }

    (tmp_path / "evaluation_results.json").write_text(
        json.dumps(original_results)
    )

    improved_dir = tmp_path / "improved"
    improved_dir.mkdir()

    (improved_dir / "evaluation_results.json").write_text(
        json.dumps(improved_results)
    )

    client = create_app(tmp_path).test_client()
    response = client.get("/api/results")

    assert response.status_code == 200

    results = response.get_json()
    assert results["static"]["best_model"] == "Static Original"
    assert results["network"]["best_model"] == "Hist Gradient Boosting"


def test_results_api_falls_back_when_improved_results_missing(tmp_path):
    from backend.app import create_app

    original_results = {
        "static": {"best_model": "Static Original"},
        "network": {"best_model": "Network Original"},
    }

    (tmp_path / "evaluation_results.json").write_text(
        json.dumps(original_results)
    )

    client = create_app(tmp_path).test_client()
    response = client.get("/api/results")

    assert response.status_code == 200
    assert response.get_json()["network"]["best_model"] == "Network Original"
