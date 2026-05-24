# Universal Form Filler — Design Spec (v1)

## Goal

Expand the Job Autopilot Bot to handle any web-based job application form (Greenhouse, Lever, Workday, Ashby, Microsoft Forms, custom company forms) using Playwright browser automation and LLM-guided field filling — while adding eligibility filtering to skip jobs the user genuinely cannot apply to.

## Out of Scope (v1)

- LinkedIn Easy Apply (requires login session, deferred to v2)
- Proactive job scraping from LinkedIn/Naukri (separate system, next phase)
- Cloud deployment (separate phase)

---

## Architecture

### Flow

```
Receive job (Telegram)
    → Parse job details (existing parser.py)
    → Duplicate check (tracker.py) — skip if already applied
    → Eligibility check (eligibility.py) — skip if batch/experience/skills mismatch
    → Tailor resume + compile PDF (existing resume_tailor.py)
    → Route by apply type:
        EMAIL     → existing email_sender.py
        FORM      → existing form_filler.py (Google Forms HTTP POST)
        WEB_FORM  → new web_form_filler.py (Playwright + LLM)
        UNKNOWN   → notify user, skip
    → Log to tracker.py
    → Notify via Telegram
```

---

## Components

### 1. `config/profile.json` — User Profile

Single source of truth for all user data. Any user can set up the bot by editing this file.

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
  "skills": ["Python", "Node.js", "TypeScript", "REST APIs", "MongoDB", "Firebase", "AWS", "LLM APIs", "n8n", "FastAPI"],
  "resume_pdf_path": "templates/MuditCV.pdf",
  "summary": "Backend developer with 2 years of experience building production-grade APIs, automation systems, and LLM-integrated pipelines. Skilled in Python, Node.js, TypeScript, Firebase, AWS, and AI APIs."
}
```

---

### 2. `src/profile.py` — Profile Loader

Loads `config/profile.json` and exposes a typed `UserProfile` dataclass used by eligibility, form filler, and resume tailor.

**Responsibilities:**
- Load and parse `config/profile.json`
- Expose as `UserProfile` dataclass
- Single import used by all other modules — no module reads the JSON file directly

---

### 3. `src/eligibility.py` — Eligibility Checker

Checks whether the user should apply to a job before any work is done.

**Rules (checked in order):**

1. **Batch year** — If job specifies a graduation year (e.g. "2026 passout only") and it doesn't match user's `graduation_year`, skip.
2. **Experience** — If job specifies minimum years of experience and user's `years_of_experience` is below it, skip.
3. **Skills** — Use Gemini to compare job's required skills against user's skill list. If clearly less than 40% overlap, skip.

**Returns:** `EligibilityResult(eligible: bool, reason: str)`

**On skip:** Sends Telegram notification — "Skipped [Role] at [Company] — [reason]"

**Design note:** Rules 1 and 2 run without LLM (pure logic, fast). Rule 3 calls Gemini only if rules 1 and 2 pass — to keep it cheap.

---

### 4. `src/tracker.py` — Application Tracker

SQLite database at `data/applications.db` tracking every application attempt.

**Schema:**

```sql
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    apply_target TEXT,
    apply_type TEXT,
    status TEXT,       -- 'applied', 'skipped', 'failed'
    skip_reason TEXT,
    applied_at TEXT
);
```

**Responsibilities:**
- `is_duplicate(company, role) -> bool` — returns True if already applied
- `log_application(...)` — insert record after attempt
- Called in orchestrator before eligibility check (duplicate) and after apply (log)

---

### 5. `src/web_form_filler.py` — Universal Playwright Form Filler

Handles any web-based job application form using headless Playwright + Gemini.

**Flow per call:**

1. Launch Playwright (headless Chromium)
2. Navigate to the form URL, wait for network idle
3. Check for CAPTCHA — if detected, raise `CaptchaDetectedError` and abort gracefully
4. **Page loop** (handles multi-page forms):
   a. Extract all visible form fields — label text, input type, name/id, and for dropdowns/radio buttons: all available options
   b. Build a prompt: user profile + JD summary + field list → send to Gemini
   c. Gemini returns `{field_identifier: answer}` for every field
   d. Fill each field:
      - `text` / `textarea` → type the answer
      - `select` → select matching option
      - `radio` / `checkbox` → click matching option
      - `file` → upload the compiled resume PDF using `set_input_files()`
   e. Look for a "Next" / "Continue" button — if found, click and loop back to step (a)
   f. If no Next button found, look for Submit button → click
5. Wait for confirmation (URL change or success text)
6. Return success/failure

**CAPTCHA handling:** Detect common CAPTCHA indicators (reCAPTCHA iframe, hCaptcha, `captcha` in page text). If found, raise error — orchestrator catches it, logs it, and sends Telegram notification so user can apply manually.

**File upload:** Uses the compiled tailored PDF (already generated by resume_tailor.py before this is called). Path passed as argument.

**Cover letter / "Why this company" fields:** Gemini generates a 3-4 sentence response specific to the company and role using the JD summary and user summary from profile. Not generic.

---

### 6. `src/parser.py` — WEB_FORM Detection (modification)

Add URL pattern matching to detect known ATS platforms and return `ApplyType.WEB_FORM`:

- `greenhouse.io`
- `lever.co`
- `workday.com`
- `ashbyhq.com`
- `forms.office.com` (Microsoft Forms)
- `bamboohr.com`
- `recruitcrm.io`
- Any other URL that is not an email and not `docs.google.com/forms`

If the URL looks like a job application page (contains `/apply`, `/jobs`, `/careers` etc.) and isn't already categorized, treat as `WEB_FORM`.

---

### 7. `src/models.py` — ApplyType Update (modification)

Add `WEB_FORM = "web_form"` to the `ApplyType` enum.

---

### 8. `src/orchestrator.py` — Updated Flow (modification)

Wire the new components:

```
1. duplicate check → if duplicate, log + notify + return
2. eligibility check → if ineligible, log + notify + return
3. tailor resume (existing)
4. if WEB_FORM → web_form_filler.fill_web_form(...)
5. log to tracker
6. notify success
```

---

## Error Handling

| Error | Behaviour |
|---|---|
| CAPTCHA detected | Notify user via Telegram to apply manually |
| Form submit fails | Retry once, then notify user |
| Playwright timeout | Notify user, log as failed |
| Eligibility skip | Notify user with reason |
| Duplicate | Silent skip (just logged) |

---

## Dependencies to Add

```
playwright
sqlite3  (stdlib, no install needed)
```

Run after install: `playwright install chromium`

---

## What Does NOT Change

- `src/email_sender.py` — untouched
- `src/form_filler.py` — untouched (Google Forms HTTP POST still works fine)
- `src/resume_tailor.py` — untouched
- `src/monitor.py` — untouched
- `src/notifier.py` — untouched
- `templates/MuditCV.tex` — untouched
