"""
Indeed job scraper — no login needed, public listings.
"""
import os, time, random, logging
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
from src.scrapers.base import ScrapedJob, is_blacklisted

log = logging.getLogger(__name__)
_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/indeed.json")

def _human_delay(a=0.8, b=2.0): time.sleep(random.uniform(a, b))

def _build_url(keyword: str, location: str, exp_max: int) -> str:
    kw = keyword.replace(" ", "+")
    loc = location.replace(" ", "+")
    # jt=fulltime, explvl=entry_level, fromage=1 (last 1 day)
    return (
        f"https://in.indeed.com/jobs?q={kw}&l={loc}"
        f"&jt=fulltime&fromage=1&sort=date"
    )

def _extract(page: Page, blacklist: List[str]) -> List[ScrapedJob]:
    jobs = []
    try:
        page.wait_for_selector(".job_seen_beacon, .tapItem", timeout=10000)
    except PWTimeout:
        return jobs

    # Collect ALL card data as plain dicts BEFORE navigating away.
    # ElementHandles go stale after page.goto(), so we extract everything in one JS call.
    raw_cards = page.eval_on_selector_all(
        ".job_seen_beacon, .tapItem",
        """els => els.map(el => {
            const titleEl = el.querySelector(
                'h2.jobTitle span[title], h2.jobTitle a span, h2.jobTitle span');
            const companyEl = el.querySelector(
                '[data-testid="company-name"], .companyName');
            const locationEl = el.querySelector(
                '[data-testid="text-location"], .companyLocation');
            const linkEl = el.querySelector('h2.jobTitle a, a.jcs-JobTitle');
            return {
                title:    titleEl   ? titleEl.innerText.trim()   : '',
                company:  companyEl ? companyEl.innerText.trim() : 'Unknown',
                location: locationEl? locationEl.innerText.trim(): '',
                href:     linkEl    ? linkEl.href                : ''
            };
        })"""
    )
    log.info(f"Indeed: {len(raw_cards)} cards found")

    for card in raw_cards:
        title    = card.get("title", "").strip()
        company  = card.get("company", "Unknown").strip()
        location = card.get("location", "").strip()
        href     = card.get("href", "").strip()

        if not title or not href:
            continue
        if is_blacklisted(title, blacklist):
            log.info(f"Indeed: blacklisted — {title}")
            continue
        if not href.startswith("http"):
            href = "https://in.indeed.com" + href

        try:
            search_url = page.url
            page.goto(href, timeout=20000)
            _human_delay(1.0, 2.0)

            jd_text = ""
            jd_el = page.query_selector("#jobDescriptionText, .jobsearch-jobDescriptionText")
            if jd_el:
                jd_text = jd_el.inner_text().strip()[:3000]

            jobs.append(ScrapedJob(title=title, company=company, location=location,
                                   apply_url=href, jd_text=jd_text, source="indeed"))
            log.info(f"Indeed: {title} @ {company}")

            page.goto(search_url, timeout=20000)
            _human_delay(1.5, 2.5)

        except Exception as e:
            log.warning(f"Indeed job page error: {e}")

    return jobs


def scrape_indeed(keywords: List[str], locations: List[str],
                  experience_max: int = 3, blacklist: List[str] = [],
                  max_jobs: int = 30) -> List[ScrapedJob]:
    all_jobs, seen = [], set()
    session_file = os.path.abspath(_SESSION_FILE)
    session = session_file if os.path.exists(session_file) else None
    if not session:
        log.error("Indeed session not found. Run: python setup_sessions.py")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
                                    args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            storage_state=session,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        log.info("Indeed: loaded saved session")

        for kw in keywords:
            for loc in locations:
                if len(all_jobs) >= max_jobs: break
                url = _build_url(kw, loc, experience_max)
                log.info(f"Indeed: {kw} in {loc}")
                try:
                    page.goto(url, timeout=30000)
                    _human_delay(2.0, 3.5)
                    for job in _extract(page, blacklist):
                        if job.apply_url not in seen and len(all_jobs) < max_jobs:
                            seen.add(job.apply_url)
                            all_jobs.append(job)
                except Exception as e:
                    log.warning(f"Indeed search failed: {e}")
                _human_delay(2.0, 4.0)

        browser.close()
    log.info(f"Indeed total: {len(all_jobs)}")
    return all_jobs
