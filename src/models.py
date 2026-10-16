from dataclasses import dataclass
from enum import Enum

class ApplyType(Enum):
    EMAIL = "email"
    FORM = "form"
    WEB_FORM = "web_form"
    LINKEDIN_EASY_APPLY = "linkedin_easy_apply"
    NAUKRI_APPLY = "naukri_apply"
    INTERNSHALA_APPLY = "internshala_apply"
    WELLFOUND_APPLY = "wellfound_apply"
    INDEED_APPLY = "indeed_apply"
    INSTAHYRE_APPLY = "instahyre_apply"
    UNKNOWN = "unknown"

@dataclass
class JobPosting:
    company: str
    role: str
    location: str
    jd_summary: str
    apply_type: ApplyType
    apply_target: str      # email address, Google Form URL, or ATS/web form URL
    is_relevant: bool = True
    salary: str = ""
    batch: str = ""
    raw_message: str = ""
    source: str = ""       # linkedin / naukri / indeed / wellfound / internshala
