"""
Test Naukri Apply on a single job URL.

Usage:
    python test_naukri_apply.py          # dry run
    DRY_RUN=false python test_naukri_apply.py   # actually apply
"""
import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.profile import load_profile
from src.applicators.naukri_apply import apply_naukri

# Find a Naukri job via: https://www.naukri.com/software-engineer-jobs
# Naukri job URL — override with TEST_URL env var for a specific job
TEST_URL  = os.getenv("TEST_URL", "https://www.naukri.com/job-listings-software-developer-acciojob-noida-hyderabad-pune-0-to-5-years-260526033178")
COMPANY   = os.getenv("TEST_COMPANY", "Acciojob")
ROLE      = os.getenv("TEST_ROLE", "Software Developer")
JD_SUMMARY = "Software Engineer role requiring Python/Node.js backend development skills."

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"

PDF_PATH = "output/MuditKumar_resume.pdf"
if not os.path.exists(PDF_PATH):
    import glob
    pdfs = glob.glob("output/*.pdf")
    PDF_PATH = pdfs[0] if pdfs else ""

if not TEST_URL:
    print("\nNo TEST_URL set. Finding a Naukri job automatically...\n")
    import time
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            storage_state="sessions/naukri.json",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()
        page.goto("https://www.naukri.com/software-developer-jobs?experience=0&jobAge=1", timeout=30000)
        time.sleep(6)
        cards = page.query_selector_all(".srp-jobtuple-wrapper, article.jobTuple")
        found = []
        for c in cards[:10]:
            a  = c.query_selector("a.title, .jobTitle a")
            co = c.query_selector(".comp-name, .companyInfo a")
            if a:
                href = a.get_attribute("href")
                if href:
                    found.append({
                        "title":   a.inner_text().strip(),
                        "company": co.inner_text().strip() if co else "",
                        "url":     href,
                    })
        browser.close()
        if found:
            c = found[0]
            TEST_URL = c["url"]
            COMPANY  = c["company"] or COMPANY
            ROLE     = c["title"]   or ROLE
            print(f"Found: {ROLE} @ {COMPANY}")
            print(f"URL:   {TEST_URL}\n")
        else:
            print("Could not auto-find a Naukri job. Set TEST_URL env var manually.")
            exit(1)

profile = load_profile()

print(f"\n{'='*55}")
print(f"  Naukri Apply Test")
print(f"  Job  : {ROLE} @ {COMPANY}")
print(f"  URL  : {TEST_URL}")
print(f"  Mode : {'DRY RUN (no Submit)' if DRY_RUN else '⚠️  LIVE — will actually apply!'}")
print(f"{'='*55}\n")

result = apply_naukri(
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
