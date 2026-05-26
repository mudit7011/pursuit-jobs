import json
import os
from dataclasses import dataclass
from typing import List

DEFAULT_PROFILE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "profile.json"
)


@dataclass
class UserProfile:
    name: str
    email: str
    phone: str
    linkedin: str
    github: str
    portfolio: str
    college: str
    degree: str
    cgpa: str
    graduation_year: int
    years_of_experience: int
    current_ctc: str
    expected_ctc: str
    notice_period: str
    location_preference: str
    work_authorization: str
    skills: List[str]
    resume_pdf_path: str
    summary: str
    raw: dict = None  # full JSON for extra fields like job_search config


def load_profile(path: str = DEFAULT_PROFILE_PATH) -> UserProfile:
    """Load user profile from a JSON file and return a UserProfile dataclass."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path, "r") as f:
        data = json.load(f)
    known_fields = {f for f in UserProfile.__dataclass_fields__ if f != "raw"}
    profile_data = {k: v for k, v in data.items() if k in known_fields}
    profile = UserProfile(**profile_data)
    profile.raw = data
    return profile
