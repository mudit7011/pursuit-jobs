import json
import re
import google.generativeai as genai
from src.config import GEMINI_API_KEY
from src.models import JobPosting, ApplyType

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

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
  "apply_target": "email address or Google Form URL or empty string",
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
    apply_type_map = {
        "email": ApplyType.EMAIL,
        "form": ApplyType.FORM,
    }
    return JobPosting(
        company=data.get("company", ""),
        role=data.get("role", ""),
        salary=data.get("salary", ""),
        location=data.get("location", ""),
        jd_summary=data.get("jd_summary", ""),
        apply_type=apply_type_map.get(data.get("apply_type", "unknown"), ApplyType.UNKNOWN),
        apply_target=data.get("apply_target", ""),
        batch=data.get("batch", ""),
        raw_message=message,
        is_relevant=data.get("is_relevant", False),
    )
