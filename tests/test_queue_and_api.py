import sqlite3

import pytest
from fastapi.testclient import TestClient

import src.tracker as tracker


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", str(tmp_path / "apps.db"))
    return tmp_path / "apps.db"


@pytest.fixture
def client(db):
    from src.api.server import app
    return TestClient(app)


def _queue(**kw):
    defaults = dict(company="Acme", role="SWE", apply_target="https://x.test/apply",
                    apply_type="web_form", status="pending_approval", fit_score=80)
    return tracker.log_application(**{**defaults, **kw})


def test_migrates_v1_database_in_place(db):
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE applications (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL,
        role TEXT NOT NULL, apply_target TEXT, apply_type TEXT, status TEXT, skip_reason TEXT, applied_at TEXT)""")
    conn.execute("INSERT INTO applications (company, role, status, applied_at) "
                 "VALUES ('Old', 'Dev', 'applied', '2026-01-02T10:00:00')")
    conn.commit()
    conn.close()

    conn = tracker.connect()
    row = dict(conn.execute("SELECT * FROM applications").fetchone())
    assert row["submitted_at"] == "2026-01-02T10:00:00"
    assert row["created_at"] == "2026-01-02T10:00:00"
    assert tracker.is_duplicate("old", "dev")


def test_queued_job_counts_as_duplicate(db):
    _queue()
    assert tracker.is_duplicate("Acme", "SWE")


def test_claim_only_takes_approved_and_marks_applying(db):
    pending = _queue()
    approved = _queue(role="Backend", status="approved")
    row = tracker.claim_next_approved(grace_seconds=0)
    assert row["id"] == approved
    assert tracker.claim_next_approved(grace_seconds=0) is None
    conn = tracker.connect()
    statuses = dict(conn.execute("SELECT id, status FROM applications"))
    assert statuses == {pending: "pending_approval", approved: "applying"}


def test_freshly_approved_rows_wait_for_undo_window(db):
    _queue(status="approved")
    assert tracker.claim_next_approved() is None
    assert tracker.claim_next_approved(grace_seconds=0) is not None


def test_interrupted_apply_is_flagged_not_resubmitted(db):
    _queue(status="approved")
    tracker.claim_next_approved(grace_seconds=0)
    assert tracker.recover_interrupted() == 1
    assert tracker.claim_next_approved(grace_seconds=0) is None


def test_settings_defaults_and_override(db):
    assert tracker.get_setting("apply_mode") == "approval"
    tracker.set_setting("apply_mode", "auto")
    assert tracker.get_settings()["apply_mode"] == "auto"


def test_approve_then_bulk_dismiss(client):
    a, b, c = _queue(), _queue(role="B"), _queue(role="C")
    assert client.post(f"/api/applications/{a}/approve").json()["status"] == "approved"
    r = client.post("/api/queue/bulk", json={"ids": [a, b, c], "action": "dismiss"}).json()
    assert r["updated"] == 2  # a was already approved, left alone
    assert client.get(f"/api/applications/{a}").json()["status"] == "approved"


def test_cannot_set_worker_owned_status_by_hand(client):
    a = _queue()
    assert client.patch(f"/api/applications/{a}", json={"status": "applying"}).status_code == 400
    assert client.patch(f"/api/applications/{a}", json={"status": "interview"}).status_code == 200


def test_retry_only_from_failed(client):
    a = _queue()
    assert client.post(f"/api/applications/{a}/retry").status_code == 409
    tracker.set_status(a, "failed", "CAPTCHA detected")
    assert client.post(f"/api/applications/{a}/retry").json()["status"] == "approved"


def test_timeline_records_every_transition(client):
    a = _queue()
    client.post(f"/api/applications/{a}/approve")
    kinds = [e["kind"] for e in client.get(f"/api/applications/{a}").json()["events"]]
    assert kinds == ["pending_approval", "approved"]


def test_resume_endpoint_rejects_paths_outside_output(client):
    a = _queue(pdf_path="/etc/passwd")
    assert client.get(f"/api/applications/{a}/resume").status_code == 404


def test_overview_and_insights_shape(client):
    _queue(status="applied")
    tracker.log_application("Z", "Y", "", "email", "skipped", "Batch mismatch — job requires 2025")
    ov = client.get("/api/overview").json()
    assert ov["kpis"]["submitted_total"] == 1
    assert ov["focus"]["pending_approval"] == 0
    assert len(ov["heatmap"]) == 364
    ins = client.get("/api/insights").json()
    assert ins["skip_reasons"] == [{"reason": "Batch mismatch", "count": 1}]


def test_settings_validation(client):
    assert client.put("/api/settings", json={"min_fit": 150}).status_code == 400
    assert client.put("/api/settings", json={"apply_mode": "auto"}).json()["apply_mode"] == "auto"


def test_daily_cap_holds_platform_but_not_others(db):
    tracker.set_setting("daily_caps", {"linkedin": 1})
    tracker.log_application("Done", "SWE", "u", "linkedin_easy_apply", "applied")
    li = _queue(role="Li", apply_type="linkedin_easy_apply", status="approved")
    nk = _queue(role="Nk", apply_type="naukri_apply", status="approved")
    skip = tracker.capped_apply_types()
    assert skip == ("linkedin_easy_apply",)
    assert tracker.claim_next_approved(grace_seconds=0, skip_types=skip)["id"] == nk
    assert tracker.claim_next_approved(grace_seconds=0, skip_types=skip) is None
    assert li  # still approved, waits for tomorrow


def test_platforms_endpoint_reports_sessions(client, tmp_path, monkeypatch):
    import json, time
    import src.sessions as sessions
    monkeypatch.setattr(sessions, "SESSIONS_DIR", str(tmp_path))
    (tmp_path / "linkedin.json").write_text(json.dumps({"cookies": [{"name": "li_at", "expires": time.time() + 86400}]}))
    (tmp_path / "wellfound.json").write_text(json.dumps({"cookies": [{"name": "_wellfound", "expires": time.time() - 86400}]}))
    rows = {r["platform"]: r for r in client.get("/api/platforms").json()}
    assert rows["linkedin"]["status"] == "connected"
    assert rows["wellfound"]["status"] == "expired"
    assert rows["naukri"]["status"] == "missing"
    assert rows["instahyre"]["refresh_command"].endswith("setup_sessions.py instahyre")
    assert {"wellfound", "naukri"} <= sessions.logged_out_platforms()
    assert "linkedin" not in sessions.logged_out_platforms()


def test_daily_caps_setting_validation(client):
    assert client.put("/api/settings", json={"daily_caps": {"myspace": 3}}).status_code == 400
    caps = client.put("/api/settings", json={"daily_caps": {"linkedin": 10}}).json()["daily_caps"]
    assert caps["linkedin"] == 10 and caps["naukri"] == 30


def test_answering_missing_questions_saves_to_bank_and_requeues(client):
    from src.ats import answer_bank
    a = _queue()
    tracker.set_status(a, "failed", "Needs your answers: 10th score")
    tracker.set_missing_questions(a, ["How much did you score in your 10th Class?"])
    row = client.get(f"/api/applications/{a}").json()
    assert row["missing_questions"] == ["How much did you score in your 10th Class?"]
    r = client.post(f"/api/applications/{a}/answers", json={"answers": {"How much did you score in your 10th Class?": "82%"}})
    assert r.json()["status"] == "approved" and r.json()["missing_questions"] == []
    # Same question worded differently on another form
    assert answer_bank.lookup("12. How much did you score in your 10th class? Required to answer.") == "82%"
    assert client.get("/api/answers").json()[0]["answer"] == "82%"


def test_assist_endpoint_requeues_with_flag(client):
    a = _queue(apply_type="web_form")
    tracker.set_status(a, "failed", "CAPTCHA detected")
    assert client.post(f"/api/applications/{a}/assist").json()["status"] == "approved"
    row = tracker.claim_next_approved(grace_seconds=0)
    assert row["assist"] == 1
    e = _queue(role="Mail", apply_type="email")
    tracker.set_status(e, "failed", "x")
    assert client.post(f"/api/applications/{e}/assist").status_code == 400


def test_bot_stop_refuses_mid_submit_and_never_touches_launchd(client, monkeypatch):
    import src.api.server as server
    calls = []
    monkeypatch.setattr(server.subprocess, "run", lambda *a, **k: calls.append(a[0]) or type("R", (), {"returncode": 0, "stderr": ""})())
    a = _queue(status="approved")
    tracker.claim_next_approved(grace_seconds=0)        # now 'applying'
    r = client.post("/api/bot/stop")
    assert r.status_code == 409 and "Acme" in r.json()["detail"]
    assert not any(c[:2] == ["launchctl", "unload"] for c in calls)
