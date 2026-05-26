# JobAutoCopilot

Autonomous job application bot. Monitors Telegram groups 24/7, checks eligibility, tailors your resume, and submits applications — zero human input after setup.

**[Landing Page](https://landing-one-eta-52.vercel.app)**

---

## How it works

**Step 1 — Intercept**
The bot connects to your Telegram groups via Telethon. The moment a job post appears, it's parsed and queued. No polling delay, no manual copy-paste.

**Step 2 — Eligibility check (cheapest-first)**
- Regex checks batch year and experience requirements instantly (free)
- If you pass, Gemini API scores skill overlap against the JD
- Doesn't qualify? Silently skipped. No wasted LLM calls.

**Step 3 — Apply**
- Your LaTeX template is recompiled with keywords extracted from the JD
- Playwright opens the real application form — Greenhouse, Lever, Workday, Ashby, or anything unknown
- Every field extracted, answers generated via LLM, PDF uploaded, form submitted
- You get a Telegram notification: applied / CAPTCHA hit / ineligible

---

## Stack

| Layer | Tech |
|---|---|
| Telegram listener | Telethon |
| Job parsing & eligibility | Gemini API + regex |
| Resume tailoring | Gemini API + LaTeX + Tectonic |
| Form automation | Playwright |
| Duplicate tracking | SQLite |
| Notifications | Telegram Bot API |
| Config | profile.json + .env |

---

## Project structure

```
job-autopilot/
├── src/
│   ├── main.py             # Entry point
│   ├── monitor.py          # Telegram listener (Telethon)
│   ├── parser.py           # Job post parser
│   ├── eligibility.py      # Regex + Gemini eligibility pipeline
│   ├── resume_tailor.py    # LaTeX resume compiler
│   ├── web_form_filler.py  # Playwright form filler
│   ├── orchestrator.py     # Wires everything together
│   ├── tracker.py          # SQLite application tracker
│   ├── notifier.py         # Telegram notifications
│   ├── profile.py          # User profile loader
│   ├── models.py           # Data models
│   └── config.py           # Env config
├── config/
│   └── profile.json        # Your details (name, skills, batch year, etc.)
├── templates/
│   └── MuditCV.tex         # Your LaTeX resume template
├── tests/                  # Pytest test suite
├── .env.example            # Required env vars
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.11+
- [Tectonic](https://tectonic-typesetting.github.io) — for LaTeX compilation
- Playwright browsers

### 1. Clone and install

```bash
git clone https://github.com/mudit7011/jobcopilot.git
cd jobcopilot
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
# Telegram — get from https://my.telegram.org
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION_STRING=
TELEGRAM_GROUP_ID=        # e.g. -1001234567890
TELEGRAM_SELF_ID=         # your Telegram user ID

# Gemini — get from https://aistudio.google.com
GEMINI_API_KEY=

# Gmail (optional — for email notifications)
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
```

To get your `TELEGRAM_SESSION_STRING`, run:

```bash
python generate_session.py
```

To find your `TELEGRAM_GROUP_ID`, run:

```bash
python get_group_id.py
```

### 3. Set up your profile

Edit `config/profile.json` with your details:

```json
{
  "name": "Your Name",
  "email": "you@example.com",
  "phone": "+91 XXXXXXXXXX",
  "linkedin": "https://linkedin.com/in/yourprofile",
  "github": "https://github.com/yourusername",
  "skills": ["Python", "Node.js", "TypeScript"],
  "batch_year": 2024,
  "experience_years": 1,
  "expected_ctc": "8 LPA"
}
```

### 4. Add your resume template

Replace `templates/MuditCV.tex` with your own LaTeX resume. The bot injects keywords from each JD into the skills and project sections before compiling.

### 5. Run

```bash
python -m src.main
```

---

## Configuration notes

**Which Telegram groups to watch** — set `TELEGRAM_GROUP_ID` in `.env`. You can watch multiple groups by running multiple instances or extending `monitor.py`.

**Eligibility thresholds** — edit `src/eligibility.py` to adjust batch year range and max experience years.

**Form filling behaviour** — Playwright runs headless by default. Set `HEADLESS=false` in `.env` to watch it work.

---

## Tests

```bash
pytest tests/ -v
```

---

## Disclaimer

This tool automates form submission on job portals. Use responsibly and in accordance with each platform's terms of service. The author is not liable for any account restrictions resulting from automated usage.

---

## License

MIT — see [LICENSE](LICENSE)

---

Built by [Mudit Kumar](https://github.com/mudit7011) · [LinkedIn](https://linkedin.com/in/mudit-dev)
