"""Answers the user gave once, reused on every later form that asks the same thing.

Forms ask things no profile covers (10th marks, date of birth, postal address...).
The bot never guesses those: the application goes to "Needs you" with the
questions, the user answers once in the dashboard, and the answer lands here.
"""
import re
from datetime import datetime
from typing import Optional

from src import tracker

MATCH_MIN_OVERLAP = 0.8

_STOP = {"the", "a", "an", "your", "you", "of", "in", "is", "are", "do", "what", "please", "enter",
         "to", "for", "and", "or", "if", "any", "this", "with", "me", "my", "on", "at", "be"}


def normalize(question: str) -> str:
    q = question.lower()
    q = re.sub(r"required to answer.*$", "", q, flags=re.S)       # Microsoft Forms suffix
    q = re.sub(r"^\s*\d+\s*[.)]\s*", "", q)                         # "12. " numbering
    q = re.sub(r"[^a-z0-9 ]+", " ", q)
    return " ".join(q.split())


def _tokens(q: str) -> set:
    return {t for t in normalize(q).split() if t not in _STOP}


def _conn():
    conn = tracker.connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answer_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            norm TEXT NOT NULL UNIQUE,
            answer TEXT NOT NULL,
            times_used INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    return conn


def lookup(question: str) -> Optional[str]:
    norm = normalize(question)
    if not norm:
        return None
    want = _tokens(question)
    conn = _conn()
    rows = conn.execute("SELECT id, norm, answer FROM answer_bank").fetchall()
    best, best_score = None, 0.0
    for r in rows:
        if r["norm"] == norm:
            best, best_score = r, 1.0
            break
        have = {t for t in r["norm"].split() if t not in _STOP}
        if want and have:
            score = len(want & have) / len(want | have)
            if score > best_score:
                best, best_score = r, score
    if best is not None and best_score >= MATCH_MIN_OVERLAP:
        conn.execute("UPDATE answer_bank SET times_used = times_used + 1 WHERE id = ?", (best["id"],))
        conn.commit()
        conn.close()
        return best["answer"]
    conn.close()
    return None


def save(question: str, answer: str) -> None:
    norm = normalize(question)
    if not norm or not answer.strip():
        return
    conn = _conn()
    conn.execute(
        "INSERT INTO answer_bank (question, norm, answer, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(norm) DO UPDATE SET answer = excluded.answer, question = excluded.question, "
        "updated_at = excluded.updated_at",
        (question.strip(), norm, answer.strip(), datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def all_answers() -> list[dict]:
    conn = _conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, question, answer, times_used, updated_at FROM answer_bank ORDER BY updated_at DESC"
    )]
    conn.close()
    return rows


def delete(answer_id: int) -> None:
    conn = _conn()
    conn.execute("DELETE FROM answer_bank WHERE id = ?", (answer_id,))
    conn.commit()
    conn.close()
