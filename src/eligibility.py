import re
import json
import os
import logging
import google.generativeai as genai
from dataclasses import dataclass
from src.models import JobPosting
from src.profile import UserProfile
from src.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")
log = logging.getLogger(__name__)

MOCK_GEMINI = os.getenv("MOCK_GEMINI", "false").lower() == "true"


@dataclass
class EligibilityResult:
    eligible: bool
    reason: str


def check_eligibility(job: JobPosting, profile: UserProfile) -> EligibilityResult:
    """
    Check whether the user is eligible to apply to this job.
    Runs batch and experience checks without LLM first (fast).
    Only calls Gemini for skills check if the first two rules pass.
    """
    # Rule 1: batch year check
    if job.batch:
        years_in_job = re.findall(r"\b(20\d{2})\b", job.batch)
        if years_in_job:
            allowed = [int(y) for y in years_in_job]
            if profile.graduation_year not in allowed:
                return EligibilityResult(
                    eligible=False,
                    reason=(
                        f"Batch mismatch — job requires {job.batch}, "
                        f"you are {profile.graduation_year} passout"
                    ),
                )

    # Rule 2: experience check
    exp_match = re.search(
        r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:\w+\s+){0,3}(?:experience|exp)\b",
        job.jd_summary,
        re.IGNORECASE,
    )
    if exp_match:
        required_exp = int(exp_match.group(1))
        if profile.years_of_experience < required_exp:
            return EligibilityResult(
                eligible=False,
                reason=(
                    f"Experience mismatch — job requires {required_exp}+ years, "
                    f"you have {profile.years_of_experience}"
                ),
            )

    # Rule 3: skills overlap via Gemini (skipped in mock mode)
    if MOCK_GEMINI:
        log.info("MOCK_GEMINI=true — skipping Gemini skills check, defaulting to 75% overlap")
        return EligibilityResult(eligible=True, reason="[MOCK] 75% skills overlap")

    prompt = f"""Given this job description and candidate skills, return ONLY a JSON object.

Job description: {job.jd_summary}
Candidate skills: {", ".join(profile.skills)}

Return exactly: {{"overlap_percent": <integer 0-100>, "reason": "<one sentence>"}}
overlap_percent is the percentage of required job skills the candidate has."""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
        overlap = int(result.get("overlap_percent", 100))
        if overlap < 40:
            return EligibilityResult(
                eligible=False,
                reason=(
                    f"Skills mismatch — only {overlap}% overlap: "
                    f"{result.get('reason', '')}"
                ),
            )
    except Exception as e:
        log.warning(f"Skills eligibility check failed, defaulting to eligible: {e}")

    return EligibilityResult(eligible=True, reason="")
