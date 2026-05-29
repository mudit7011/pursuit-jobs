"""
LinkedIn Easy Apply applicator.
Uses saved session (sessions/linkedin.json) to navigate to a job page,
click Easy Apply, navigate through all modal steps with Gemini filling
screening questions, then submit.
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

# ATS domains whose iframes we scan (LinkedIn-native iframes are excluded)
_ATS_DOMAINS = (
    "greenhouse.io", "lever.co", "workable.com", "ashbyhq.com",
    "smartrecruiters.com", "jobvite.com", "icims.com", "taleo.net",
    "breezy.hr", "recruitee.com", "pyjamahr.com", "pyjamaHR.com",
)


def _delay(a=0.6, b=1.5):
    time.sleep(random.uniform(a, b))


# ── Rules-based answers (no Gemini tokens needed) ────────────────────────────

def _rules_based_answer(field: dict, profile: UserProfile) -> str | None:
    """Return an answer for common fields without calling Gemini.
    Returns None if we don't know — caller should ask Gemini then."""
    label = field.get("label", "").lower()
    ftype = field.get("type", "text")
    name  = field.get("name", "").lower()

    # Skip file inputs
    if ftype == "file":
        return None

    # Name fields
    if any(kw in label for kw in ("first name",)):
        return profile.name.split()[0]
    if any(kw in label for kw in ("last name", "surname")):
        parts = profile.name.split()
        return parts[-1] if len(parts) > 1 else profile.name
    if any(kw in label for kw in ("full name", "your name", "candidate name")) and "first" not in label:
        return profile.name

    # Contact
    if any(kw in label for kw in ("email", "e-mail")):
        return profile.email
    if any(kw in label for kw in ("phone", "mobile", "contact number", "cell", "whatsapp")):
        return profile.phone
    if any(kw in label for kw in ("linkedin", "linkedin url", "linkedin profile", "linkedin link")):
        return profile.linkedin
    if any(kw in label for kw in ("github",)):
        return profile.github or ""
    if any(kw in label for kw in ("portfolio", "website", "personal site")):
        return profile.portfolio or ""

    # Location — city typeahead or plain text
    if ftype in ("text", "search") and any(
        kw in label for kw in ("city", "location", "where", "search", "current city")
    ):
        return "New Delhi"

    # Experience (total / overall — not skill-specific)
    if any(kw in label for kw in (
        "years of experience", "total experience", "overall experience",
        "how many years", "total years", "work experience", "years of professional"
    )) and "specific" not in label and "technology" not in label and "tool" not in label:
        return str(profile.years_of_experience)

    # Months of experience (additional months beyond full years)
    if any(kw in label for kw in ("additional months", "months of experience", "months experience", "total months")):
        return "0"

    # Notice period / availability
    if any(kw in label for kw in ("notice period", "notice", "availability", "joining", "when can you join")):
        return profile.notice_period

    # CTC / Salary
    if any(kw in label for kw in ("current ctc", "current salary", "current compensation", "present salary")):
        return str(profile.current_ctc)
    if any(kw in label for kw in (
        "expected ctc", "expected salary", "salary expectation",
        "desired salary", "desired compensation", "ctc expectation"
    )):
        return profile.expected_ctc

    # Work authorization
    if any(kw in label for kw in (
        "authorized to work", "work authorization", "right to work",
        "eligible to work", "legally authorized"
    )):
        return "Yes"
    if "require" in label and "sponsor" in label:
        return "No"  # No sponsorship needed for India

    # Education
    if any(kw in label for kw in ("college", "university", "institution", "school")) and ftype == "text":
        return profile.college
    if any(kw in label for kw in ("degree", "qualification", "highest education")) and ftype == "text":
        return profile.degree
    if "cgpa" in label or ("gpa" in label and "company" not in label):
        return str(profile.cgpa)
    if any(kw in label for kw in ("graduation year", "year of graduation", "passed out", "batch")):
        return str(profile.graduation_year)

    # Language proficiency fields — default English
    if any(kw in label for kw in ("select language", "language proficiency", "language")):
        if ftype == "select":
            return "English"

    # "Follow company" — always optional, skip silently
    if "follow" in label and ftype == "checkbox":
        return None  # don't touch it

    return None


# ── Gemini helper (only for unknown fields) ───────────────────────────────────

def _gemini_answers(fields: list, profile: UserProfile,
                    jd_summary: str, company: str, role: str) -> dict:
    """Ask Gemini only for fields that rules-based couldn't answer.
    Returns {field_key: answer}."""
    if _MOCK_GEMINI or not fields:
        return {}

    # Strip properties Gemini doesn't need (saves tokens)
    slim_fields = []
    for f in fields:
        sf = {
            "key":   f.get("id") or f.get("name") or f.get("label", ""),
            "label": f.get("label", ""),
            "type":  f.get("type", "text"),
        }
        if f.get("options"):
            sf["options"] = f["options"]
        if f.get("currentValue"):
            sf["current"] = f["currentValue"]
        slim_fields.append(sf)

    prompt = (
        f"Fill LinkedIn Easy Apply form. Return ONLY a JSON object, no markdown.\n"
        f"Role: {role} at {company}\n"
        f"JD: {jd_summary[:200]}\n"
        f"Candidate: {profile.name}, {profile.years_of_experience}yr exp, "
        f"skills: {', '.join(profile.skills[:10])}, "
        f"location: {profile.location_preference}, "
        f"notice: {profile.notice_period}, expected CTC: {profile.expected_ctc}, "
        f"auth: {profile.work_authorization}\n"
        f"Fields:\n{json.dumps(slim_fields)}\n"
        f"Rules:\n"
        f"- key = field id/name as shown\n"
        f"- For select/radio: exact option text from options list\n"
        f"- Work auth in India = Yes, no sponsorship needed\n"
        f"- Skill-specific years: estimate from profile\n"
        f"- For numeric fields (0-99 range) for experience: give integer\n"
        f"- Return only JSON {{key: answer}}"
    )

    try:
        resp = _model.generate_content(prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        log.warning(f"Gemini failed: {e}")
        return {}


# ── Field extraction JS ───────────────────────────────────────────────────────

_EXTRACT_FIELDS_JS = """() => {
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
            id, name: el.name || '', label: labelTxt || id || el.name || '',
            type, inputmode: el.getAttribute('inputmode') || '',
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

    // Strategy 1: label[for] -> getElementById
    document.querySelectorAll('label[for]').forEach(label => {
        const id = label.htmlFor;
        if (!id || seen.has(id)) return;
        const el = document.getElementById(id);
        if (!el) return;
        const labelTxt = label.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim();
        const f = makeField(el, labelTxt);
        if (f) fields.push(f);
    });

    // Strategy 2: aria-labelledby
    document.querySelectorAll(
        'input[aria-labelledby], textarea[aria-labelledby], select[aria-labelledby]'
    ).forEach(el => {
        const labelId  = el.getAttribute('aria-labelledby') || '';
        const labelEl  = labelId ? document.getElementById(labelId) : null;
        const labelTxt = labelEl ? labelEl.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim() : '';
        const f = makeField(el, labelTxt || el.getAttribute('aria-label') || '');
        if (f) fields.push(f);
    });

    // Strategy 3: LinkedIn data-test containers
    const liContainers = [
        '[data-test-single-line-text-form-component]',
        '[data-test-multiline-text-form-component]',
        '[data-test-text-selectable-option__input]',
        '[data-test-numeric-text-form-component]',
        '[data-test-form-builder-radio-button-form-component]',
        '[data-test-checkbox-form-component]',
        '[data-test-dropdown-form-component]',
        '[data-test-single-typeahead-entity-form-component]',
    ];
    document.querySelectorAll(liContainers.join(',')).forEach(container => {
        const inp = container.querySelector('input, textarea, select');
        if (!inp) return;
        const lbl = container.querySelector('label, legend, h3, h4, [class*="label"]');
        const lblTxt = lbl ? lbl.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim() : '';
        const f = makeField(inp, lblTxt || inp.getAttribute('aria-label') || '');
        if (f) fields.push(f);
    });

    // Strategy 3b: LinkedIn typeahead -la/-lv split
    document.querySelectorAll('label[for$="-la"]').forEach(label => {
        const laId = label.htmlFor;
        const lvId = laId.slice(0, -3) + '-lv';
        if (seen.has(laId) || seen.has(lvId)) return;
        const el = document.getElementById(lvId) || document.getElementById(laId);
        if (!el) return;
        const labelTxt = label.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim();
        const f = makeField(el, labelTxt);
        if (f) fields.push(f);
    });

    // Strategy 4: aria-label / placeholder fallback (inside modal only)
    const modalRoot = document.querySelector(
        '.jobs-easy-apply-modal, [data-test-modal-id="easy-apply-modal"], .jobs-easy-apply-content'
    ) || document;
    modalRoot.querySelectorAll(
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

    // ── Strategy 5: Proximity-based label scan ────────────────────────────
    // Catches third-party ATS fields (PyjamaHR, Greenhouse) where the label
    // has no "for" attribute and the input has no aria-label/placeholder.
    // Walk up the DOM from each unfound select/input to find adjacent text.
    modalRoot.querySelectorAll('select, input[type="text"], input[type="number"]').forEach(el => {
        const id  = el.id || '';
        const key = id || el.name;
        if (key && seen.has(key)) return;
        const type = el.tagName.toLowerCase() === 'select' ? 'select'
                   : (el.getAttribute('type') || 'text').toLowerCase();
        if (['hidden','submit','button','file'].includes(type)) return;

        let labelTxt = '';
        let node = el.parentElement;
        for (let depth = 0; depth < 5 && node && !labelTxt; depth++) {
            for (const child of node.children) {
                if (child === el || child.contains(el)) continue;
                const tag = child.tagName.toLowerCase();
                if (['label','span','p','div','h3','h4','legend','strong'].includes(tag)) {
                    const txt = (child.innerText || '').trim().replace(/\\s*\\*\\s*$/, '').trim();
                    if (txt && txt.length > 3 && txt.length < 120 && !txt.includes('\\n')) {
                        labelTxt = txt;
                        break;
                    }
                }
            }
            node = node.parentElement;
        }

        if (!labelTxt) return;
        const f = makeField(el, labelTxt);
        if (f) fields.push(f);
    });

    return fields;
}"""


# ── Field filler ─────────────────────────────────────────────────────────────

def _fill_field(target, field: dict, answer: str) -> None:
    """Fill a single form field. target = Playwright Page or Frame."""
    fid   = field.get("id", "")
    sel   = field.get("selector") or (f'#{fid}' if fid else None)
    ftype = field.get("type", "text")
    if not sel and not fid:
        return

    try:
        if ftype in ("text", "email", "tel", "number", "url", "textarea",
                     "date", "search", "password"):
            label_lower = field.get("label", "").lower()
            is_city = ftype in ("text", "search") and any(
                kw in label_lower for kw in ("city", "location", "where", "search", "")
            ) and label_lower not in ("skills", "company", "job title", "title")

            if is_city:
                # Typeahead fill: focus → clear → type → pick first real option
                if fid:
                    target.evaluate("""(id) => {
                        const el = document.getElementById(id);
                        if (!el) return;
                        el.focus();
                        el.value = '';
                        el.dispatchEvent(new Event('input', {bubbles:true}));
                    }""", fid)
                elif sel:
                    target.click(sel)
                    target.fill(sel, "")
                target.keyboard.type("New Delhi", delay=60)
                _delay(1.2, 1.8)

                # Pick first REAL option (skip "See all results" type links)
                try:
                    target.wait_for_selector(
                        '[role="listbox"], [role="option"], '
                        '.basic-typeahead__triggered-content, '
                        'ul[class*="typeahead"], ul[class*="dropdown"]',
                        timeout=4000
                    )
                    picked = False
                    for opt_sel in [
                        '[role="option"]',
                        '[role="listbox"] li',
                        '.basic-typeahead__selectable',
                        '[data-test-autocomplete-result]',
                        'ul[class*="typeahead"] li',
                        'ul[class*="dropdown"] li',
                    ]:
                        opts = target.query_selector_all(opt_sel)
                        for opt in opts:
                            if not opt.is_visible():
                                continue
                            txt = (opt.inner_text() or "").strip().lower()
                            if not txt or "see all" in txt or "more result" in txt:
                                continue
                            target.evaluate("""el => {
                                el.dispatchEvent(new MouseEvent('mousedown', {bubbles:true}));
                                el.dispatchEvent(new MouseEvent('mouseup',   {bubbles:true}));
                                el.click();
                            }""", opt)
                            _delay(0.4, 0.6)
                            picked = True
                            log.info(f"Typeahead picked: '{opt.inner_text().strip()[:50]}'")
                            break
                        if picked:
                            break
                    if not picked:
                        # Fallback: ArrowDown + Enter
                        if fid:
                            target.evaluate("""(id) => {
                                const el = document.getElementById(id);
                                if (el) el.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowDown', bubbles:true}));
                            }""", fid)
                        _delay(0.3, 0.5)
                        target.keyboard.press("Enter")
                except Exception:
                    pass
                if fid:
                    target.evaluate("""(id) => {
                        const el = document.getElementById(id);
                        if (el) el.dispatchEvent(new Event('blur', {bubbles:true}));
                    }""", fid)
            elif fid:
                target.evaluate("""([id, val]) => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    el.focus();
                    const ns = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
                            || Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
                    if (ns && ns.set) { ns.set.call(el, val); }
                    else { el.value = val; }
                    el.dispatchEvent(new Event('input',  {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                }""", [fid, str(answer)])
                _delay(0.3, 0.6)
            else:
                target.fill(sel, str(answer))
                _delay(0.3, 0.6)

        elif ftype == "select":
            opts = field.get("options", [])
            real = [o for o in opts if o.lower() not in
                    ("select an option", "select", "please select", "--select--", "")]
            if real:
                # 1. Exact match
                best = next((o for o in real if answer.lower() == o.lower()), None)

                # 2. Numeric range match — e.g. answer="2" → "2-3 years" or "1-2 years"
                if best is None:
                    try:
                        n = float(answer)
                        # Prefer option whose range contains n (e.g. "1-2" contains 2)
                        for o in real:
                            nums = re.findall(r'\d+(?:\.\d+)?', o)
                            if len(nums) >= 2 and float(nums[0]) <= n <= float(nums[1]):
                                best = o
                                break
                        # Fallback: largest lower bound that's <= n
                        if best is None:
                            candidates = []
                            for o in real:
                                nums = re.findall(r'\d+(?:\.\d+)?', o)
                                if nums and float(nums[0]) <= n:
                                    candidates.append((float(nums[0]), o))
                            if candidates:
                                best = max(candidates, key=lambda x: x[0])[1]
                    except (ValueError, TypeError):
                        pass

                # 3. Substring match
                if best is None:
                    best = next(
                        (o for o in real if answer.lower() in o.lower() or o.lower() in answer.lower()),
                        real[0]
                    )

                log.info(f"Select '{field.get('label','')[:40]}': answer={answer!r} → option={best!r}")
                target.select_option(sel, label=best)
            else:
                target.select_option(sel, label=str(answer))

        elif ftype == "checkbox":
            label_text = field.get("label", "").lower()
            # "Follow company" is optional — don't force-check it
            if "follow" in label_text:
                return
            affirmative = answer.lower() in ("yes", "true", "agree", "consent",
                                              "accept", "i consent", "i agree", "1")
            consent_kw  = any(w in label_text for w in
                               ("consent", "agree", "accept", "privacy",
                                "terms", "acknowledge", "declaration", "certif"))
            if affirmative or consent_kw:
                if fid:
                    result = target.evaluate("""(id) => {
                        const el = document.getElementById(id);
                        if (!el) return false;
                        if (!el.checked) { el.click(); return true; }
                        return 'already';
                    }""", fid)
                    if result and result != "already":
                        log.info(f"Checkbox checked: '{label_text[:50]}'")
                        _delay(0.2, 0.4)
                else:
                    el = target.query_selector(sel)
                    if el and not el.is_checked():
                        el.click()
                        _delay(0.2, 0.4)

        elif ftype == "radio":
            name = field.get("name", "")
            if name:
                radios = target.locator(f'input[name="{name}"]')
                for i in range(radios.count()):
                    r   = radios.nth(i)
                    rid = r.get_attribute("id") or ""
                    lbl = target.locator(f'label[for="{rid}"]')
                    txt = lbl.text_content() or "" if lbl.count() > 0 else ""
                    if answer.lower() in txt.lower():
                        r.click()
                        break

    except Exception as e:
        log.debug(f"Fill failed for '{field.get('label', sel)}': {e}")


# ── Fill one modal step ───────────────────────────────────────────────────────

def _fill_step(page: Page, profile: UserProfile,
               jd_summary: str, company: str, role: str, pdf_path: str,
               force_fill: bool = False) -> None:
    """Extract and fill all fields in the current modal step."""

    # Resume upload detection
    heading = page.query_selector(
        '.jobs-easy-apply-modal h3, .jobs-easy-apply-modal h2, '
        '.jobs-easy-apply-content h3, .jobs-easy-apply-content h2'
    )
    heading_text = (heading.inner_text().strip().lower() if heading else "")
    if "resume" in heading_text or "cv" in heading_text:
        resume_section = page.query_selector(
            '.jobs-document-upload-redesign-card__container, .jobs-document-upload'
        )
        if resume_section and pdf_path:
            try:
                file_inputs = page.evaluate("""() =>
                    [...document.querySelectorAll('input[type="file"]')]
                    .map((el, i) => ({index: i, id: el.id || ''}))
                """)
                if file_inputs:
                    page.locator('input[type="file"]').nth(0).set_input_files(pdf_path)
                    log.info(f"Resume uploaded: {pdf_path}")
                    _delay(3.0, 4.0)
                    page.evaluate("""() => {
                        const radios = [...document.querySelectorAll(
                            'input.jobs-document-upload-redesign-card__toggle[type="radio"]'
                        )];
                        if (radios.length) radios[0].click();
                    }""")
                    _delay(0.5, 1.0)
            except Exception as e:
                log.warning(f"Resume upload error: {e}")
            return

    # Scroll modal to top so all fields are visible
    try:
        page.evaluate("""() => {
            const s = document.querySelector(
                '.artdeco-modal__content, .jobs-easy-apply-modal__content'
            );
            if (s) s.scrollTop = 0;
        }""")
        _delay(0.2, 0.4)
    except Exception:
        pass

    # Scan main frame + ATS iframes only
    ats_frames = [
        f for f in page.frames
        if not f.is_detached()
        and f.url not in ('about:blank', '', page.url)
        and any(d in f.url for d in _ATS_DOMAINS)
    ]
    frame_objects = [page] + ats_frames

    fields = []
    for idx, ctx in enumerate(frame_objects):
        try:
            f_fields = ctx.evaluate(_EXTRACT_FIELDS_JS)
            # Remove reCAPTCHA/bot fields
            f_fields = [
                f for f in f_fields
                if not any(kw in (f.get('id','') + f.get('name','')).lower()
                           for kw in ('recaptcha', 'g-recaptcha', 'captcha', 'bot'))
            ]
            for f in f_fields:
                f['_fidx'] = idx
            fields.extend(f_fields)
            if idx > 0 and f_fields:
                log.info(f"ATS iframe[{idx}] ({ctx.url[:60]}): {len(f_fields)} fields")
        except Exception as ex:
            log.debug(f"Frame[{idx}] extraction failed: {ex}")

    if not fields:
        return

    log.info(f"Extracted {len(fields)} fields: " +
             str([(f.get('label') or f.get('id'), f.get('type')) for f in fields]))

    # Decide which fields need filling
    PLACEHOLDER_VALS = {"", "select an option", "select", "please select", "--select--"}

    error_ids = set(page.evaluate("""() => {
        const ids = new Set();
        document.querySelectorAll('[id$="-error"]:not(:empty)').forEach(e => {
            const fid = e.id.replace(/-error$/, '');
            if (fid) ids.add(fid);
        });
        document.querySelectorAll('[class*="artdeco-inline-feedback--error"]').forEach(e => {
            const c = e.closest('[data-test-single-line-text-form-component],[data-test-numeric-text-form-component]');
            if (c) { const inp = c.querySelector('input,textarea,select'); if (inp && inp.id) ids.add(inp.id); }
        });
        return [...ids];
    }""") or [])

    def needs_fill(f: dict) -> bool:
        if f.get("type") == "file":
            return False
        if force_fill:
            return True
        cv    = f.get("currentValue", "").lower()
        ftype = f.get("type", "text")
        im    = f.get("inputmode", "")
        label = f.get("label", "").lower()
        # Skip optional "follow company" checkbox
        if ftype == "checkbox" and "follow" in label:
            return False
        if ftype in ("radio", "checkbox"):
            return True
        if f.get("id", "") in error_ids:
            return True
        if cv in PLACEHOLDER_VALS:
            return True
        if im in ("numeric", "decimal") and cv in ("0", ""):
            return True
        return False

    to_fill = [f for f in fields if needs_fill(f)]
    if not to_fill:
        return

    log.info(f"Fields to fill ({len(to_fill)}): " +
             str([f.get('label') or f.get('id') for f in to_fill]))

    # 1. Rules-based fill (no Gemini tokens)
    needs_gemini = []
    for field in to_fill:
        ans = _rules_based_answer(field, profile)
        if ans is not None:
            fidx   = field.get('_fidx', 0)
            target = frame_objects[fidx] if fidx < len(frame_objects) else page
            _fill_field(target, field, str(ans))
            _delay(0.1, 0.2)
        else:
            needs_gemini.append(field)

    # 2. Gemini for unknown fields only
    if needs_gemini:
        log.info(f"Asking Gemini for {len(needs_gemini)} unknown fields")
        answers = _gemini_answers(needs_gemini, profile, jd_summary, company, role)
        log.info(f"Gemini answers: {answers}")

        def _norm(s: str) -> str:
            return re.sub(r'[^a-z0-9]', '', s.lower())

        norm_ans = {_norm(k): v for k, v in answers.items()}

        for field in needs_gemini:
            key       = field.get("id") or field.get("name") or ""
            label_low = field.get("label", "").lower()
            ftype     = field.get("type", "text")

            ans = (answers.get(key)
                   or (norm_ans.get(_norm(key)) if key else None))

            # Label-based match fallback
            if not ans and label_low:
                for ak, av in answers.items():
                    if label_low in ak.lower() or ak.lower() in label_low:
                        ans = av
                        break

            # Numeric fallback: experience field
            if not ans and ftype in ("text", "number") and any(
                kw in label_low for kw in ("experience", "year")
            ):
                ans = str(profile.years_of_experience)

            if ans and str(ans) not in ("RESUME_PDF", ""):
                fidx   = field.get('_fidx', 0)
                target = frame_objects[fidx] if fidx < len(frame_objects) else page
                _fill_field(target, field, str(ans))
                _delay(0.1, 0.2)


# ── Main applicator ───────────────────────────────────────────────────────────

def apply_linkedin_easy_apply(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    """Complete LinkedIn Easy Apply and submit (or stop before Submit in dry_run mode)."""
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
            page.goto(apply_url, timeout=30000)
            _delay(2.0, 3.0)

            # Open the Easy Apply modal
            if not page.query_selector(".jobs-easy-apply-modal, [data-test-modal-id='easy-apply-modal']"):
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
            review_streak     = 0
            prev_field_hashes: list = []  # track last N field fingerprints to detect true stuck

            for step in range(50):
                try:
                    page.wait_for_selector(
                        ".jobs-easy-apply-modal, [data-test-modal-id='easy-apply-modal'], "
                        ".jobs-easy-apply-content",
                        timeout=8000
                    )
                except PWTimeout:
                    # Modal closed — check for success
                    try:
                        page.wait_for_selector(
                            "[data-test-modal-id='post-apply-modal'], "
                            ".jobs-post-apply-modal, "
                            "h2:has-text('Application submitted'), "
                            "h2:has-text('Your application was sent')",
                            timeout=3000
                        )
                        log.info(f"✅ Applied: '{role}' @ {company}")
                        return True
                    except PWTimeout:
                        pass
                    log.warning(f"Modal disappeared at step {step}")
                    break

                _delay(0.8, 1.2)

                # Detect truly stuck: same field fingerprint 4 steps in a row
                fingerprint = frozenset(
                    f.get("id","") or f.get("name","")
                    for _, f in [(0, f) for f in (
                        page.evaluate(_EXTRACT_FIELDS_JS) if True else []
                    )]
                ) if False else None  # computed below after fill

                force_fill = review_streak >= 3

                if force_fill:
                    log.warning(f"Step {step}: stuck on Review (streak={review_streak}), forcing full fill")

                _fill_step(page, profile, jd_summary, company, role, pdf_path,
                           force_fill=force_fill)
                _delay(0.5, 0.8)

                # Navigation buttons
                # Submit
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
                    if dry_run:
                        log.info(f"DRY RUN — would submit: '{role}' @ {company}")
                        return True
                    page.evaluate("el => el.click()", submit_btn)
                    _delay(2.0, 3.0)
                    log.info(f"✅ Applied: '{role}' @ {company}")
                    return True

                # Review
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
                    # Truly stuck: give up after 8 review clicks (likely unfillable required field)
                    if review_streak > 8:
                        log.warning(f"Step {step}: exceeded review limit, giving up")
                        break
                    log.info(f"Step {step}: clicking Review (streak={review_streak})")
                    page.evaluate("el => el.click()", review_btn)
                    _delay(1.5, 2.0)

                    # Fix error fields
                    error_fields = page.evaluate("""() => {
                        const results = []; const seen = new Set();
                        document.querySelectorAll('[id$="-error"]').forEach(errEl => {
                            const errTxt = errEl.innerText.trim();
                            if (!errTxt) return;
                            const inputId = errEl.id.replace(/-error$/, '');
                            if (seen.has(inputId)) return;
                            const inp = document.getElementById(inputId);
                            if (!inp) return;
                            seen.add(inputId);
                            let lbl = '';
                            document.querySelectorAll('label[for]').forEach(l => {
                                if (l.htmlFor === inputId) lbl = l.innerText.trim().replace(/\\s*\\*\\s*$/, '').trim();
                            });
                            if (!lbl) {
                                const lbId = inp.getAttribute('aria-labelledby');
                                if (lbId) { const lbEl = document.getElementById(lbId); if (lbEl) lbl = lbEl.innerText.trim(); }
                            }
                            results.push({ id: inputId, label: lbl || inputId, type: inp.type || 'text',
                                           inputmode: inp.getAttribute('inputmode') || '',
                                           currentValue: inp.value || '', error: errTxt, selector: null, name: inp.name || '' });
                        });
                        document.querySelectorAll('[class*="artdeco-inline-feedback--error"]').forEach(errEl => {
                            const errTxt = errEl.innerText.trim(); if (!errTxt) return;
                            const c = errEl.closest('[data-test-single-line-text-form-component],[data-test-numeric-text-form-component]');
                            if (!c) return;
                            const inp = c.querySelector('input,textarea,select');
                            if (!inp || !inp.id || seen.has(inp.id)) return;
                            seen.add(inp.id);
                            const lbl = c.querySelector('label,[class*="label"]');
                            results.push({ id: inp.id, label: lbl ? lbl.innerText.trim() : inp.id,
                                           type: inp.type || 'text', inputmode: inp.getAttribute('inputmode') || '',
                                           currentValue: inp.value || '', error: errTxt, selector: null, name: inp.name || '' });
                        });
                        return results;
                    }""")

                    if error_fields:
                        log.info(f"Error fields: {[f['label'][:40] for f in error_fields]}")
                        for field in error_fields:
                            ans = _rules_based_answer(field, profile)
                            if not ans:
                                lbl = field.get("label", "").lower()
                                im  = field.get("inputmode", "")
                                if "year" in lbl or "experience" in lbl or im in ("numeric", "decimal"):
                                    ans = str(profile.years_of_experience)
                            if ans:
                                _fill_field(page, field, str(ans))
                                _delay(0.2, 0.4)
                    continue

                # Next
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
                    review_streak = 0
                    log.info(f"Step {step}: clicking Next")
                    page.evaluate("el => el.click()", next_btn)
                    _delay(1.0, 1.5)
                    continue

                # Fallback primary button
                fallback = page.query_selector(
                    ".jobs-easy-apply-modal button.artdeco-button--primary, "
                    ".jobs-easy-apply-content button.artdeco-button--primary"
                )
                if fallback and fallback.is_visible():
                    btn_text = fallback.inner_text().strip().lower()
                    log.info(f"Step {step}: fallback '{btn_text}'")
                    if dry_run and "submit" in btn_text:
                        log.info(f"DRY RUN — would submit: '{role}' @ {company}")
                        return True
                    page.evaluate("el => el.click()", fallback)
                    _delay(1.0, 1.5)
                    if "submit" in btn_text:
                        log.info(f"✅ Applied: '{role}' @ {company}")
                        return True
                    continue

                log.warning(f"Step {step}: no navigation button found")
                break

            log.warning(f"Easy Apply: did not reach Submit for '{role}' @ {company}")
            return False

        except Exception as e:
            log.error(f"LinkedIn Easy Apply error: {e}")
            return False
        finally:
            browser.close()
