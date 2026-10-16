"""
Naukri.com job scraper using Playwright.
Searches jobs, extracts apply URLs (external ATS links or Naukri apply).
"""

import os
import time
import random
import logging
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from src.scrapers.base import ScrapedJob, is_blacklisted

log = logging.getLogger(__name__)
_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/naukri.json")


def _human_delay(min_s: float = 0.8, max_s: float = 2.0):
    time.sleep(random.uniform(min_s, max_s))


def _login(page: Page, email: str, password: str) -> bool:
    try:
        page.goto("https://www.naukri.com/nlogin/login", timeout=45000, wait_until="domcontentloaded")
        _human_delay(1.5, 2.5)

        page.fill("#usernameField", email)
        _human_delay()
        page.fill("#passwordField", password)
        _human_delay(0.5, 1.0)
        page.click('[type="submit"], button.loginButton')
        page.wait_for_url("**/mnjuser/**", timeout=20000)
        log.info("Naukri login successful")
        return True
    except Exception as e:
        log.error(f"Naukri login failed: {e}")
        return False


def _build_search_url(keyword: str, experience: int) -> str:
    keyword_slug = keyword.lower().replace(" ", "-")
    return f"https://www.naukri.com/{keyword_slug}-jobs?experience={experience}&jobAge=1"


def _extract_jobs(page: Page, blacklist: List[str]) -> List[ScrapedJob]:
    jobs = []
    try:
        page.wait_for_selector(".srp-jobtuple-wrapper, article.jobTuple", timeout=10000)
    except PWTimeout:
        return jobs

    cards = page.query_selector_all(".srp-jobtuple-wrapper, article.jobTuple")
    log.info(f"Naukri: found {len(cards)} job cards")

    for card in cards:
        try:
            title_el = card.query_selector("a.title, .jobTitle a")
            company_el = card.query_selector(".comp-name, .companyInfo a")
            location_el = card.query_selector(".locWdth, .location span")

            if not title_el:
                continue

            title = title_el.inner_text().strip()
            company = company_el.inner_text().strip() if company_el else "Unknown"
            location = location_el.inner_text().strip() if location_el else ""

            if is_blacklisted(title, blacklist):
                log.info(f"Naukri: blacklisted — {title}")
                continue

            job_url = title_el.get_attribute("href")
            if not job_url:
                continue
            if not job_url.startswith("http"):
                job_url = "https://www.naukri.com" + job_url

            # Open job page to get JD + apply URL
            with page.context.expect_page() as new_page_info:
                title_el.click()
            job_page = new_page_info.value
            job_page.wait_for_load_state("domcontentloaded", timeout=15000)
            _human_delay(1.0, 2.0)

            # Get JD
            jd_text = ""
            jd_el = job_page.query_selector(".job-desc, .JDC__dang-inner-html")
            if jd_el:
                jd_text = jd_el.inner_text().strip()[:3000]

            # Check for external apply link
            apply_url = job_url
            ext_apply = job_page.query_selector("a.apply-button[target='_blank'], a[data-ga-track*='apply']")
            if ext_apply:
                href = ext_apply.get_attribute("href")
                if href and href.startswith("http"):
                    apply_url = href

            job_page.close()

            jobs.append(ScrapedJob(
                title=title, company=company, location=location,
                apply_url=apply_url, jd_text=jd_text,
                source="naukri", easy_apply=False,
            ))
            log.info(f"Naukri: {title} @ {company}")
            _human_delay(0.5, 1.2)

        except Exception as e:
            log.warning(f"Naukri: card parse error — {e}")
            continue

    return jobs


def scrape_naukri(
    email: str = "",
    password: str = "",
    keywords: List[str] = [],
    experience: int = 1,
    blacklist: List[str] = [],
    max_jobs: int = 30,
) -> List[ScrapedJob]:
    all_jobs: List[ScrapedJob] = []
    seen_urls: set = set()

    session_file = os.path.abspath(_SESSION_FILE)
    session = session_file if os.path.exists(session_file) else None

    if not session:
        log.error("Naukri session not found. Run: python setup_sessions.py")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            storage_state=session,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        log.info("Naukri: loaded saved session")

        for keyword in keywords:
            if len(all_jobs) >= max_jobs:
                break

            url = _build_search_url(keyword, experience)
            log.info(f"Naukri scraping: {keyword}")
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            _human_delay(2.0, 3.0)

            jobs = _extract_jobs(page, blacklist)
            for job in jobs:
                if job.apply_url not in seen_urls and len(all_jobs) < max_jobs:
                    seen_urls.add(job.apply_url)
                    all_jobs.append(job)

            _human_delay(2.0, 3.5)

        browser.close()

    log.info(f"Naukri total scraped: {len(all_jobs)} jobs")
    return all_jobs
