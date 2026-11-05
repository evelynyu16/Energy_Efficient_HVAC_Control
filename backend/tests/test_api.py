import pytest
from fastapi.testclient import TestClient

from app.config import SAMPLE_DATA_DIR
from app.main import create_app


@pytest.fixture
def make_client(tmp_path):
    def _make():
        app = create_app(db_path=tmp_path / "test.db", data_dir=tmp_path / "none",
                         fallback_dir=SAMPLE_DATA_DIR)
        return TestClient(app)
    return _make


def test_full_session_flow_and_persistence(make_client):
    with make_client() as c:
        assert c.get("/api/health").json()["simulation"] is True
        assert c.get("/api/dataset").json()["report"]["invalid_records"] == 1

        sid = c.post("/api/sessions").json()["session_id"]
        assert c.post(f"/api/sessions/{sid}/step", json={"count": 1}).status_code == 409
        assert c.post(f"/api/sessions/{sid}/play").json()["status"] == "RUNNING"
        body = c.post(f"/api/sessions/{sid}/step", json={"count": 100}).json()
        assert len(body["frames"]) == 100 and body["state"]["cursor"] == 100

        c.post(f"/api/sessions/{sid}/pause")
        assert c.post(f"/api/sessions/{sid}/step", json={"count": 1}).status_code == 409

        m = c.post(f"/api/sessions/{sid}/manual", json={"mode": "COOLING", "reason": "demo"})
        assert m.json()["source"] == "MANUAL"
        c.post(f"/api/sessions/{sid}/auto", json={"reason": "done"})
        report = c.post(f"/api/sessions/{sid}/end").json()
        assert report["status"] == "ENDED" and "disclaimer" in report

        new_sid = c.post("/api/sessions").json()["session_id"]   # reset keeps old logs
        assert new_sid != sid
        events = c.get(f"/api/sessions/{sid}/events").json()
        assert events["total"] >= 3

    with make_client() as c:  # restart: events and settings persist
        assert c.get(f"/api/sessions/{sid}/events").json()["total"] == events["total"]
        assert c.get(f"/api/sessions/{sid}/report").json()["session_id"] == sid
        assert c.get(f"/api/sessions/{new_sid}").json()["status"] == "INTERRUPTED"


def test_settings_validation_and_change_log(make_client):
    with make_client() as c:
        bad = c.put("/api/settings", json={"lower_bound_c": 25})
        assert bad.status_code == 422
        ok = c.put("/api/settings", json={"vacancy_delay_s": 900})
        assert ok.status_code == 200
        assert ok.json()["changes"] == [
            {"field": "vacancy_delay_s", "old_value": 600, "new_value": 900}
        ]
        assert c.get("/api/settings/changes").json()[0]["field"] == "vacancy_delay_s"


def test_full_playback_is_deterministic(make_client):
    def run():
        with make_client() as c:
            sid = c.post("/api/sessions").json()["session_id"]
            c.post(f"/api/sessions/{sid}/play")
            modes = []
            while True:
                r = c.post(f"/api/sessions/{sid}/step", json={"count": 500}).json()
                modes += [f["proposed"]["mode"] for f in r["frames"]]
                if r["state"]["status"] == "COMPLETED":
                    return modes, c.get(f"/api/sessions/{sid}/report").json()
    (m1, r1), (m2, r2) = run(), run()
    assert m1 == m2
    assert {k: v for k, v in r1.items() if k != "session_id"} == \
           {k: v for k, v in r2.items() if k != "session_id"}
    assert r1["excluded_gap_s"] > 0
    assert r1["baseline"]["active_s"] > 0
