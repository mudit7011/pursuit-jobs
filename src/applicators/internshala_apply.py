"""
Internshala Apply applicator.
Uses saved session (sessions/internshala.json) to open a job/internship page,
click Apply, fill any questions with Gemini, then submit.
"""

import os
import json
import re
import time
import random
import logging
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
import google.generativeai as genai

from src.config import GEMINI_API_KEY
from src.profile import UserProfile

log = logging.getLogger(__name__)

_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/internshala.json")
_MOCK_GEMINI  = os.getenv("MOCK_GEMINI", "false").lower() == "true"

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _delay(a=0.6, b=1.4):
    time.sleep(random.uniform(a, b))


# ── Gemini helpers ────────────────────────────────────────────────────────────

def _gemini_answers(fields: list, profile: UserProfile,
                    jd_summary: str, company: str, role: str) -> dict:
    if _MOCK_GEMINI or not fields:
        return {}

    prompt = f"""You are filling an Internshala job/internship application form.
Role: {role} at {company}
Job summary: {jd_summary[:400]}

Candidate:
Name: {profile.name}
Email: {profile.email}
Phone: {profile.phone}
Experience: {profile.years_of_experience} years
Skills: {', '.join(profile.skills[:12])}
Location: {profile.location_preference}
Notice period: {profile.notice_period}
Expected CTC: {profile.expected_ctc}
College: {profile.college} | {profile.degree} | CGPA {profile.cgpa}
Graduation year: {profile.graduation_year}

Form fields:
{json.dumps(fields, indent=2)}

Rules:
- Return ONLY a JSON object {{field_key: answer}}.
- field_key = field id if present, else field name.
- For "cover letter" / "SOP" / "Why are you interested": write 3-4 sentences about genuine interest in the role, relevant skills, and what you can contribute.
- For availability: use "Immediate" or profile notice_period.
- For yes/no: answer honestly.
- No markdown, no explanations."""

    try:
        resp = _model.generate_content(prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        log.warning(f"Gemini answer generation failed: {e}")
        return {}


def _gemini_assessment(questions: list, profile: UserProfile,
                        jd_summary: str, company: str, role: str) -> list:
    """Answer multiple-choice or text assessment questions."""
    if _MOCK_GEMINI or not questions:
        return []

    prompt = f"""You are answering assessment questions for a job application.
Role: {role} at {company}
Job summary: {jd_summary[:300]}

Candidate skills: {', '.join(profile.skills[:10])}
Experience: {profile.years_of_experience} years

Questions:
{json.dumps(questions, indent=2)}

Return ONLY a JSON array of {{"question_index": <int>, "answer": "<answer>"}} objects.
For MCQ: return the EXACT option text.
For text: write a concise relevant answer.
No markdown, no explanations."""

    try:
        resp = _model.generate_content(prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        log.warning(f"Gemini assessment failed: {e}")
        return []


# ── Field extraction JS ───────────────────────────────────────────────────────

_EXTRACT_FIELDS_JS = """() => {
    const inputs = document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]),' +
        'textarea, select'
    );
    return [...inputs].map(el => {
        const id   = el.id || '';
        const name = el.name || '';
        let label  = '';
        if (id) {
            const lEl = document.querySelector('label[for="' + id + '"]');
            if (lEl) label = lEl.innerText.trim();
        }
        if (!label) label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || '';
        if (!label) {
            const parentLbl = el.closest('label');
            if (parentLbl) label = parentLbl.innerText.trim();
        }
        if (!label) {
            const prev = el.previousElementSibling;
            if (prev) label = prev.innerText.trim().replace(/\\*$/, '').trim();
        }
        const tag  = el.tagName.toLowerCase();
        const type = tag === 'select' ? 'select' : (el.getAttribute('type') || 'text').toLowerCase();
        const field = { id, name, label, type,
            selector: id ? '#' + id : (name ? '[name="' + name + '"]' : null),
            currentValue: (type === 'checkbox') ? (el.checked ? 'checked' : '') : (el.value || '')
        };
        if (type === 'select') {
            field.options = [...el.options].map(o => o.text.trim()).filter(Boolean);
        }
        if (type === 'radio' || type === 'checkbox') {
            if (name) {
                const grp = document.querySelectorAll('input[name="' + name + '"]');
                field.options = [...grp].map(r => {
                    const lbl = document.querySelector('label[for="' + r.id + '"]');
                    return lbl ? lbl.innerText.trim() : r.value;
                }).filter(Boolean);
            }
        }
        return (id || name) && field.selector ? field : null;
    }).filter(Boolean);
}"""


# ── Field filler ─────────────────────────────────────────────────────────────

def _fill_field(page: Page, field: dict, answer: str) -> None:
    sel   = field["selector"]
    ftype = field.get("type", "text")
    try:
        if ftype in ("text", "email", "tel", "number", "url", "textarea",
                     "date", "search", "password"):
            page.fill(sel, str(answer))
            _delay(0.4, 0.8)

            # Typeahead dropdown (JS click bypasses pointer-events interception)
            listbox_appeared = False
            typeahead_selected = False
            try:
                page.wait_for_selector('[role="listbox"], [role="option"], .tt-menu',
                                       timeout=2000)
                listbox_appeared = True
                for opt_sel in [
                    '[role="listbox"] [role="option"]:first-child',
                    '[role="listbox"] li:first-child',
                    '.tt-menu .tt-suggestion:first-child',
                    '.autocomplete-suggestions div:first-child',
                ]:
                    try:
                        opt = page.query_selector(opt_sel)
                        if opt and opt.is_visible():
                            page.evaluate("el => el.click()", opt)
                            _delay(0.3, 0.5)
                            typeahead_selected = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if listbox_appeared and not typeahead_selected:
                try:
                    el = page.query_selector(sel)
                    if el:
                        el.press("ArrowDown")
                        _delay(0.2, 0.4)
                        el.press("Enter")
                        _delay(0.2, 0.4)
                except Exception:
                    pass

        elif ftype == "select":
            opts = field.get("options", [])
            real_opts = [o for o in opts if o.lower() not in
                         ("select", "select an option", "please select", "--select--", "")]
            if real_opts:
                best = next(
                    (o for o in real_opts if answer.lower() in o.lower()
                     or o.lower() in answer.lower()),
                    real_opts[0]
                )
                page.select_option(sel, label=best)

        elif ftype == "checkbox":
            label_text = field.get("label", "").lower()
            affirmative = answer.lower() in ("yes", "true", "agree", "consent",
                                              "accept", "i agree", "1")
            consent_kw  = any(w in label_text for w in
                               ("consent", "agree", "accept", "privacy", "terms"))
            if affirmative or consent_kw:
                fid = field.get("id", "")
                if fid:
                    page.evaluate("""(id) => {
                        const el = document.getElementById(id);
                        if (el && !el.checked) el.click();
                    }""", fid)
                    _delay(0.2, 0.4)
                else:
                    el = page.query_selector(sel)
                    if el and not el.is_checked():
                        el.click()
                        _delay(0.2, 0.4)

        elif ftype == "radio":
            name = field.get("name", "")
            if name:
                radios = page.locator(f'input[name="{name}"]')
                for i in range(radios.count()):
                    r   = radios.nth(i)
                    rid = r.get_attribute("id") or ""
                    lbl = page.locator(f'label[for="{rid}"]')
                    txt = lbl.text_content() or "" if lbl.count() > 0 else ""
                    if answer.lower() in txt.lower():
                        r.click()
                        break
    except Exception as e:
        log.debug(f"Fill failed for '{field.get('label', sel)}': {e}")


def _fill_step(page: Page, profile: UserProfile,
               jd_summary: str, company: str, role: str, pdf_path: str) -> None:
    """Fill all unfilled fields on the current page/step."""
    # Upload resume if file input present
    if pdf_path:
        try:
            file_inputs = page.evaluate("""() => {
                return [...document.querySelectorAll('input[type="file"]')]
                    .map((el, i) => ({index: i, id: el.id, name: el.name,
                        isResume: (el.id || '').toLowerCase().includes('resume')
                                  || (el.name || '').toLowerCase().includes('resume')}));
            }""")
            if file_inputs:
                target = next((f for f in file_inputs if f["isResume"]), file_inputs[0])
                page.locator('input[type="file"]').nth(target["index"]).set_input_files(pdf_path)
                log.info("Internshala: resume uploaded")
                _delay(0.5, 1.0)
        except Exception as e:
            log.warning(f"Internshala: file upload error — {e}")

    PLACEHOLDER_VALS = {"", "select an option", "select", "please select", "--select--"}
    fields = page.evaluate(_EXTRACT_FIELDS_JS)
    other_fields = [
        f for f in (fields or [])
        if f["type"] != "file" and (
            f.get("currentValue", "").lower() in PLACEHOLDER_VALS
            or f["type"] in ("radio", "checkbox")
        )
    ]

    if other_fields:
        log.info(f"Internshala: fields to fill ({len(other_fields)}): "
                 + str([f.get("label") or f.get("name") for f in other_fields]))
        answers = _gemini_answers(other_fields, profile, jd_summary, company, role)
        for field in other_fields:
            key = field.get("id") or field.get("name")
            ans = answers.get(key)
            if ans and str(ans) not in ("RESUME_PDF", ""):
                _fill_field(page, field, str(ans))
                _delay(0.1, 0.3)


# ── Main applicator ──────────────────────────────────────────────────────────

def apply_internshala(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    """
    Navigate to an Internshala job/internship page, click Apply Now,
    fill all questions with Gemini, and submit. Returns True on success.
    """
    session_file = os.path.abspath(_SESSION_FILE)
    if not os.path.exists(session_file):
        log.error("Internshala session not found — run setup_sessions.py first")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            storage_state=session_file,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        log.info(f"Internshala Apply: '{role}' @ {company}")

        try:
            page.goto(apply_url, timeout=30000)
            _delay(2.0, 3.0)

            # Click Apply Now button
            apply_btn = None
            for sel in [
                "#apply-button",
                "a#apply-button",
                ".apply_now_btn",
                "button:has-text('Apply Now')",
                "a:has-text('Apply Now')",
                "button:has-text('Apply')",
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        apply_btn = el
                        break
                except Exception:
                    continue

            if not apply_btn:
                log.warning(f"Internshala: Apply button not found for '{role}'")
                return False

            apply_btn.click()
            _delay(1.5, 2.5)

            # ── Step loop ────────────────────────────────────────────────────
            for step in range(10):
                try:
                    page.wait_for_selector(
                        "#apply-section, .apply-modal, #application-form, "
                        "form.application-form, #cover-letter, "
                        "form[action*='apply'], .modal-body",
                        timeout=6000
                    )
                except PWTimeout:
                    log.warning(f"Internshala step {step}: no form found")
                    break

                _delay(0.8, 1.2)
                _fill_step(page, profile, jd_summary, company, role, pdf_path)
                _delay(0.5, 1.0)

                log.info(f"Internshala step {step}: looking for navigation button")

                # Submit button
                submit_btn = None
                for sel in [
                    "button:has-text('Submit')",
                    "input[value='Submit']",
                    "button[type='submit']",
                    "button:has-text('Apply')",
                    "#submit",
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            submit_btn = el
                            break
                    except Exception:
                        continue

                if submit_btn:
                    if dry_run:
                        log.info(f"DRY RUN — would submit Internshala: '{role}' @ {company}")
                        return True
                    submit_btn.click()
                    _delay(2.0, 3.0)
                    log.info(f"✅ Applied (Internshala): '{role}' @ {company}")
                    return True

                # Next button
                next_btn = None
                for sel in [
                    "button:has-text('Next')",
                    "button:has-text('Continue')",
                    ".continue-btn",
                    "button.btn-primary:has-text('Next')",
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            next_btn = el
                            break
                    except Exception:
                        continue

                if next_btn:
                    log.info(f"Internshala step {step}: clicking Next")
                    next_btn.click()
                    _delay(1.0, 2.0)
                    continue

                # Log visible errors
                try:
                    errors = page.eval_on_selector_all(
                        ".error-block, .help-block.error, [class*='error']",
                        "els => els.map(e => e.innerText.trim()).filter(Boolean).slice(0,5)"
                    )
                    if errors:
                        log.warning(f"Internshala step {step}: visible errors — {errors}")
                except Exception:
                    pass

                log.warning(f"Internshala step {step}: no navigation button found")
                break

            log.warning(f"Internshala: did not reach Submit for '{role}' @ {company}")
            return False

        except Exception as e:
            log.error(f"Internshala Apply error: {e}")
            return False
        finally:
            browser.close()
