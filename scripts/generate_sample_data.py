"""Generate the bundled SYNTHETIC sample in UCI Occupancy Detection format.

It exists so the app and tests run without downloading the real dataset. It deliberately
contains one exact duplicate, one invalid row and one 20-minute gap to exercise FR-01/FR-11.
Output is deterministic. Usage: python scripts/generate_sample_data.py
"""

from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "sample" / "sample_occupancy.txt"


def main() -> None:
    rng = random.Random(42)
    start = datetime(2015, 2, 4, 0, 0)
    lines = ['"date","Temperature","Humidity","Light","CO2","HumidityRatio","Occupancy"']
    row_id = 1
    for minute in range(3 * 24 * 60):
        ts = start + timedelta(minutes=minute)
        if datetime(2015, 2, 5, 13, 0) <= ts < datetime(2015, 2, 5, 13, 20):
            continue  # 20-minute recording gap
        hour = ts.hour + ts.minute / 60
        occupied = int(8.5 <= hour < 12 or 13 <= hour < 17.5)
        temp = 22 + 3.2 * math.sin((hour - 9) / 24 * 2 * math.pi) + (0.8 if occupied else 0)
        temp += rng.uniform(-0.15, 0.15)
        hum = 27 + 4 * math.sin(hour / 24 * 2 * math.pi) + rng.uniform(-0.5, 0.5)
        light = 450 + rng.uniform(-20, 20) if occupied else rng.uniform(0, 5)
        co2 = 700 + rng.uniform(-50, 150) if occupied else 440 + rng.uniform(-10, 10)
        ratio = 0.0045 + rng.uniform(-0.0002, 0.0002)
        if ts == datetime(2015, 2, 6, 10, 0):
            hum = 120.0  # invalid: humidity outside 0-100 %
        line = (f'"{row_id}","{ts:%Y-%m-%d %H:%M:%S}",{temp:.4f},{hum:.4f},{light:.2f},'
                f"{co2:.2f},{ratio:.8f},{occupied}")
        lines.append(line)
        row_id += 1
        if ts == datetime(2015, 2, 4, 12, 0):
            lines.append(line)  # exact duplicate
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(lines) - 1} rows to {OUT}")


if __name__ == "__main__":
    main()
