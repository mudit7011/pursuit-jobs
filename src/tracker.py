import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "applications.db")


def _get_conn() -> sqlite3.Connection:
    dir_path = os.path.dirname(DB_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    return conn


def is_duplicate(company: str, role: str) -> bool:
    """Return True if we have already successfully applied to this company+role."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT id FROM applications WHERE company = ? COLLATE NOCASE AND role = ? COLLATE NOCASE AND status = 'applied'",
        (company, role),
    ).fetchone()
    conn.close()
    return row is not None


def log_application(
    company: str,
    role: str,
    apply_target: str,
    apply_type: str,
    status: str,
    skip_reason: str = "",
) -> None:
    """Insert an application record into the database."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO applications
           (company, role, apply_target, apply_type, status, skip_reason, applied_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (company, role, apply_target, apply_type, status, skip_reason,
         datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
