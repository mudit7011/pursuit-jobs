"""
LinkedIn job scraper using Playwright.
Searches for jobs, returns external apply URLs for the existing form filler.
LinkedIn Easy Apply jobs are handled separately via fill_linkedin_easy_apply().
"""

import os
import time
import random
import logging
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from src.scrapers.base import ScrapedJob, is_blacklisted

log = logging.getLogger(__name__)

_LINKEDIN_BASE  = "https://www.linkedin.com"
_SESSION_FILE   = os.path.join(os.path.dirname(__file__), "../../sessions/linkedin.json")


def _human_delay(min_s: float = 0.8, max_s: float = 2.2):
    time.sleep(random.uniform(min_s, max_s))


def _login(page: Page, email: str, password: str) -> bool:
    try:
        page.goto("https://www.linkedin.com/login", timeout=30000)
        page.fill("#username", email)
        _human_delay()
        page.fill("#password", password)
        _human_delay(0.5, 1.0)
        page.click('[type="submit"]')
        page.wait_for_url("**/feed/**", timeout=20000)
        log.info("LinkedIn login successful")
        return True
    except Exception as e:
        log.error(f"LinkedIn login failed: {e}")
        return False


def _build_search_url(keyword: str, location: str, exp_min: int, exp_max: int) -> str:
    # experience levels: 1=Internship, 2=Entry, 3=Associate, 4=Mid-Senior, 5=Director, 6=Executive
    exp_levels = []
    if exp_min == 0 and exp_max <= 1:
        exp_levels = ["1", "2"]
    elif exp_max <= 3:
        exp_levels = ["2", "3"]
    else:
        exp_levels = ["2", "3", "4"]

    f_E = "%2C".join(exp_levels)
    keyword_enc = keyword.replace(" ", "%20")
    location_enc = location.replace(" ", "%20")

    return (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={keyword_enc}&location={location_enc}"
        f"&f_E={f_E}&f_TPR=r86400&sortBy=DD"  # last 24h, sorted by date
    )


def _extract_jobs_from_page(page: Page, blacklist: List[str]) -> List[ScrapedJob]:
    jobs = []
    try:
        page.wait_for_selector("li.scaffold-layout__list-item, .job-card-container", timeout=10000)
    except PWTimeout:
        return jobs

    # Collect all job links from the list panel first
    job_links = page.eval_on_selector_all(
        "a.job-card-list__title--link, a.job-card-container__link",
        "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
    )
    log.info(f"LinkedIn: found {len(job_links)} job links on page")

    for item in job_links:
        href = item.get("href", "")
        title_raw = item.get("text", "")
        if not href or not title_raw:
            continue

        title = title_raw.split("\n")[0].strip()
        if is_blacklisted(title, blacklist):
            log.info(f"LinkedIn: blacklisted — {title}")
            continue

        try:
            # Navigate to each job page directly
            page.goto(href, timeout=20000)
            _human_delay(1.5, 2.5)

            # Extract company + location from page title "Role | Company | LinkedIn"
            company = ""
            location = ""
            page_title = page.title()
            parts = [p.strip() for p in page_title.split("|")]
            if len(parts) >= 2:
                company = parts[1]  # "Python Developer | Xceedance | LinkedIn"

            # Location from meta or visible text
            loc_el = page.query_selector("span.tvm__text:first-child, .job-details-jobs-unified-top-card__bullet")
            if loc_el:
                location = loc_el.inner_text().strip()

            # JD text
            jd_text = ""
            jd_el = page.query_selector(".jobs-description__content, .show-more-less-html__markup")
            if jd_el:
                jd_text = jd_el.inner_text().strip()[:3000]

            # Easy Apply is an <a> tag with aria-label on LinkedIn
            easy_apply_el = page.query_selector(
                "a[aria-label*='Easy Apply'], "
                "a[href*='/apply?openSNUIApply']"
            )
            external_apply_el = page.query_selector(
                "a[aria-label*='Apply on company website'], "
                "a[data-tracking-control-name*='external_apply']"
            )

            if easy_apply_el:
                apply_url = easy_apply_el.get_attribute("href") or page.url
                if not apply_url.startswith("http"):
                    apply_url = "https://www.linkedin.com" + apply_url
                jobs.append(ScrapedJob(
                    title=title, company=company, location=location,
                    apply_url=apply_url, jd_text=jd_text,
                    source="linkedin", easy_apply=True,
                ))
                log.info(f"LinkedIn Easy Apply: {title} @ {company}")

            elif external_apply_el:
                external_url = external_apply_el.get_attribute("href") or page.url
                jobs.append(ScrapedJob(
                    title=title, company=company, location=location,
                    apply_url=external_url, jd_text=jd_text,
                    source="linkedin", easy_apply=False,
                ))
                log.info(f"LinkedIn external: {title} @ {company} → {external_url}")

            else:
                log.warning(f"LinkedIn: no apply element found for {title} — skipping")

        except Exception as e:
            log.warning(f"LinkedIn: error on {title} — {e}")
            continue

    return jobs


def scrape_linkedin(
    email: str = "",
    password: str = "",
    keywords: List[str] = [],
    locations: List[str] = [],
    experience_min: int = 0,
    experience_max: int = 3,
    blacklist: List[str] = [],
    max_jobs: int = 30,
) -> List[ScrapedJob]:
    all_jobs: List[ScrapedJob] = []
    seen_urls: set = set()

    session_file = os.path.abspath(_SESSION_FILE)
    session = session_file if os.path.exists(session_file) else None

    if not session:
        log.error("LinkedIn session not found. Run: python setup_sessions.py")
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
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        log.info("LinkedIn: loaded saved session")

        for keyword in keywords:
            if len(all_jobs) >= max_jobs:
                break
            for location in locations:
                if len(all_jobs) >= max_jobs:
                    break

                url = _build_search_url(keyword, location, experience_min, experience_max)
                log.info(f"LinkedIn scraping: {keyword} in {location}")
                page.goto(url, timeout=30000)
                _human_delay(2.0, 3.5)

                jobs = _extract_jobs_from_page(page, blacklist)
                for job in jobs:
                    if job.apply_url not in seen_urls:
                        seen_urls.add(job.apply_url)
                        all_jobs.append(job)

                _human_delay(2.0, 4.0)

        browser.close()

    log.info(f"LinkedIn total scraped: {len(all_jobs)} jobs")
    return all_jobs


def fill_linkedin_easy_apply(
    page: Page,
    job_url: str,
    profile,
    pdf_path: str,
) -> bool:
    """
    Handle LinkedIn Easy Apply multi-step form.
    Returns True if submitted successfully.
    """
    try:
        page.goto(job_url, timeout=30000)
        _human_delay(1.5, 2.5)

        apply_btn = page.wait_for_selector(".jobs-apply-button--top-card", timeout=8000)
        apply_btn.click()
        _human_delay(1.0, 1.5)

        # Loop through easy apply modal steps
        for step in range(10):
            # Upload resume if file input visible
            file_input = page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(pdf_path)
                _human_delay()

            # Fill text inputs with profile data
            inputs = page.query_selector_all("input[type='text'], input[type='email'], input[type='tel']")
            for inp in inputs:
                label_el = page.query_selector(f"label[for='{inp.get_attribute('id')}']")
                label = label_el.inner_text().lower() if label_el else ""
                val = ""
                if "phone" in label or "mobile" in label:
                    val = profile.phone
                elif "email" in label:
                    val = profile.email
                elif "name" in label and "first" in label:
                    val = profile.name.split()[0]
                elif "name" in label and "last" in label:
                    val = profile.name.split()[-1]
                elif "linkedin" in label:
                    val = profile.linkedin
                elif "city" in label or "location" in label:
                    val = "Delhi"
                elif "experience" in label or "years" in label:
                    val = str(profile.years_of_experience)

                if val:
                    inp.fill("")
                    inp.fill(val)
                    _human_delay(0.2, 0.5)

            # Next / Submit button
            next_btn = page.query_selector("button[aria-label='Continue to next step'], button[aria-label='Submit application']")
            if not next_btn:
                next_btn = page.query_selector("button.artdeco-button--primary")

            if next_btn:
                btn_text = next_btn.inner_text().lower()
                next_btn.click()
                _human_delay(1.0, 2.0)
                if "submit" in btn_text:
                    log.info("LinkedIn Easy Apply submitted")
                    return True
            else:
                break

        return False

    except Exception as e:
        log.error(f"LinkedIn Easy Apply failed: {e}")
        return False
