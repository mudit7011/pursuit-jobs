"""
LinkedIn Easy Apply applicator.
Uses saved session (sessions/linkedin.json) to navigate to a job page,
click Easy Apply, navigate through all modal steps with Gemini filling
any custom screening questions, then submit.
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

_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/linkedin.json")
_MOCK_GEMINI  = os.getenv("MOCK_GEMINI", "false").lower() == "true"

genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.5-flash")


def _delay(a=0.6, b=1.5):
    time.sleep(random.uniform(a, b))


# ── Gemini helper ────────────────────────────────────────────────────────────

def _gemini_answers(fields: list, profile: UserProfile,
                    jd_summary: str, company: str, role: str) -> dict:
    """Ask Gemini to fill every form field. Returns {field_key: answer}."""
    if _MOCK_GEMINI or not fields:
        return {}

    prompt = f"""You are filling a LinkedIn Easy Apply form.
Role: {role} at {company}
Job summary: {jd_summary[:400]}

Candidate:
Name: {profile.name}
Email: {profile.email}
Phone: {profile.phone}
LinkedIn: {profile.linkedin}
Experience: {profile.years_of_experience} years
Skills: {', '.join(profile.skills[:12])}
Location preference: {profile.location_preference}
Notice period: {profile.notice_period}
Current CTC: {profile.current_ctc}
Expected CTC: {profile.expected_ctc}
Work authorization: {profile.work_authorization}
College: {profile.college} | {profile.degree} | CGPA {profile.cgpa}
Graduation year: {profile.graduation_year}

Form fields (fill each):
{json.dumps(fields, indent=2)}

Rules:
- Return ONLY a JSON object {{field_key: answer}}.
- field_key = field id if present, else field name.
- For select/radio: return the EXACT option text from the "options" list.
- For yes/no sponsorship/authorization: answer honestly (Indian citizen, no sponsorship needed for India jobs).
- For years of experience with a specific skill: estimate from the profile.
- For "city" or "location": use "Delhi" or "Bangalore" based on job location.
- For salary in INR: use expected_ctc value.
- Leave pre-filled fields as-is by not including them in the response.
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


# ── Field extraction ─────────────────────────────────────────────────────────

_EXTRACT_FIELDS_JS = """() => {
    const modal = document.querySelector(
        '.jobs-easy-apply-modal, [data-test-modal-id="easy-apply-modal"], ' +
        '[aria-label="Easy Apply"]'
    );
    const root = modal || document;
    const inputs = root.querySelectorAll(
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
            # Always fill — overwrite any stale/pre-filled value.
            # Gemini is given the correct profile values so pre-filled fields
            # get their correct value written back; screening answers get updated.
            page.fill(sel, str(answer))
            _delay(0.8, 1.2)

            # LinkedIn typeahead: after typing, a dropdown may appear.
            # Strategy 1 — JS click (bypasses pointer-events interception).
            # Strategy 2 — keyboard: ArrowDown → Enter (only if listbox appeared).
            typeahead_selected = False
            listbox_appeared = False
            try:
                page.wait_for_selector(
                    '[role="listbox"], .basic-typeahead__triggered-content, '
                    '[data-test-text-entity-list-form-select]',
                    timeout=2500
                )
                listbox_appeared = True
                # Try clicking the first visible option via JavaScript.
                # page.evaluate bypasses Playwright's pointer-events actionability checks.
                for opt_sel in [
                    '[role="listbox"] [role="option"]:first-child',
                    '[role="listbox"] li:first-child',
                    '.basic-typeahead__triggered-content .basic-typeahead__selectable:first-child',
                    '[data-test-text-entity-list-form-select] li:first-child',
                    '[data-test-autocomplete-result]:first-child',
                ]:
                    try:
                        opt = page.query_selector(opt_sel)
                        if opt and opt.is_visible():
                            # JS click sidesteps pointer-event interception entirely
                            page.evaluate("el => el.click()", opt)
                            _delay(0.3, 0.5)
                            typeahead_selected = True
                            log.info(f"Typeahead JS-click: '{opt.inner_text().strip()[:60]}'")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            # Keyboard fallback — ONLY if a listbox appeared but click failed.
            # Do NOT use ArrowDown+Enter on regular text fields (no listbox).
            if listbox_appeared and not typeahead_selected:
                try:
                    el = page.query_selector(sel)
                    if el:
                        el.press("ArrowDown")
                        _delay(0.3, 0.5)
                        el.press("Enter")
                        _delay(0.3, 0.5)
                        typeahead_selected = True
                        log.info("Typeahead: used ArrowDown+Enter")
                except Exception:
                    pass

        elif ftype == "select":
            # Skip placeholder options ("Select an option", "Select", etc.)
            opts = field.get("options", [])
            real_opts = [o for o in opts if o.lower() not in
                         ("select an option", "select", "please select", "--select--", "")]
            if real_opts:
                # Pick the option whose text best matches the answer (case-insensitive)
                best = next(
                    (o for o in real_opts if answer.lower() in o.lower()
                     or o.lower() in answer.lower()),
                    real_opts[0]  # fallback to first real option
                )
                page.select_option(sel, label=best)
            else:
                page.select_option(sel, label=str(answer))

        elif ftype == "checkbox":
            # Consent/privacy/agreement checkboxes — always check them.
            # Other checkboxes — check only if answer is affirmative.
            label_text = field.get("label", "").lower()
            affirmative = answer.lower() in ("yes", "true", "agree", "consent",
                                              "accept", "i consent", "i agree", "1")
            consent_kw  = any(w in label_text for w in
                               ("consent", "agree", "accept", "privacy",
                                "terms", "acknowledge", "declaration"))
            if affirmative or consent_kw:
                fid = field.get("id", "")
                # Use JavaScript getElementById — handles special chars in IDs
                # (LinkedIn URN IDs contain ":", "(", ")" which break CSS selectors)
                if fid:
                    checked = page.evaluate("""(id) => {
                        const el = document.getElementById(id);
                        if (el && !el.checked) { el.click(); return true; }
                        if (el && el.checked) return 'already';
                        return false;
                    }""", fid)
                    if checked and checked != "already":
                        log.info(f"Checkbox checked via JS getElementById: '{label_text[:50]}'")
                        _delay(0.2, 0.4)
                    elif checked == "already":
                        log.info(f"Checkbox already checked: '{label_text[:50]}'")
                else:
                    # Fallback: CSS selector (works for simple IDs)
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
    """Extract and fill all fields visible in the current modal step."""
    fields = page.evaluate(_EXTRACT_FIELDS_JS)
    if not fields:
        return

    # Separate file fields
    file_fields  = [f for f in fields if f["type"] == "file"]

    # Include unfilled fields:
    # - text/textarea with empty currentValue
    # - select with placeholder value ("Select an option", empty)
    # - radio/checkbox (always include)
    PLACEHOLDER_VALS = {"", "select an option", "select", "please select", "--select--"}
    other_fields = [
        f for f in fields
        if f["type"] != "file" and (
            f.get("currentValue", "").lower() in PLACEHOLDER_VALS
            or f["type"] in ("radio", "checkbox")
        )
    ]

    # Upload resume — LinkedIn file input IDs contain "(" and ")" which break CSS selectors.
    # Use JavaScript to find the first resume file input and set files via locator.
    if pdf_path and file_fields:
        try:
            # Find file input elements via JS (avoids CSS selector issues with special chars)
            file_inputs = page.evaluate("""() => {
                const inputs = document.querySelectorAll('input[type="file"]');
                return [...inputs].map((el, i) => ({index: i, id: el.id, name: el.name,
                    isResume: (el.id || '').includes('resume') || (el.name || '').includes('resume')}));
            }""")
            # Prefer resume input, else first file input
            target = next((f for f in file_inputs if f["isResume"]), None)
            if not target and file_inputs:
                target = file_inputs[0]
            if target is not None:
                # Use nth() to target by index — avoids special-char selector issues
                file_el = page.locator('input[type="file"]').nth(target["index"])
                file_el.set_input_files(pdf_path)
                log.info("LinkedIn Easy Apply: resume uploaded")
                _delay(0.5, 1.0)
        except Exception as e:
            log.warning(f"LinkedIn Easy Apply: file upload error — {e}")

    if other_fields:
        log.info(f"Fields to fill ({len(other_fields)}): " +
                 str([f.get('label') or f.get('name') or f.get('id') for f in other_fields]))
        answers = _gemini_answers(other_fields, profile, jd_summary, company, role)
        log.info(f"Gemini answers: {answers}")
        for field in other_fields:
            key = field.get("id") or field.get("name")
            ans = answers.get(key)
            if ans and str(ans) not in ("RESUME_PDF", ""):
                _fill_field(page, field, str(ans))
                _delay(0.1, 0.3)


# ── Main applicator ──────────────────────────────────────────────────────────

def apply_linkedin_easy_apply(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    """
    Navigate to the LinkedIn Easy Apply URL, complete all modal steps,
    and submit the application.

    dry_run=True fills everything but stops before clicking "Submit application"
    (useful for testing without actually applying).

    Returns True on success.
    """
    session_file = os.path.abspath(_SESSION_FILE)
    if not os.path.exists(session_file):
        log.error("LinkedIn session not found — run setup_sessions.py first")
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
        log.info(f"LinkedIn Easy Apply: '{role}' @ {company}")

        try:
            # Navigate to the job/apply URL
            page.goto(apply_url, timeout=30000)
            _delay(2.0, 3.0)

            # If the URL doesn't auto-open the modal, click Easy Apply button
            modal_present = page.query_selector(
                ".jobs-easy-apply-modal, [data-test-modal-id='easy-apply-modal']")
            if not modal_present:
                easy_btn = None
                for sel in [
                    "button[aria-label*='Easy Apply']",
                    "button.jobs-apply-button",
                    "a[aria-label*='Easy Apply']",
                ]:
                    el = page.query_selector(sel)
                    if el:
                        easy_btn = el
                        break
                if not easy_btn:
                    log.warning(f"Easy Apply button not found for '{role}'")
                    return False
                easy_btn.click()
                _delay(1.5, 2.5)

            # ── Step loop ────────────────────────────────────────────────────
            for step in range(20):  # increase limit to handle longer forms
                # Wait for modal to be visible
                try:
                    page.wait_for_selector(
                        ".jobs-easy-apply-modal, [data-test-modal-id='easy-apply-modal'], "
                        ".jobs-easy-apply-content",
                        timeout=8000
                    )
                except PWTimeout:
                    log.warning(f"Easy Apply modal disappeared at step {step}")
                    break

                _delay(1.0, 1.5)

                # Fill all fields in current step
                _fill_step(page, profile, jd_summary, company, role, pdf_path)
                _delay(0.5, 1.0)

                # ── Button priority: Submit > Review > Next ───────────────
                log.info(f"Step {step}: looking for navigation button")
                # Check Submit
                submit_btn = None
                for sel in [
                    "button[aria-label='Submit application']",
                    "button:has-text('Submit application')",
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        submit_btn = el
                        break

                if submit_btn:
                    log.info(f"Step {step}: found Submit button")
                    if dry_run:
                        log.info(f"DRY RUN — would submit: '{role}' @ {company}")
                        return True
                    submit_btn.click()
                    _delay(2.0, 3.0)
                    log.info(f"✅ Applied (Easy Apply): '{role}' @ {company}")
                    return True

                # Check Review
                review_btn = None
                for sel in [
                    "button[aria-label='Review your application']",
                    "button:has-text('Review')",
                    "button[aria-label='Review']",
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        review_btn = el
                        break

                if review_btn:
                    log.info(f"Step {step}: clicking Review")
                    review_btn.click()
                    _delay(1.0, 2.0)
                    continue

                # Check Next / Continue
                next_btn = None
                for sel in [
                    "button[aria-label='Continue to next step']",
                    "button:has-text('Next')",
                    "button:has-text('Continue')",
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        next_btn = el
                        break

                if next_btn:
                    log.info(f"Step {step}: clicking Next")
                    next_btn.click()
                    _delay(1.0, 2.0)
                    continue

                # Fallback: any primary button in modal
                fallback = page.query_selector(
                    ".jobs-easy-apply-modal button.artdeco-button--primary, "
                    ".jobs-easy-apply-content button.artdeco-button--primary"
                )
                if fallback and fallback.is_visible():
                    btn_text = fallback.inner_text().strip().lower()
                    log.info(f"Step {step}: fallback primary button '{btn_text}'")
                    if dry_run and "submit" in btn_text:
                        log.info(f"DRY RUN — would submit: '{role}' @ {company}")
                        return True
                    fallback.click()
                    _delay(1.0, 2.0)
                    if "submit" in btn_text:
                        log.info(f"✅ Applied (Easy Apply): '{role}' @ {company}")
                        return True
                    continue

                log.warning(f"Step {step}: no navigation button found — checking for errors")
                # Log any visible error messages to help diagnose
                try:
                    errors = page.eval_on_selector_all(
                        ".artdeco-inline-feedback--error, [class*='error']",
                        "els => els.map(e => e.innerText.trim()).filter(Boolean).slice(0,5)"
                    )
                    if errors:
                        log.warning(f"Step {step}: visible errors — {errors}")
                except Exception:
                    pass
                break

            log.warning(f"Easy Apply: did not reach Submit for '{role}' @ {company}")
            return False

        except Exception as e:
            log.error(f"LinkedIn Easy Apply error: {e}")
            return False
        finally:
            browser.close()
