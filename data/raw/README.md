# Raw dataset (not committed)

Place the UCI Occupancy Detection files here:

- `datatraining.txt`
- `datatest.txt`
- `datatest2.txt`

Download them with `python scripts/fetch_dataset.py`, or manually from the UCI Machine Learning
Repository (Candanedo, 2016, CC BY 4.0). When this folder has no data files, the backend falls
back to `data/sample/sample_occupancy.txt`, which is **synthetic** and only for development.
