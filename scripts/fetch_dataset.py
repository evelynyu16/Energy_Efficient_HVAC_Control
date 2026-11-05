"""Download the UCI Occupancy Detection dataset (CC BY 4.0) into data/raw/.

Candanedo, L. (2016). Occupancy Detection. UCI Machine Learning Repository.
https://doi.org/10.24432/C5X01N
Usage: python scripts/fetch_dataset.py
"""

from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip"
WANTED = {"datatraining.txt", "datatest.txt", "datatest2.txt"}
DEST = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL}")
    with urllib.request.urlopen(URL, timeout=60) as resp:
        payload = resp.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for name in zf.namelist():
            base = Path(name).name
            if base in WANTED:
                (DEST / base).write_bytes(zf.read(name))
                print(f"  saved data/raw/{base}")


if __name__ == "__main__":
    main()
