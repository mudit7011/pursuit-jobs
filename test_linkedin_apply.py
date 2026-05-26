"""
Test LinkedIn Easy Apply on a single job URL.

Usage:
    # Dry run (fills everything, does NOT click Submit):
    python test_linkedin_apply.py

    # Actually apply:
    DRY_RUN=false python test_linkedin_apply.py
"""
import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.profile import load_profile
from src.applicators.linkedin_easy_apply import apply_linkedin_easy_apply

# ── Paste a real LinkedIn Easy Apply URL here ─────────────────────────────
# Format: https://www.linkedin.com/jobs/view/<job_id>/apply/?openSDUIApplyFlow=true...
# OR just:  https://www.linkedin.com/jobs/view/<job_id>/
TEST_URL = "https://www.linkedin.com/jobs/view/4419144105/apply/?openSDUIApplyFlow=true"  # Software Engineer @ Eurofins

# ── Job details (matching what scraper would provide) ─────────────────────
COMPANY    = "Eurofins"
ROLE       = "Software Engineer"
JD_SUMMARY = "Software Engineer role at Eurofins. Backend development, Python, REST APIs, database management."

# ── dry_run=True = fills all fields but stops before Submit ───────────────
DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"

# ── Resume PDF path ───────────────────────────────────────────────────────
PDF_PATH = "output/MuditKumar_resume.pdf"
if not os.path.exists(PDF_PATH):
    # Try to find any PDF in output/
    import glob
    pdfs = glob.glob("output/*.pdf")
    PDF_PATH = pdfs[0] if pdfs else ""
    if not PDF_PATH:
        print("WARNING: No resume PDF found in output/ — file upload will be skipped")
        PDF_PATH = ""

# ─────────────────────────────────────────────────────────────────────────

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
