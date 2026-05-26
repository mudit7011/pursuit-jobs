"""
Indeed Easy Apply applicator.
Uses saved session (sessions/indeed.json) to open a job page,
click "Easily apply", fill questions with Gemini, upload resume, submit.
Skips jobs that redirect to an external company site.
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

_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/indeed.json")
_MOCK_GEMINI  = os.getenv("MOCK_GEMINI", "false").lower() == "true"

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _delay(a=0.6, b=1.4):
    time.sleep(random.uniform(a, b))


# ── Gemini answers ────────────────────────────────────────────────────────────

def _gemini_answers(fields: list, profile: UserProfile,
                    jd_summary: str, company: str, role: str) -> dict:
    if _MOCK_GEMINI or not fields:
        return {}

    prompt = f"""You are filling an Indeed job application form.
Role: {role} at {company}
Job summary: {jd_summary[:400]}

Candidate:
Name: {profile.name}
Email: {profile.email}
Phone: {profile.phone}
LinkedIn: {profile.linkedin}
Experience: {profile.years_of_experience} years
Skills: {', '.join(profile.skills[:12])}
Location: {profile.location_preference}
Notice period: {profile.notice_period}
Expected CTC: {profile.expected_ctc}
College: {profile.college}, {profile.degree}
Graduation year: {profile.graduation_year}

Form fields:
{json.dumps(fields, indent=2)}

Rules:
- Return ONLY a JSON object {{field_key: answer}}.
- field_key = field id if present, else field label.
- For text/textarea: concise, relevant answer (2-4 sentences max).
- For yes/no or radio: answer honestly based on candidate profile.
- For select: return exact text of best matching option.
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


# ── Field extraction ──────────────────────────────────────────────────────────

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
            const p = el.closest('label');
            if (p) label = p.innerText.trim();
        }
        const tag  = el.tagName.toLowerCase();
        const type = tag === 'select' ? 'select' : (el.getAttribute('type') || 'text').toLowerCase();
        const field = {
            id, name, label, type,
            selector: id ? '#' + CSS.escape(id) : (name ? '[name="' + name + '"]' : null),
            currentValue: type === 'checkbox' ? (el.checked ? 'checked' : '') : (el.value || '')
        };
        if (type === 'select') {
            field.options = [...el.options].map(o => o.text.trim()).filter(Boolean);
        }
        if (type === 'radio' && name) {
            const group = document.querySelectorAll('input[name="' + name + '"]');
            field.options = [...group].map(r => {
                const lbl = document.querySelector('label[for="' + r.id + '"]');
                return lbl ? lbl.innerText.trim() : (r.value || '');
            }).filter(Boolean);
        }
        return field.selector ? field : null;
    }).filter(Boolean);
}"""


# ── Field filler ──────────────────────────────────────────────────────────────

def _fill_field(page: Page, field: dict, answer: str) -> None:
    sel   = field["selector"]
    ftype = field.get("type", "text")
    try:
        if ftype in ("text", "email", "tel", "number", "url", "textarea",
                     "date", "search", "password"):
            page.click(sel, timeout=5000)
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            page.keyboard.type(str(answer), delay=20)
            _delay(0.3, 0.6)

        elif ftype == "select":
            opts = field.get("options", [])
            real = [o for o in opts if o.lower() not in
                    ("select", "select an option", "please select", "--select--", "")]
            if real:
                best = next(
                    (o for o in real if answer.lower() in o.lower()
                     or o.lower() in answer.lower()),
                    real[0]
                )
                page.select_option(sel, label=best)

        elif ftype == "radio":
            name = field.get("name", "")
            if name:
                radios = page.locator(f'input[name="{name}"]')
                for i in range(radios.count()):
                    r = radios.nth(i)
                    rid = r.get_attribute("id") or ""
                    lbl = page.locator(f'label[for="{rid}"]')
                    txt = lbl.text_content() or "" if lbl.count() > 0 else ""
                    if answer.lower() in txt.lower():
                        r.click()
                        break

        elif ftype == "checkbox":
            label_text = field.get("label", "").lower()
            affirmative = answer.lower() in ("yes", "true", "agree", "consent", "accept", "1")
            consent_kw  = any(w in label_text for w in
                              ("consent", "agree", "accept", "privacy", "terms"))
            if affirmative or consent_kw:
                el = page.query_selector(sel)
                if el and not el.is_checked():
                    el.click()
                    _delay(0.2, 0.4)

    except Exception as e:
        log.debug(f"Fill failed for '{field.get('label', sel)}': {e}")


# ── Main applicator ───────────────────────────────────────────────────────────

def apply_indeed(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    """
    Open an Indeed job page, click 'Easily apply', fill form with Gemini,
    upload resume, and submit.
    Returns True on success, False if external-apply or on error.
    """
    session_file = os.path.abspath(_SESSION_FILE)
    if not os.path.exists(session_file):
        log.error("Indeed session not found — run setup_sessions.py first")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
            ],
        )
        ctx = browser.new_context(
            storage_state=session_file,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = ctx.new_page()
        log.info(f"Indeed Apply: '{role}' @ {company}")

        try:
            page.goto(apply_url, timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass
            _delay(1.5, 2.5)

            log.info(f"Indeed: page title = {page.title()}")

            # ── Find the apply button ─────────────────────────────────────────
            # India Indeed uses "Apply with Indeed" for hosted apply,
            # "Apply on company site" for external redirects — skip those.
            easy_apply_btn = None
            for sel in [
                "button:has-text('Apply with Indeed')",
                "button:has-text('Easily apply')",
                "button:has-text('Easily Apply')",
                "[data-testid='indeedApplyButton']",
                "button[aria-label*='apply' i]",
            ]:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    btn_text = el.inner_text().strip().lower()
                    if "company site" in btn_text or "company website" in btn_text:
                        log.info(f"Indeed: skipping external apply button — '{btn_text}'")
                        continue
                    easy_apply_btn = el
                    log.info(f"Indeed: found apply button '{el.inner_text().strip()}'")
                    break

            if not easy_apply_btn:
                log.warning(f"Indeed: Easily apply button not found for '{role}' — may be external apply only")
                return False

            url_before = page.url
            easy_apply_btn.click()
            _delay(2.0, 3.0)

            # If navigated away, it's an external application — skip
            if page.url != url_before and "indeed.com" not in page.url:
                log.warning(f"Indeed: redirected to external site {page.url} — skipping")
                return False

            # Wait for the application form/modal to appear
            try:
                page.wait_for_selector(
                    "[class*='ia-'], [id*='apply'], form, "
                    "button:has-text('Continue'), button:has-text('Submit')",
                    timeout=10000
                )
                log.info("Indeed: application form appeared")
            except PWTimeout:
                log.warning("Indeed: application form did not appear after clicking Apply")
                return False

            # ── Step loop ─────────────────────────────────────────────────────
            for step in range(15):
                # Wait for page to settle after any navigation
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except PWTimeout:
                    pass
                _delay(0.8, 1.2)

                # Scroll to bottom so all buttons and fields are in view
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                _delay(0.5, 0.8)

                current_url = page.url
                log.info(f"Indeed step {step}: URL = {current_url}")

                # If on the review page, wait for the submit button to render
                if "review-module" in current_url:
                    log.info("Indeed: on review page — waiting for Submit button to render...")
                    try:
                        page.wait_for_selector(
                            "button:has-text('Submit your application')",
                            timeout=15000
                        )
                        log.info("Indeed: Submit button found on review page")
                    except PWTimeout:
                        log.warning("Indeed: Submit button did not appear on review page after 15s")

                # Upload resume if file input is present
                if pdf_path:
                    try:
                        file_inputs = page.query_selector_all('input[type="file"]')
                        if file_inputs:
                            file_inputs[0].set_input_files(pdf_path)
                            log.info(f"Indeed step {step}: resume uploaded")
                            _delay(0.5, 1.0)
                    except Exception as e:
                        log.debug(f"Indeed: file upload — {e}")

                # Extract and fill unfilled fields
                SKIP_VALUES = {"", "select an option", "select", "please select"}
                # Skip reCAPTCHA internal fields and file inputs
                SKIP_NAMES  = {"g-recaptcha-response", "h-captcha-response"}
                fields = page.evaluate(_EXTRACT_FIELDS_JS)
                fillable = [
                    f for f in (fields or [])
                    if f["type"] != "file"
                    and f.get("name", "") not in SKIP_NAMES
                    and f.get("id", "") not in SKIP_NAMES
                    and (
                        f.get("currentValue", "").lower() in SKIP_VALUES
                        or f["type"] in ("radio", "checkbox")
                    )
                ]

                if fillable:
                    log.info(f"Indeed step {step}: {len(fillable)} fields — "
                             + str([f.get("label") or f.get("name") for f in fillable]))
                    answers = _gemini_answers(fillable, profile, jd_summary, company, role)
                    for field in fillable:
                        key = field.get("id") or field.get("label") or field.get("name")
                        ans = answers.get(key)
                        if ans and str(ans) not in ("RESUME_PDF", ""):
                            _fill_field(page, field, str(ans))
                            _delay(0.1, 0.3)

                # Log all buttons for debugging
                visible_btns = page.evaluate("""() =>
                    [...document.querySelectorAll('button')]
                    .map(b => ({text: b.innerText.trim().slice(0,40), disabled: b.disabled}))
                    .filter(b => b.text.length > 0)
                """)
                log.info(f"Indeed step {step}: buttons — {visible_btns}")

                # Look for Submit / Apply final button (visible OR disabled — handle disabled below)
                submit_btn = None
                for sel in [
                    "button:has-text('Submit your application')",
                    "button:has-text('Submit application')",
                    "button:has-text('Submit')",
                    "button:has-text('Apply')",
                    "button[type='submit']",
                    "input[type='submit']",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        submit_btn = el
                        log.info(f"Indeed step {step}: found submit btn '{el.inner_text().strip()}' disabled={page.evaluate('el => el.disabled', el)}")
                        break

                if submit_btn:
                    if dry_run:
                        log.info(f"DRY RUN — would submit Indeed: '{role}' @ {company}")
                        return True

                    # Check if submit is disabled — likely waiting for CAPTCHA
                    is_disabled = page.evaluate("el => el.disabled", submit_btn)
                    if is_disabled:
                        has_captcha = page.query_selector(
                            "iframe[src*='recaptcha'], div.g-recaptcha, .recaptcha-checkbox"
                        )
                        if has_captcha:
                            log.info("Indeed: reCAPTCHA detected — waiting for you to solve it in the browser...")
                            print("\n⚠️  Please solve the 'I am not a robot' CAPTCHA in the browser window, then wait.")
                            # Poll until submit becomes enabled (max 120 seconds)
                            for _ in range(60):
                                time.sleep(2)
                                still_disabled = page.evaluate("el => el.disabled", submit_btn)
                                if not still_disabled:
                                    log.info("Indeed: CAPTCHA solved — submitting now")
                                    break
                            else:
                                log.warning("Indeed: CAPTCHA not solved within 120s — skipping")
                                return False
                        else:
                            log.warning("Indeed: Submit disabled (reason unknown) — skipping")
                            return False

                    _delay(0.5, 1.0)
                    page.evaluate("el => el.click()", submit_btn)
                    _delay(2.0, 3.0)
                    log.info(f"Indeed: submitted application for '{role}' @ {company}")
                    return True

                # Look for Continue / Next button
                FORWARD_TEXTS = {"continue", "next", "next step", "proceed", "save and continue"}
                next_btn = None
                for sel in [
                    "button:has-text('Continue')",
                    "button:has-text('Next')",
                    "button[data-testid='continue-button']",
                    "button[data-testid='next-button']",
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        btn_text = el.inner_text().strip().lower()
                        if btn_text in FORWARD_TEXTS:
                            next_btn = el
                            log.info(f"Indeed step {step}: found nav button '{el.inner_text().strip()}'")
                            break

                if next_btn:
                    page.evaluate("el => el.click()", next_btn)
                    _delay(1.0, 2.0)
                    continue

                log.warning(f"Indeed step {step}: no navigation button found — stopping")
                break

            log.warning(f"Indeed: did not reach Submit for '{role}' @ {company}")
            return False

        except Exception as e:
            log.error(f"Indeed Apply error: {e}")
            return False
        finally:
            browser.close()
