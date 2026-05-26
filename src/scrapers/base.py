from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScrapedJob:
    title: str
    company: str
    location: str
    apply_url: str
    jd_text: str = ""
    source: str = ""          # "linkedin", "naukri", "instahyre"
    easy_apply: bool = False  # platform's own apply flow


def is_blacklisted(title: str, blacklist: List[str]) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in blacklist)
