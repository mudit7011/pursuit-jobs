"""
Internshala job scraper — Indian market, public listings, no login needed.
"""
import os, time, random, logging
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
from src.scrapers.base import ScrapedJob, is_blacklisted

log = logging.getLogger(__name__)
_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/internshala.json")

def _human_delay(a=0.8, b=2.0): time.sleep(random.uniform(a, b))

def _build_url(keyword: str) -> str:
    kw = keyword.lower().replace(" ", "-")
    return f"https://internshala.com/jobs/{kw}-jobs"


def _extract(page: Page, blacklist: List[str]) -> List[ScrapedJob]:
    jobs = []
    if "user_preference" in page.url:
        log.warning("Internshala wants you to confirm your preferences once — "
                    "run: python setup_sessions.py internshala, click Continue, then press Enter")
        return jobs
    try:
        page.wait_for_selector(".individual_internship, .job-internship-card", timeout=10000)
    except PWTimeout:
        log.warning(f"Internshala: no job cards found on {page.url} (layout may have changed)")
        return jobs

    cards = page.query_selector_all(".individual_internship, .job-internship-card")
    log.info(f"Internshala: {len(cards)} cards")

    for card in cards:
        try:
            title_el = card.query_selector(".job-title-href, .profile a, h3 a")
            company_el = card.query_selector(".company-name, .company_name")
            location_el = card.query_selector(".locations span, .location_link")

            if not title_el:
                continue

            title = title_el.inner_text().strip()
            # The company cell also holds badges like "Actively hiring" on later lines.
            company = company_el.inner_text().strip().split("\n")[0].strip() if company_el else "Unknown"
            location = location_el.inner_text().strip() if location_el else "India"

            if is_blacklisted(title, blacklist):
                log.info(f"Internshala: blacklisted — {title}")
                continue

            href = title_el.get_attribute("href") or ""
            if not href.startswith("http"):
                href = "https://internshala.com" + href

            # Get JD
            with page.context.expect_page() as np:
                title_el.click()
            job_page = np.value
            job_page.wait_for_load_state("domcontentloaded", timeout=15000)
            _human_delay(1.0, 2.0)

            jd_text = ""
            jd_el = job_page.query_selector("#about_job .internship_details, .about-section")
            if jd_el:
                jd_text = jd_el.inner_text().strip()[:3000]

            # Apply URL — Internshala has its own apply flow
            apply_url = href

            job_page.close()
            jobs.append(ScrapedJob(title=title, company=company, location=location,
                                   apply_url=apply_url, jd_text=jd_text, source="internshala"))
            log.info(f"Internshala: {title} @ {company}")
            _human_delay(0.5, 1.2)

        except Exception as e:
            log.warning(f"Internshala card error: {e}")

    return jobs


def scrape_internshala(keywords: List[str], blacklist: List[str] = [],
                       max_jobs: int = 30) -> List[ScrapedJob]:
    all_jobs, seen = [], set()
    session_file = os.path.abspath(_SESSION_FILE)
    session = session_file if os.path.exists(session_file) else None
    if not session:
        log.error("Internshala session not found. Run: python setup_sessions.py")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            storage_state=session,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        log.info("Internshala: loaded saved session")

        for kw in keywords:
            if len(all_jobs) >= max_jobs: break
            try:
                page.goto(_build_url(kw), timeout=45000, wait_until="domcontentloaded")
                _human_delay(2.0, 3.5)
                for job in _extract(page, blacklist):
                    if job.apply_url not in seen and len(all_jobs) < max_jobs:
                        seen.add(job.apply_url)
                        all_jobs.append(job)
            except Exception as e:
                log.warning(f"Internshala search failed for {kw}: {e}")
            _human_delay(2.0, 3.5)

        browser.close()
    log.info(f"Internshala total: {len(all_jobs)}")
    return all_jobs
