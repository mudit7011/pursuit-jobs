from dataclasses import dataclass
from enum import Enum

class ApplyType(Enum):
    EMAIL = "email"
    FORM = "form"
    WEB_FORM = "web_form"
    UNKNOWN = "unknown"

@dataclass
class JobPosting:
    company: str
    role: str
    salary: str
    location: str
    jd_summary: str
    apply_type: ApplyType
    apply_target: str      # email address, Google Form URL, or ATS/web form URL
    batch: str
    raw_message: str
    is_relevant: bool = True
