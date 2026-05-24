import json
import re
import logging
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
import google.generativeai as genai
from src.config import GEMINI_API_KEY
from src.profile import UserProfile

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
log = logging.getLogger(__name__)

_CAPTCHA_INDICATORS = ["recaptcha", "hcaptcha", "cf-turnstile", "captcha"]

_EXTRACT_FIELDS_JS = """() => {
    const fields = [];
    const inputs = document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]), textarea, select'
    );
    inputs.forEach(input => {
        const id = input.id || '';
        const name = input.name || '';
        let label = '';
        if (id) {
            const labelEl = document.querySelector('label[for="' + id + '"]');
            if (labelEl) label = labelEl.textContent.trim();
        }
        if (!label) label = input.getAttribute('aria-label') || '';
        if (!label) label = input.getAttribute('placeholder') || '';
        if (!label) {
            const parentLabel = input.closest('label');
            if (parentLabel) label = parentLabel.textContent.trim();
        }
        if (!label) {
            const prev = input.previousElementSibling;
            if (prev) label = prev.textContent.trim().replace(/\\*$/, '').trim();
        }
        const type = input.tagName.toLowerCase() === 'select'
            ? 'select'
            : (input.getAttribute('type') || 'text').toLowerCase();
        const field = { id: id, name: name, label: label, type: type,
                        selector: id ? '#' + id : '[name="' + name + '"]' };
        if (type === 'select') {
            field.options = Array.from(input.options)
                .map(o => o.text.trim()).filter(Boolean);
        }
        if (type === 'radio' || type === 'checkbox') {
            if (name) {
                const group = document.querySelectorAll('input[name="' + name + '"]');
                field.options = Array.from(group).map(el => {
                    const lbl = document.querySelector('label[for="' + el.id + '"]');
                    return lbl ? lbl.textContent.trim() : (el.value || '');
                }).filter(Boolean);
            }
        }
        if (id || name) fields.push(field);
    });
    return fields;
}"""


class CaptchaDetectedError(Exception):
    pass


class FormSubmitError(Exception):
    pass


def _check_captcha_in_content(html_content: str) -> bool:
    """Return True if any CAPTCHA indicator is found in the page HTML."""
    lower = html_content.lower()
    return any(indicator in lower for indicator in _CAPTCHA_INDICATORS)


def _generate_answers(
    fields: list,
    profile: UserProfile,
    jd_summary: str,
    company: str,
    role: str,
) -> dict:
    """Ask Gemini to fill all form fields based on the candidate profile."""
    prompt = f"""You are filling a job application form for: {role} at {company}.

Job requirements: {jd_summary}

Candidate profile:
Name: {profile.name}
Email: {profile.email}
Phone: {profile.phone}
LinkedIn: {profile.linkedin}
College: {profile.college}, {profile.degree}, CGPA: {profile.cgpa}
Graduation year: {profile.graduation_year}
Years of experience: {profile.years_of_experience}
Current CTC: {profile.current_ctc}
Expected CTC: {profile.expected_ctc}
Notice period: {profile.notice_period}
Location preference: {profile.location_preference}
Work authorization: {profile.work_authorization}
Skills: {", ".join(profile.skills)}
Summary: {profile.summary}

Form fields to fill:
{json.dumps(fields, indent=2)}

Rules:
- For each field, return the best answer from the candidate profile.
- For "Why do you want to work here", "Cover letter", or "About yourself" fields: write 3-4 specific sentences referencing the company name, the role, and the candidate's relevant experience.
- For select/radio fields: pick the EXACT text of the best matching option from the "options" list.
- For file upload fields (type="file"): return the string "RESUME_PDF".
- Use the field's "id" if present, else "name" as the JSON key.
- Return ONLY a valid JSON object with no markdown fences."""

    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning(f"Gemini returned malformed JSON for form answers: {e}. Returning empty answers.")
        return {}


def _fill_field(page: Page, field: dict, answer: str) -> None:
    """Fill a single form field. Silently logs on failure."""
    selector = field.get("selector") or f'[name="{field["name"]}"]'
    field_type = field.get("type", "text")
    try:
        if field_type in ("text", "email", "tel", "number", "url", "textarea", "date", "search", "password"):
            page.fill(selector, str(answer))
        elif field_type == "select":
            page.select_option(selector, label=str(answer))
        elif field_type in ("radio", "checkbox"):
            name = field.get("name", "")
            if name:
                radios = page.locator(f'input[name="{name}"]')
                count = radios.count()
                for i in range(count):
                    radio = radios.nth(i)
                    rid = radio.get_attribute("id") or ""
                    label_el = page.locator(f'label[for="{rid}"]')
                    label_text = label_el.text_content() if label_el.count() > 0 else ""
                    if label_text and answer.lower() in label_text.lower():
                        radio.click()
                        break
    except Exception as e:
        log.warning(f"Could not fill field '{field.get('label', selector)}': {e}")


def fill_web_form(
    url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
) -> bool:
    """
    Open a job application URL in a headless browser, fill all form fields
    using Gemini, and submit. Handles multi-page forms.

    Returns True on successful submission.
    Raises CaptchaDetectedError if a CAPTCHA is found.
    Raises FormSubmitError if the submit button cannot be found.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            try:
                page.goto(url, timeout=30000, wait_until="networkidle")
            except PlaywrightTimeoutError:
                log.warning("networkidle timeout, continuing with domcontentloaded")
                page.goto(url, timeout=30000, wait_until="domcontentloaded")

            if _check_captcha_in_content(page.content()):
                raise CaptchaDetectedError(f"CAPTCHA detected on {url}")

            max_pages = 10
            for _ in range(max_pages):
                page.wait_for_timeout(1500)

                fields = page.evaluate(_EXTRACT_FIELDS_JS)
                if not fields:
                    break

                answers = _generate_answers(fields, profile, jd_summary, company, role)

                for field in fields:
                    key = field.get("id") or field.get("name")
                    if not key:
                        continue
                    if field.get("type") == "file":
                        try:
                            page.set_input_files(field["selector"], pdf_path)
                        except Exception as e:
                            log.warning(f"File upload failed for '{field.get('label')}': {e}")
                        continue
                    answer = answers.get(key)
                    if answer and str(answer) != "RESUME_PDF":
                        _fill_field(page, field, str(answer))

                # Check for Next / Continue button
                next_btn = None
                for label in ["Next", "Continue", "Next Step", "Proceed"]:
                    btn = page.get_by_role("button", name=re.compile(label, re.IGNORECASE))
                    if btn.count() > 0:
                        next_btn = btn.first
                        break

                if next_btn:
                    next_btn.click()
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except PlaywrightTimeoutError:
                        pass
                    if _check_captcha_in_content(page.content()):
                        raise CaptchaDetectedError(f"CAPTCHA appeared mid-form on {url}")
                    continue

                # Check for Submit button
                submit_btn = None
                for label in ["Submit", "Apply", "Submit Application", "Apply Now", "Send Application"]:
                    btn = page.get_by_role("button", name=re.compile(label, re.IGNORECASE))
                    if btn.count() > 0:
                        submit_btn = btn.first
                        break

                if submit_btn:
                    submit_btn.click()
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except PlaywrightTimeoutError:
                        pass
                    return True

                # No Next or Submit found
                break

            raise FormSubmitError(f"Could not find submit button after filling form at {url}")
        finally:
            browser.close()
