"""
Test LinkedIn Easy Apply on a single job URL.

Usage:
    python test_linkedin_apply.py                    # auto-find job, dry run
    DRY_RUN=false python test_linkedin_apply.py      # auto-find job, actually apply
    TEST_URL="https://www.linkedin.com/jobs/view/..." python test_linkedin_apply.py
"""
import os
import glob
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.profile import load_profile
from src.applicators.linkedin_easy_apply import apply_linkedin_easy_apply
from src.resume_tailor import save_pdf

TEST_URL   = os.getenv("TEST_URL", "")
COMPANY    = os.getenv("TEST_COMPANY", "")
ROLE       = os.getenv("TEST_ROLE", "Software Engineer")
JD_SUMMARY = "Software Engineer role requiring Python/Node.js backend development skills."

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"

PDF_PATH = "output/MuditKumar_resume.pdf"
if not os.path.exists(PDF_PATH):
    pdfs = glob.glob("output/*.pdf")
    PDF_PATH = pdfs[0] if pdfs else ""

if not TEST_URL:
    print("\nNo TEST_URL set. Finding a LinkedIn Easy Apply job based on your profile...\n")
    import time
    from playwright.sync_api import sync_playwright

    _profile_for_search = load_profile()
    _job_cfg   = _profile_for_search.raw.get("job_search", {})
    _keywords  = _job_cfg.get("keywords", ["Backend Developer", "Python Developer"])
    _blacklist = [k.lower() for k in _job_cfg.get("blacklist_keywords", [])]

    # Try each keyword until we find a fresh Easy Apply job
    found = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            storage_state="sessions/linkedin.json",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        page = ctx.new_page()

        for kw in _keywords:
            kw_enc = kw.replace(" ", "%20")
            page.goto(
                f"https://www.linkedin.com/jobs/search/?f_AL=true&f_E=1%2C2&f_TPR=r7200"
                f"&sortBy=DD&keywords={kw_enc}&location=India",
                timeout=30000
            )
            time.sleep(5)

            jobs = page.evaluate("""() => {
                const jobs = [];
                document.querySelectorAll('a[href*="/jobs/view/"]').forEach(a => {
                    const card = a.closest('li');
                    if (!card) return;
                    if (!card.innerText.includes('Easy Apply')) return;
                    const title = a.innerText.trim();
                    if (!title || title.length < 3) return;
                    const url = a.href.split('?')[0];
                    const companyEl = card.querySelector(
                        '.job-card-container__primary-description, .artdeco-entity-lockup__subtitle'
                    );
                    jobs.push({ title, company: companyEl ? companyEl.innerText.trim() : '', url });
                });
                const seen = new Set();
                return jobs.filter(j => { if (seen.has(j.url)) return false; seen.add(j.url); return true; });
            }""")

            # Filter out blacklisted titles
            for j in jobs:
                t = j["title"].lower()
                if any(bl in t for bl in _blacklist):
                    continue
                found.append(j)

            if found:
                print(f"Found {len(found)} jobs for keyword: {kw}")
                break

        browser.close()

    if found:
        job = found[0]
        TEST_URL = job["url"]
        COMPANY  = job["company"] or "Unknown Company"
        ROLE     = job["title"] or ROLE
        print(f"Picked: {ROLE} @ {COMPANY}")
        print(f"URL:    {TEST_URL}\n")
    else:
        print("Could not auto-find a LinkedIn Easy Apply job.")
        print("Set TEST_URL manually:")
        print('  TEST_URL="https://www.linkedin.com/jobs/view/..." python test_linkedin_apply.py')
        exit(1)

profile = load_profile()

# Generate JD-tailored resume before applying
safe_name = f"{COMPANY}_{ROLE}".replace(" ", "_").replace("/", "-")
tailored_pdf = f"output/LinkedIn_{safe_name}.pdf"
print(f"Generating tailored resume for {ROLE} @ {COMPANY}...")
try:
    save_pdf(COMPANY, ROLE, JD_SUMMARY, tailored_pdf)
    PDF_PATH = tailored_pdf
    print(f"Resume ready: {PDF_PATH}\n")
except Exception as e:
    print(f"Resume tailor failed ({e}), using fallback: {PDF_PATH}\n")

print(f"\n{'='*55}")
print(f"  LinkedIn Easy Apply Test")
print(f"  Job  : {ROLE} @ {COMPANY}")
print(f"  URL  : {TEST_URL}")
print(f"  Resume: {PDF_PATH}")
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
