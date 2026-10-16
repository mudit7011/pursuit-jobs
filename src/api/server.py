"""Local dashboard API. Reads/writes the same SQLite DB the bot uses.

Run:  python -m src.api   (binds 127.0.0.1 only — this API has no auth)
"""
import json
import os
import sys
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()  # the API reads the same .env as the bot (dashboard URL, launchd label...)

from src import resume_library, sessions, tracker
from src.ats import answer_bank

# The interpreter the bot runs on (has Playwright); `python` may not exist on the PATH.
_PYTHON = sys.executable
from src.profile import DEFAULT_PROFILE_PATH

OUTPUT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "output"))
MANUAL_MINUTES_PER_APP = 15   # rough time a manual application takes
HEARTBEAT_STALE_SECONDS = 90

app = FastAPI(title="Pursuit API", docs_url="/api/docs", openapi_url="/api/openapi.json")

_LIST_COLUMNS = (
    "id, company, role, apply_target, apply_type, status, skip_reason, location, source, "
    "fit_score, fit_reason, pdf_path IS NOT NULL AS has_resume, notes, created_at, updated_at, "
    "submitted_at, followup_at, resume_source, missing_questions"
)

_PLATFORM_BY_TYPE = {
    "linkedin_easy_apply": "linkedin", "naukri_apply": "naukri", "internshala_apply": "internshala",
    "wellfound_apply": "wellfound", "indeed_apply": "indeed", "instahyre_apply": "instahyre", "email": "email",
    "form": "google form", "web_form": "web form",
}


def _platform(row: dict) -> str:
    return row.get("source") or _PLATFORM_BY_TYPE.get(row.get("apply_type") or "", "other")


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = tracker.connect()
    try:
        out = []
        for r in conn.execute(sql, params):
            d = dict(r)
            d["platform"] = _platform(d)
            if "answers_used" in d:
                d["answers_used"] = json.loads(d["answers_used"]) if d["answers_used"] else []
            if "missing_questions" in d:
                d["missing_questions"] = json.loads(d["missing_questions"]) if d["missing_questions"] else []
            if "has_resume" in d:
                d["has_resume"] = bool(d["has_resume"])
            out.append(d)
        return out
    finally:
        conn.close()


def _get(app_id: int) -> dict:
    rows = _rows(f"SELECT {_LIST_COLUMNS}, jd_summary, answers_used FROM applications WHERE id = ?", (app_id,))
    if not rows:
        raise HTTPException(404, "Application not found")
    return rows[0]


def _reason_bucket(reason: str) -> str:
    """Collapse free-text skip/failure reasons into a few readable groups."""
    if not reason:
        return "Unknown"
    head = reason.split(" — ")[0].split(":")[0].strip()
    r = reason.lower()
    if "sync api" in r:
        return "Playwright async bug (fixed)"
    if "no form fields" in r:
        return "Form not detected"
    if "captcha" in r:
        return "CAPTCHA"
    if "google form id" in r:
        return "Not a Google Form"
    if re.search(r"\b55\d\b", r):
        return "Email rejected"
    if "did not reach submission" in r:
        return "Portal flow stuck"
    if "interrupted" in r:
        return "Interrupted"
    return head[:48] or "Unknown"


def _days_ago(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        return (datetime.now() - datetime.fromisoformat(iso)).total_seconds() / 86400
    except ValueError:
        return None


def _followups_due(settings: dict) -> list[dict]:
    days = int(settings["followup_days"])
    today = date.today().isoformat()
    return _rows(
        f"SELECT {_LIST_COLUMNS} FROM applications WHERE status = 'applied' AND ("
        "(followup_at IS NOT NULL AND followup_at <= ?) OR "
        "(followup_at IS NULL AND submitted_at <= ?)) ORDER BY submitted_at",
        (today, (datetime.now() - timedelta(days=days)).isoformat()),
    )


@app.get("/api/overview")
def overview() -> dict:
    settings = tracker.get_settings()
    conn = tracker.connect()
    try:
        counts = dict(conn.execute("SELECT status, COUNT(*) FROM applications GROUP BY status").fetchall())
        week_start = (datetime.now() - timedelta(days=7)).isoformat()
        prev_week_start = (datetime.now() - timedelta(days=14)).isoformat()
        this_week = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE submitted_at >= ?", (week_start,)
        ).fetchone()[0]
        last_week = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE submitted_at >= ? AND submitted_at < ?",
            (prev_week_start, week_start),
        ).fetchone()[0]
        needs_answers = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'failed' AND missing_questions IS NOT NULL"
        ).fetchone()[0]
        recent_failed = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'failed' AND missing_questions IS NULL AND updated_at >= ?",
            ((datetime.now() - timedelta(days=7)).isoformat(),),
        ).fetchone()[0]
        avg_fit = conn.execute(
            "SELECT AVG(fit_score) FROM applications WHERE fit_score IS NOT NULL "
            "AND status NOT IN ('skipped', 'dismissed')"
        ).fetchone()[0]
        since = (date.today() - timedelta(days=7 * 52)).isoformat()
        heat = dict(conn.execute(
            "SELECT substr(submitted_at, 1, 10) d, COUNT(*) FROM applications "
            "WHERE submitted_at >= ? GROUP BY d", (since,)
        ).fetchall())
        found = dict(conn.execute(
            "SELECT substr(created_at, 1, 10) d, COUNT(*) FROM applications "
            "WHERE created_at >= ? GROUP BY d", (since,)
        ).fetchall())
    finally:
        conn.close()

    submitted = sum(counts.get(s, 0) for s in tracker.SUBMITTED_STATUSES)
    responded = sum(counts.get(s, 0) for s in ("screening", "interview", "offer", "rejected"))
    interviews = counts.get("interview", 0) + counts.get("offer", 0)
    heartbeat = settings.get("bot_heartbeat")
    hb_age = _days_ago(heartbeat)
    recent = _rows(
        f"SELECT {_LIST_COLUMNS} FROM applications WHERE status NOT IN ('skipped') "
        "ORDER BY updated_at DESC, id DESC LIMIT 8"
    )
    return {
        "counts": counts,
        "kpis": {
            "applied_this_week": this_week,
            "applied_last_week": last_week,
            "submitted_total": submitted,
            "response_rate": round(100 * responded / submitted, 1) if submitted else None,
            "interviews": interviews,
            "offers": counts.get("offer", 0),
            "avg_fit": round(avg_fit) if avg_fit is not None else None,
            "minutes_saved": submitted * MANUAL_MINUTES_PER_APP,
            "jobs_seen": sum(counts.values()),
            "resumes": resume_library.stats(),
        },
        "focus": {
            "pending_approval": counts.get("pending_approval", 0),
            "failed": counts.get("failed", 0),
            "needs_answers": needs_answers,
            "failed_this_week": recent_failed,
            "followups_due": len(_followups_due(settings)),
            "in_flight": counts.get("approved", 0) + counts.get("applying", 0),
        },
        "funnel": [
            {"stage": "Found", "count": sum(counts.values())},
            {"stage": "Eligible", "count": sum(counts.values()) - counts.get("skipped", 0)},
            {"stage": "Applied", "count": submitted},
            {"stage": "Response", "count": responded},
            {"stage": "Interview", "count": interviews},
            {"stage": "Offer", "count": counts.get("offer", 0)},
        ],
        "heatmap": [{"date": d, "applied": heat.get(d, 0), "found": found.get(d, 0)}
                    for d in ((date.today() - timedelta(days=i)).isoformat() for i in range(7 * 52 - 1, -1, -1))],
        "recent": recent,
        "bot": {
            "heartbeat": heartbeat,
            "online": hb_age is not None and hb_age * 86400 < HEARTBEAT_STALE_SECONDS,
            "mode": settings["apply_mode"],
        },
    }


@app.get("/api/applications")
def list_applications(
    status: Optional[str] = None, q: Optional[str] = None, platform: Optional[str] = None,
    limit: int = 500, offset: int = 0,
) -> list[dict]:
    where, params = [], []
    if status:
        statuses = status.split(",")
        where.append(f"status IN ({','.join('?' * len(statuses))})")
        params += statuses
    if q:
        where.append("(company LIKE ? OR role LIKE ? OR location LIKE ?)")
        params += [f"%{q}%"] * 3
    sql = f"SELECT {_LIST_COLUMNS} FROM applications"
    if where:
        sql += " WHERE " + " AND ".join(where)
    order = "fit_score DESC, created_at" if status == "pending_approval" else "updated_at DESC, id DESC"
    sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
    rows = _rows(sql, (*params, min(limit, 2000), offset))
    if platform:
        rows = [r for r in rows if r["platform"] == platform]
    return rows


@app.get("/api/applications/{app_id}")
def get_application(app_id: int) -> dict:
    row = _get(app_id)
    row["events"] = _rows(
        "SELECT at, kind, message FROM events WHERE application_id = ? ORDER BY at, id", (app_id,)
    )
    return row


class ApplicationPatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    followup_at: Optional[str] = None


# Statuses the user may set by hand. Queue/apply states are owned by the worker.
_USER_SETTABLE = set(tracker.SUBMITTED_STATUSES) | {"dismissed", "pending_approval"}


@app.patch("/api/applications/{app_id}")
def patch_application(app_id: int, body: ApplicationPatch) -> dict:
    current = _get(app_id)
    conn = tracker._get_conn()
    try:
        if body.status and body.status != current["status"]:
            if body.status not in _USER_SETTABLE:
                raise HTTPException(400, f"Status '{body.status}' can't be set manually")
            if current["status"] == "applying":
                raise HTTPException(409, "The bot is applying to this one right now")
            tracker.set_status(app_id, body.status, "Changed in dashboard", conn=conn)
        if body.notes is not None:
            conn.execute("UPDATE applications SET notes = ? WHERE id = ?", (body.notes, app_id))
            tracker.add_event(conn, app_id, "note", "Notes updated")
        if body.followup_at is not None:
            conn.execute("UPDATE applications SET followup_at = ? WHERE id = ?", (body.followup_at or None, app_id))
        conn.commit()
    finally:
        conn.close()
    return get_application(app_id)


def _transition(app_id: int, allowed_from: tuple, to: str, message: str) -> dict:
    current = _get(app_id)
    if current["status"] not in allowed_from:
        raise HTTPException(409, f"Can't move from '{current['status']}' to '{to}'")
    tracker.set_status(app_id, to, message)
    return _get(app_id)


@app.post("/api/applications/{app_id}/approve")
def approve(app_id: int) -> dict:
    return _transition(app_id, ("pending_approval", "dismissed"), "approved", "Approved in dashboard")


@app.post("/api/applications/{app_id}/dismiss")
def dismiss(app_id: int) -> dict:
    return _transition(app_id, ("pending_approval", "approved", "failed"), "dismissed", "Dismissed in dashboard")


@app.post("/api/applications/{app_id}/retry")
def retry(app_id: int) -> dict:
    return _transition(app_id, ("failed",), "approved", "Retry requested")


@app.post("/api/applications/{app_id}/assist")
def assist(app_id: int) -> dict:
    """Fill the form in a visible window and let the user solve the CAPTCHA and submit."""
    current = _get(app_id)
    if current["status"] != "failed":
        raise HTTPException(409, "Only stuck applications can be finished this way")
    if current["apply_type"] not in ("form", "web_form"):
        raise HTTPException(400, "Fill-and-finish works for company sites and Google/Microsoft forms")
    conn = tracker._get_conn()
    conn.execute("UPDATE applications SET assist = 1 WHERE id = ?", (app_id,))
    tracker.set_status(app_id, "approved", "Fill and let me finish", conn=conn)
    conn.commit()
    conn.close()
    return _get(app_id)


@app.post("/api/applications/{app_id}/mark-applied")
def mark_applied(app_id: int) -> dict:
    return _transition(app_id, ("failed", "pending_approval", "dismissed", "skipped"), "applied",
                       "Applied manually")


class BulkBody(BaseModel):
    ids: list[int]
    action: Literal["approve", "dismiss"]


@app.post("/api/queue/bulk")
def bulk(body: BulkBody) -> dict:
    to = "approved" if body.action == "approve" else "dismissed"
    conn = tracker._get_conn()
    done = 0
    try:
        for app_id in body.ids:
            row = conn.execute("SELECT status FROM applications WHERE id = ?", (app_id,)).fetchone()
            if row and row[0] == "pending_approval":
                tracker.set_status(app_id, to, f"Bulk {body.action} in dashboard", conn=conn)
                done += 1
        conn.commit()
    finally:
        conn.close()
    return {"updated": done}


@app.get("/api/applications/{app_id}/resume")
def resume_pdf(app_id: int) -> FileResponse:
    conn = tracker.connect()
    row = conn.execute("SELECT pdf_path FROM applications WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not row or not row["pdf_path"]:
        raise HTTPException(404, "No tailored resume for this application")
    path = os.path.realpath(row["pdf_path"])
    if not path.startswith(OUTPUT_DIR + os.sep) or not os.path.isfile(path):
        raise HTTPException(404, "Resume file missing")
    return FileResponse(path, media_type="application/pdf", content_disposition_type="inline")


@app.get("/api/followups")
def followups() -> list[dict]:
    return _followups_due(tracker.get_settings())


@app.get("/api/insights")
def insights() -> dict:
    rows = _rows("SELECT status, skip_reason, apply_type, source, fit_score, created_at, submitted_at "
                 "FROM applications")
    skip = Counter(_reason_bucket(r["skip_reason"]) for r in rows if r["status"] == "skipped")
    fail = Counter(_reason_bucket(r["skip_reason"]) for r in rows if r["status"] == "failed")

    plat: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        p = plat[r["platform"]]
        p["found"] += 1
        if r["status"] in tracker.SUBMITTED_STATUSES:
            p["applied"] += 1
        if r["status"] == "failed":
            p["failed"] += 1
        if r["status"] in ("screening", "interview", "offer", "rejected"):
            p["responses"] += 1
    platforms = []
    for name, c in plat.items():
        attempted = c["applied"] + c["failed"]
        platforms.append({
            "platform": name, **c,
            "success_rate": round(100 * c["applied"] / attempted, 1) if attempted else None,
            "response_rate": round(100 * c["responses"] / c["applied"], 1) if c["applied"] else None,
        })
    platforms.sort(key=lambda p: -p["found"])

    buckets = Counter()
    for r in rows:
        if r["fit_score"] is not None:
            buckets[min(r["fit_score"] // 10, 9)] += 1

    weeks: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if not r["created_at"]:
            continue
        d = datetime.fromisoformat(r["created_at"]).date()
        wk = (d - timedelta(days=d.weekday())).isoformat()
        weeks[wk]["found"] += 1
        if r["status"] in tracker.SUBMITTED_STATUSES:
            weeks[wk]["applied"] += 1
        if r["status"] == "failed":
            weeks[wk]["failed"] += 1

    return {
        "skip_reasons": [{"reason": k, "count": v} for k, v in skip.most_common(8)],
        "failure_reasons": [{"reason": k, "count": v} for k, v in fail.most_common(8)],
        "platforms": platforms,
        "fit_distribution": [{"bucket": f"{i * 10}–{i * 10 + 9}", "count": buckets.get(i, 0)} for i in range(10)],
        "weekly": [{"week": k, **v} for k, v in sorted(weeks.items())[-16:]],
    }


class SettingsBody(BaseModel):
    apply_mode: Optional[Literal["approval", "auto"]] = None
    auto_approve_min_fit: Optional[int] = None
    min_fit: Optional[int] = None
    notify_skips: Optional[bool] = None
    followup_days: Optional[int] = None
    daily_caps: Optional[dict[str, int]] = None


@app.get("/api/settings")
def get_settings() -> dict:
    return tracker.get_settings()


@app.put("/api/settings")
def put_settings(body: SettingsBody) -> dict:
    for key, value in body.model_dump(exclude_none=True).items():
        if key in ("auto_approve_min_fit", "min_fit") and not 0 <= value <= 100:
            raise HTTPException(400, f"{key} must be 0–100")
        if key == "followup_days" and not 1 <= value <= 60:
            raise HTTPException(400, "followup_days must be 1–60")
        if key == "daily_caps":
            unknown = set(value) - set(tracker.PLATFORM_APPLY_TYPES)
            if unknown or any(not 0 <= n <= 200 for n in value.values()):
                raise HTTPException(400, "daily_caps: known platforms only, 0–200 each")
            value = {**tracker.get_setting("daily_caps"), **value}
        tracker.set_setting(key, value)
    return tracker.get_settings()


@app.get("/api/platforms")
def platforms() -> list[dict]:
    caps = tracker.get_setting("daily_caps") or {}
    today = tracker.applied_today_by_type()
    conn = tracker.connect()
    queued = dict(conn.execute(
        "SELECT apply_type, COUNT(*) FROM applications WHERE status IN ('approved', 'pending_approval') "
        "GROUP BY apply_type"
    ).fetchall())
    conn.close()
    return [
        {
            "platform": platform,
            **sessions.session_status(platform),
            "applied_today": today.get(apply_type, 0),
            "daily_cap": caps.get(platform),
            "queued": queued.get(apply_type, 0),
            "refresh_command": f"{_PYTHON} setup_sessions.py {platform}",
        }
        for platform, apply_type in tracker.PLATFORM_APPLY_TYPES.items()
    ]


@app.get("/api/profile")
def get_profile() -> dict:
    try:
        with open(DEFAULT_PROFILE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, "config/profile.json not found")


@app.put("/api/profile")
def put_profile(body: dict[str, Any]) -> dict:
    required = {"name": str, "email": str, "skills": list}
    for key, typ in required.items():
        if not isinstance(body.get(key), typ) or not body.get(key):
            raise HTTPException(400, f"'{key}' is required")
    tmp = DEFAULT_PROFILE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(body, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DEFAULT_PROFILE_PATH)
    return body


# ── Answer bank ───────────────────────────────────────────────────────────────

class AnswerBody(BaseModel):
    question: str
    answer: str


@app.get("/api/answers")
def list_answers() -> list[dict]:
    return answer_bank.all_answers()


@app.put("/api/answers")
def put_answer(body: AnswerBody) -> list[dict]:
    if not body.question.strip() or not body.answer.strip():
        raise HTTPException(400, "Question and answer are both required")
    answer_bank.save(body.question, body.answer)
    return answer_bank.all_answers()


@app.delete("/api/answers/{answer_id}")
def delete_answer(answer_id: int) -> list[dict]:
    answer_bank.delete(answer_id)
    return answer_bank.all_answers()


class MissingAnswersBody(BaseModel):
    answers: dict[str, str]


@app.post("/api/applications/{app_id}/answers")
def answer_missing(app_id: int, body: MissingAnswersBody) -> dict:
    """Save the user's answers to the bank and send the application back to the worker."""
    current = _get(app_id)
    if current["status"] != "failed":
        raise HTTPException(409, "Only stuck applications take answers")
    answered = {q: a for q, a in body.answers.items() if a.strip()}
    if not answered:
        raise HTTPException(400, "Answer at least one question")
    for q, a in answered.items():
        answer_bank.save(q, a)
    tracker.set_missing_questions(app_id, [])
    tracker.set_status(app_id, "approved", f"You answered {len(answered)} question(s); retrying")
    return _get(app_id)


# ── Base resume ───────────────────────────────────────────────────────────────

class ResumeUpload(BaseModel):
    filename: str
    data_b64: str


@app.get("/api/resume")
def resume_info() -> dict:
    from src import resume_base
    return resume_base.info()


@app.get("/api/resume/pdf")
def resume_base_pdf() -> FileResponse:
    from src import resume_base
    if not os.path.exists(resume_base.BASE_PDF):
        raise HTTPException(404, "No compiled base resume yet")
    return FileResponse(resume_base.BASE_PDF, media_type="application/pdf", content_disposition_type="inline")


@app.post("/api/resume/draft")
def resume_draft(body: ResumeUpload) -> dict:
    import base64
    from src import resume_base
    try:
        data = base64.b64decode(body.data_b64, validate=True)
        return resume_base.make_draft(body.filename, data)
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(400, str(e))


@app.get("/api/resume/draft/{draft_id}/pdf")
def resume_draft_pdf(draft_id: str) -> FileResponse:
    from src import resume_base
    try:
        return FileResponse(resume_base.draft_path(draft_id, "pdf"), media_type="application/pdf",
                            content_disposition_type="inline")
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/resume/draft/{draft_id}/use")
def resume_use(draft_id: str) -> dict:
    from src import resume_base
    try:
        return resume_base.use_draft(draft_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.delete("/api/resume/draft/{draft_id}")
def resume_discard(draft_id: str) -> dict:
    from src import resume_base
    resume_base.discard_draft(draft_id)
    return {"ok": True}


# ── Bot on/off (launchd) ──────────────────────────────────────────────────────

import subprocess

BOT_LABEL = os.getenv("BOT_LAUNCHD_LABEL", "com.pursuit.bot")
BOT_PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{BOT_LABEL}.plist")


def _bot_loaded() -> bool:
    return subprocess.run(["launchctl", "list", BOT_LABEL], capture_output=True).returncode == 0


def _bot_state() -> dict:
    hb = tracker.get_setting("bot_heartbeat")
    age = _days_ago(hb)
    return {
        "loaded": _bot_loaded(),
        "online": age is not None and age * 86400 < HEARTBEAT_STALE_SECONDS,
        "heartbeat": hb,
        "can_control": os.path.exists(BOT_PLIST),
    }


@app.get("/api/bot")
def bot_state() -> dict:
    return _bot_state()


@app.post("/api/bot/start")
def bot_start() -> dict:
    if not os.path.exists(BOT_PLIST):
        raise HTTPException(400, f"No launchd service at {BOT_PLIST}")
    if not _bot_loaded():
        r = subprocess.run(["launchctl", "load", BOT_PLIST], capture_output=True, text=True)
        if r.returncode != 0:
            raise HTTPException(500, f"Couldn't start the bot: {r.stderr.strip()[:200]}")
    return _bot_state()


@app.post("/api/bot/stop")
def bot_stop() -> dict:
    conn = tracker.connect()
    busy = conn.execute("SELECT company FROM applications WHERE status = 'applying' LIMIT 1").fetchone()
    conn.close()
    if busy:
        raise HTTPException(409, f"The bot is submitting to {busy['company']} right now. Try again in a minute.")
    if _bot_loaded():
        r = subprocess.run(["launchctl", "unload", BOT_PLIST], capture_output=True, text=True)
        if r.returncode != 0:
            raise HTTPException(500, f"Couldn't stop the bot: {r.stderr.strip()[:200]}")
    # run.sh restarts the bot in a loop; make sure nothing is left behind.
    subprocess.run(["pkill", "-f", "job-autopilot/run.sh"], capture_output=True)
    subprocess.run(["pkill", "-f", "[-]m src[.]main"], capture_output=True)
    tracker.set_setting("bot_heartbeat", None)
    return _bot_state()
