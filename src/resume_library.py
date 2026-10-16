"""Tailored resume library: reuse a resume already made for a similar job.

Tailoring a resume costs a Gemini call plus a LaTeX compile (~30 s). Most jobs a
person applies to cluster into a few shapes ("backend, Python, AWS"), so a resume
tailored for one usually fits the next. A job's shape is described locally,
without an LLM: its role family (from the title) and the tech skills its JD asks for.

Reuse rule: same role family, and the earlier resume covers at least
REUSE_MIN_COVERAGE of the new job's skills. If a JD names too few skills to judge,
the titles must match instead.
"""
import json
import os
import re
import shutil
from dataclasses import dataclass
from typing import Callable, Optional

from src import tracker

REUSE_MIN_COVERAGE = 0.8
MIN_SKILLS_TO_JUDGE = 3

# Title keyword → family. First match wins, so specific families come first.
_FAMILIES = [
    ("ai-ml", r"\b(ai|ml|machine learning|llm|genai|gen ai|data scientist|nlp|computer vision|deep learning)\b"),
    ("data", r"\b(data engineer|data analyst|analytics|bi developer|etl)\b"),
    ("devops", r"\b(devops|sre|site reliability|platform engineer|infrastructure|cloud engineer)\b"),
    ("mobile", r"\b(android|ios|flutter|react native|mobile)\b"),
    ("fullstack", r"\b(full[\s-]?stack|mern|mean)\b"),
    ("frontend", r"\b(front[\s-]?end|ui developer|react developer|angular|vue)\b"),
    ("backend", r"\b(back[\s-]?end|api|node\.?js|python developer|java developer|golang|django|fastapi|spring)\b"),
    ("qa", r"\b(qa|test|sdet|quality)\b"),
    ("product", r"\b(product manager|apm|product analyst|product intern)\b"),
    ("swe", r"\b(software|sde|swe|developer|engineer|programmer)\b"),
]

# Canonical skill → patterns that mean it. Word-boundary matched, case-insensitive.
_SKILLS = {
    "python": [r"python"], "javascript": [r"javascript", r"\bjs\b"], "typescript": [r"typescript", r"\bts\b"],
    "java": [r"\bjava\b(?!script)"], "go": [r"golang", r"\bgo\b(?= developer| engineer|lang)"],
    "c++": [r"c\+\+", r"\bcpp\b"], "c#": [r"c#", r"\.net\b", r"dotnet"], "rust": [r"\brust\b"],
    "kotlin": [r"kotlin"], "swift": [r"\bswift\b"], "dart": [r"\bdart\b"], "php": [r"\bphp\b"], "ruby": [r"\bruby\b"],
    "node.js": [r"node\.?js", r"\bnode\b"], "express": [r"express(\.js)?"], "react": [r"react(\.js)?(?! native)"],
    "react native": [r"react native"], "next.js": [r"next\.?js"], "angular": [r"angular"], "vue": [r"\bvue(\.js)?\b"],
    "flutter": [r"flutter"], "django": [r"django"], "flask": [r"flask"], "fastapi": [r"fastapi"],
    "spring": [r"spring( boot)?"], "graphql": [r"graphql"], "rest api": [r"rest(ful)?( api)?s?\b", r"\bapis?\b"],
    "microservices": [r"micro-?services?"], "grpc": [r"grpc"],
    "postgresql": [r"postgres(ql)?"], "mysql": [r"mysql"], "mongodb": [r"mongo(db)?"], "redis": [r"redis"],
    "sql": [r"\bsql\b"], "sqlite": [r"sqlite"], "dynamodb": [r"dynamodb"], "elasticsearch": [r"elastic ?search"],
    "firebase": [r"firebase"], "supabase": [r"supabase"],
    "kafka": [r"kafka"], "rabbitmq": [r"rabbitmq"], "celery": [r"celery"],
    "aws": [r"\baws\b", r"amazon web services", r"\blambda\b", r"\bs3\b", r"\bec2\b"], "gcp": [r"\bgcp\b", r"google cloud"],
    "azure": [r"azure"], "docker": [r"docker", r"container"], "kubernetes": [r"kubernetes", r"\bk8s\b"],
    "terraform": [r"terraform"], "ci/cd": [r"ci\s*/\s*cd", r"github actions", r"jenkins"], "linux": [r"linux"],
    "git": [r"\bgit\b", r"github"],
    "llm": [r"\bllms?\b", r"large language model", r"gpt", r"openai", r"gemini", r"claude", r"\bgenai\b", r"generative ai"],
    "langchain": [r"langchain", r"llamaindex"], "rag": [r"\brag\b", r"retrieval[- ]augmented"],
    "machine learning": [r"machine learning", r"\bml\b"], "deep learning": [r"deep learning", r"neural net"],
    "pytorch": [r"pytorch"], "tensorflow": [r"tensorflow"], "nlp": [r"\bnlp\b", r"natural language"],
    "pandas": [r"pandas"], "data analysis": [r"data analy(sis|tics)"], "n8n": [r"\bn8n\b"],
    "html/css": [r"\bhtml\b", r"\bcss\b", r"tailwind"], "system design": [r"system design", r"scalab"],
    "testing": [r"unit test", r"pytest", r"\bjest\b", r"test automation"],
}
_COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in _SKILLS.items()}


def role_family(title: str) -> str:
    t = title.lower()
    for family, pattern in _FAMILIES:
        if re.search(pattern, t):
            return family
    return "other"


def extract_skills(text: str) -> set:
    return {skill for skill, pats in _COMPILED.items() if any(p.search(text or "") for p in pats)}


def _norm_title(title: str) -> str:
    t = re.sub(r"\(.*?\)|[^a-z0-9 ]", " ", title.lower())
    t = re.sub(r"\b(sr|senior|jr|junior|i{1,3}|1|2|3|intern|trainee|remote|hybrid)\b", " ", t)
    return " ".join(t.split())


def _conn():
    conn = tracker.connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            company TEXT, role TEXT, family TEXT, title_norm TEXT,
            skills TEXT NOT NULL,
            created_at TEXT, times_reused INTEGER DEFAULT 0
        )
    """)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(resumes)")}
    if "base_version" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN base_version TEXT")
    return conn


def _base_version() -> str:
    # Lazy import: resume_base pulls in config, which tests may not have set up.
    try:
        from src.resume_base import base_version
        return base_version()
    except Exception:
        return ""


@dataclass
class Match:
    resume_id: int
    path: str
    company: str
    role: str
    coverage: float


def find_reusable(role: str, jd: str) -> Optional[Match]:
    family = role_family(role)
    want = extract_skills(f"{role}\n{jd}")
    title = _norm_title(role)
    conn = _conn()
    # Only resumes tailored from the current base resume; an upload makes older ones stale.
    rows = conn.execute(
        "SELECT * FROM resumes WHERE family = ? AND COALESCE(base_version, '') = ? ORDER BY created_at DESC",
        (family, _base_version()),
    ).fetchall()
    conn.close()

    best: Optional[Match] = None
    for r in rows:
        if not os.path.isfile(r["path"]):
            continue
        have = set(json.loads(r["skills"]))
        if len(want) >= MIN_SKILLS_TO_JUDGE:
            coverage = len(want & have) / len(want)
            if coverage < REUSE_MIN_COVERAGE:
                continue
        else:
            # Too little in the JD to compare skills; only reuse for the same title.
            if r["title_norm"] != title:
                continue
            coverage = 1.0
        if best is None or coverage > best.coverage:
            best = Match(r["id"], r["path"], r["company"], r["role"], coverage)
    return best


def record(path: str, company: str, role: str, jd: str) -> None:
    from datetime import datetime
    conn = _conn()
    conn.execute(
        "INSERT INTO resumes (path, company, role, family, title_norm, skills, created_at, base_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (path, company, role, role_family(role), _norm_title(role),
         json.dumps(sorted(extract_skills(f"{role}\n{jd}"))), datetime.now().isoformat(timespec="seconds"),
         _base_version()),
    )
    conn.commit()
    conn.close()


@dataclass
class ResumeChoice:
    path: str
    reused_from: Optional[str] = None   # "Company · Role" of the resume reused
    coverage: Optional[float] = None


def get_resume(
    company: str, role: str, jd: str, output_path: str,
    tailor: Callable[[str, str, str, str], bool],
) -> ResumeChoice:
    """Reuse a resume tailored for a similar job, or tailor a new one.

    `tailor(company, role, jd, output_path)` writes the PDF and returns True if it
    was actually tailored (False = fell back to the base template, not worth reusing).
    """
    match = find_reusable(role, jd)
    if match:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        # Copy under this job's name — the file name is visible to the recruiter.
        if os.path.abspath(match.path) != os.path.abspath(output_path):
            shutil.copyfile(match.path, output_path)
        conn = _conn()
        conn.execute("UPDATE resumes SET times_reused = times_reused + 1 WHERE id = ?", (match.resume_id,))
        conn.commit()
        conn.close()
        return ResumeChoice(output_path, f"{match.company} · {match.role}", round(match.coverage, 2))

    if tailor(company, role, jd, output_path):
        record(output_path, company, role, jd)
    return ResumeChoice(output_path)


def stats() -> dict:
    conn = _conn()
    made, reused = conn.execute("SELECT COUNT(*), COALESCE(SUM(times_reused), 0) FROM resumes").fetchone()
    conn.close()
    return {"tailored": made, "reused": reused}

