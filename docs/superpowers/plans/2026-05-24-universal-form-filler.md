# Universal Form Filler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the Job Autopilot Bot to handle any web-based job application form (Greenhouse, Lever, Workday, Ashby, Microsoft Forms, custom forms) using Playwright browser automation and LLM-guided field filling, plus add eligibility filtering and duplicate prevention.

**Architecture:** A profile config file replaces all hardcoded user data. An eligibility checker runs before any work is done, skipping jobs with batch year / experience / skills mismatch. A Playwright-based universal form filler handles multi-page ATS forms by extracting fields, asking Gemini for answers, and filling/submitting — with CAPTCHA detection and file upload support.

**Tech Stack:** Python, Playwright (sync API), SQLite (stdlib), Gemini API, pytest, unittest.mock

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `config/profile.json` | Create | Single source of truth for user data |
| `src/profile.py` | Create | Loads profile.json, exposes UserProfile dataclass |
| `src/tracker.py` | Create | SQLite log — duplicate check + application logging |
| `src/eligibility.py` | Create | Checks batch year, experience, skills before applying |
| `src/models.py` | Modify | Add WEB_FORM to ApplyType enum |
| `src/parser.py` | Modify | Detect Greenhouse/Lever/Workday/etc. URLs as WEB_FORM |
| `src/web_form_filler.py` | Create | Playwright + Gemini universal form filler |
| `src/orchestrator.py` | Modify | Wire duplicate check, eligibility, and web_form_filler |
| `tests/test_profile.py` | Create | Tests for profile loading |
| `tests/test_tracker.py` | Create | Tests for duplicate check and logging |
| `tests/test_eligibility.py` | Create | Tests for all three eligibility rules |
| `tests/test_parser.py` | Modify | Add WEB_FORM URL detection tests, fix existing FORM test |
| `tests/test_web_form_filler.py` | Create | Tests for field extraction helpers and CAPTCHA detection |

---

## Task 1: Install Playwright + create profile config

**Files:**
- Create: `config/profile.json`
- Modify: `requirements.txt`

- [ ] **Step 1: Install playwright**

```bash
pip install playwright==1.44.0
playwright install chromium
```

- [ ] **Step 2: Add playwright to requirements.txt**

Open `requirements.txt` and add this line at the end:

```
playwright==1.44.0
```

- [ ] **Step 3: Create config directory and profile.json**

```bash
mkdir -p config
```

Create `config/profile.json` with this exact content:

```json
{
  "name": "Mudit Kumar",
  "email": "muditkumar7011@gmail.com",
  "phone": "+91 8533888088",
  "linkedin": "https://linkedin.com/in/mudit-dev",
  "github": "",
  "portfolio": "",
  "college": "Dr APJ Abdul Kalam Technical University, Lucknow",
  "degree": "B.Tech Computer Science Engineering",
  "cgpa": "7.49",
  "graduation_year": 2024,
  "years_of_experience": 2,
  "current_ctc": "0",
  "expected_ctc": "8 LPA",
  "notice_period": "Immediate",
  "location_preference": "Remote / Gurugram / Noida / Bangalore",
  "work_authorization": "Authorized to work in India",
  "skills": ["Python", "Node.js", "TypeScript", "REST APIs", "MongoDB", "Firebase", "AWS", "LLM APIs", "n8n", "FastAPI", "Express.js", "PostgreSQL", "SQLite", "Docker", "Gemini API", "Claude API", "OpenAI API"],
  "resume_pdf_path": "templates/MuditCV.pdf",
  "summary": "Backend developer with 2 years of experience building production-grade APIs, automation systems, and LLM-integrated pipelines. Skilled in Python, Node.js, TypeScript, Firebase, AWS, and AI APIs. Built and shipped FootPrints, a full-stack app with real users, and Job Autopilot Bot, a fully automated job application system."
}
```

- [ ] **Step 4: Add config/ to .gitignore so profile stays local**

Open `.gitignore` and add:

```
config/
data/
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "chore: add playwright dependency and profile config structure"
```

---

## Task 2: src/profile.py — UserProfile loader

**Files:**
- Create: `src/profile.py`
- Create: `tests/test_profile.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_profile.py`:

```python
import os
import json
import tempfile
import pytest
from src.profile import load_profile, UserProfile

def test_load_profile_returns_userprofile(tmp_path):
    profile_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+91 9999999999",
        "linkedin": "https://linkedin.com/in/test",
        "github": "",
        "portfolio": "",
        "college": "Test University",
        "degree": "B.Tech",
        "cgpa": "8.0",
        "graduation_year": 2024,
        "years_of_experience": 2,
        "current_ctc": "0",
        "expected_ctc": "8 LPA",
        "notice_period": "Immediate",
        "location_preference": "Remote",
        "work_authorization": "Authorized to work in India",
        "skills": ["Python", "Node.js"],
        "resume_pdf_path": "templates/MuditCV.pdf",
        "summary": "A backend developer."
    }
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(json.dumps(profile_data))

    profile = load_profile(str(profile_file))

    assert isinstance(profile, UserProfile)
    assert profile.name == "Test User"
    assert profile.graduation_year == 2024
    assert profile.years_of_experience == 2
    assert "Python" in profile.skills

def test_load_profile_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_profile("/nonexistent/path/profile.json")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_profile.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.profile'`

- [ ] **Step 3: Create src/profile.py**

```python
import json
import os
from dataclasses import dataclass
from typing import List

DEFAULT_PROFILE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "profile.json"
)


@dataclass
class UserProfile:
    name: str
    email: str
    phone: str
    linkedin: str
    github: str
    portfolio: str
    college: str
    degree: str
    cgpa: str
    graduation_year: int
    years_of_experience: int
    current_ctc: str
    expected_ctc: str
    notice_period: str
    location_preference: str
    work_authorization: str
    skills: List[str]
    resume_pdf_path: str
    summary: str


def load_profile(path: str = DEFAULT_PROFILE_PATH) -> UserProfile:
    """Load user profile from a JSON file and return a UserProfile dataclass."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path, "r") as f:
        data = json.load(f)
    return UserProfile(**data)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_profile.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/profile.py tests/test_profile.py
git commit -m "feat: add UserProfile dataclass and profile loader"
```

---

## Task 3: src/tracker.py — SQLite application tracker

**Files:**
- Create: `src/tracker.py`
- Create: `tests/test_tracker.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tracker.py`:

```python
import os
import pytest
import tempfile

# Patch DB_PATH before importing tracker
import src.tracker as tracker_module


def test_is_duplicate_returns_false_for_new_job(tmp_path):
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    assert tracker_module.is_duplicate("Acme Corp", "SWE Intern") is False


def test_log_and_detect_duplicate(tmp_path):
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    tracker_module.log_application(
        company="Acme Corp",
        role="SWE Intern",
        apply_target="hr@acme.com",
        apply_type="email",
        status="applied",
        skip_reason="",
    )
    assert tracker_module.is_duplicate("Acme Corp", "SWE Intern") is True


def test_skipped_job_not_counted_as_duplicate(tmp_path):
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    tracker_module.log_application(
        company="Beta Inc",
        role="PM",
        apply_target="",
        apply_type="",
        status="skipped",
        skip_reason="Batch mismatch",
    )
    # Skipped jobs should NOT block future re-evaluation
    assert tracker_module.is_duplicate("Beta Inc", "PM") is False


def test_log_application_stores_all_fields(tmp_path):
    import sqlite3
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    tracker_module.log_application(
        company="Gamma Ltd",
        role="Backend Dev",
        apply_target="https://greenhouse.io/gamma/backend",
        apply_type="web_form",
        status="applied",
        skip_reason="",
    )
    conn = sqlite3.connect(tracker_module.DB_PATH)
    row = conn.execute(
        "SELECT company, role, apply_type, status FROM applications WHERE company='Gamma Ltd'"
    ).fetchone()
    conn.close()
    assert row == ("Gamma Ltd", "Backend Dev", "web_form", "applied")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_tracker.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.tracker'`

- [ ] **Step 3: Create src/tracker.py**

```python
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "applications.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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
        "SELECT id FROM applications WHERE company = ? AND role = ? AND status = 'applied'",
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_tracker.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tracker.py tests/test_tracker.py
git commit -m "feat: add SQLite application tracker with duplicate prevention"
```

---

## Task 4: src/eligibility.py — Eligibility checker

**Files:**
- Create: `src/eligibility.py`
- Create: `tests/test_eligibility.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_eligibility.py`:

```python
import os
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "fakehash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", "fakesession")
os.environ.setdefault("TELEGRAM_GROUP_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_SELF_ID", "999999")
os.environ.setdefault("GEMINI_API_KEY", "fakekey")
os.environ.setdefault("GMAIL_ADDRESS", "fake@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "fakepassword")

import pytest
from unittest.mock import patch, MagicMock
from src.models import JobPosting, ApplyType
from src.profile import UserProfile
from src.eligibility import check_eligibility, EligibilityResult


def _make_profile(**overrides) -> UserProfile:
    defaults = dict(
        name="Mudit Kumar", email="m@m.com", phone="+91 999",
        linkedin="", github="", portfolio="",
        college="AKTU", degree="B.Tech", cgpa="7.49",
        graduation_year=2024, years_of_experience=2,
        current_ctc="0", expected_ctc="8 LPA",
        notice_period="Immediate", location_preference="Remote",
        work_authorization="Authorized to work in India",
        skills=["Python", "Node.js", "Firebase"],
        resume_pdf_path="templates/MuditCV.pdf",
        summary="Backend dev.",
    )
    defaults.update(overrides)
    return UserProfile(**defaults)


def _make_job(**overrides) -> JobPosting:
    defaults = dict(
        company="Acme", role="SWE Intern", salary="", location="",
        jd_summary="Python backend development role",
        apply_type=ApplyType.EMAIL, apply_target="hr@acme.com",
        batch="", raw_message="", is_relevant=True,
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


def test_batch_mismatch_returns_ineligible():
    profile = _make_profile(graduation_year=2024)
    job = _make_job(batch="2026 passout only")
    result = check_eligibility(job, profile)
    assert result.eligible is False
    assert "batch" in result.reason.lower()


def test_batch_match_passes():
    profile = _make_profile(graduation_year=2024)
    job = _make_job(batch="2023/2024/2025")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 80, "reason": "Good match"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is True


def test_experience_mismatch_returns_ineligible():
    profile = _make_profile(years_of_experience=1)
    job = _make_job(jd_summary="Requires 3+ years of backend experience with Python")
    result = check_eligibility(job, profile)
    assert result.eligible is False
    assert "experience" in result.reason.lower()


def test_experience_match_passes():
    profile = _make_profile(years_of_experience=2)
    job = _make_job(jd_summary="1+ years of Python backend experience required")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 75, "reason": "Good skill match"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is True


def test_skills_mismatch_returns_ineligible():
    profile = _make_profile(skills=["Python", "Firebase"])
    job = _make_job(jd_summary="Java, Spring Boot, Kubernetes, Kafka, Scala required")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 10, "reason": "No Java experience"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is False
    assert "skills" in result.reason.lower()


def test_skills_check_skipped_if_gemini_fails():
    profile = _make_profile(graduation_year=2024, years_of_experience=2)
    job = _make_job(jd_summary="Python backend role for 2024 graduates")
    with patch("src.eligibility.model") as mock_model:
        mock_model.generate_content.side_effect = Exception("API error")
        result = check_eligibility(job, profile)
    # Defaults to eligible when skills check fails
    assert result.eligible is True


def test_no_batch_in_job_skips_batch_rule():
    profile = _make_profile(graduation_year=2024)
    job = _make_job(batch="")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 80, "reason": "Good match"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_eligibility.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.eligibility'`

- [ ] **Step 3: Create src/eligibility.py**

```python
import re
import json
import logging
import google.generativeai as genai
from dataclasses import dataclass
from src.models import JobPosting
from src.profile import UserProfile
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
log = logging.getLogger(__name__)


@dataclass
class EligibilityResult:
    eligible: bool
    reason: str


def check_eligibility(job: JobPosting, profile: UserProfile) -> EligibilityResult:
    """
    Check whether the user is eligible to apply to this job.
    Runs batch and experience checks without LLM first (fast).
    Only calls Gemini for skills check if the first two rules pass.
    """
    # Rule 1: batch year check
    if job.batch:
        years_in_job = re.findall(r"\b(20\d{2})\b", job.batch)
        if years_in_job:
            allowed = [int(y) for y in years_in_job]
            if profile.graduation_year not in allowed:
                return EligibilityResult(
                    eligible=False,
                    reason=(
                        f"Batch mismatch — job requires {job.batch}, "
                        f"you are {profile.graduation_year} passout"
                    ),
                )

    # Rule 2: experience check
    exp_match = re.search(
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)",
        job.jd_summary,
        re.IGNORECASE,
    )
    if exp_match:
        required_exp = int(exp_match.group(1))
        if profile.years_of_experience < required_exp:
            return EligibilityResult(
                eligible=False,
                reason=(
                    f"Experience mismatch — job requires {required_exp}+ years, "
                    f"you have {profile.years_of_experience}"
                ),
            )

    # Rule 3: skills overlap via Gemini
    prompt = f"""Given this job description and candidate skills, return ONLY a JSON object.

Job description: {job.jd_summary}
Candidate skills: {", ".join(profile.skills)}

Return exactly: {{"overlap_percent": <integer 0-100>, "reason": "<one sentence>"}}
overlap_percent is the percentage of required job skills the candidate has."""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
        overlap = int(result.get("overlap_percent", 100))
        if overlap < 40:
            return EligibilityResult(
                eligible=False,
                reason=(
                    f"Skills mismatch — only {overlap}% overlap: "
                    f"{result.get('reason', '')}"
                ),
            )
    except Exception as e:
        log.warning(f"Skills eligibility check failed, defaulting to eligible: {e}")

    return EligibilityResult(eligible=True, reason="")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_eligibility.py -v
```

Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/eligibility.py tests/test_eligibility.py
git commit -m "feat: add eligibility checker (batch, experience, skills)"
```

---

## Task 5: Add WEB_FORM to models + parser

**Files:**
- Modify: `src/models.py`
- Modify: `src/parser.py`
- Modify: `tests/test_parser.py`

- [ ] **Step 1: Write the failing test**

Add these tests to `tests/test_parser.py` (append after the existing tests):

```python
from src.parser import _is_web_form

def test_is_web_form_greenhouse():
    assert _is_web_form("https://boards.greenhouse.io/company/jobs/123456") is True

def test_is_web_form_lever():
    assert _is_web_form("https://jobs.lever.co/company/abc123/apply") is True

def test_is_web_form_workday():
    assert _is_web_form("https://company.wd5.myworkdayjobs.com/en-US/jobs") is True

def test_is_web_form_ashby():
    assert _is_web_form("https://jobs.ashbyhq.com/company/role/apply") is True

def test_is_web_form_microsoft_forms():
    assert _is_web_form("https://forms.office.com/r/abc123") is True

def test_is_web_form_bamboohr():
    assert _is_web_form("https://company.bamboohr.com/jobs/view.php?id=123") is True

def test_is_web_form_email_is_not_web_form():
    assert _is_web_form("hr@company.com") is False

def test_is_web_form_google_form_is_not_web_form():
    assert _is_web_form("https://docs.google.com/forms/d/e/abc123/viewform") is False

def test_is_web_form_empty_string_is_not_web_form():
    assert _is_web_form("") is False

def test_parse_greenhouse_url_returns_web_form():
    sample_response = '''{
        "company": "Acme",
        "role": "Backend Engineer",
        "salary": "",
        "location": "Remote",
        "jd_summary": "Python backend role",
        "apply_type": "form",
        "apply_target": "https://boards.greenhouse.io/acme/jobs/7654321",
        "batch": "",
        "is_relevant": true
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("some job posting text")
    assert result.apply_type == ApplyType.WEB_FORM
    assert "greenhouse" in result.apply_target
```

Also update the existing `test_parse_form_job` in `tests/test_parser.py`. It currently expects `ApplyType.FORM` for a `people-jobs.com` URL, but with our new logic that URL (which has `/apply/` in it) becomes `WEB_FORM`. Change the assertion:

```python
def test_parse_form_job():
    sample_response = '''{
        "company": "Aspire",
        "role": "Software Engineering Intern",
        "salary": "₹40,000/month",
        "location": "Gurugram",
        "jd_summary": "Backend, APIs, AI tools, Python",
        "apply_type": "form",
        "apply_target": "https://people-jobs.com/aspire/apply/software-engineering-intern",
        "batch": "2024/2025/2026",
        "is_relevant": true
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("some message text")
    assert result.apply_type == ApplyType.WEB_FORM
    assert "aspire" in result.apply_target
```

- [ ] **Step 2: Run test to verify the new tests fail**

```bash
pytest tests/test_parser.py -v
```

Expected: FAIL with `ImportError: cannot import name '_is_web_form' from 'src.parser'`

- [ ] **Step 3: Update src/models.py — add WEB_FORM**

Replace the entire `ApplyType` class in `src/models.py`:

```python
class ApplyType(Enum):
    EMAIL = "email"
    FORM = "form"
    WEB_FORM = "web_form"
    UNKNOWN = "unknown"
```

- [ ] **Step 4: Update src/parser.py — add _is_web_form and update routing**

Add this constant and function after the imports, before `_build_prompt`:

```python
_ATS_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "ashbyhq.com",
    "forms.office.com",
    "bamboohr.com",
    "recruitcrm.io",
]

_APPLY_PATH_KEYWORDS = ["/apply", "/apply/"]


def _is_web_form(url: str) -> bool:
    """Return True if the URL looks like an ATS or web application form."""
    if not url or "@" in url:
        return False
    if "docs.google.com/forms" in url:
        return False
    if any(domain in url for domain in _ATS_DOMAINS):
        return True
    if any(kw in url for kw in _APPLY_PATH_KEYWORDS):
        return True
    return False
```

Then replace the apply_type resolution block in `parse_job_message` (the part that currently reads `if apply_type_raw == "form" and "docs.google.com/forms" not in apply_target`) with:

```python
    # Resolve apply type
    if apply_type_raw == "email" and apply_target and "@" in apply_target:
        final_apply_type = ApplyType.EMAIL
    elif apply_type_raw == "form" and "docs.google.com/forms" in apply_target:
        final_apply_type = ApplyType.FORM
    elif _is_web_form(apply_target):
        final_apply_type = ApplyType.WEB_FORM
    else:
        final_apply_type = ApplyType.UNKNOWN

    return JobPosting(
        company=data.get("company", ""),
        role=data.get("role", ""),
        salary=data.get("salary", ""),
        location=data.get("location", ""),
        jd_summary=data.get("jd_summary", ""),
        apply_type=final_apply_type,
        apply_target=apply_target,
        batch=data.get("batch", ""),
        raw_message=message,
        is_relevant=data.get("is_relevant", False),
    )
```

Remove the old `apply_type_map` dict and the old return statement since the new block handles everything.

- [ ] **Step 5: Run all parser tests to verify they pass**

```bash
pytest tests/test_parser.py -v
```

Expected: PASS (all tests including new ones)

- [ ] **Step 6: Run the full test suite to make sure nothing broke**

```bash
pytest -v
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add src/models.py src/parser.py tests/test_parser.py
git commit -m "feat: add WEB_FORM apply type and ATS URL detection in parser"
```

---

## Task 6: src/web_form_filler.py — Playwright universal form filler

**Files:**
- Create: `src/web_form_filler.py`
- Create: `tests/test_web_form_filler.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_web_form_filler.py`:

```python
import os
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "fakehash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", "fakesession")
os.environ.setdefault("TELEGRAM_GROUP_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_SELF_ID", "999999")
os.environ.setdefault("GEMINI_API_KEY", "fakekey")
os.environ.setdefault("GMAIL_ADDRESS", "fake@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "fakepassword")

import pytest
from unittest.mock import patch, MagicMock
from src.web_form_filler import (
    _check_captcha_in_content,
    _generate_answers,
    CaptchaDetectedError,
    FormSubmitError,
)
from src.profile import UserProfile


def _make_profile() -> UserProfile:
    return UserProfile(
        name="Mudit Kumar", email="m@m.com", phone="+91 999",
        linkedin="https://linkedin.com/in/mudit-dev", github="", portfolio="",
        college="AKTU", degree="B.Tech", cgpa="7.49",
        graduation_year=2024, years_of_experience=2,
        current_ctc="0", expected_ctc="8 LPA",
        notice_period="Immediate", location_preference="Remote",
        work_authorization="Authorized to work in India",
        skills=["Python", "Node.js", "Firebase"],
        resume_pdf_path="templates/MuditCV.pdf",
        summary="Backend dev with 2 years of experience.",
    )


def test_captcha_detection_positive():
    content = "<html><div class='g-recaptcha'>Please verify</div></html>"
    assert _check_captcha_in_content(content) is True


def test_captcha_detection_hcaptcha():
    content = "<html><script src='hcaptcha.com/api.js'></script></html>"
    assert _check_captcha_in_content(content) is True


def test_captcha_detection_negative():
    content = "<html><form><input type='text' name='email'></form></html>"
    assert _check_captcha_in_content(content) is False


def test_generate_answers_returns_dict():
    profile = _make_profile()
    fields = [
        {"id": "name_field", "label": "Full Name", "type": "text", "name": "name_field"},
        {"id": "email_field", "label": "Email Address", "type": "email", "name": "email_field"},
    ]
    mock_response = MagicMock()
    mock_response.text = '{"name_field": "Mudit Kumar", "email_field": "m@m.com"}'
    with patch("src.web_form_filler.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        answers = _generate_answers(fields, profile, "Python backend role", "Acme", "SWE")
    assert answers["name_field"] == "Mudit Kumar"
    assert answers["email_field"] == "m@m.com"


def test_generate_answers_strips_markdown_fences():
    profile = _make_profile()
    fields = [{"id": "f1", "label": "Name", "type": "text", "name": "f1"}]
    mock_response = MagicMock()
    mock_response.text = '```json\n{"f1": "Mudit Kumar"}\n```'
    with patch("src.web_form_filler.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        answers = _generate_answers(fields, profile, "role desc", "Co", "Role")
    assert answers["f1"] == "Mudit Kumar"


def test_captcha_detected_error_is_exception():
    with pytest.raises(CaptchaDetectedError):
        raise CaptchaDetectedError("CAPTCHA found")


def test_form_submit_error_is_exception():
    with pytest.raises(FormSubmitError):
        raise FormSubmitError("Submit button not found")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_web_form_filler.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.web_form_filler'`

- [ ] **Step 3: Create src/web_form_filler.py**

```python
import json
import re
import logging
from typing import Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import google.generativeai as genai
from src.config import GEMINI_API_KEY
from src.profile import UserProfile

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
log = logging.getLogger(__name__)

_CAPTCHA_INDICATORS = ["recaptcha", "hcaptcha", "cf-turnstile", "captcha"]

_EXTRACT_FIELDS_JS = """() => {
    const fields = [];
    const inputs = document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]), textarea, select'
    );
    inputs.forEach(input => {
        const id = input.id || '';
        const name = input.name || '';
        let label = '';
        if (id) {
            const labelEl = document.querySelector('label[for="' + id + '"]');
            if (labelEl) label = labelEl.textContent.trim();
        }
        if (!label) label = input.getAttribute('aria-label') || '';
        if (!label) label = input.getAttribute('placeholder') || '';
        if (!label) {
            const parentLabel = input.closest('label');
            if (parentLabel) label = parentLabel.textContent.trim();
        }
        if (!label) {
            const prev = input.previousElementSibling;
            if (prev) label = prev.textContent.trim().replace(/\\*$/, '').trim();
        }
        const type = input.tagName.toLowerCase() === 'select'
            ? 'select'
            : (input.getAttribute('type') || 'text').toLowerCase();
        const field = { id: id, name: name, label: label, type: type,
                        selector: id ? '#' + id : '[name="' + name + '"]' };
        if (type === 'select') {
            field.options = Array.from(input.options)
                .map(o => o.text.trim()).filter(Boolean);
        }
        if (type === 'radio' || type === 'checkbox') {
            if (name) {
                const group = document.querySelectorAll('input[name="' + name + '"]');
                field.options = Array.from(group).map(el => {
                    const lbl = document.querySelector('label[for="' + el.id + '"]');
                    return lbl ? lbl.textContent.trim() : (el.value || '');
                }).filter(Boolean);
            }
        }
        if (id || name) fields.push(field);
    });
    return fields;
}"""


class CaptchaDetectedError(Exception):
    pass


class FormSubmitError(Exception):
    pass


def _check_captcha_in_content(html_content: str) -> bool:
    """Return True if any CAPTCHA indicator is found in the page HTML."""
    lower = html_content.lower()
    return any(indicator in lower for indicator in _CAPTCHA_INDICATORS)


def _generate_answers(
    fields: list,
    profile: UserProfile,
    jd_summary: str,
    company: str,
    role: str,
) -> dict:
    """Ask Gemini to fill all form fields based on the candidate profile."""
    prompt = f"""You are filling a job application form for: {role} at {company}.

Job requirements: {jd_summary}

Candidate profile:
Name: {profile.name}
Email: {profile.email}
Phone: {profile.phone}
LinkedIn: {profile.linkedin}
College: {profile.college}, {profile.degree}, CGPA: {profile.cgpa}
Graduation year: {profile.graduation_year}
Years of experience: {profile.years_of_experience}
Current CTC: {profile.current_ctc}
Expected CTC: {profile.expected_ctc}
Notice period: {profile.notice_period}
Location preference: {profile.location_preference}
Work authorization: {profile.work_authorization}
Skills: {", ".join(profile.skills)}
Summary: {profile.summary}

Form fields to fill:
{json.dumps(fields, indent=2)}

Rules:
- For each field, return the best answer from the candidate profile.
- For "Why do you want to work here", "Cover letter", or "About yourself" fields: write 3-4 specific sentences referencing the company name, the role, and the candidate's relevant experience.
- For select/radio fields: pick the EXACT text of the best matching option from the "options" list.
- For file upload fields (type="file"): return the string "RESUME_PDF".
- Use the field's "id" if present, else "name" as the JSON key.
- Return ONLY a valid JSON object with no markdown fences."""

    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _fill_field(page: Page, field: dict, answer: str) -> None:
    """Fill a single form field. Silently logs on failure."""
    selector = field.get("selector") or f'[name="{field["name"]}"]'
    field_type = field.get("type", "text")
    try:
        if field_type in ("text", "email", "tel", "number", "url", "textarea"):
            page.fill(selector, str(answer))
        elif field_type == "select":
            page.select_option(selector, label=str(answer))
        elif field_type in ("radio", "checkbox"):
            name = field.get("name", "")
            if name:
                radios = page.locator(f'input[name="{name}"]')
                count = radios.count()
                for i in range(count):
                    radio = radios.nth(i)
                    rid = radio.get_attribute("id") or ""
                    label_el = page.locator(f'label[for="{rid}"]')
                    label_text = label_el.text_content() if label_el.count() > 0 else ""
                    if label_text and answer.lower() in label_text.lower():
                        radio.click()
                        break
    except Exception as e:
        log.warning(f"Could not fill field '{field.get('label', selector)}': {e}")


def fill_web_form(
    url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
) -> bool:
    """
    Open a job application URL in a headless browser, fill all form fields
    using Gemini, and submit. Handles multi-page forms.

    Returns True on successful submission.
    Raises CaptchaDetectedError if a CAPTCHA is found.
    Raises FormSubmitError if the submit button cannot be found.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
        except PlaywrightTimeoutError:
            log.warning("networkidle timeout, continuing with domcontentloaded")
            page.goto(url, timeout=30000, wait_until="domcontentloaded")

        if _check_captcha_in_content(page.content()):
            browser.close()
            raise CaptchaDetectedError(f"CAPTCHA detected on {url}")

        max_pages = 10
        for _ in range(max_pages):
            page.wait_for_timeout(1500)

            fields = page.evaluate(_EXTRACT_FIELDS_JS)
            if not fields:
                break

            answers = _generate_answers(fields, profile, jd_summary, company, role)

            for field in fields:
                key = field.get("id") or field.get("name")
                if not key:
                    continue
                if field.get("type") == "file":
                    try:
                        page.set_input_files(field["selector"], pdf_path)
                    except Exception as e:
                        log.warning(f"File upload failed for '{field.get('label')}': {e}")
                    continue
                answer = answers.get(key)
                if answer and str(answer) != "RESUME_PDF":
                    _fill_field(page, field, str(answer))

            # Check for Next / Continue button
            next_btn = None
            for label in ["Next", "Continue", "Next Step", "Proceed"]:
                btn = page.get_by_role("button", name=re.compile(label, re.IGNORECASE))
                if btn.count() > 0:
                    next_btn = btn.first
                    break

            if next_btn:
                next_btn.click()
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    pass
                if _check_captcha_in_content(page.content()):
                    browser.close()
                    raise CaptchaDetectedError(f"CAPTCHA appeared mid-form on {url}")
                continue

            # Check for Submit button
            submit_btn = None
            for label in ["Submit", "Apply", "Submit Application", "Apply Now", "Send Application"]:
                btn = page.get_by_role("button", name=re.compile(label, re.IGNORECASE))
                if btn.count() > 0:
                    submit_btn = btn.first
                    break

            if submit_btn:
                submit_btn.click()
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeoutError:
                    pass
                browser.close()
                return True

            # No Next or Submit found — cannot proceed
            break

        browser.close()
        raise FormSubmitError(f"Could not find submit button after filling form at {url}")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_web_form_filler.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/web_form_filler.py tests/test_web_form_filler.py
git commit -m "feat: add Playwright universal web form filler with CAPTCHA detection"
```

---

## Task 7: Wire everything into orchestrator.py

**Files:**
- Modify: `src/orchestrator.py`

- [ ] **Step 1: Read the current orchestrator**

Open `src/orchestrator.py` and read it fully. The current flow is:
1. Check is_relevant + apply_type
2. Compile resume PDF
3. Upload to Drive
4. Send email or fill Google Form
5. Notify

The new flow inserts before step 2: duplicate check, then eligibility check. And after step 3: routes WEB_FORM to `fill_web_form`. Logs every outcome to tracker.

- [ ] **Step 2: Replace src/orchestrator.py with the updated version**

```python
import os
import logging
from datetime import datetime
from src.models import ApplyType, JobPosting
from src.resume_tailor import save_pdf
from src.drive_uploader import upload_pdf
from src.email_sender import send_email
from src.form_filler import fill_form
from src.web_form_filler import fill_web_form, CaptchaDetectedError, FormSubmitError
from src.notifier import notify_self, format_success, format_error
from src.config import OUTPUT_DIR, LOG_PATH
from src.profile import load_profile
from src.eligibility import check_eligibility
from src.tracker import is_duplicate, log_application

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Load user profile once at startup
_profile = load_profile()


async def process_job(job: JobPosting) -> None:
    if not job.is_relevant:
        log.info("Skipping irrelevant message")
        return

    if job.apply_type == ApplyType.UNKNOWN or not job.apply_target:
        log.warning(f"Unknown apply method for {job.company} — {job.role}")
        return

    # Duplicate check
    if is_duplicate(job.company, job.role):
        log.info(f"Already applied to {job.role} at {job.company} — skipping")
        return

    # Eligibility check
    eligibility = check_eligibility(job, _profile)
    if not eligibility.eligible:
        log.info(f"Ineligible: {job.role} at {job.company} — {eligibility.reason}")
        log_application(
            company=job.company,
            role=job.role,
            apply_target=job.apply_target,
            apply_type=job.apply_type.value,
            status="skipped",
            skip_reason=eligibility.reason,
        )
        await notify_self(
            f"⏭ Skipped: {job.role} at {job.company}\nReason: {eligibility.reason}"
        )
        return

    log.info(f"Processing: {job.role} at {job.company} ({job.apply_type.value})")

    safe_name = f"{job.company}_{job.role}".replace(" ", "_").replace("/", "-")
    pdf_path = os.path.join(OUTPUT_DIR, f"{safe_name}.pdf")

    try:
        save_pdf(job.company, job.role, job.jd_summary, pdf_path)
        log.info(f"Resume compiled: {pdf_path}")
    except Exception as e:
        log.error(f"Resume tailor failed: {e}")
        await notify_self(format_error(job.company, job.role, f"Resume tailor: {e}"))
        return

    drive_link = ""
    try:
        drive_link = upload_pdf(pdf_path, f"MuditKumar_{safe_name}.pdf")
        log.info(f"PDF uploaded to Drive: {drive_link}")
    except Exception as e:
        log.warning(f"Drive upload failed (continuing): {e}")
        drive_link = "https://linkedin.com/in/mudit-dev"

    try:
        if job.apply_type == ApplyType.EMAIL:
            send_email(job.apply_target, job.company, job.role, job.location, pdf_path)
            log.info(f"Email sent to {job.apply_target}")

        elif job.apply_type == ApplyType.FORM:
            fill_form(job.apply_target, job.company, job.role, job.jd_summary, drive_link)
            log.info(f"Google Form submitted: {job.apply_target}")

        elif job.apply_type == ApplyType.WEB_FORM:
            fill_web_form(
                url=job.apply_target,
                company=job.company,
                role=job.role,
                jd_summary=job.jd_summary,
                pdf_path=pdf_path,
                profile=_profile,
            )
            log.info(f"Web form submitted: {job.apply_target}")

    except CaptchaDetectedError as e:
        log.warning(str(e))
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason="CAPTCHA detected",
        )
        await notify_self(
            f"🔒 CAPTCHA on {job.role} at {job.company} — apply manually:\n{job.apply_target}"
        )
        return

    except FormSubmitError as e:
        log.warning(str(e))
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason="Submit button not found",
        )
        await notify_self(
            f"⚠️ Form submit failed for {job.role} at {job.company} — apply manually:\n{job.apply_target}"
        )
        return

    except Exception as e:
        log.error(f"Apply failed: {e}")
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason=str(e),
        )
        await notify_self(format_error(job.company, job.role, str(e)))
        return

    log_application(
        company=job.company, role=job.role,
        apply_target=job.apply_target, apply_type=job.apply_type.value,
        status="applied",
    )
    await notify_self(
        format_success(job.company, job.role, job.apply_type.value, job.apply_target)
    )
    log.info(f"Done: {job.company} — {job.role} at {datetime.now().isoformat()}")
```

- [ ] **Step 3: Run the full test suite**

```bash
pytest -v
```

Expected: all tests pass (profile loading at module level needs `config/profile.json` to exist — tests that import orchestrator need to mock `load_profile` or have the file present. If tests fail due to missing profile.json, add this fixture to the failing test file at the top):

```python
import json, os, tempfile
# If orchestrator tests fail, patch load_profile:
# with patch("src.orchestrator._profile", _make_profile()):
```

The existing tests do not import orchestrator, so this should be fine.

- [ ] **Step 4: Manual smoke test — verify the full pipeline logic**

Run:
```bash
python -c "
from src.profile import load_profile
from src.eligibility import check_eligibility, EligibilityResult
from src.tracker import is_duplicate, log_application
from src.models import JobPosting, ApplyType

profile = load_profile()
print('Profile loaded:', profile.name)

job = JobPosting(company='Test', role='SWE', salary='', location='',
    jd_summary='Python backend role', apply_type=ApplyType.EMAIL,
    apply_target='hr@test.com', batch='2026 passout', raw_message='', is_relevant=True)

result = check_eligibility(job, profile)
print('Eligibility (should be False - batch 2026):', result.eligible, '-', result.reason)
"
```

Expected output:
```
Profile loaded: Mudit Kumar
Eligibility (should be False - batch 2026): False - Batch mismatch — job requires 2026 passout, you are 2024 passout
```

- [ ] **Step 5: Commit**

```bash
git add src/orchestrator.py
git commit -m "feat: wire eligibility check, duplicate prevention, and web form filler into orchestrator"
```

---

## Task 8: Final integration check

- [ ] **Step 1: Run the complete test suite**

```bash
pytest -v
```

Expected: all tests pass with output similar to:
```
tests/test_eligibility.py::test_batch_mismatch_returns_ineligible PASSED
tests/test_eligibility.py::test_batch_match_passes PASSED
tests/test_eligibility.py::test_experience_mismatch_returns_ineligible PASSED
tests/test_eligibility.py::test_experience_match_passes PASSED
tests/test_eligibility.py::test_skills_mismatch_returns_ineligible PASSED
tests/test_eligibility.py::test_skills_check_skipped_if_gemini_fails PASSED
tests/test_eligibility.py::test_no_batch_in_job_skips_batch_rule PASSED
tests/test_form_filler.py::test_extract_form_id_from_url PASSED
tests/test_form_filler.py::test_extract_form_id_from_short_url PASSED
tests/test_form_filler.py::test_build_submit_url PASSED
tests/test_form_filler.py::test_generate_answers_returns_dict PASSED
tests/test_parser.py::test_build_prompt_contains_message PASSED
tests/test_parser.py::test_parse_email_job PASSED
tests/test_parser.py::test_parse_form_job PASSED
tests/test_parser.py::test_parse_irrelevant_message PASSED
tests/test_parser.py::test_is_web_form_greenhouse PASSED
tests/test_parser.py::test_is_web_form_lever PASSED
... (all new parser tests) PASSED
tests/test_profile.py::test_load_profile_returns_userprofile PASSED
tests/test_profile.py::test_load_profile_missing_file_raises PASSED
tests/test_tracker.py::test_is_duplicate_returns_false_for_new_job PASSED
tests/test_tracker.py::test_log_and_detect_duplicate PASSED
tests/test_tracker.py::test_skipped_job_not_counted_as_duplicate PASSED
tests/test_tracker.py::test_log_application_stores_all_fields PASSED
tests/test_web_form_filler.py::test_captcha_detection_positive PASSED
tests/test_web_form_filler.py::test_captcha_detection_hcaptcha PASSED
tests/test_web_form_filler.py::test_captcha_detection_negative PASSED
tests/test_web_form_filler.py::test_generate_answers_returns_dict PASSED
tests/test_web_form_filler.py::test_generate_answers_strips_markdown_fences PASSED
tests/test_web_form_filler.py::test_captcha_detected_error_is_exception PASSED
tests/test_web_form_filler.py::test_form_submit_error_is_exception PASSED
```

- [ ] **Step 2: Commit final state**

```bash
git add .
git commit -m "feat: universal form filler v1 complete — eligibility, tracker, Playwright ATS support"
```
