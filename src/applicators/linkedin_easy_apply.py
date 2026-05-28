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
- For "city" or "location" or any field labelled "Search" that is a text input: use "New Delhi" (Mudit's city).
- For fields with label containing "notice" or "notice period": use profile notice_period.
- For fields with label containing "salary" or "CTC" or "compensation": use expected_ctc.
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
    // Comprehensive extraction covering all LinkedIn form patterns.
    const fields = [];
    const seen  = new Set();

    function makeField(el, labelTxt) {
        const tag  = el.tagName.toLowerCase();
        const type = tag === 'select' ? 'select'
                   : (el.getAttribute('type') || 'text').toLowerCase();
        if (['hidden', 'submit', 'button', 'image', 'reset', 'file'].includes(type)) return null;
        const id  = el.id || '';
        const key = id || el.name;
        if (key && seen.has(key)) return null;
        if (key) seen.add(key);

        // Build a CSS selector so _fill_field can target this element even
        // when it has no id.  Prefer id > name > placeholder > aria-label.
        let selector = null;
        if (!id) {
            if (el.name) {
                selector = '[name="' + el.name.replace(/"/g, '\\"') + '"]';
            } else {
                const ph = el.getAttribute('placeholder');
                const al = el.getAttribute('aria-label');
                if (ph) selector = '[placeholder="' + ph.replace(/"/g, '\\"') + '"]';
                else if (al) selector = '[aria-label="' + al.replace(/"/g, '\\"') + '"]';
            }
        }

        const field = {
            id,
            name:       el.name  || '',
            label:      labelTxt || id || el.name || '',
            type,
            inputmode:  el.getAttribute('inputmode') || '',
            selector,
            currentValue: type === 'checkbox' ? (el.checked ? 'checked' : '')
                        : (el.value || ''),
        };
        if (!field.label) return null;
        if (type === 'select') {
            field.options = [...el.options].map(o => o.text.trim()).filter(Boolean);
        }
        if ((type === 'radio' || type === 'checkbox') && el.name) {
            field.options = [...document.querySelectorAll(
                'input[name="' + CSS.escape(el.name) + '"]'
            )].map(r => {
                const l = document.querySelector('label[for="' + r.id + '"]')
                       || document.getElementById(r.getAttribute('aria-labelledby') || '');
                return l ? l.innerText.trim() : r.value;
            }).filter(Boolean);
        }
        return field;
    }

    // ── Strategy 1: label[for] -> getElementById ──────────────────────────
    // getElementById handles any ID format (colons, brackets, URNs).
    document.querySelectorAll('label[for]').forEach(label => {
        const id = label.htmlFor;
        if (!id || seen.has(id)) return;
        const el = document.getElementById(id);
        if (!el) return;
        const labelTxt = label.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim();
        const f = makeField(el, labelTxt);
        if (f) fields.push(f);
    });

    // ── Strategy 2: aria-labelledby ───────────────────────────────────────
    // LinkedIn screening questions often use aria-labelledby instead of label[for].
    document.querySelectorAll(
        'input[aria-labelledby], textarea[aria-labelledby], select[aria-labelledby]'
    ).forEach(el => {
        const labelId  = el.getAttribute('aria-labelledby') || '';
        const labelEl  = labelId ? document.getElementById(labelId) : null;
        const labelTxt = labelEl ? labelEl.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim() : '';
        const f = makeField(el, labelTxt || el.getAttribute('aria-label') || '');
        if (f) fields.push(f);
    });

    // ── Strategy 3: LinkedIn data-test component containers ───────────────
    // Covers [data-test-single-line-text-form-component], [data-test-text-selectable-option__input], etc.
    const liContainers = [
        '[data-test-single-line-text-form-component]',
        '[data-test-multiline-text-form-component]',
        '[data-test-text-selectable-option__input]',
        '[data-test-numeric-text-form-component]',
        '[data-test-form-builder-radio-button-form-component]',
        '[data-test-checkbox-form-component]',
        '[data-test-dropdown-form-component]',
    ];
    document.querySelectorAll(liContainers.join(',')).forEach(container => {
        const inp = container.querySelector('input, textarea, select');
        if (!inp) return;
        // Try label inside container first
        const lbl = container.querySelector('label, legend, h3, h4, [class*="label"]');
        const lblTxt = lbl ? lbl.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim() : '';
        const f = makeField(inp, lblTxt || inp.getAttribute('aria-label') || '');
        if (f) fields.push(f);
    });

    // ── Strategy 4: aria-label / placeholder fallback ────────────────────
    // Catches city typeahead and any remaining unlabelled inputs.
    document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="file"]),' +
        'textarea, select'
    ).forEach(el => {
        const id  = el.id || '';
        const key = id || el.name;
        if (key && seen.has(key)) return;
        const ariaLabel   = el.getAttribute('aria-label')   || '';
        const placeholder = el.getAttribute('placeholder')  || '';
        const labelTxt    = ariaLabel || placeholder || '';
        if (!labelTxt && !id && !el.name) return;
        const f = makeField(el, labelTxt || id || el.name);
        if (f) fields.push(f);
    });

    return fields;
}"""


# ── Field filler ─────────────────────────────────────────────────────────────

def _fill_field(page: Page, field: dict, answer: str) -> None:
    fid   = field.get("id", "")
    sel   = field.get("selector") or (f'#{fid}' if fid else None)
    ftype = field.get("type", "text")
    if not sel and not fid:
        return
    try:
        if ftype in ("text", "email", "tel", "number", "url", "textarea",
                     "date", "search", "password"):
            # If label is "Search" and answer looks like tech/skills, override with city
            label_lower = field.get("label", "").lower()
            if label_lower in ("search", "") and ftype in ("text", "search"):
                answer = "New Delhi, Delhi, India"
            if fid:
                # Always use getElementById — handles any ID format safely
                page.evaluate("""([id, val]) => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    el.focus();
                    // Use nativeInputValueSetter for React-controlled inputs
                    const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ) || Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, 'value'
                    );
                    if (nativeSetter && nativeSetter.set) {
                        nativeSetter.set.call(el, val);
                    } else {
                        el.value = val;
                    }
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }""", [fid, str(answer)])
                _delay(0.4, 0.8)
            elif sel:
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
               jd_summary: str, company: str, role: str, pdf_path: str,
               force_fill: bool = False) -> None:
    """Extract and fill all fields visible in the current modal step.

    force_fill=True — include fields that already have a value (used when
    stuck in a Review loop so we can overwrite stale/wrong data).
    """

    # ── Resume upload step ────────────────────────────────────────────────────
    # LinkedIn shows a resume selection page with hidden file inputs.
    # Detect it by checking for the document-upload section.
    # Only treat as resume step if the heading says "Resume"
    resume_section = None
    heading = page.query_selector(
        '.jobs-easy-apply-modal h3, .jobs-easy-apply-modal h2, '
        '.jobs-easy-apply-content h3, .jobs-easy-apply-content h2'
    )
    heading_text = heading.inner_text().strip().lower() if heading else ""
    if "resume" in heading_text or "cv" in heading_text:
        resume_section = page.query_selector(
            '.jobs-document-upload-redesign-card__container, '
            '.jobs-document-upload'
        )
    if resume_section and pdf_path:
        try:
            # Count resume cards before upload so we can identify the new one after
            before_count = page.evaluate("""() =>
                document.querySelectorAll('.jobs-document-upload-redesign-card__container').length
            """)
            log.info(f"LinkedIn Easy Apply: {before_count} resumes already on file")

            # Upload the tailored PDF via the hidden file input
            # The "Upload resume" label triggers this input — we set files directly
            file_inputs = page.evaluate("""() => {
                return [...document.querySelectorAll('input[type="file"]')]
                    .map((el, i) => ({index: i, id: el.id || '', name: el.name || ''}));
            }""")
            if file_inputs:
                file_el = page.locator('input[type="file"]').nth(0)
                file_el.set_input_files(pdf_path)
                log.info(f"LinkedIn Easy Apply: uploading tailored resume — {pdf_path}")
                _delay(3.0, 4.0)  # wait for LinkedIn to process the upload

                # After upload, select the newly added resume (first card = newest)
                selected = page.evaluate("""() => {
                    const radios = [...document.querySelectorAll(
                        'input.jobs-document-upload-redesign-card__toggle[type="radio"]'
                    )];
                    if (radios.length === 0) return 'no_radios';
                    // LinkedIn adds new resume at top — click first radio
                    radios[0].click();
                    const label = document.querySelector(
                        'label.jobs-document-upload-redesign-card__toggle-label'
                    );
                    return 'selected: ' + (label ? label.innerText.trim() : 'first');
                }""")
                log.info(f"LinkedIn Easy Apply: resume selection — {selected}")
                _delay(0.5, 1.0)
        except Exception as e:
            log.warning(f"LinkedIn Easy Apply: resume upload error — {e}")
        # Resume step done — step loop will click Next
        return

    # Scroll the modal content area so that all fields are rendered/visible.
    try:
        page.evaluate("""() => {
            const scroller = document.querySelector(
                '.artdeco-modal__content, '
                + '.jobs-easy-apply-modal .artdeco-modal__content, '
                + '.jobs-easy-apply-modal__content'
            );
            if (scroller) scroller.scrollTop = 0;
        }""")
        _delay(0.3, 0.5)
    except Exception:
        pass

    fields = page.evaluate(_EXTRACT_FIELDS_JS)

    # Log every extracted field so we can see what's detected
    log.info(f"All extracted fields ({len(fields)}): " +
             str([(f.get('label') or f.get('id'), f.get('type'),
                   f.get('inputmode'), f.get('currentValue', '')) for f in fields]))

    if not fields:
        return

    # Include fields that need filling:
    # - text/textarea with empty currentValue
    # - select with placeholder value
    # - numeric inputs with empty value OR value "0" (unfilled default)
    # - radio/checkbox (always verify)
    # - any field with a visible validation error
    # - if force_fill: include everything (used when stuck in Review loop)
    PLACEHOLDER_VALS = {"", "select an option", "select", "please select", "--select--"}

    # Collect IDs of fields with visible validation errors
    error_field_ids = set(page.evaluate("""() => {
        const errorEls = document.querySelectorAll(
            '[class*="artdeco-inline-feedback--error"], [class*="form-element__error"], '
            + '[id$="-error"]:not(:empty)'
        );
        const ids = new Set();
        errorEls.forEach(el => {
            const fieldId = el.id ? el.id.replace(/-error$/, '') : '';
            if (fieldId) ids.add(fieldId);
            const container = el.closest(
                '[data-test-single-line-text-form-component], '
                + '[data-test-form-element], .artdeco-text-input'
            );
            if (container) {
                const inp = container.querySelector('input, textarea, select');
                if (inp && inp.id) ids.add(inp.id);
            }
        });
        return [...ids];
    }""") or [])

    def _needs_fill(f: dict) -> bool:
        if f.get("type") == "file":
            return False
        if force_fill:
            return True
        cv = f.get("currentValue", "").lower()
        ftype = f.get("type", "text")
        inputmode = f.get("inputmode", "")
        # Always include radio/checkbox (must verify selection)
        if ftype in ("radio", "checkbox"):
            return True
        # Include if error
        if f.get("id", "") in error_field_ids:
            return True
        # Include if empty/placeholder
        if cv in PLACEHOLDER_VALS:
            return True
        # Numeric input with value "0" is considered unfilled
        if inputmode in ("numeric", "decimal") and cv in ("0", ""):
            return True
        return False

    other_fields = [f for f in fields if _needs_fill(f)]

    if other_fields:
        log.info(f"Fields to fill ({len(other_fields)}): " +
                 str([f.get('label') or f.get('name') or f.get('id') for f in other_fields]))
        answers = _gemini_answers(other_fields, profile, jd_summary, company, role)
        log.info(f"Gemini answers: {answers}")

        # Pre-build a normalised lookup so we can match even when Gemini
        # strips colons/hyphens from React IDs (e.g. ':r2:' → 'r2').
        def _normalise(s: str) -> str:
            return re.sub(r'[^a-z0-9]', '', s.lower())

        norm_answers = {_normalise(k): v for k, v in answers.items()}

        for field in other_fields:
            key        = field.get("id") or field.get("name") or ""
            label_low  = field.get("label", "").lower()
            ftype      = field.get("type", "text")

            # 1. Exact key match
            ans = answers.get(key)

            # 2. Normalised key match (handles ':r2:' == 'r2')
            if not ans and key:
                ans = norm_answers.get(_normalise(key))

            # 3. Label-based match (Gemini sometimes uses the label as key)
            if not ans and label_low:
                for ak, av in answers.items():
                    if label_low in ak.lower() or ak.lower() in label_low:
                        ans = av
                        break

            # 4. Hardcoded city/location fallback — never leave this blank
            if not ans and ftype in ("text", "search") and any(
                kw in label_low for kw in ("city", "location", "search", "where")
            ):
                ans = "New Delhi"

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
            # review_streak tracks consecutive Review clicks without progress.
            # After 2 straight Reviews we switch to force_fill mode.
            review_streak = 0

            for step in range(25):
                # Wait for modal to be visible
                try:
                    page.wait_for_selector(
                        ".jobs-easy-apply-modal, [data-test-modal-id='easy-apply-modal'], "
                        ".jobs-easy-apply-content",
                        timeout=8000
                    )
                except PWTimeout:
                    # Modal closed — check if it's because application was submitted
                    try:
                        page.wait_for_selector(
                            "[data-test-modal-id='post-apply-modal'], "
                            ".jobs-post-apply-modal, "
                            "[aria-label*='application was sent'], "
                            "h2:has-text('Application submitted'), "
                            "h2:has-text('Your application was sent')",
                            timeout=3000
                        )
                        log.info(f"✅ Applied (Easy Apply): '{role}' @ {company}")
                        return True
                    except PWTimeout:
                        pass
                    log.warning(f"Easy Apply modal disappeared at step {step}")
                    break

                _delay(1.0, 1.5)

                # Force-fill when we've been clicking Review without progress.
                force_fill = review_streak >= 2
                if force_fill:
                    log.warning(f"Step {step}: stuck on Review (streak={review_streak}), forcing full fill")

                # Fill all fields in current step
                _fill_step(page, profile, jd_summary, company, role, pdf_path,
                           force_fill=force_fill)
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
                    review_streak += 1
                    log.info(f"Step {step}: clicking Review (streak={review_streak})")
                    # Use JS click to bypass any overlay interception
                    page.evaluate("el => el.click()", review_btn)
                    _delay(1.5, 2.0)

                    # After clicking Review, check for validation errors.
                    # LinkedIn renders error messages in elements whose id = fieldId + "-error".
                    # Also look inside artdeco-inline-feedback--error containers.
                    error_fields = page.evaluate("""() => {
                        const results = [];
                        const seen = new Set();
                        // Pattern A: [id$="-error"] elements
                        document.querySelectorAll('[id$="-error"]').forEach(errEl => {
                            const errTxt = errEl.innerText.trim();
                            if (!errTxt) return;
                            const inputId = errEl.id.replace(/-error$/, '');
                            if (seen.has(inputId)) return;
                            const inp = document.getElementById(inputId);
                            if (!inp) return;
                            seen.add(inputId);
                            let labelTxt = '';
                            document.querySelectorAll('label[for]').forEach(l => {
                                if (l.htmlFor === inputId)
                                    labelTxt = l.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim();
                            });
                            if (!labelTxt) {
                                const lbId = inp.getAttribute('aria-labelledby');
                                if (lbId) {
                                    const lbEl = document.getElementById(lbId);
                                    if (lbEl) labelTxt = lbEl.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim();
                                }
                            }
                            results.push({
                                id: inputId,
                                label: labelTxt || inputId,
                                type: inp.type || 'text',
                                inputmode: inp.getAttribute('inputmode') || '',
                                currentValue: inp.value || '',
                                error: errTxt,
                                selector: null,
                                name: inp.name || '',
                            });
                        });
                        // Pattern B: artdeco-inline-feedback--error without the id convention
                        document.querySelectorAll('[class*="artdeco-inline-feedback--error"]').forEach(errEl => {
                            const errTxt = errEl.innerText.trim();
                            if (!errTxt) return;
                            const container = errEl.closest(
                                '[data-test-single-line-text-form-component], '
                                + '[data-test-numeric-text-form-component], '
                                + '[data-test-form-element]'
                            );
                            if (!container) return;
                            const inp = container.querySelector('input, textarea, select');
                            if (!inp || !inp.id || seen.has(inp.id)) return;
                            seen.add(inp.id);
                            const lbl = container.querySelector('label, [class*="label"]');
                            const labelTxt = lbl ? lbl.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim() : '';
                            results.push({
                                id: inp.id,
                                label: labelTxt || inp.id,
                                type: inp.type || 'text',
                                inputmode: inp.getAttribute('inputmode') || '',
                                currentValue: inp.value || '',
                                error: errTxt,
                                selector: null,
                                name: inp.name || '',
                            });
                        });
                        return results;
                    }""")
                    if error_fields:
                        log.info(f"Step {step}: {len(error_fields)} error fields — "
                                 f"{[f['label'][:40] for f in error_fields]}")
                        answers = _gemini_answers(error_fields, profile, jd_summary, company, role)
                        log.info(f"Gemini answers for errors: {answers}")
                        for field in error_fields:
                            key = field.get("id") or field.get("name")
                            ans = (answers.get(key)
                                   or answers.get(field.get("label", "")))
                            if not ans:
                                lbl = field.get("label", "").lower()
                                im  = field.get("inputmode", "")
                                if "year" in lbl or "experience" in lbl or im in ("numeric", "decimal"):
                                    ans = str(profile.years_of_experience)
                            if ans:
                                _fill_field(page, field, str(ans))
                                _delay(0.3, 0.5)
                        _delay(0.5, 1.0)
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
                    review_streak = 0   # made progress
                    log.info(f"Step {step}: clicking Next")
                    # JS click to bypass any overlay
                    page.evaluate("el => el.click()", next_btn)
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
                    page.evaluate("el => el.click()", fallback)
                    _delay(1.0, 2.0)
                    if "submit" in btn_text:
                        log.info(f"✅ Applied (Easy Apply): '{role}' @ {company}")
                        return True
                    continue

                log.warning(f"Step {step}: no navigation button found — checking for errors")
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
