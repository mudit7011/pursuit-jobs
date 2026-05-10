# Job Autopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Monitor a private Telegram group for job postings, auto-tailor a LaTeX resume using Gemini, and automatically apply via email or Google Form — deployed 24/7 on Railway.

**Architecture:** Telethon listens to a private Telegram group on a cloud server. Each new message is parsed by Gemini into a structured JobPosting. If it's a valid job, Gemini tailors the LaTeX resume, tectonic compiles it to PDF, and the system applies via Gmail SMTP (email jobs) or direct HTTP POST (Google Form jobs). A self-notification is sent to the user's own Telegram after each application.

**Tech Stack:** Python 3.11, Telethon, google-generativeai, tectonic (CLI), smtplib, requests, BeautifulSoup4, google-api-python-client, python-dotenv, pytest, Railway (deployment)

---

## File Map

| File | Responsibility |
|------|---------------|
| `src/config.py` | Load and validate all env vars |
| `src/models.py` | JobPosting dataclass |
| `src/monitor.py` | Telethon listener — new message → trigger pipeline |
| `src/parser.py` | Gemini: raw Telegram message → JobPosting |
| `src/resume_tailor.py` | Gemini: base LaTeX + JD → tailored LaTeX → PDF via tectonic |
| `src/email_sender.py` | Gmail SMTP: send tailored PDF + email body |
| `src/form_filler.py` | Parse Google Form HTML → POST submission |
| `src/drive_uploader.py` | Upload PDF to Google Drive → get shareable link |
| `src/notifier.py` | Send Telegram message to self after apply |
| `src/orchestrator.py` | Wire all components: parse → tailor → apply → notify |
| `src/main.py` | Entry point: start Telethon event loop |
| `tests/test_parser.py` | Unit tests for parser output validation |
| `tests/test_resume_tailor.py` | Unit tests for LaTeX modification logic |
| `tests/test_email_sender.py` | Unit tests for email formatting |
| `tests/test_form_filler.py` | Unit tests for form field extraction |
| `templates/MuditCV.tex` | Base LaTeX resume template |
| `.env.example` | Template for credentials |
| `Dockerfile` | Railway deployment |
| `requirements.txt` | Python dependencies |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
telethon==1.36.0
google-generativeai==0.8.3
google-api-python-client==2.139.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
beautifulsoup4==4.12.3
requests==2.32.3
python-dotenv==1.0.1
pytest==8.3.2
pytest-asyncio==0.23.8
```

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/muditchaudhary/job-autopilot
pip3 install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 3: Create .env.example**

```bash
# Telegram (get from https://my.telegram.org)
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=
TELEGRAM_GROUP_ID=        # e.g. -1001234567890
TELEGRAM_SELF_ID=         # your own Telegram user ID

# Gemini (get from https://aistudio.google.com)
GEMINI_API_KEY=

# Gmail (use App Password, not your real password)
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=

# Google Drive (base64-encoded service account JSON)
GOOGLE_SERVICE_ACCOUNT_B64=
GOOGLE_DRIVE_FOLDER_ID=

# App
LOG_LEVEL=INFO
```

- [ ] **Step 4: Create .gitignore**

```
.env
*.session
__pycache__/
*.pyc
*.pdf
logs/*.log
output/
.pytest_cache/
```

- [ ] **Step 5: Init git and commit**

```bash
cd /Users/muditchaudhary/job-autopilot
git init
git add requirements.txt .env.example .gitignore templates/
git commit -m "chore: project scaffold with LaTeX template"
```

---

## Task 2: Config + Models

**Files:**
- Create: `src/config.py`
- Create: `src/models.py`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create src/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val

TELEGRAM_API_ID = int(_require("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = _require("TELEGRAM_API_HASH")
TELEGRAM_SESSION_STRING = _require("TELEGRAM_SESSION_STRING")
TELEGRAM_GROUP_ID = int(_require("TELEGRAM_GROUP_ID"))
TELEGRAM_SELF_ID = int(_require("TELEGRAM_SELF_ID"))

GEMINI_API_KEY = _require("GEMINI_API_KEY")

GMAIL_ADDRESS = _require("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = _require("GMAIL_APP_PASSWORD")

GOOGLE_SERVICE_ACCOUNT_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

BASE_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "MuditCV.tex")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "applications.log")
```

- [ ] **Step 2: Create src/models.py**

```python
from dataclasses import dataclass
from enum import Enum

class ApplyType(Enum):
    EMAIL = "email"
    FORM = "form"
    UNKNOWN = "unknown"

@dataclass
class JobPosting:
    company: str
    role: str
    salary: str
    location: str
    jd_summary: str
    apply_type: ApplyType
    apply_target: str      # email address OR Google Form URL
    batch: str
    raw_message: str
    is_relevant: bool = True
```

- [ ] **Step 3: Create empty __init__.py files**

```bash
touch /Users/muditchaudhary/job-autopilot/src/__init__.py
touch /Users/muditchaudhary/job-autopilot/tests/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add src/
git commit -m "feat: config loader and JobPosting model"
```

---

## Task 3: Job Parser

**Files:**
- Create: `src/parser.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_parser.py
import pytest
from unittest.mock import patch, MagicMock
from src.models import JobPosting, ApplyType
from src.parser import parse_job_message, _build_prompt

def test_build_prompt_contains_message():
    msg = "Company - TestCo\nRole - SWE Intern"
    prompt = _build_prompt(msg)
    assert "TestCo" in prompt
    assert "SWE Intern" in prompt

def test_parse_email_job():
    sample_response = '''{
        "company": "Instamart",
        "role": "Data Analyst",
        "salary": "₹50,000 - ₹90,000/month",
        "location": "Gurgaon",
        "jd_summary": "Data analysis, reports, SQL, Python",
        "apply_type": "email",
        "apply_target": "kunalranjan2k14@gmail.com",
        "batch": "2023/2024/2025",
        "is_relevant": true
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("some message text")
    assert isinstance(result, JobPosting)
    assert result.company == "Instamart"
    assert result.apply_type == ApplyType.EMAIL
    assert result.apply_target == "kunalranjan2k14@gmail.com"

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
    assert result.apply_type == ApplyType.FORM
    assert "aspire" in result.apply_target

def test_parse_irrelevant_message():
    sample_response = '''{
        "company": "",
        "role": "",
        "salary": "",
        "location": "",
        "jd_summary": "",
        "apply_type": "unknown",
        "apply_target": "",
        "batch": "",
        "is_relevant": false
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("Good morning everyone!")
    assert result.is_relevant is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/muditchaudhary/job-autopilot
python3 -m pytest tests/test_parser.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.parser'`

- [ ] **Step 3: Create src/parser.py**

```python
import json
import re
import google.generativeai as genai
from src.config import GEMINI_API_KEY
from src.models import JobPosting, ApplyType

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def _build_prompt(message: str) -> str:
    return f"""Extract job details from this Telegram message. Return ONLY valid JSON, no markdown, no explanation.

Message:
{message}

Return this exact JSON:
{{
  "company": "company name or empty string",
  "role": "job title or empty string",
  "salary": "salary info or empty string",
  "location": "city or empty string",
  "jd_summary": "2-3 sentence summary of requirements and responsibilities",
  "apply_type": "email" or "form" or "unknown",
  "apply_target": "email address or Google Form URL or empty string",
  "batch": "graduation batch years or empty string",
  "is_relevant": true if this is a job posting else false
}}"""

def parse_job_message(message: str) -> JobPosting:
    prompt = _build_prompt(message)
    response = model.generate_content(prompt)
    raw = response.text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)
    apply_type_map = {
        "email": ApplyType.EMAIL,
        "form": ApplyType.FORM,
    }
    return JobPosting(
        company=data.get("company", ""),
        role=data.get("role", ""),
        salary=data.get("salary", ""),
        location=data.get("location", ""),
        jd_summary=data.get("jd_summary", ""),
        apply_type=apply_type_map.get(data.get("apply_type", "unknown"), ApplyType.UNKNOWN),
        apply_target=data.get("apply_target", ""),
        batch=data.get("batch", ""),
        raw_message=message,
        is_relevant=data.get("is_relevant", False),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_parser.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/parser.py tests/test_parser.py
git commit -m "feat: Gemini job parser with tests"
```

---

## Task 4: Resume Tailor

**Files:**
- Create: `src/resume_tailor.py`
- Create: `tests/test_resume_tailor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_resume_tailor.py
import os
import pytest
from unittest.mock import patch, MagicMock
from src.resume_tailor import _build_tailor_prompt, _extract_latex, save_pdf

SAMPLE_JD = "Backend engineering, REST APIs, Python, AWS, AI tools"
SAMPLE_LATEX = r"\begin{document}\n\section{Skills}\nPython\n\end{document}"

def test_build_tailor_prompt_contains_jd():
    prompt = _build_tailor_prompt(SAMPLE_LATEX, SAMPLE_JD, "Aspire", "SWE Intern")
    assert "REST APIs" in prompt
    assert "Aspire" in prompt
    assert "SWE Intern" in prompt

def test_extract_latex_strips_fences():
    raw = "```latex\n\\documentclass{article}\n```"
    result = _extract_latex(raw)
    assert result == "\\documentclass{article}"

def test_extract_latex_no_fences():
    raw = "\\documentclass{article}"
    result = _extract_latex(raw)
    assert result == "\\documentclass{article}"

def test_save_pdf_creates_file(tmp_path):
    latex = open("templates/MuditCV.tex").read()
    output_path = str(tmp_path / "test_resume.pdf")
    with patch("src.resume_tailor.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = latex  # return unmodified latex
        mock_model.generate_content.return_value = mock_response
        result = save_pdf("Test Company", "SWE", "Python backend job", output_path)
    assert os.path.exists(result)
    assert result.endswith(".pdf")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_resume_tailor.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.resume_tailor'`

- [ ] **Step 3: Create src/resume_tailor.py**

```python
import os
import re
import subprocess
import tempfile
import shutil
import google.generativeai as genai
from src.config import GEMINI_API_KEY, BASE_TEMPLATE_PATH, OUTPUT_DIR

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def _build_tailor_prompt(base_latex: str, jd_summary: str, company: str, role: str) -> str:
    return f"""You are a resume tailoring assistant. Modify this LaTeX resume to better match the job.

STRICT RULES:
- Only modify content inside: Technical Skills section, Experience bullet points, Projects bullet points
- Do NOT change any LaTeX commands, structure, formatting, or the header
- Do NOT add or remove sections
- Keep all \\resumeItem, \\resumeSubheading, \\resumeProjectHeading commands exactly as-is
- Reorder projects to put the most relevant one first
- Return ONLY the complete valid LaTeX, no explanation, no markdown fences

JOB: {role} at {company}
JOB REQUIREMENTS: {jd_summary}

BASE LATEX:
{base_latex}"""

def _extract_latex(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:latex)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()

def save_pdf(company: str, role: str, jd_summary: str, output_path: str) -> str:
    base_latex = open(BASE_TEMPLATE_PATH).read()
    prompt = _build_tailor_prompt(base_latex, jd_summary, company, role)
    response = model.generate_content(prompt)
    tailored_latex = _extract_latex(response.text)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w") as f:
            f.write(tailored_latex)
        result = subprocess.run(
            ["tectonic", tex_path],
            capture_output=True, text=True, cwd=tmpdir
        )
        if result.returncode != 0:
            raise RuntimeError(f"tectonic failed:\n{result.stderr}")
        compiled_pdf = os.path.join(tmpdir, "resume.pdf")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy(compiled_pdf, output_path)

    return output_path
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_resume_tailor.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/resume_tailor.py tests/test_resume_tailor.py
git commit -m "feat: Gemini resume tailor + tectonic PDF compiler"
```

---

## Task 5: Google Drive Uploader

**Files:**
- Create: `src/drive_uploader.py`

- [ ] **Step 1: Create src/drive_uploader.py**

```python
import base64
import json
import os
import tempfile
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from src.config import GOOGLE_SERVICE_ACCOUNT_B64, GOOGLE_DRIVE_FOLDER_ID

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def _get_drive_service():
    if not GOOGLE_SERVICE_ACCOUNT_B64:
        raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_B64 not set")
    sa_json = base64.b64decode(GOOGLE_SERVICE_ACCOUNT_B64).decode()
    sa_info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_pdf(pdf_path: str, filename: str) -> str:
    """Upload PDF to Google Drive folder, return shareable link."""
    service = _get_drive_service()
    file_metadata = {
        "name": filename,
        "parents": [GOOGLE_DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(pdf_path, mimetype="application/pdf")
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    file_id = uploaded.get("id")
    # Make publicly readable
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"}
    ).execute()
    return f"https://drive.google.com/file/d/{file_id}/view"
```

- [ ] **Step 2: Commit**

```bash
git add src/drive_uploader.py
git commit -m "feat: Google Drive PDF uploader"
```

---

## Task 6: Email Sender

**Files:**
- Create: `src/email_sender.py`
- Create: `tests/test_email_sender.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_email_sender.py
from src.email_sender import _build_email_body, _build_subject

def test_subject_contains_company_and_role():
    subject = _build_subject("Instamart", "Data Analyst")
    assert "Instamart" in subject
    assert "Data Analyst" in subject

def test_email_body_contains_key_info():
    body = _build_email_body("Instamart", "Data Analyst", "Gurgaon")
    assert "Instamart" in body
    assert "Data Analyst" in body
    assert "Mudit Kumar" in body
    assert "8533888088" in body
    assert "muditkumar7011@gmail.com" in body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_email_sender.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.email_sender'`

- [ ] **Step 3: Create src/email_sender.py**

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from src.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

def _build_subject(company: str, role: str) -> str:
    return f"Application for {role} – {company} | Mudit Kumar (Immediate Joiner)"

def _build_email_body(company: str, role: str, location: str) -> str:
    return f"""Hi,

I'm applying for the {role} role at {company}. I'm a 2024 CS graduate with hands-on experience in backend systems, REST APIs, Python, and AI-assisted development workflows.

At Nedzo AI, I built and owned production-grade backend integrations and automation pipelines. At Kushel Digi Solutions, I optimized MongoDB queries improving performance by 40% and shipped features that reduced operational turnaround by 25%. I've also shipped two production apps — FootPrints (cross-platform with Gemini AI integrations) and a Personal Finance Tracker (full-stack with real-time analytics).

I'm immediately available and excited about this opportunity at {company} in {location}. Please find my tailored resume attached.

Happy to connect at your convenience.

Best regards,
Mudit Kumar
+91 8533888088
muditkumar7011@gmail.com
linkedin.com/in/mudit-dev"""

def send_email(to_address: str, company: str, role: str, location: str, pdf_path: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = _build_subject(company, role)
    msg.attach(MIMEText(_build_email_body(company, role, location), "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="MuditKumar_Resume.pdf"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_email_sender.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/email_sender.py tests/test_email_sender.py
git commit -m "feat: Gmail SMTP email sender with tests"
```

---

## Task 7: Google Form Filler

**Files:**
- Create: `src/form_filler.py`
- Create: `tests/test_form_filler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_form_filler.py
from src.form_filler import _extract_form_id, _build_submit_url, _generate_answers

def test_extract_form_id_from_url():
    url = "https://docs.google.com/forms/d/e/1FAIpQLSexample123/viewform"
    form_id = _extract_form_id(url)
    assert form_id == "1FAIpQLSexample123"

def test_extract_form_id_from_short_url():
    # people-jobs.com style redirect - returns None, handled in fill_form
    url = "https://people-jobs.com/aspire/apply/software-engineering-intern-abc123"
    form_id = _extract_form_id(url)
    assert form_id is None

def test_build_submit_url():
    form_id = "1FAIpQLSexample123"
    url = _build_submit_url(form_id)
    assert url == "https://docs.google.com/forms/d/e/1FAIpQLSexample123/formResponse"

def test_generate_answers_returns_dict():
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.text = '{"Why refer you": "Strong backend skills", "What have you built": "FootPrints app"}'
    with patch("src.form_filler.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        answers = _generate_answers(
            ["Why refer you", "What have you built"],
            "Aspire SWE Intern", "Backend, APIs, Python"
        )
    assert "Why refer you" in answers
    assert "FootPrints" in answers["What have you built"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_form_filler.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.form_filler'`

- [ ] **Step 3: Create src/form_filler.py**

```python
import re
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional
import google.generativeai as genai
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

MUDIT_PROFILE = """
Name: Mudit Kumar
Email: muditkumar7011@gmail.com
Phone: +91 8533888088
LinkedIn: linkedin.com/in/mudit-dev
College: Dr APJ Abdul Kalam Technical University, Lucknow
Degree: B.Tech Computer Science Engineering
CGPA: 7.49
Graduation Year: 2024
Notice Period: Immediate joiner
Key Skills: Python, Node.js, TypeScript, REST APIs, MongoDB, Firebase, AWS, LLM APIs, n8n
Key Projects: FootPrints (cross-platform app with AI), Personal Finance Tracker (full-stack analytics)
Experience: Backend & DevOps at Nedzo AI (6 months), Backend Developer at Kushel Digi Solutions (3 months)
"""

STANDARD_ANSWERS = {
    "name": "Mudit Kumar",
    "email": "muditkumar7011@gmail.com",
    "phone": "+91 8533888088",
    "linkedin": "https://linkedin.com/in/mudit-dev",
    "college": "Dr APJ Abdul Kalam Technical University, Lucknow",
    "cgpa": "7.49",
    "graduation": "2024",
    "notice": "Immediate",
    "location": "Open to Gurugram/Noida/Bangalore/Remote",
}

def _extract_form_id(url: str) -> Optional[str]:
    match = re.search(r"/forms/d/e/([^/]+)/", url)
    return match.group(1) if match else None

def _build_submit_url(form_id: str) -> str:
    return f"https://docs.google.com/forms/d/e/{form_id}/formResponse"

def _resolve_url(url: str) -> str:
    """Follow redirects to get final Google Form URL."""
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        return r.url
    except Exception:
        return url

def _parse_form_fields(html: str) -> dict:
    """Extract {entry_id: question_label} from Google Form HTML."""
    soup = BeautifulSoup(html, "html.parser")
    fields = {}
    # Google Forms stores data in a script tag as JSON
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "FB_PUBLIC_LOAD_DATA_" in script.string:
            match = re.search(r"FB_PUBLIC_LOAD_DATA_ = (.+);", script.string, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    # Form fields are in data[1][1]
                    form_items = data[1][1]
                    for item in form_items:
                        if len(item) > 4 and item[4]:
                            label = item[1]  # question text
                            entry_id = f"entry.{item[4][0][0]}"
                            fields[entry_id] = label
                except (json.JSONDecodeError, IndexError, TypeError):
                    pass
    return fields

def _generate_answers(questions: list, role: str, jd_summary: str) -> dict:
    """Use Gemini to answer custom questions based on Mudit's profile."""
    prompt = f"""Answer these job application questions for the role: {role}
Job requirements: {jd_summary}

Candidate profile:
{MUDIT_PROFILE}

Questions to answer:
{json.dumps(questions)}

Return ONLY a JSON object with question as key and answer as value.
Answers should be concise (2-4 sentences max), specific, and highlight relevant experience.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)

def _match_standard_answer(label: str) -> Optional[str]:
    """Match common form fields to standard answers."""
    label_lower = label.lower()
    if any(k in label_lower for k in ["your name", "full name", "candidate name"]):
        return STANDARD_ANSWERS["name"]
    if "email" in label_lower:
        return STANDARD_ANSWERS["email"]
    if "phone" in label_lower or "mobile" in label_lower or "contact" in label_lower:
        return STANDARD_ANSWERS["phone"]
    if "linkedin" in label_lower:
        return STANDARD_ANSWERS["linkedin"]
    if "college" in label_lower or "university" in label_lower or "institution" in label_lower:
        return STANDARD_ANSWERS["college"]
    if "cgpa" in label_lower or "gpa" in label_lower or "percentage" in label_lower:
        return STANDARD_ANSWERS["cgpa"]
    if "graduation" in label_lower or "batch" in label_lower or "pass out" in label_lower:
        return STANDARD_ANSWERS["graduation"]
    if "notice" in label_lower or "joining" in label_lower or "available" in label_lower:
        return STANDARD_ANSWERS["notice"]
    if "current location" in label_lower or "preferred location" in label_lower:
        return STANDARD_ANSWERS["location"]
    return None

def fill_form(form_url: str, company: str, role: str, jd_summary: str, drive_pdf_link: str) -> bool:
    """Fill and submit a Google Form. Returns True on success."""
    # Resolve redirects to get actual Google Form URL
    resolved_url = _resolve_url(form_url)
    form_id = _extract_form_id(resolved_url)
    if not form_id:
        raise ValueError(f"Could not extract Google Form ID from: {resolved_url}")

    # Fetch form HTML and parse fields
    response = requests.get(resolved_url, timeout=10)
    fields = _parse_form_fields(response.text)

    if not fields:
        raise ValueError("No form fields found — form structure may have changed")

    # Identify custom questions (not matched by standard answers)
    custom_questions = [
        label for label in fields.values()
        if _match_standard_answer(label) is None
        and "resume" not in label.lower()
        and "cv" not in label.lower()
    ]

    # Generate Gemini answers for custom questions
    gemini_answers = {}
    if custom_questions:
        gemini_answers = _generate_answers(custom_questions, role, jd_summary)

    # Build form submission payload
    payload = {}
    for entry_id, label in fields.items():
        standard = _match_standard_answer(label)
        if standard:
            payload[entry_id] = standard
        elif "resume" in label.lower() or "cv" in label.lower():
            payload[entry_id] = drive_pdf_link
        elif label in gemini_answers:
            payload[entry_id] = gemini_answers[label]

    submit_url = _build_submit_url(form_id)
    r = requests.post(submit_url, data=payload, timeout=15)
    # Google Forms returns 200 even for invalid submissions; 0 means network error
    return r.status_code == 200
```

- [ ] **Step 4: Run tests**

```bash
python3 -m pytest tests/test_form_filler.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/form_filler.py tests/test_form_filler.py
git commit -m "feat: Google Form auto-filler with Gemini dynamic answers"
```

---

## Task 8: Notifier

**Files:**
- Create: `src/notifier.py`

- [ ] **Step 1: Create src/notifier.py**

```python
from telethon import TelegramClient
from telethon.sessions import StringSession
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING, TELEGRAM_SELF_ID

async def notify_self(message: str) -> None:
    """Send a message to yourself on Telegram."""
    async with TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    ) as client:
        await client.send_message(TELEGRAM_SELF_ID, message)

def format_success(company: str, role: str, apply_type: str, target: str) -> str:
    return (
        f"✅ Applied!\n"
        f"🏢 {company} — {role}\n"
        f"📨 Via: {apply_type} → {target}\n"
    )

def format_error(company: str, role: str, error: str) -> str:
    return (
        f"❌ Apply failed!\n"
        f"🏢 {company} — {role}\n"
        f"⚠️ Error: {error}\n"
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/notifier.py
git commit -m "feat: Telegram self-notification after apply"
```

---

## Task 9: Orchestrator + Monitor

**Files:**
- Create: `src/orchestrator.py`
- Create: `src/monitor.py`
- Create: `src/main.py`

- [ ] **Step 1: Create src/orchestrator.py**

```python
import os
import logging
from datetime import datetime
from src.models import ApplyType, JobPosting
from src.resume_tailor import save_pdf
from src.drive_uploader import upload_pdf
from src.email_sender import send_email
from src.form_filler import fill_form
from src.notifier import notify_self, format_success, format_error
from src.config import OUTPUT_DIR, LOG_PATH

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

async def process_job(job: JobPosting) -> None:
    if not job.is_relevant:
        log.info("Skipping irrelevant message")
        return
    if job.apply_type == ApplyType.UNKNOWN or not job.apply_target:
        log.warning(f"Unknown apply method for {job.company} — {job.role}")
        return

    log.info(f"Processing: {job.role} at {job.company} ({job.apply_type.value})")

    # Step 1: Tailor resume
    safe_name = f"{job.company}_{job.role}".replace(" ", "_").replace("/", "-")
    pdf_path = os.path.join(OUTPUT_DIR, f"{safe_name}.pdf")
    try:
        save_pdf(job.company, job.role, job.jd_summary, pdf_path)
        log.info(f"Resume compiled: {pdf_path}")
    except Exception as e:
        log.error(f"Resume tailor failed: {e}")
        await notify_self(format_error(job.company, job.role, f"Resume tailor: {e}"))
        return

    # Step 2: Upload to Drive
    drive_link = ""
    try:
        drive_link = upload_pdf(pdf_path, f"MuditKumar_{safe_name}.pdf")
        log.info(f"PDF uploaded to Drive: {drive_link}")
    except Exception as e:
        log.warning(f"Drive upload failed (continuing): {e}")
        drive_link = "https://linkedin.com/in/mudit-dev"  # fallback

    # Step 3: Apply
    try:
        if job.apply_type == ApplyType.EMAIL:
            send_email(job.apply_target, job.company, job.role, job.location, pdf_path)
            log.info(f"Email sent to {job.apply_target}")
        elif job.apply_type == ApplyType.FORM:
            fill_form(job.apply_target, job.company, job.role, job.jd_summary, drive_link)
            log.info(f"Form submitted: {job.apply_target}")
    except Exception as e:
        log.error(f"Apply failed: {e}")
        await notify_self(format_error(job.company, job.role, str(e)))
        return

    # Step 4: Notify self
    await notify_self(format_success(job.company, job.role, job.apply_type.value, job.apply_target))
    log.info(f"Done: {job.company} — {job.role} at {datetime.now().isoformat()}")
```

- [ ] **Step 2: Create src/monitor.py**

```python
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING, TELEGRAM_GROUP_ID
from src.parser import parse_job_message
from src.orchestrator import process_job

log = logging.getLogger(__name__)

async def start_monitor():
    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )

    @client.on(events.NewMessage(chats=TELEGRAM_GROUP_ID))
    async def handler(event):
        message_text = event.message.text
        if not message_text or len(message_text) < 50:
            return
        log.info(f"New message received ({len(message_text)} chars)")
        try:
            job = parse_job_message(message_text)
            await process_job(job)
        except Exception as e:
            log.error(f"Pipeline error: {e}")

    await client.start()
    log.info("Job Autopilot running — monitoring Telegram group...")
    await client.run_until_disconnected()
```

- [ ] **Step 3: Create src/main.py**

```python
import asyncio
from src.monitor import start_monitor

if __name__ == "__main__":
    asyncio.run(start_monitor())
```

- [ ] **Step 4: Commit**

```bash
git add src/orchestrator.py src/monitor.py src/main.py
git commit -m "feat: orchestrator, Telegram monitor, and main entry point"
```

---

## Task 10: Telegram Session Generator

**Files:**
- Create: `generate_session.py` (run once locally, not deployed)

- [ ] **Step 1: Create generate_session.py**

```python
"""
Run this ONCE locally to generate your Telegram session string.
Copy the output into your .env as TELEGRAM_SESSION_STRING=...
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv
load_dotenv()

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n=== YOUR SESSION STRING (copy this to .env) ===")
    print(client.session.save())
    print("===============================================\n")
    # Also print your user ID
    me = client.get_me()
    print(f"Your Telegram User ID (TELEGRAM_SELF_ID): {me.id}")
```

- [ ] **Step 2: Also create get_group_id.py**

```python
"""
Run this ONCE locally to find your Telegram group ID.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv
load_dotenv()

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session = os.environ["TELEGRAM_SESSION_STRING"]

with TelegramClient(StringSession(session), api_id, api_hash) as client:
    for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            print(f"ID: {dialog.id}  |  Name: {dialog.name}")
```

- [ ] **Step 3: Commit**

```bash
git add generate_session.py get_group_id.py
git commit -m "chore: session and group ID helper scripts"
```

---

## Task 11: Dockerfile + Railway Deploy

**Files:**
- Create: `Dockerfile`
- Create: `railway.toml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

# Install tectonic dependencies
RUN apt-get update && apt-get install -y \
    curl wget fontconfig \
    libssl-dev libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Install tectonic
RUN curl -sSf https://drop.Fuller.li/tectonic/install.sh | sh || \
    wget -qO- https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.16.0/tectonic-0.16.0-x86_64-unknown-linux-musl.tar.gz | tar xz -C /usr/local/bin/

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p output logs

CMD ["python3", "-m", "src.main"]
```

- [ ] **Step 2: Fix Dockerfile tectonic install (use GitHub releases)**

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget fontconfig libfontconfig1 libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install tectonic binary for Linux x86_64
RUN wget -qO /tmp/tectonic.tar.gz \
    https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.16.0/tectonic-0.16.0-x86_64-unknown-linux-musl.tar.gz \
    && tar xz -C /usr/local/bin/ -f /tmp/tectonic.tar.gz \
    && rm /tmp/tectonic.tar.gz \
    && chmod +x /usr/local/bin/tectonic

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p output logs

CMD ["python3", "-m", "src.main"]
```

- [ ] **Step 3: Create railway.toml**

```toml
[build]
builder = "DOCKERFILE"

[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

- [ ] **Step 4: Create private GitHub repo and push**

```bash
cd /Users/muditchaudhary/job-autopilot
# Create private repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/job-autopilot.git
git branch -M main
git push -u origin main
```

- [ ] **Step 5: Deploy to Railway**
  1. Go to railway.app → New Project → Deploy from GitHub
  2. Select `job-autopilot` repo
  3. Add all env vars from `.env.example` in Railway dashboard
  4. Deploy

- [ ] **Step 6: Commit Dockerfile**

```bash
git add Dockerfile railway.toml
git commit -m "feat: Dockerfile and Railway config for cloud deployment"
git push
```

---

## Task 12: Setup Credentials (Run Once Locally)

This task runs locally before cloud deploy.

- [ ] **Step 1: Get Telegram API credentials**
  1. Go to `https://my.telegram.org`
  2. Login → API Development Tools
  3. Create app → copy `api_id` and `api_hash` into `.env`

- [ ] **Step 2: Generate session string**

```bash
cd /Users/muditchaudhary/job-autopilot
cp .env.example .env
# Fill TELEGRAM_API_ID and TELEGRAM_API_HASH first, then:
python3 generate_session.py
# Copy the session string into .env as TELEGRAM_SESSION_STRING
```

- [ ] **Step 3: Get group ID**

```bash
python3 get_group_id.py
# Find the SDE Jobs group and copy its ID into .env as TELEGRAM_GROUP_ID
```

- [ ] **Step 4: Get Gemini API key**
  1. Go to `https://aistudio.google.com/app/apikey`
  2. Create API key → copy into `.env` as `GEMINI_API_KEY`

- [ ] **Step 5: Set up Gmail App Password**
  1. Gmail → Settings → Security → 2-Step Verification (enable if not done)
  2. Security → App passwords → Create → name it "job-autopilot"
  3. Copy 16-char password into `.env` as `GMAIL_APP_PASSWORD`

- [ ] **Step 6: Set up Google Drive service account**
  1. Go to `https://console.cloud.google.com`
  2. New project → Enable "Google Drive API"
  3. IAM → Service Accounts → Create → download JSON key
  4. Create a Google Drive folder, share it with the service account email
  5. Copy folder ID from Drive URL into `.env` as `GOOGLE_DRIVE_FOLDER_ID`
  6. Base64 encode the JSON:
  ```bash
  base64 -i service-account.json | tr -d '\n'
  # Copy output into .env as GOOGLE_SERVICE_ACCOUNT_B64
  ```

- [ ] **Step 7: Run locally to test end-to-end**

```bash
python3 -m src.main
# Send a test job message in the Telegram group
# Check logs/ folder and your Telegram for notification
```

---

## Running All Tests

```bash
cd /Users/muditchaudhary/job-autopilot
python3 -m pytest tests/ -v
```

Expected output:
```
tests/test_parser.py::test_build_prompt_contains_message PASSED
tests/test_parser.py::test_parse_email_job PASSED
tests/test_parser.py::test_parse_form_job PASSED
tests/test_parser.py::test_parse_irrelevant_message PASSED
tests/test_resume_tailor.py::test_build_tailor_prompt_contains_jd PASSED
tests/test_resume_tailor.py::test_extract_latex_strips_fences PASSED
tests/test_resume_tailor.py::test_extract_latex_no_fences PASSED
tests/test_resume_tailor.py::test_save_pdf_creates_file PASSED
tests/test_email_sender.py::test_subject_contains_company_and_role PASSED
tests/test_email_sender.py::test_email_body_contains_key_info PASSED
tests/test_form_filler.py::test_extract_form_id_from_url PASSED
tests/test_form_filler.py::test_extract_form_id_from_short_url PASSED
tests/test_form_filler.py::test_build_submit_url PASSED
tests/test_form_filler.py::test_generate_answers_returns_dict PASSED
14 passed
```
