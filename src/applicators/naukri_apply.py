"""
Naukri Quick Apply applicator.
Uses saved session (sessions/naukri.json) to open a job page,
click Apply, fill any screening questions with Gemini, then submit.
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

_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/naukri.json")
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

    prompt = f"""You are filling a Naukri job application form.
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
Current CTC: {profile.current_ctc}
Expected CTC: {profile.expected_ctc}
College: {profile.college} | {profile.degree} | CGPA {profile.cgpa}
Graduation year: {profile.graduation_year}

Form fields:
{json.dumps(fields, indent=2)}

Rules:
- Return ONLY a JSON object {{field_key: answer}}.
- field_key = field id if present, else field name.
- For select/radio: return EXACT option text from "options" list.
- For notice period: use profile notice_period value.
- For CTC fields: use profile values.
- For yes/no work authorization (India jobs): "Yes" (Indian citizen).
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
                page.wait_for_selector('[role="listbox"], [role="option"], .suggestor-list',
                                       timeout=2000)
                listbox_appeared = True
                for opt_sel in [
                    '[role="listbox"] [role="option"]:first-child',
                    '[role="listbox"] li:first-child',
                    '.suggestor-list li:first-child',
                    'ul.nI-gNb-nI-nH li:first-child',
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
    """Fill all unfilled fields on the current page/modal step."""
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
                log.info("Naukri: resume uploaded")
                _delay(0.5, 1.0)
        except Exception as e:
            log.warning(f"Naukri: file upload error — {e}")

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
        log.info(f"Naukri: fields to fill ({len(other_fields)}): "
                 + str([f.get("label") or f.get("name") for f in other_fields]))
        answers = _gemini_answers(other_fields, profile, jd_summary, company, role)
        for field in other_fields:
            key = field.get("id") or field.get("name")
            ans = answers.get(key)
            if ans and str(ans) not in ("RESUME_PDF", ""):
                _fill_field(page, field, str(ans))
                _delay(0.1, 0.3)


# ── Main applicator ──────────────────────────────────────────────────────────

def apply_naukri(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    """
    Navigate to a Naukri job page, click Apply, fill all fields with Gemini,
    and submit the application. Returns True on success.
    """
    session_file = os.path.abspath(_SESSION_FILE)
    if not os.path.exists(session_file):
        log.error("Naukri session not found — run setup_sessions.py first")
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
        log.info(f"Naukri Apply: '{role}' @ {company}")

        try:
            # Naukri job pages only render properly when there's a Naukri Referer.
            # Set the Referer header before navigating directly to the job URL.
            page.set_extra_http_headers({
                "Referer": "https://www.naukri.com/software-developer-jobs"
            })
            page.goto(apply_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=25000)
            _delay(2.0, 3.0)

            log.info(f"Naukri: job page loaded — {page.title()}")

            # Wait for the Apply button to appear (JS-rendered)
            try:
                page.wait_for_selector(
                    "button:has-text('Apply'), button:has-text('Quick Apply')",
                    timeout=8000
                )
            except PWTimeout:
                log.warning("Naukri: timed out waiting for Apply button")

            # Naukri may show a login prompt — session should handle it.
            # Click the Apply / Quick Apply button.
            apply_btn = None
            all_btns = page.evaluate("""() =>
                [...document.querySelectorAll('button')]
                .map(b => b.innerText.trim())
                .filter(t => t)
            """)
            log.info(f"Naukri: all buttons on job page — {all_btns}")

            for sel in [
                "button:has-text('Apply')",
                "button:has-text('Quick Apply')",
                "a:has-text('Apply')",
            ]:
                try:
                    els = page.query_selector_all(sel)
                    for el in els:
                        btn_text = el.inner_text().strip().lower()
                        # Skip external apply buttons
                        if "company site" in btn_text or "company website" in btn_text:
                            continue
                        apply_btn = el
                        break
                    if apply_btn:
                        break
                except Exception:
                    continue

            if not apply_btn:
                log.warning(f"Naukri: Apply button not found for '{role}' (may be external apply only)")
                return False

            log.info(f"Naukri: clicking Apply button — '{apply_btn.inner_text().strip()}'")

            if dry_run:
                log.info(f"DRY RUN — would click Apply for Naukri: '{role}' @ {company}")
                return True

            apply_btn.click()
            _delay(1.5, 2.5)

            # Debug: log all visible buttons after click
            btns = page.evaluate("""() =>
                [...document.querySelectorAll('button')]
                .filter(b => b.offsetParent !== null)
                .map(b => b.innerText.trim().slice(0,40))
                .filter(t => t)
            """)
            log.info(f"Naukri: buttons after Apply click — {btns[:15]}")
            log.info(f"Naukri: page URL after Apply click — {page.url}")

            # Naukri Quick Apply: check for immediate success via URL
            current_url = page.url
            if "multiApplyResp" in current_url and "%3A200" in current_url:
                log.info(f"✅ Applied (Naukri Quick Apply): '{role}' @ {company}")
                return True
            if "saveApply" in current_url and "multiApplyResp" in current_url:
                log.info(f"✅ Applied (Naukri Quick Apply): '{role}' @ {company}")
                return True

            # ── Step loop ────────────────────────────────────────────────────
            for step in range(10):
                try:
                    # Wait for any modal or form to appear
                    page.wait_for_selector(
                        ".chatbot_DrawerContentWrapper, .apply-modal, "
                        "form[class*='apply'], [class*='questionnaire'], "
                        ".sprinkle-typography, form",
                        timeout=6000
                    )
                except PWTimeout:
                    log.warning(f"Naukri step {step}: no form found")
                    break

                _delay(0.8, 1.2)
                _fill_step(page, profile, jd_summary, company, role, pdf_path)
                _delay(0.5, 1.0)

                log.info(f"Naukri step {step}: looking for navigation button")

                # Check for Submit
                submit_btn = None
                for sel in [
                    "button:has-text('Submit')",
                    "button[type='submit']",
                    "input[type='submit']",
                    "button:has-text('Apply')",
                    "button:has-text('Send')",
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            submit_btn = el
                            break
                    except Exception:
                        continue

                if submit_btn:
                    btn_text = submit_btn.inner_text().strip().lower() \
                               if hasattr(submit_btn, 'inner_text') else "submit"
                    if dry_run:
                        log.info(f"DRY RUN — would submit Naukri: '{role}' @ {company}")
                        return True
                    submit_btn.click()
                    _delay(2.0, 3.0)
                    # Check for success confirmation
                    try:
                        page.wait_for_selector(
                            "[class*='success'], [class*='confirm'], "
                            "h1:has-text('applied'), .applied",
                            timeout=5000
                        )
                    except PWTimeout:
                        pass
                    log.info(f"✅ Applied (Naukri): '{role}' @ {company}")
                    return True

                # Check for Next
                next_btn = None
                for sel in [
                    "button:has-text('Next')",
                    "button:has-text('Continue')",
                    "button[class*='next']",
                    "button[class*='Next']",
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el and el.is_visible():
                            next_btn = el
                            break
                    except Exception:
                        continue

                if next_btn:
                    log.info(f"Naukri step {step}: clicking Next")
                    next_btn.click()
                    _delay(1.0, 2.0)
                    continue

                # Fallback: primary button
                fallback = page.query_selector(
                    "button.styles_btn-primary__RNaOv, button.btn-primary, "
                    "button[class*='primary']:not([disabled])"
                )
                if fallback and fallback.is_visible():
                    btn_text = fallback.inner_text().strip().lower()
                    log.info(f"Naukri step {step}: fallback button '{btn_text}'")
                    if dry_run and "submit" in btn_text:
                        log.info(f"DRY RUN — would submit Naukri: '{role}' @ {company}")
                        return True
                    fallback.click()
                    _delay(1.0, 2.0)
                    if "submit" in btn_text or "apply" in btn_text:
                        log.info(f"✅ Applied (Naukri): '{role}' @ {company}")
                        return True
                    continue

                # Log any visible errors
                try:
                    errors = page.eval_on_selector_all(
                        "[class*='error'], .errText, .err-msg",
                        "els => els.map(e => e.innerText.trim()).filter(Boolean).slice(0,5)"
                    )
                    if errors:
                        log.warning(f"Naukri step {step}: visible errors — {errors}")
                except Exception:
                    pass

                log.warning(f"Naukri step {step}: no navigation button found")
                break

            log.warning(f"Naukri: did not reach Submit for '{role}' @ {company}")
            return False

        except Exception as e:
            log.error(f"Naukri Apply error: {e}")
            return False
        finally:
            browser.close()
