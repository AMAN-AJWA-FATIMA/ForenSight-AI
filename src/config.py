"""Central paths and constants (all relative to the project root)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_STATIC = ROOT / "datasets" / "static_analysis"
DATA_NETWORK = ROOT / "datasets" / "network_analysis"
ARTIFACTS = ROOT / "artifacts"
FIGURES = ROOT / "reports" / "figures"      # matplotlib EDA figures (notebooks + report)

STATIC_CSV = DATA_STATIC / "TUANDROMD.csv"
NETWORK_CSV = DATA_NETWORK / "cicandmal2017_flows.csv"   # built by src/preprocessing/build_network_dataset.py
NETWORK_RAW_DIR = DATA_NETWORK / "raw"                    # unzip CICAndMal2017 flow CSVs here

RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
