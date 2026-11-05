"""Sensor dataset import and validation (FR-01).

Accepts the UCI Occupancy Detection comma-delimited text files (datatraining.txt, datatest.txt,
datatest2.txt). Those files carry a quoted row-id column whose header is missing; pandas handles
that by using it as the index, which we discard.

Pipeline: read -> combine -> parse -> drop exact duplicates -> flag conflicting timestamps ->
validate required fields -> sort chronologically -> SensorRecord stream + ValidationReport.
Rows with an unparseable timestamp cannot be placed in time and are reported then dropped.
Other invalid rows stay in the stream with valid=False so the controller enters
DATA_UNAVAILABLE when playback reaches them (FR-11).
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.config import MAX_GAP_SECONDS
from app.control.records import SensorRecord

REQUIRED_COLUMNS = ("date", "temperature", "humidity", "occupancy")
UCI_FILES = ("datatraining.txt", "datatest.txt", "datatest2.txt")


@dataclass
class RowIssue:
    source: str
    row: int
    timestamp: str | None
    reason: str


@dataclass
class ValidationReport:
    files: list[str] = field(default_factory=list)
    rows_read: int = 0
    exact_duplicates_removed: int = 0
    conflicting_timestamps: int = 0
    unplaceable_rows: int = 0
    invalid_records: int = 0
    valid_records: int = 0
    gaps_over_limit: int = 0
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    issues: list[RowIssue] = field(default_factory=list)


@dataclass
class Dataset:
    label: str
    records: list[SensorRecord]
    report: ValidationReport


def discover_files(directory: Path) -> list[Path]:
    """Return UCI files in `directory` if present, else any *.txt / *.csv files, sorted."""
    uci = [directory / name for name in UCI_FILES if (directory / name).is_file()]
    if uci:
        return uci
    return sorted(p for p in directory.glob("*") if p.suffix.lower() in {".txt", ".csv"})


def load_dataset(paths: Iterable[Path], label: str | None = None) -> Dataset:
    paths = list(paths)
    if not paths:
        raise FileNotFoundError("no dataset files found")
    report = ValidationReport(files=[p.name for p in paths])

    frames = []
    for path in paths:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{path.name}: missing required columns {missing}")
        df = df.reset_index(drop=True)
        df["_source"] = path.name
        df["_row"] = df.index + 2  # 1-based line number including the header line
        frames.append(df[[*REQUIRED_COLUMNS, "_source", "_row"]])
    raw = pd.concat(frames, ignore_index=True)
    report.rows_read = len(raw)

    # Exact duplicates (identical required values, possibly across files).
    dup_mask = raw.duplicated(subset=list(REQUIRED_COLUMNS), keep="first")
    report.exact_duplicates_removed = int(dup_mask.sum())
    df = raw.loc[~dup_mask].copy()

    df["ts"] = pd.to_datetime(df["date"].str.strip(), errors="coerce")
    df["temp"] = pd.to_numeric(df["temperature"], errors="coerce")
    df["hum"] = pd.to_numeric(df["humidity"], errors="coerce")
    df["occ"] = pd.to_numeric(df["occupancy"], errors="coerce")

    unplaceable = df["ts"].isna()
    for _, r in df.loc[unplaceable].iterrows():
        report.issues.append(RowIssue(r["_source"], int(r["_row"]), r["date"] or None,
                                      "unparseable timestamp"))
    report.unplaceable_rows = int(unplaceable.sum())
    df = df.loc[~unplaceable].sort_values(["ts", "_source", "_row"], kind="stable")

    records: list[SensorRecord] = []
    for ts, group in df.groupby("ts", sort=True):
        first = group.iloc[0]
        if len(group) > 1:
            report.conflicting_timestamps += 1
            for _, r in group.iterrows():
                report.issues.append(RowIssue(r["_source"], int(r["_row"]), str(ts),
                                              "conflicting values for the same timestamp"))
            records.append(_record(len(records), ts, None, None, None,
                                   "conflicting values for the same timestamp"))
            continue
        error = _validate(first["temp"], first["hum"], first["occ"])
        if error:
            report.issues.append(RowIssue(first["_source"], int(first["_row"]), str(ts), error))
        records.append(_record(len(records), ts, first["temp"], first["hum"], first["occ"], error))

    report.valid_records = sum(r.valid for r in records)
    report.invalid_records = len(records) - report.valid_records
    report.gaps_over_limit = sum(
        (b.timestamp - a.timestamp).total_seconds() > MAX_GAP_SECONDS
        for a, b in zip(records, records[1:], strict=False)
    )
    if records:
        report.first_timestamp = records[0].timestamp
        report.last_timestamp = records[-1].timestamp
    return Dataset(label or ", ".join(report.files), records, report)


def _validate(temp: float, hum: float, occ: float) -> str | None:
    problems = []
    if not _finite(temp):
        problems.append("temperature is not numeric")
    if not _finite(hum):
        problems.append("humidity is not numeric")
    elif not 0 <= hum <= 100:
        problems.append("humidity outside 0-100%")
    if not _finite(occ) or occ not in (0, 1):
        problems.append("occupancy is not 0 or 1")
    return "; ".join(problems) or None


def _finite(x: float) -> bool:
    return x is not None and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def _record(index, ts, temp, hum, occ, error) -> SensorRecord:
    valid = error is None
    return SensorRecord(
        index=index,
        timestamp=ts.to_pydatetime(),
        temperature_c=float(temp) if valid else (float(temp) if _finite(temp) else None),
        humidity_pct=float(hum) if valid else (float(hum) if _finite(hum) else None),
        occupancy=int(occ) if valid else (int(occ) if _finite(occ) and occ in (0, 1) else None),
        valid=valid,
        error=error,
    )
