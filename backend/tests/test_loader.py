from pathlib import Path

from app.config import SAMPLE_DATA_DIR
from app.data.loader import discover_files, load_dataset

HEADER = '"date","Temperature","Humidity","Light","CO2","HumidityRatio","Occupancy"\n'


def write(tmp_path: Path, name: str, rows: list[str]) -> Path:
    p = tmp_path / name
    p.write_text(HEADER + "\n".join(rows) + "\n")
    return p


def test_uci_format_sorted_deduplicated_and_validated(tmp_path):
    a = write(tmp_path, "a.txt", [
        '"1","2015-02-04 17:52:00",23.1,27.2,426,721,0.0047,1',
        '"2","2015-02-04 17:51:00",23.2,27.3,426,721,0.0047,1',
        '"3","2015-02-04 17:53:00",23.0,140,426,721,0.0047,1',   # humidity invalid
        '"4","2015-02-04 17:54:00",abc,27,426,721,0.0047,2',     # temp + occupancy invalid
        '"5","not a date",23.0,27,426,721,0.0047,1',              # unplaceable
    ])
    b = write(tmp_path, "b.txt", [
        '"1","2015-02-04 17:51:00",23.2,27.3,426,721,0.0047,1',   # exact duplicate of a#2
        '"2","2015-02-04 17:55:00",23.0,27.0,426,721,0.0047,0',
        '"3","2015-02-04 17:55:00",23.9,27.0,426,721,0.0047,0',   # conflicting timestamp
    ])
    ds = load_dataset([a, b])
    r = ds.report
    assert r.rows_read == 8 and r.exact_duplicates_removed == 1
    assert r.unplaceable_rows == 1 and r.conflicting_timestamps == 1
    stamps = [x.timestamp for x in ds.records]
    assert stamps == sorted(stamps) and len(stamps) == 5
    assert [x.valid for x in ds.records] == [True, True, False, False, False]
    assert r.valid_records == 2 and r.invalid_records == 3


def test_bundled_sample_loads():
    ds = load_dataset(discover_files(SAMPLE_DATA_DIR))
    assert ds.report.exact_duplicates_removed == 1
    assert ds.report.invalid_records == 1
    assert ds.report.gaps_over_limit == 1
