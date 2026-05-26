"""
Wellfound (AngelList) apply applicator.
Uses saved session (sessions/wellfound.json) to open a job page,
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

_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/wellfound.json")
_MOCK_GEMINI  = os.getenv("MOCK_GEMINI", "false").lower() == "true"

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _delay(a=0.6, b=1.4):
    time.sleep(random.uniform(a, b))


# ── Gemini helper ────────────────────────────────────────────────────────────

def _gemini_answers(fields: list, profile: UserProfile,
                    jd_summary: str, company: str, role: str) -> dict:
    if _MOCK_GEMINI or not fields:
        return {}

    prompt = f"""You are filling a Wellfound (AngelList Talent) job application form.
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

Form fields:
{json.dumps(fields, indent=2)}

Rules:
- Return ONLY a JSON object {{field_key: answer}}.
- field_key = field id if present, else field name.
- For textarea/text: write a concise, relevant answer (2-4 sentences max).
- For "What interests you": express genuine interest in the role and company.
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
        const tag  = el.tagName.toLowerCase();
        const type = tag === 'select' ? 'select' : (el.getAttribute('type') || 'text').toLowerCase();
        const field = { id, name, label, type,
            selector: id ? '#' + id : (name ? '[name="' + name + '"]' : null),
            currentValue: (type === 'checkbox') ? (el.checked ? 'checked' : '') : (el.value || '')
        };
        if (type === 'select') {
            field.options = [...el.options].map(o => o.text.trim()).filter(Boolean);
        }
        // For fields without id/name, use a data-index attribute for targeting
        if (!field.selector) {
            el.setAttribute('data-autopilot-idx', String(Array.from(inputs).indexOf(el)));
            field.selector = '[data-autopilot-idx="' + el.getAttribute('data-autopilot-idx') + '"]';
        }
        return field.selector ? field : null;
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

            # Typeahead dropdown handling (JS click bypasses pointer-events)
            listbox_appeared = False
            typeahead_selected = False
            try:
                page.wait_for_selector('[role="listbox"], [role="option"]', timeout=2000)
                listbox_appeared = True
                for opt_sel in [
                    '[role="listbox"] [role="option"]:first-child',
                    '[role="listbox"] li:first-child',
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


# ── Main applicator ──────────────────────────────────────────────────────────

def apply_wellfound(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    """
    Open the Wellfound job page, click Apply, fill all questions with Gemini,
    upload resume, and submit.
    Returns True on success.
    """
    session_file = os.path.abspath(_SESSION_FILE)
    if not os.path.exists(session_file):
        log.error("Wellfound session not found — run setup_sessions.py first")
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
        log.info(f"Wellfound Apply: '{role}' @ {company}")

        try:
            page.goto(apply_url, timeout=30000)
            _delay(2.0, 3.0)

            # Click Apply button
            apply_btn = None
            for sel in [
                "button:has-text('Apply')",
                "a:has-text('Apply')",
                "[data-test='apply-button']",
                "button[aria-label*='Apply']",
            ]:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    apply_btn = el
                    break

            if apply_btn:
                apply_btn.click()
                _delay(1.5, 2.5)
            else:
                log.warning("Wellfound: Apply button not found — may already be on apply page")

            # ── Step loop ────────────────────────────────────────────────────
            for step in range(10):
                _delay(0.8, 1.2)

                # Upload resume if file input present
                if pdf_path:
                    try:
                        file_inputs = page.evaluate("""() => {
                            return [...document.querySelectorAll('input[type="file"]')]
                                .map((el, i) => ({index: i, id: el.id, name: el.name}));
                        }""")
                        if file_inputs:
                            target = file_inputs[0]
                            page.locator('input[type="file"]').nth(target["index"]).set_input_files(pdf_path)
                            log.info("Wellfound: resume uploaded")
                            _delay(0.5, 1.0)
                    except Exception as e:
                        log.warning(f"Wellfound: file upload error — {e}")

                # Extract and fill unfilled fields
                PLACEHOLDER_VALS = {"", "select an option", "select", "please select", "--select--"}
                # Skip stray site-wide inputs (search bars, nav inputs, etc.)
                SKIP_LABELS = {"search everything", "search", "search jobs", "search companies"}
                fields = page.evaluate(_EXTRACT_FIELDS_JS)
                other_fields = [
                    f for f in (fields or [])
                    if f["type"] != "file"
                    and f.get("label", "").lower() not in SKIP_LABELS
                    and (
                        f.get("currentValue", "").lower() in PLACEHOLDER_VALS
                        or f["type"] in ("radio", "checkbox")
                    )
                ]

                if other_fields:
                    log.info(f"Wellfound step {step}: fields to fill ({len(other_fields)}): "
                             + str([f.get("label") or f.get("name") for f in other_fields]))
                    answers = _gemini_answers(other_fields, profile, jd_summary, company, role)
                    for field in other_fields:
                        key = field.get("id") or field.get("name")
                        ans = answers.get(key)
                        if ans and str(ans) not in ("RESUME_PDF", ""):
                            _fill_field(page, field, str(ans))
                            _delay(0.1, 0.3)

                # Navigation buttons
                submit_btn = None
                for sel in [
                    "button[type='submit']",
                    "button:has-text('Submit application')",
                    "button:has-text('Submit')",
                    "input[type='submit']",
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        submit_btn = el
                        break

                if submit_btn:
                    btn_text = submit_btn.inner_text().strip().lower() if hasattr(submit_btn, 'inner_text') else "submit"
                    if dry_run:
                        log.info(f"DRY RUN — would submit Wellfound: '{role}' @ {company}")
                        return True
                    submit_btn.click()
                    _delay(2.0, 3.0)
                    log.info(f"✅ Applied (Wellfound): '{role}' @ {company}")
                    return True

                # Next button
                next_btn = None
                for sel in [
                    "button:has-text('Next')",
                    "button:has-text('Continue')",
                    "button[type='button']:has-text('Next')",
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        next_btn = el
                        break

                if next_btn:
                    log.info(f"Wellfound step {step}: clicking Next")
                    next_btn.click()
                    _delay(1.0, 2.0)
                    continue

                log.warning(f"Wellfound step {step}: no navigation button found")
                break

            log.warning(f"Wellfound: did not reach Submit for '{role}' @ {company}")
            return False

        except Exception as e:
            log.error(f"Wellfound Apply error: {e}")
            return False
        finally:
            browser.close()
