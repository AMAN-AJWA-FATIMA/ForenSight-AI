"""Run:  python -m backend.app   ->  http://127.0.0.1:5000"""
from flask import Flask
from src import config
from backend.routes import bp


def create_app(artifacts_dir=None):
    app = Flask(__name__, template_folder=str(config.ROOT / "frontend" / "templates"),
                static_folder=str(config.ROOT / "frontend" / "static"))
    app.config["ARTIFACTS_DIR"] = artifacts_dir or config.ARTIFACTS
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024      # 25 MB upload cap
    app.register_blueprint(bp)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
