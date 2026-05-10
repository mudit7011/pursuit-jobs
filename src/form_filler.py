import re
import json
import requests
from bs4 import BeautifulSoup
from typing import Optional
import google.generativeai as genai
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

MUDIT_PROFILE = """
Name: Mudit Kumar
Email: muditkumar7011@gmail.com
Phone: +91 8533888088
LinkedIn: linkedin.com/in/mudit-dev
College: Dr APJ Abdul Kalam Technical University, Lucknow
Degree: B.Tech Computer Science Engineering
CGPA: 7.49
Graduation Year: 2024
Notice Period: Immediate joiner
Key Skills: Python, Node.js, TypeScript, REST APIs, MongoDB, Firebase, AWS, LLM APIs, n8n
Key Projects: FootPrints (cross-platform app with AI), Personal Finance Tracker (full-stack analytics)
Experience: Backend & DevOps at Nedzo AI (6 months), Backend Developer at Kushel Digi Solutions (3 months)
"""

STANDARD_ANSWERS = {
    "name": "Mudit Kumar",
    "email": "muditkumar7011@gmail.com",
    "phone": "+91 8533888088",
    "linkedin": "https://linkedin.com/in/mudit-dev",
    "college": "Dr APJ Abdul Kalam Technical University, Lucknow",
    "cgpa": "7.49",
    "graduation": "2024",
    "notice": "Immediate",
    "location": "Open to Gurugram/Noida/Bangalore/Remote",
}


def _extract_form_id(url: str) -> Optional[str]:
    match = re.search(r"/forms/d/e/([^/]+)/", url)
    return match.group(1) if match else None


def _build_submit_url(form_id: str) -> str:
    return f"https://docs.google.com/forms/d/e/{form_id}/formResponse"


def _resolve_url(url: str) -> str:
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        return r.url
    except Exception:
        return url


def _parse_form_fields(html: str) -> dict:
    """Extract {entry_id: question_label} from Google Form HTML."""
    soup = BeautifulSoup(html, "html.parser")
    fields = {}
    for script in soup.find_all("script"):
        if script.string and "FB_PUBLIC_LOAD_DATA_" in script.string:
            match = re.search(r"FB_PUBLIC_LOAD_DATA_ = (.+);", script.string, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    for item in data[1][1]:
                        if len(item) > 4 and item[4]:
                            entry_id = f"entry.{item[4][0][0]}"
                            fields[entry_id] = item[1]
                except (json.JSONDecodeError, IndexError, TypeError):
                    pass
    return fields


def _generate_answers(questions: list, role: str, jd_summary: str) -> dict:
    """Use Gemini to answer custom form questions based on Mudit's profile."""
    prompt = f"""Answer these job application questions for the role: {role}
Job requirements: {jd_summary}

Candidate profile:
{MUDIT_PROFILE}

Questions to answer:
{json.dumps(questions)}

Return ONLY a JSON object with question as key and answer as value.
Answers should be concise (2-4 sentences max), specific, and highlight relevant experience.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _match_standard_answer(label: str) -> Optional[str]:
    label_lower = label.lower()
    if any(k in label_lower for k in ["your name", "full name", "candidate name"]):
        return STANDARD_ANSWERS["name"]
    if "email" in label_lower:
        return STANDARD_ANSWERS["email"]
    if "phone" in label_lower or "mobile" in label_lower or "contact" in label_lower:
        return STANDARD_ANSWERS["phone"]
    if "linkedin" in label_lower:
        return STANDARD_ANSWERS["linkedin"]
    if "college" in label_lower or "university" in label_lower or "institution" in label_lower:
        return STANDARD_ANSWERS["college"]
    if "cgpa" in label_lower or "gpa" in label_lower or "percentage" in label_lower:
        return STANDARD_ANSWERS["cgpa"]
    if "graduation" in label_lower or "batch" in label_lower or "pass out" in label_lower:
        return STANDARD_ANSWERS["graduation"]
    if "notice" in label_lower or "joining" in label_lower or "available" in label_lower:
        return STANDARD_ANSWERS["notice"]
    if "current location" in label_lower or "preferred location" in label_lower:
        return STANDARD_ANSWERS["location"]
    return None


def fill_form(form_url: str, company: str, role: str, jd_summary: str, drive_pdf_link: str) -> bool:
    """Fill and submit a Google Form. Returns True on success."""
    resolved_url = _resolve_url(form_url)
    form_id = _extract_form_id(resolved_url)
    if not form_id:
        raise ValueError(f"Could not extract Google Form ID from: {resolved_url}")

    response = requests.get(resolved_url, timeout=10)
    fields = _parse_form_fields(response.text)
    if not fields:
        raise ValueError("No form fields found — form structure may have changed")

    custom_questions = [
        label for label in fields.values()
        if _match_standard_answer(label) is None
        and "resume" not in label.lower()
        and "cv" not in label.lower()
    ]

    gemini_answers = _generate_answers(custom_questions, role, jd_summary) if custom_questions else {}

    payload = {}
    for entry_id, label in fields.items():
        standard = _match_standard_answer(label)
        if standard:
            payload[entry_id] = standard
        elif "resume" in label.lower() or "cv" in label.lower():
            payload[entry_id] = drive_pdf_link
        elif label in gemini_answers:
            payload[entry_id] = gemini_answers[label]

    r = requests.post(_build_submit_url(form_id), data=payload, timeout=15)
    return r.status_code == 200
