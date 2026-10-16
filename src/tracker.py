import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "applications.db")

# Lifecycle of a row:
#   skipped                      ineligible, never queued
#   pending_approval -> approved -> applying -> applied | failed
#   pending_approval -> dismissed (user said no)
#   applied -> screening -> interview -> offer | rejected | ghosted
QUEUE_STATUSES = ("pending_approval", "approved", "applying")
SUBMITTED_STATUSES = ("applied", "screening", "interview", "offer", "rejected", "ghosted")
ALL_STATUSES = ("skipped", "dismissed", "failed") + QUEUE_STATUSES + SUBMITTED_STATUSES

# Columns added after v1. Old databases get them via ALTER TABLE on first connect.
_NEW_COLUMNS = {
    "location": "TEXT",
    "source": "TEXT",
    "jd_summary": "TEXT",
    "fit_score": "INTEGER",
    "fit_reason": "TEXT",
    "pdf_path": "TEXT",
    "payload": "TEXT",
    "notes": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
    "submitted_at": "TEXT",
    "followup_at": "TEXT",
    "resume_source": "TEXT",
    "missing_questions": "TEXT",
    "answers_used": "TEXT",
    "assist": "INTEGER",           # 1 = fill in a window and let the user finish (CAPTCHA etc.)        # JSON [[question, answer, source], ...] actually sent   # JSON list: required questions only the user can answer   # null = tailored for this job; else "Company · Role" it was reused from
}

DEFAULT_SETTINGS = {
    "apply_mode": "approval",       # "approval" | "auto"
    "auto_approve_min_fit": 0,      # 0 = off; else jobs at/above this fit skip the queue
    "min_fit": 40,                  # below this skills overlap a job is skipped
    "notify_skips": False,          # Telegram ping for every skipped job (noisy)
    "followup_days": 7,
    # Max submissions per platform per day. Portals flag accounts that apply in bulk.
    "daily_caps": {"linkedin": 25, "naukri": 30, "instahyre": 30, "wellfound": 20,
                   "indeed": 30, "internshala": 30},
}

PLATFORM_APPLY_TYPES = {
    "linkedin": "linkedin_easy_apply", "naukri": "naukri_apply", "instahyre": "instahyre_apply",
    "wellfound": "wellfound_apply", "indeed": "indeed_apply", "internshala": "internshala_apply",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _migrate(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            apply_target TEXT,
            apply_type TEXT,
            status TEXT,
            skip_reason TEXT,
            applied_at TEXT
        )
    """)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(applications)")}
    added = [c for c in _NEW_COLUMNS if c not in existing]
    for col in added:
        conn.execute(f"ALTER TABLE applications ADD COLUMN {col} {_NEW_COLUMNS[col]}")
    if added:
        # v1 rows only had applied_at, which was really "logged at".
        conn.execute("UPDATE applications SET created_at = applied_at WHERE created_at IS NULL")
        conn.execute("UPDATE applications SET updated_at = applied_at WHERE updated_at IS NULL")
        conn.execute(
            "UPDATE applications SET submitted_at = applied_at "
            "WHERE submitted_at IS NULL AND status = 'applied'"
        )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            at TEXT NOT NULL,
            kind TEXT NOT NULL,
            message TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_app ON events(application_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")


def _get_conn() -> sqlite3.Connection:
    dir_path = os.path.dirname(DB_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    # The bot and the dashboard API both write; WAL lets them do so without blocking reads.
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    _migrate(conn)
    conn.commit()
    return conn


def connect() -> sqlite3.Connection:
    """Connection with dict-like rows, for callers that read many columns."""
    conn = _get_conn()
    conn.row_factory = sqlite3.Row
    return conn


def is_duplicate(company: str, role: str) -> bool:
    """True if this company+role is already queued or was submitted."""
    statuses = QUEUE_STATUSES + SUBMITTED_STATUSES
    conn = _get_conn()
    row = conn.execute(
        f"SELECT id FROM applications WHERE company = ? COLLATE NOCASE AND role = ? COLLATE NOCASE "
        f"AND status IN ({','.join('?' * len(statuses))})",
        (company, role, *statuses),
    ).fetchone()
    conn.close()
    return row is not None


def add_event(conn: sqlite3.Connection, app_id: int, kind: str, message: str = "") -> None:
    conn.execute(
        "INSERT INTO events (application_id, at, kind, message) VALUES (?, ?, ?, ?)",
        (app_id, _now(), kind, message),
    )


def log_application(
    company: str,
    role: str,
    apply_target: str,
    apply_type: str,
    status: str,
    skip_reason: str = "",
    **extra: Any,
) -> int:
    """Insert an application record into the database and return its id.

    `extra` may set any of the v2 columns (location, source, jd_summary, fit_score, ...).
    """
    extra = {k: v for k, v in extra.items() if k in _NEW_COLUMNS}
    if isinstance(extra.get("payload"), dict):
        extra["payload"] = json.dumps(extra["payload"])
    now = _now()
    extra.setdefault("created_at", now)
    extra.setdefault("updated_at", now)
    if status == "applied":
        extra.setdefault("submitted_at", now)
    cols = ["company", "role", "apply_target", "apply_type", "status", "skip_reason", "applied_at", *extra]
    vals = [company, role, apply_target, apply_type, status, skip_reason, now, *extra.values()]
    conn = _get_conn()
    cur = conn.execute(
        f"INSERT INTO applications ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        vals,
    )
    app_id = cur.lastrowid
    add_event(conn, app_id, status, skip_reason)
    conn.commit()
    conn.close()
    return app_id


def set_status(app_id: int, status: str, message: str = "", conn: Optional[sqlite3.Connection] = None) -> None:
    if status not in ALL_STATUSES:
        raise ValueError(f"Unknown status: {status}")
    own = conn is None
    conn = conn or _get_conn()
    now = _now()
    sets = ["status = ?", "updated_at = ?"]
    vals: list = [status, now]
    if status in ("failed", "skipped"):
        sets.append("skip_reason = ?")
        vals.append(message)
    if status == "applied":
        sets.append("submitted_at = COALESCE(submitted_at, ?)")
        vals.append(now)
        sets.append("skip_reason = NULL")   # an old failure message no longer applies
    conn.execute(f"UPDATE applications SET {', '.join(sets)} WHERE id = ?", (*vals, app_id))
    add_event(conn, app_id, status, message)
    if own:
        conn.commit()
        conn.close()


def applied_today_by_type() -> dict:
    today = datetime.now().date().isoformat()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT apply_type, COUNT(*) FROM applications WHERE submitted_at >= ? GROUP BY apply_type",
        (today,),
    ).fetchall()
    conn.close()
    return dict(rows)


def capped_apply_types() -> tuple:
    """Apply types whose platform hit today's cap; the worker leaves them queued until tomorrow."""
    caps = get_setting("daily_caps") or {}
    done = applied_today_by_type()
    return tuple(
        t for platform, t in PLATFORM_APPLY_TYPES.items()
        if platform in caps and done.get(t, 0) >= int(caps[platform])
    )


def set_answers_used(app_id: int, filled: list) -> None:
    conn = _get_conn()
    conn.execute("UPDATE applications SET answers_used = ? WHERE id = ?",
                 (json.dumps([[str(q), v if isinstance(v, (str, list)) else str(v), s] for q, v, s in filled]), app_id))
    conn.commit()
    conn.close()


def clear_assist(app_id: int) -> None:
    conn = _get_conn()
    conn.execute("UPDATE applications SET assist = NULL WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def set_missing_questions(app_id: int, questions: list) -> None:
    conn = _get_conn()
    conn.execute("UPDATE applications SET missing_questions = ? WHERE id = ?",
                 (json.dumps(questions) if questions else None, app_id))
    conn.commit()
    conn.close()


def claim_next_approved(grace_seconds: int = 10, skip_types: tuple = ()) -> Optional[dict]:
    """Atomically move the oldest approved row to 'applying' and return it.

    Rows approved less than `grace_seconds` ago are left alone so the dashboard's
    Undo still works.
    """
    cutoff = (datetime.now() - timedelta(seconds=grace_seconds)).isoformat(timespec="seconds")
    conn = connect()
    conn.execute("BEGIN IMMEDIATE")
    skip_sql = f" AND apply_type NOT IN ({','.join('?' * len(skip_types))})" if skip_types else ""
    row = conn.execute(
        "SELECT * FROM applications WHERE status = 'approved' AND updated_at <= ?"
        f"{skip_sql} ORDER BY updated_at, id LIMIT 1",
        (cutoff, *skip_types),
    ).fetchone()
    if row is None:
        conn.rollback()
        conn.close()
        return None
    set_status(row["id"], "applying", conn=conn)
    conn.commit()
    conn.close()
    return dict(row)


def recover_interrupted() -> int:
    """Rows left in 'applying' by a crash may or may not have been submitted.

    Never resubmit blindly — flag them so the user checks.
    """
    conn = _get_conn()
    ids = [r[0] for r in conn.execute("SELECT id FROM applications WHERE status = 'applying'")]
    for app_id in ids:
        set_status(app_id, "failed", "Interrupted mid-apply — check the site before retrying", conn=conn)
    conn.commit()
    conn.close()
    return len(ids)


def get_setting(key: str) -> Any:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else DEFAULT_SETTINGS.get(key)


def get_settings() -> dict:
    conn = _get_conn()
    stored = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM settings")}
    conn.close()
    return {**DEFAULT_SETTINGS, **stored}


def set_setting(key: str, value: Any) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value)),
    )
    conn.commit()
    conn.close()
