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


def load_profile(path: str = DEFAULT_PROFILE_PATH) -> UserProfile:
    """Load user profile from a JSON file and return a UserProfile dataclass."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")
    with open(path, "r") as f:
        data = json.load(f)
    return UserProfile(**data)
