"""
Wellfound (AngelList Talent) job scraper.
Search returns company cards — we visit each company's /jobs page and
extract individual job listings from there.
"""
import os, time, random, logging
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
from src.scrapers.base import ScrapedJob, is_blacklisted

# ── Title relevance filter (same logic as job_crawler) ───────────────────────
_RELEVANT = {
    "software engineer", "software developer", "swe", "sde",
    "backend engineer", "backend developer", "backend dev",
    "frontend engineer", "frontend developer",
    "fullstack", "full stack", "full-stack",
    "node.js", "nodejs", "python developer", "python engineer",
    "api developer", "api engineer", "web developer", "web engineer",
    "typescript", "javascript developer",
    "ai engineer", "ml engineer", "llm engineer",
    "platform engineer", "devops engineer",
    "application developer", "application engineer",
    "engineer", "developer",
}
_IRRELEVANT = {
    "analyst", "business analyst", "data analyst", "product analyst",
    "project manager", "program manager", "scrum master",
    "qa engineer", "qa automation", "quality assurance", "test engineer",
    "automation tester", "automation engineer", "performance test",
    "sap", "oracle", "salesforce", "snowflake", "informatica",
    "hr ", "recruiter", "talent acquisition",
    "designer", "ux", "ui designer", "graphic",
    "content writer", "technical writer",
    "finance", "accountant", "chartered",
    "consultant", "visio", "monday.com",
    "data governance", "capital markets", "asset management",
    "banking domain", "loan iq", "pl/sql", "idq", "cdq",
    "snaplogic", "architect",  # data/solution architects not target
}

def _is_relevant(title: str) -> bool:
    t = title.lower()
    if any(kw in t for kw in _IRRELEVANT):
        return False
    return any(kw in t for kw in _RELEVANT)

log = logging.getLogger(__name__)
_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/wellfound.json")

_STEALTH_JS = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin',  filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1 },
            { name: 'Chrome PDF Viewer',  filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1 },
            { name: 'Native Client',      filename: 'internal-nacl-plugin', description: '', length: 2 },
        ]
    });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    try {
        const origQuery = window.navigator.permissions.query.bind(navigator.permissions);
        window.navigator.permissions.query = (p) =>
            p.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : origQuery(p);
    } catch(_) {}
"""


def _human_delay(a=0.8, b=2.0): time.sleep(random.uniform(a, b))


def _build_search_url(keyword: str, location: str = "") -> str:
    import urllib.parse
    kw = urllib.parse.quote(keyword)
    base = f"https://wellfound.com/jobs?q={kw}"
    if location:
        base += f"&locations[]={urllib.parse.quote(location)}"
    return base


def _get_company_slugs(page: Page, max_slugs: int = 20) -> List[str]:
    """Extract company slugs from the search results page, scrolling to load more."""
    try:
        page.wait_for_selector(
            "[data-test='StartupResult'], a[href*='/company/']", timeout=12000)
    except PWTimeout:
        return []

    # Scroll down multiple times to load more results (infinite scroll / lazy load)
    for _ in range(5):
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        _human_delay(1.2, 2.0)

    def _extract():
        return page.eval_on_selector_all(
            "a[href*='/company/']",
            """els => {
                const seen = new Set();
                return els
                    .map(e => {
                        const m = e.href.match(/\\/company\\/([^\\/\\?#]+)/);
                        return m ? m[1] : null;
                    })
                    .filter(s => {
                        if (!s || seen.has(s)) return false;
                        const NAV = new Set(['settings','profile','people','culture','jobs','home','applications','messages','saved','hidden']);
                        if (NAV.has(s)) return false;
                        // Must contain a hyphen or digit — real company slugs do
                        if (!/[-0-9]/.test(s)) return false;
                        seen.add(s);
                        return true;
                    });
            }"""
        )

    slugs = _extract()
    random.shuffle(slugs)   # randomise so we don't always hit the same top companies
    log.info(f"Wellfound: {len(slugs)} company slugs from search")
    return slugs[:max_slugs]


def _jobs_from_company(page: Page, slug: str, blacklist: List[str]) -> List[ScrapedJob]:
    """Visit /company/<slug>/jobs and return ScrapedJob list."""
    jobs = []
    url = f"https://wellfound.com/company/{slug}/jobs"
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        _human_delay(1.5, 2.5)
    except Exception as e:
        log.warning(f"Wellfound: failed to load {url} — {e}")
        return jobs

    # Check for bot detection page
    page_text = page.evaluate("() => document.body ? document.body.innerText : ''")
    if "access is temporarily restricted" in page_text.lower():
        log.warning("Wellfound: bot detection on company page — skipping (refresh session via setup_sessions.py)")
        return jobs

    # Extract company name from page (strip "Jobs at " prefix if present)
    company = slug.replace("-", " ").title()
    co_el = page.query_selector("h1, [data-test='startup-name'], .styles_name__")
    if co_el:
        raw = co_el.inner_text().strip().split("\n")[0]
        company = raw.removeprefix("Jobs at ").strip() or raw

    # Job cards on the company jobs page
    try:
        page.wait_for_selector(
            "[data-test='JobListing'], .styles_jobListing__, "
            "[class*='JobListing'], article, .job-listing", timeout=8000)
    except PWTimeout:
        pass

    raw_jobs = page.eval_on_selector_all(
        "[data-test='JobListing'], [class*='jobListing'], [class*='JobListing'], article",
        """els => els.map(el => {
            const titleEl = el.querySelector('h2, h3, [class*="title"], a');
            const locationEl = el.querySelector('[class*="location"], [class*="Location"]');
            const link = el.querySelector('a[href]');
            return {
                title:    titleEl   ? titleEl.innerText.trim().split('\\n')[0]  : '',
                location: locationEl? locationEl.innerText.trim()               : '',
                href:     link      ? link.href                                 : ''
            };
        })"""
    )

    if not raw_jobs:
        # Fallback: grab all job-titled links on the company jobs page
        raw_jobs = page.eval_on_selector_all(
            "a[href*='/jobs/']",
            """els => {
                const seen = new Set();
                return els
                    .filter(e => {
                        const path = new URL(e.href).pathname;
                        // individual job: /jobs/<id>-<slug>
                        return /^\\/jobs\\/[a-z0-9]+-[a-z0-9-]+$/.test(path);
                    })
                    .map(e => ({title: e.innerText.trim().split('\\n')[0], href: e.href, location: ''}))
                    .filter(item => {
                        if (seen.has(item.href) || !item.title || item.title.length < 3) return false;
                        seen.add(item.href);
                        return true;
                    });
            }"""
        )

    log.info(f"Wellfound: {len(raw_jobs)} jobs at {company}")

    for item in raw_jobs:
        title    = item.get("title", "").strip()
        location = item.get("location", "Remote").strip() or "Remote"
        href     = item.get("href", "").strip()

        if not title or len(title) < 3:
            continue
        if is_blacklisted(title, blacklist):
            log.info(f"Wellfound: blacklisted — {title}")
            continue
        # Skip irrelevant titles BEFORE opening the detail page (saves time)
        if not _is_relevant(title):
            log.info(f"Wellfound: skipping irrelevant — {title}")
            continue
        if not href:
            href = url  # fallback to company jobs page

        # Get title + JD from job detail page
        jd_text = ""
        try:
            with page.context.expect_page() as np:
                page.evaluate(f"window.open('{href}')")
            job_page = np.value
            job_page.wait_for_load_state("domcontentloaded", timeout=15000)
            _human_delay(1.0, 2.0)

            # Prefer page h1/h2 as the definitive job title
            title_page_el = job_page.query_selector(
                "h1, h2, [data-test='job-title'], [class*='jobTitle'], [class*='JobTitle']")
            if title_page_el:
                candidate = title_page_el.inner_text().strip().split("\n")[0]
                # Strip " at <company>" suffix Wellfound appends in page titles
                if " at " in candidate:
                    candidate = candidate[:candidate.rfind(" at ")].strip()
                # Only override if it looks like a real title (not all-caps single word)
                if candidate and not (candidate.isupper() and len(candidate.split()) <= 2):
                    title = candidate

            jd_el = job_page.query_selector(
                ".prose, [data-test='job-description'], "
                "[class*='description'], [class*='Description'], .content")
            if jd_el:
                jd_text = jd_el.inner_text().strip()[:3000]
            job_page.close()
        except Exception as e:
            log.warning(f"Wellfound: JD fetch error for '{title}' — {e}")

        # Last resort: derive title from URL slug (e.g. /jobs/123-ai-backend-engineer)
        if not title or title.isupper():
            slug_part = href.rstrip("/").split("/")[-1]
            title = " ".join(w.capitalize() for w in slug_part.split("-")[1:]) or slug_part

        # Final relevance check after title is confirmed from detail page
        if not _is_relevant(title):
            log.info(f"Wellfound: skipping irrelevant (final) — {title}")
            continue

        jobs.append(ScrapedJob(
            title=title, company=company, location=location,
            apply_url=href, jd_text=jd_text,
            source="wellfound", easy_apply=True,
        ))
        log.info(f"Wellfound: {title} @ {company}")
        _human_delay(0.5, 1.2)

    return jobs


def scrape_wellfound(keywords: List[str], blacklist: List[str] = [],
                     locations: List[str] = ["India", "Remote"],
                     max_jobs: int = 30) -> List[ScrapedJob]:
    all_jobs, seen = [], set()
    session_file = os.path.abspath(_SESSION_FILE)
    session = session_file if os.path.exists(session_file) else None
    if not session:
        log.error("Wellfound session not found. Run: python setup_sessions.py")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        ctx = browser.new_context(
            storage_state=session,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        ctx.add_init_script(_STEALTH_JS)
        page = ctx.new_page()
        log.info("Wellfound: loaded saved session")

        search_combos = [(kw, loc) for kw in keywords for loc in (locations or [""])]
        for kw, loc in search_combos:
            if len(all_jobs) >= max_jobs: break
            try:
                page.goto(_build_search_url(kw, loc), timeout=45000, wait_until="domcontentloaded")
                _human_delay(2.0, 3.0)

                slugs = _get_company_slugs(page)
                for slug in slugs[:10]:  # max 10 companies per keyword
                    if len(all_jobs) >= max_jobs: break
                    for job in _jobs_from_company(page, slug, blacklist):
                        if job.apply_url not in seen and len(all_jobs) < max_jobs:
                            seen.add(job.apply_url)
                            all_jobs.append(job)
                    _human_delay(1.0, 2.0)

            except Exception as e:
                log.warning(f"Wellfound: search failed for '{kw}' — {e}")
            _human_delay(2.0, 3.5)

        browser.close()
    log.info(f"Wellfound total: {len(all_jobs)}")
    return all_jobs
