import difflib
import json
import re
import google.generativeai as genai
from src.config import GEMINI_API_KEY
from src.models import JobPosting, ApplyType

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

_ATS_DOMAINS = [
    "greenhouse.io",
    "lever.co",
    "workday.com",
    "myworkdayjobs.com",
    "ashbyhq.com",
    "forms.office.com",
    "bamboohr.com",
    "recruitcrm.io",
    "forms.cloud.microsoft",
    "keka.com",
    "zohopublic",
    "zfrmz",
    "forms.zoho",
    "rippling.com",
    "workable.com",
    "dover.com",
    "pyjamahr.com",
]

_APPLY_PATH_KEYWORDS = ["/apply"]


def _is_web_form(url: str) -> bool:
    """Return True if the URL looks like an ATS or web application form."""
    if not url or "@" in url:
        return False
    if "docs.google.com/forms" in url or "forms.gle/" in url:
        return False
    if any(domain in url for domain in _ATS_DOMAINS):
        return True
    if any(kw in url for kw in _APPLY_PATH_KEYWORDS):
        return True
    return False


_URL_RE = re.compile(r"https?://[^\s<>\"')\]*]+")


def _clean_url(url: str) -> str:
    # Telegram markdown wraps links in **bold** / __italic__; that is not part of the URL.
    return re.sub(r"[*_~`.,;:!]+$", "", (url or "").strip())


def _verbatim_url(llm_url: str, message: str) -> str:
    """Return the apply URL exactly as written in the message.

    The LLM sometimes alters a character in long IDs (Google Form IDs especially),
    which turns a live form into a 404. Prefer the message's own text.
    """
    llm_url = _clean_url(llm_url) if "@" not in (llm_url or "") else llm_url
    urls = [_clean_url(u) for u in _URL_RE.findall(message or "")]
    if not urls or "@" in (llm_url or ""):
        return llm_url
    if llm_url in urls:
        return llm_url
    if llm_url:
        best = max(urls, key=lambda u: difflib.SequenceMatcher(None, u, llm_url).ratio())
        if difflib.SequenceMatcher(None, best, llm_url).ratio() >= 0.85:
            return best
        return llm_url
    forms = [u for u in urls if "forms" in u or _is_web_form(u)]
    return forms[0] if len(forms) == 1 else llm_url


def _build_prompt(message: str) -> str:
    return f"""Extract job details from this Telegram message. Return ONLY valid JSON, no markdown, no explanation.

Message:
{message}

Return this exact JSON:
{{
  "company": "company name or empty string",
  "role": "job title or empty string",
  "salary": "salary info or empty string",
  "location": "city or empty string",
  "jd_summary": "2-3 sentence summary of requirements and responsibilities",
  "apply_type": "email" or "form" or "unknown",
  "apply_target": "email address, Google Form URL, ATS/careers page URL, or empty string",
  "batch": "graduation batch years or empty string",
  "is_relevant": true if this is a job posting else false
}}"""

def parse_job_message(message: str) -> JobPosting:
    prompt = _build_prompt(message)
    response = model.generate_content(prompt)
    raw = response.text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    data = json.loads(raw)

    apply_type_raw = data.get("apply_type", "unknown")
    apply_target = _verbatim_url(data.get("apply_target", "") or "", message)

    # Resolve apply type with WEB_FORM detection
    if apply_type_raw == "email" and apply_target and "@" in apply_target:
        final_apply_type = ApplyType.EMAIL
    elif "docs.google.com/forms" in apply_target or "forms.gle/" in apply_target:
        final_apply_type = ApplyType.FORM
    elif _is_web_form(apply_target) or apply_target.startswith("http"):
        # Unknown careers sites go to the generic form engine rather than being dropped.
        final_apply_type = ApplyType.WEB_FORM
    else:
        final_apply_type = ApplyType.UNKNOWN

    return JobPosting(
        company=data.get("company", ""),
        role=data.get("role", ""),
        salary=data.get("salary", ""),
        location=data.get("location", ""),
        jd_summary=data.get("jd_summary", ""),
        apply_type=final_apply_type,
        apply_target=apply_target,
        batch=data.get("batch", ""),
        raw_message=message,
        is_relevant=data.get("is_relevant", False),
    )
