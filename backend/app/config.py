"""Runtime configuration. Paths can be overridden with environment variables."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Directory holding the UCI Occupancy Detection text files (datatraining.txt, datatest.txt,
# datatest2.txt). Falls back to the bundled sample when the raw files are absent.
DATA_DIR = Path(os.environ.get("HVAC_DATA_DIR", REPO_ROOT / "data" / "raw"))
SAMPLE_DATA_DIR = REPO_ROOT / "data" / "sample"

# SQLite database file for settings, sessions and events.
DB_PATH = Path(os.environ.get("HVAC_DB_PATH", REPO_ROOT / "backend" / "hvac_sim.db"))

# Allowed browser origins for the React dev server.
CORS_ORIGINS = os.environ.get(
    "HVAC_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# FR-10 / FR-11: a gap between consecutive records longer than this is a data gap.
MAX_GAP_SECONDS = 5 * 60
