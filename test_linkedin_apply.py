"""
Test LinkedIn Easy Apply on a single job URL.

Usage:
    python test_linkedin_apply.py                    # auto-find job, dry run
    DRY_RUN=false python test_linkedin_apply.py      # auto-find job, actually apply
    TEST_URL="https://www.linkedin.com/jobs/view/..." python test_linkedin_apply.py  # specific job
"""
import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.profile import load_profile
from src.applicators.linkedin_easy_apply import apply_linkedin_easy_apply

TEST_URL  = os.getenv("TEST_URL", "")
COMPANY   = os.getenv("TEST_COMPANY", "")
ROLE      = os.getenv("TEST_ROLE", "Software Engineer")
JD_SUMMARY = "Software Engineer role requiring Python/Node.js backend development skills."

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"

PDF_PATH = "output/MuditKumar_resume.pdf"
if not os.path.exists(PDF_PATH):
    import glob
    pdfs = glob.glob("output/*.pdf")
    PDF_PATH = pdfs[0] if pdfs else ""

if not TEST_URL:
    print("\nNo TEST_URL set. Finding a LinkedIn Easy Apply job automatically...\n")
    import time
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            storage_state="sessions/linkedin.json",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        page.goto(
            "https://www.linkedin.com/jobs/search/?f_AL=true&f_E=1%2C2&keywords=software%20engineer&location=India",
            timeout=30000
        )
        time.sleep(5)
        cards = page.query_selector_all(".job-card-container, .jobs-search-results__list-item")
        found = []
        for c in cards[:20]:
            title_el   = c.query_selector(".job-card-list__title, .job-card-container__link")
            company_el = c.query_selector(".job-card-container__primary-description, .job-card-container__company-name")
            easy_badge = c.query_selector("[aria-label*='Easy Apply'], .job-card-container__apply-method")
            if title_el and easy_badge:
                href = title_el.get_attribute("href") or ""
                if href and "/jobs/view/" in href:
                    url = ("https://www.linkedin.com" + href.split("?")[0]
                           if href.startswith("/") else href.split("?")[0])
                    found.append({
                        "title":   title_el.inner_text().strip(),
                        "company": company_el.inner_text().strip() if company_el else "",
                        "url":     url,
                    })
        browser.close()
        if found:
            job = found[0]
            TEST_URL = job["url"]
            COMPANY  = job["company"] or "Unknown Company"
            ROLE     = job["title"] or ROLE
            print(f"Found: {ROLE} @ {COMPANY}")
            print(f"URL:   {TEST_URL}\n")
        else:
            print("Could not auto-find a LinkedIn Easy Apply job.")
            print("Set TEST_URL manually:")
            print('  TEST_URL="https://www.linkedin.com/jobs/view/..." python test_linkedin_apply.py')
            exit(1)

profile = load_profile()

print(f"\n{'='*55}")
print(f"  LinkedIn Easy Apply Test")
print(f"  Job  : {ROLE} @ {COMPANY}")
print(f"  URL  : {TEST_URL}")
print(f"  Mode : {'DRY RUN (no Submit)' if DRY_RUN else '⚠️  LIVE — will actually apply!'}")
print(f"{'='*55}\n")

result = apply_linkedin_easy_apply(
    apply_url=TEST_URL,
    company=COMPANY,
    role=ROLE,
    jd_summary=JD_SUMMARY,
    pdf_path=PDF_PATH,
    profile=profile,
    dry_run=DRY_RUN,
)

print(f"\nResult: {'✅ SUCCESS' if result else '❌ FAILED'}")
if DRY_RUN and result:
    print("(Dry run — application was NOT submitted)")
