"""Loads the dataset once and caches it for every session."""

from __future__ import annotations

import threading
from pathlib import Path

from app.data.loader import Dataset, discover_files, load_dataset


class DatasetService:
    def __init__(self, data_dir: Path, fallback_dir: Path | None = None) -> None:
        self.data_dir = data_dir
        self.fallback_dir = fallback_dir
        self._dataset: Dataset | None = None
        self._lock = threading.Lock()

    def get(self) -> Dataset:
        with self._lock:
            if self._dataset is None:
                self._dataset = self._load()
            return self._dataset

    def reload(self) -> Dataset:
        with self._lock:
            self._dataset = self._load()
            return self._dataset

    def _load(self) -> Dataset:
        files = discover_files(self.data_dir) if self.data_dir.is_dir() else []
        label = "UCI Occupancy Detection"
        if not files and self.fallback_dir is not None:
            files = discover_files(self.fallback_dir)
            label = "Bundled synthetic sample (UCI format)"
        if not files:
            raise FileNotFoundError(
                f"no dataset files in {self.data_dir}; run scripts/fetch_dataset.py"
            )
        return load_dataset(files, label=label)
