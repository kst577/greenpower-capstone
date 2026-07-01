"""Central configuration: paths, dataset periods, and physical constants.

All modules import from here so the pipeline stays consistent end to end.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEANED = DATA / "cleaned"
OUTPUTS = ROOT / "outputs"
FIGS = OUTPUTS / "figures"
DB_PATH = DATA / "greenpower.db"          # runnable SQLite store (portable)

for _p in (RAW, CLEANED, OUTPUTS, FIGS):
    _p.mkdir(parents=True, exist_ok=True)

# ---- dataset periods (match the Week 1-3 deliverables) ----
CONS_START, CONS_END = "2006-12-16", "2010-11-26"     # UCI household
GEN_START,  GEN_END  = "2018-01-01", "2020-06-30"     # SCADA wind
WX_START,   WX_END   = "2006-12-16", "2020-12-31"     # NOAA weather (covers both)

# ---- physical constants ----
RATED_KW = 3600.0                 # SCADA wind farm rated capacity
HDD_BASE_C = 18.0                 # heating degree base
CDD_BASE_C = 24.0                 # cooling degree base
CONS_MEAN_KW = 1.092              # published Week 2 mean active power (calibration target)

# ---- modelling ----
TEST_DAYS = 60                    # chronological hold-out
LAGS = [1, 24, 168]              # hourly, daily, weekly
ROLL_WINDOW = 24

# ---- style (matches the weekly reports) ----
DARK = "#1f7045"; MID = "#3f9b6e"; LIGHT = "#a9cdb6"
ORANGE = "#d9744f"; RED = "#c0392b"; GRID = "#d9d9d9"
SEED = 20260626
