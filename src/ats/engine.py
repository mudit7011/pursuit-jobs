"""Fill and submit application forms on ATS sites and form builders.

One engine, small per-site adapters (see ADAPTERS). The engine:
  1. opens the application form (adapter.prepare)
  2. tags every visible field with data-jac and reads its label, kind, options
  3. decides answers (src.ats.answers) and fills them
  4. refuses to submit while a required field is empty -> MissingAnswersError
  5. pages through Next buttons, clicks Submit, and waits for the site's
     confirmation; no confirmation is a failure, never a silent success.
"""
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from playwright.sync_api import Page, sync_playwright

from src.ats import answers
from src.profile import UserProfile
from src.web_form_filler import CaptchaDetectedError, FormSubmitError

log = logging.getLogger(__name__)

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sessions")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


ASSIST_TIMEOUT = 15 * 60


class MissingAnswersError(Exception):
    """Required questions the bot has no facts for. The user answers them once."""

    def __init__(self, questions: list[str], report=None):
        self.questions = questions
        self.report = report
        super().__init__("Needs your answers: " + " | ".join(questions))


class LoginRequiredError(Exception):
    pass


# ── Field extraction ─────────────────────────────────────────────────────────

_FIELDS_JS = r"""() => {
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
                     return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const tag = el => { if (!el.dataset.jac) el.dataset.jac = 'j' + (window.__jacN = (window.__jacN || 0) + 1); return el.dataset.jac; };
  const clean = t => (t || '').replace(/\s+/g, ' ').replace(/Required to answer.*$/i, '')
                       .replace(/^\d+\s*[.)]\s*/, '').replace(/\s+Required$/i, '').replace(/\s*\*\s+(?=\S)/g, ' ').replace(/\s*[*✱]+\s*$/, '').replace(/[✱]/g, '').trim();
  const textOf = id => id.split(' ').map(i => document.getElementById(i)?.innerText || '').join(' ');
  const labelOf = el => {
    const item = el.closest('[role=listitem]');                         // Google Forms question
    const head = item && item.querySelector('[role=heading]');
    if (head) return head.innerText;
    if (el.id) { const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`); if (l && l.innerText.trim()) return l.innerText; }
    const lb = el.getAttribute('aria-labelledby'); if (lb && textOf(lb).trim()) return textOf(lb);
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    const wrap = el.closest('label'); if (wrap && wrap.innerText.trim()) return wrap.innerText;
    // Lever: <li class="application-question"><div class="application-label">…
    const q = el.closest('.application-question, .application-field, .field, [class*=question], [class*=form-group], [class*=FormField], fieldset');
    if (q) { const l = q.querySelector('.application-label, label, legend, [class*=label], [class*=title]'); if (l && l.innerText.trim()) return l.innerText; }
    return el.placeholder || el.name || '';
  };
  const required = (el, label) => el.required || el.getAttribute('aria-required') === 'true'
                                   || !!el.closest('[role=listitem]')?.querySelector('[aria-label="Required question"]')
                                   || /\*\s*$/.test((label || '').trim()) || /\*\s*\n/.test(label || '')
                                   || /Required to answer|\bRequired\s*$/i.test((label || '').trim());
  const heads = [...document.querySelectorAll('h1, h2, h3, h4, legend')].filter(h => h.innerText.trim());
  const sectionOf = el => { let last = ''; for (const h of heads) {
      if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) last = h.innerText.trim(); else break; }
    return last.slice(0, 60); };
  const fields = [];
  const done = new Set();

  // Radio groups (native or ARIA), incl. Google & Microsoft Forms
  document.querySelectorAll('[role=radiogroup]').forEach(g => {
    if (!vis(g)) return;
    const opts = [...g.querySelectorAll('input[type=radio], [role=radio]')];
    if (!opts.length) return;
    opts.forEach(o => done.add(o));
    const rawLabel = labelOf(g);
    fields.push({ jid: tag(g), kind: 'radio', label: clean(rawLabel), required: required(g, rawLabel),
      options: opts.map(o => clean(o.getAttribute('data-value') || o.getAttribute('aria-label') || labelOf(o) || o.value)),
      optionIds: opts.map(tag),
      filled: opts.some(o => o.checked || o.getAttribute('aria-checked') === 'true') });
  });

  // Google Forms: checkbox groups and dropdowns are divs
  document.querySelectorAll('[role=listitem]').forEach(item => {
    const boxes = [...item.querySelectorAll('[role=checkbox]')].filter(b => b.tagName !== 'INPUT');
    if (boxes.length && vis(item)) {
      const rawLabel = labelOf(boxes[0]);
      fields.push({ jid: tag(item), kind: 'checkbox', label: clean(rawLabel), required: required(item, rawLabel) || !!item.querySelector('[aria-label="Required question"]'),
        options: boxes.map(b => clean(b.getAttribute('data-answer-value') || b.getAttribute('aria-label'))), optionIds: boxes.map(tag),
        filled: boxes.some(b => b.getAttribute('aria-checked') === 'true') });
    }
    const lb = item.querySelector('[role=listbox]');
    if (lb && vis(lb)) {
      const rawLabel = labelOf(lb);
      fields.push({ jid: tag(lb), kind: 'gselect', label: clean(rawLabel), required: required(lb, rawLabel) || !!item.querySelector('[aria-label="Required question"]'),
        options: [...lb.querySelectorAll('[role=option]')].map(o => o.getAttribute('data-value')).filter(Boolean),
        filled: !!lb.querySelector('[role=option][aria-selected=true]:not([data-value=""])') });
    }
  });

  const groups = {};
  document.querySelectorAll('input, textarea, select').forEach(el => {
    if (done.has(el)) return;
    const type = (el.tagName === 'SELECT' ? 'select' : el.tagName === 'TEXTAREA' ? 'textarea' : (el.type || 'text')).toLowerCase();
    if (['hidden', 'submit', 'button', 'reset', 'image', 'search'].includes(type)) return;
    if (el.closest('header, nav, footer')) return;
    if (type !== 'file' && !vis(el)) return;                    // honeypots and off-screen fields
    if (el.tabIndex === -1 && el.getAttribute('aria-hidden') === 'true') return;
    if (/requiredInput/.test(el.className)) return;             // Greenhouse react-select mirror input
    const rawLabel = labelOf(el);
    const isCombo = el.getAttribute('role') === 'combobox' || !!el.closest('[class*=select__control]');
    if (type === 'radio' || type === 'checkbox') {
      const key = el.name || ('c_' + tag(el.closest('fieldset, [class*=question], li, div') || el));
      const g = groups[key] = groups[key] || { jid: tag(el), kind: type, name: el.name, label: '', section: sectionOf(el), required: false, options: [], optionIds: [], filled: false };
      g.options.push(clean(labelOf(el) || el.value)); g.optionIds.push(tag(el));
      g.required = g.required || el.required; g.filled = g.filled || el.checked;
      if (!g.label) {
        const box = el.closest('fieldset, .application-question, [class*=question], [class*=field]');
        const l = box && box.querySelector('legend, .application-label, label:not([for]), [class*=label], [class*=title]');
        g.label = clean(l ? l.innerText : el.name);
        g.required = g.required || /\*/.test(l ? l.innerText : '');
      }
      return;
    }
    let current = el.value || '';
    if (type === 'select') current = el.selectedIndex > 0 ? el.options[el.selectedIndex].text : '';
    if (isCombo) { const c = el.closest('[class*=select__control]') || el.closest('[class*=container]'); const sv = c && c.querySelector('[class*=single-value], [class*=singleValue]'); current = sv ? sv.innerText : ''; }
    fields.push({ jid: tag(el), kind: isCombo ? 'combobox' : type, name: el.name || el.id || '', label: clean(rawLabel), section: sectionOf(el),
      required: required(el, rawLabel), options: type === 'select' ? [...el.options].map(o => o.text.trim()).filter(Boolean) : [],
      accept: el.accept || '', filled: type === 'file' ? el.files.length > 0 : !!current.trim() });
  });
  Object.values(groups).forEach(g => fields.push(g));
  return fields;
}"""


# ── Adapters ─────────────────────────────────────────────────────────────────

_SUCCESS_GENERIC = r"thank(s| you)( for (applying|your (application|interest|response)))?|application (has been |was )?(received|submitted|sent)|successfully (submitted|applied)|response (has been |was )?(recorded|submitted)"


@dataclass
class Adapter:
    name: str
    match: Callable[[str], bool]
    form_url: Callable[[str], str] = lambda u: u
    session: Optional[str] = None             # sessions/<file> to load, e.g. google.json
    channel: Optional[str] = None             # "chrome" = the installed Chrome, not bundled Chromium
    open_buttons: tuple = ()                  # buttons that reveal the form on the job page
    submit: tuple = ("button:has-text('Submit application')", "button:has-text('Submit')",
                     "input[type=submit]", "[role=button]:has-text('Submit')", "button[type=submit]",
                     "button:has-text('Apply')")
    next: tuple = ("button:has-text('Next')", "button:has-text('Continue')", "[role=button]:has-text('Next')")
    success: str = _SUCCESS_GENERIC
    success_url: str = r"/(thanks|confirmation|success|formResponse)"


def _suffix(path: str) -> Callable[[str], str]:
    def f(u: str) -> str:
        base = u.split("?")[0].rstrip("/")
        return base if base.endswith(path) else base + path
    return f


ADAPTERS = [
    Adapter("google_forms", lambda u: "docs.google.com/forms" in u or "forms.gle" in u,
            session="google.json", channel="chrome",
            submit=("[role=button]:has-text('Submit')",), next=("[role=button]:has-text('Next')",),
            success=r"your response has been recorded|response (has been )?recorded"),
    Adapter("microsoft_forms", lambda u: "forms.office.com" in u or "forms.cloud.microsoft" in u or "forms.microsoft" in u,
            submit=("button:has-text('Submit')",), next=("button:has-text('Next')",),
            success=r"your response was submitted|thanks!|response (was )?submitted"),
    Adapter("greenhouse", lambda u: "greenhouse.io" in u or "gh_jid=" in u,
            open_buttons=("button:has-text('Apply')", "a:has-text('Apply for this job')"),
            submit=("button:has-text('Submit application')", "#submit_app", "button[type=submit]")),
    Adapter("lever", lambda u: "jobs.lever.co" in u, form_url=_suffix("/apply"),
            submit=("button:has-text('Submit application')", "#btn-submit")),
    Adapter("ashby", lambda u: "jobs.ashbyhq.com" in u, form_url=_suffix("/application"),
            submit=("button:has-text('Submit Application')",)),
    Adapter("zoho_forms", lambda u: "zohopublic" in u or "zfrmz" in u or "forms.zoho" in u,
            submit=("button:has-text('Submit')", "button:has-text('Apply')", "input[type=submit]")),
    Adapter("keka", lambda u: ".keka.com/careers" in u,
            open_buttons=("button:has-text('Apply')", "a:has-text('Apply')"),
            submit=("button:has-text('Submit')", "button:has-text('Apply')")),
    Adapter("generic", lambda u: True,
            open_buttons=("button:has-text('Apply now')", "a:has-text('Apply now')", "button:has-text('Apply')")),
]


def adapter_for(url: str) -> Adapter:
    return next(a for a in ADAPTERS if a.match(url))


# ── Filling ──────────────────────────────────────────────────────────────────

def _first_visible(page: Page, selectors: tuple):
    for sel in selectors:
        try:
            for el in page.query_selector_all(sel):
                if el.is_visible():
                    return el
        except Exception:
            continue
    return None


def _loc(page: Page, jid: str):
    return page.locator(f'[data-jac="{jid}"]').first


def _pick(page: Page, f: dict, value) -> bool:
    """Click the option(s) of a radio/checkbox group whose text matches value."""
    wanted = value if isinstance(value, list) else [value]
    hit = False
    for w in wanted:
        if w not in f["options"]:
            continue
        el = _loc(page, f["optionIds"][f["options"].index(w)])
        try:
            # Clicking an already-ticked checkbox un-ticks it, so look before clicking.
            if el.evaluate("e => e.checked === true || e.getAttribute('aria-checked') === 'true'"):
                hit = True
                continue
            if el.evaluate("e => e.tagName") == "INPUT":
                el.check(force=True)
            else:
                el.click()
            hit = True
        except Exception as e:
            log.debug(f"pick failed for {w}: {e}")
    return hit


def _fill(page: Page, f: dict, value, resume_path: str) -> bool:
    kind = f["kind"]
    el = _loc(page, f["jid"])
    try:
        if kind == "file":
            el.set_input_files(resume_path)
            return True
        if kind in ("radio", "checkbox") and f.get("optionIds"):
            return _pick(page, f, value)
        if kind == "select":
            el.select_option(label=str(value))
            return True
        if kind == "gselect":
            el.click()
            page.wait_for_timeout(500)
            opt = page.locator(f'[role=option][data-value="{value}"]').last
            opt.click()
            page.wait_for_timeout(400)
            return True
        if kind == "combobox":
            el.click()
            el.fill(str(value))
            page.wait_for_timeout(900)
            options = [o for o in page.query_selector_all("[role=option]") if o.is_visible()]
            texts = [o.inner_text().strip() for o in options]
            choice = answers.best_option(str(value), texts) if texts else None
            if choice is None:
                el.press("Escape")
                return False
            options[texts.index(choice)].click()
            return True
        if kind == "date":
            return False  # needs a real date we don't have; left to the user
        el.fill(str(value))
        return True
    except Exception as e:
        log.debug(f"fill failed for '{f['label']}': {e}")
        return False


def _is_resume_input(f: dict, file_fields: list[dict]) -> bool:
    text = f"{f['label']} {f.get('name', '')}".lower()
    if re.search(r"cover|transcript|photo|picture|portfolio", text):
        return False
    if re.search(r"resume|cv\b|curriculum", text):
        return True
    # Ashby has an unlabeled "autofill from resume" input next to the real one.
    labeled = [x for x in file_fields if re.search(r"resume|cv\b", f"{x['label']} {x.get('name', '')}".lower())]
    return not labeled and (f["required"] or len(file_fields) == 1)


_CAPTCHA_LABEL = re.compile(r"captcha|security code|enter the (code|characters)|verification code", re.I)


_CAPTCHA_FRAMES = ("iframe[src*='hcaptcha.com']", "iframe[title='reCAPTCHA']", "iframe[src*='recaptcha/api2/anchor']",
                   "iframe[src*='challenges.cloudflare.com']")


def _captcha_present(page: Page) -> bool:
    try:
        _check_captcha(page)
    except CaptchaDetectedError:
        return True
    return any(_CAPTCHA_LABEL.search(f["label"] or "") and not f["filled"] for f in page.evaluate(_FIELDS_JS))


def _hand_over(page: Page, ad: "Adapter", report: "Report", role: str, company: str) -> "Report":
    """Leave the filled form to the user and wait for the site's confirmation."""
    log.info(f"Handing {company} over to you: finish the CAPTCHA / remaining fields and click Submit")
    page.bring_to_front()
    url_before = page.url
    if _wait_success(page, ad, url_before, timeout=ASSIST_TIMEOUT):
        log.info(f"✅ You submitted {role} @ {company}")
        return report
    raise FormSubmitError("Window was left without submitting — nothing was sent")


def _check_captcha(page: Page) -> None:
    for sel in _CAPTCHA_FRAMES:
        for fr in page.query_selector_all(sel):
            box = fr.bounding_box()
            if fr.is_visible() and box and box["width"] > 60 and box["height"] > 40:
                raise CaptchaDetectedError(f"CAPTCHA on {page.url}")


@dataclass
class Report:
    adapter: str
    filled: list = field(default_factory=list)      # (label, value, source)
    missing: list = field(default_factory=list)
    pages: int = 0


def _fill_page(page: Page, profile: UserProfile, jd: str, company: str, role: str,
               resume_path: str, report: Report, resume_link: str = "", assist: bool = False) -> list[str]:
    """Fill the visible page. Returns labels of required fields still empty."""
    fields = page.evaluate(_FIELDS_JS)
    files = [f for f in fields if f["kind"] == "file"]
    for f in files:
        if not f["filled"] and answers.resume_path_ok(resume_path) and _is_resume_input(f, files):
            if _fill(page, f, None, resume_path):
                report.filled.append((f["label"] or "Resume", os.path.basename(resume_path), "resume"))
                page.wait_for_timeout(1500)  # some sites parse the resume and prefill fields

    fields = page.evaluate(_FIELDS_JS)
    # Text CAPTCHAs (Keka and others) are for a human — never send them to the LLM.
    if not assist and any(f["required"] and not f["filled"] and _CAPTCHA_LABEL.search(f["label"] or "") for f in fields):
        raise CaptchaDetectedError(f"{report.adapter} form has a CAPTCHA — finish it by hand")
    todo = [f for f in fields if not f["filled"] and f["kind"] != "file" and f["label"]
            and not _CAPTCHA_LABEL.search(f["label"])]
    decided = answers.decide(todo, profile, jd, company, role)
    if resume_link:
        # "Paste your resume link" text questions (common on Google Forms without upload).
        for f in todo:
            if f["kind"] in ("text", "url", "textarea") and re.search(r"resume|\bcv\b|drive link", f["label"], re.I):
                decided[f["jid"]] = {"value": resume_link, "source": "resume link"}
    for f in todo:
        d = decided.get(f["jid"])
        if d and _fill(page, f, d["value"], resume_path):
            report.filled.append((f["label"], d["value"], d["source"]))
            page.wait_for_timeout(150)
        elif d:
            log.info(f"Couldn't put {str(d['value'])[:40]!r} into {f['kind']} '{f['label'][:50]}'")

    after = page.evaluate(_FIELDS_JS)
    missing: list[str] = []
    for f in after:
        if not f["required"] or f["filled"] or (f["kind"] == "file" and not _is_resume_input(f, files)):
            continue
        q = answers.question_text(f) if f["label"] else (f.get("name") or "Unlabeled field")
        n, base = 2, q
        while q in missing:           # two referees both asking "Email"
            q, n = f"{base} ({n})", n + 1
        missing.append(q)
    return missing


def _wait_success(page: Page, ad: Adapter, url_before: str, timeout: float = 20) -> bool:
    end = time.time() + timeout
    pat = re.compile(ad.success, re.I)
    while time.time() < end:
        try:
            if page.url != url_before and re.search(ad.success_url, page.url, re.I):
                return True
            if pat.search(page.inner_text("body")[:20000]):
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def apply_form(url: str, company: str, role: str, jd_summary: str, pdf_path: str,
               profile: UserProfile, dry_run: bool = False, max_pages: int = 8,
               resume_link: str = "", assist: bool = False) -> Report:
    """Fill (and unless dry_run, submit) the application at `url`.

    Raises MissingAnswersError, LoginRequiredError, CaptchaDetectedError or
    FormSubmitError; returns a Report on success (or at the submit step in dry_run).

    assist=True: the user is at the screen. Fill everything, then leave the window
    open for them to solve a CAPTCHA / answer what's left and click Submit; return
    once the site confirms (up to ASSIST_TIMEOUT).
    """
    ad = adapter_for(url)
    report = Report(adapter=ad.name)
    session = os.path.join(SESSIONS_DIR, ad.session) if ad.session else None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.getenv("JAC_HEADLESS") == "1", channel=ad.channel,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            storage_state=session if session and os.path.exists(session) else None,
            user_agent=UA, viewport={"width": 1280, "height": 900}, locale="en-IN",
        )
        page = ctx.new_page()
        try:
            page.goto(ad.form_url(url), timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            if "accounts.google.com" in page.url or "login.microsoftonline.com" in page.url:
                raise LoginRequiredError(
                    "This form needs you signed in to Google — run setup_sessions.py google once"
                    if "google" in page.url else "This form needs a Microsoft sign-in — finish it by hand")
            if re.search(r"no longer accepting|this form is closed|position (has been )?(filled|closed)|job (is )?(no longer|not) available",
                         page.inner_text("body")[:8000], re.I):
                raise FormSubmitError("This job or form is closed")

            if not page.evaluate(_FIELDS_JS) and ad.open_buttons:
                btn = _first_visible(page, ad.open_buttons)
                if btn:
                    btn.click()
                    page.wait_for_timeout(3000)

            for _ in range(max_pages):
                report.pages += 1
                seen = len(report.filled)
                missing = _fill_page(page, profile, jd_summary, company, role, pdf_path, report, resume_link, assist)
                for label, value, source in report.filled[seen:]:
                    log.info(f"[{ad.name}] {label[:60]!r} ← {str(value)[:60]!r} ({source})")
                if missing and not assist:
                    report.missing = missing
                    raise MissingAnswersError(missing, report)
                if assist and (missing or _captcha_present(page)):
                    return _hand_over(page, ad, report, role, company)

                nxt = _first_visible(page, ad.next)
                sub = _first_visible(page, ad.submit)
                if nxt and not sub:
                    nxt.click()
                    page.wait_for_timeout(2500)
                    continue
                if not sub:
                    raise FormSubmitError(f"No submit button found on {ad.name} form")
                if assist:  # the user asked to press Submit themselves
                    return _hand_over(page, ad, report, role, company)
                _check_captcha(page)
                if dry_run:
                    log.info(f"DRY RUN — {ad.name}: everything filled, stopping before Submit")
                    return report
                url_before = page.url
                sub.click()
                if _wait_success(page, ad, url_before):
                    log.info(f"✅ Submitted on {ad.name}: {role} @ {company}")
                    return report
                _check_captcha(page)
                errors = page.evaluate("""() => [...document.querySelectorAll('[aria-invalid=true], [class*=error], [role=alert]')]
                    .map(e => e.innerText.trim()).filter(t => t && t.length < 200).slice(0, 3)""")
                if errors:
                    raise FormSubmitError("Form rejected the answers: " + " / ".join(errors))
                raise FormSubmitError("Clicked Submit but saw no confirmation — check the site before retrying")
            raise FormSubmitError(f"Form had more than {max_pages} pages")
        finally:
            browser.close()
