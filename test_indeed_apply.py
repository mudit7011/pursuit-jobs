"""
Test Indeed Apply on a single job URL.

Usage:
    python test_indeed_apply.py          # dry run
    DRY_RUN=false python test_indeed_apply.py   # actually apply
"""
import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.profile import load_profile
from src.applicators.indeed_apply import apply_indeed

# Indeed "Apply with Indeed" job URL
TEST_URL  = os.getenv("TEST_URL", "https://in.indeed.com/viewjob?jk=63ccbffcded95ad7")
COMPANY   = os.getenv("TEST_COMPANY", "Apex Star Technologies")
ROLE      = os.getenv("TEST_ROLE", "Python Backend Developer")
JD_SUMMARY = "Software Engineer role requiring Python/Node.js backend development skills."

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"

PDF_PATH = "output/MuditKumar_resume.pdf"
if not os.path.exists(PDF_PATH):
    import glob
    pdfs = glob.glob("output/*.pdf")
    PDF_PATH = pdfs[0] if pdfs else ""

profile = load_profile()

print(f"\n{'='*55}")
print(f"  Indeed Apply Test")
print(f"  Job  : {ROLE} @ {COMPANY}")
print(f"  URL  : {TEST_URL}")
print(f"  Mode : {'DRY RUN (no Submit)' if DRY_RUN else '⚠️  LIVE — will actually apply!'}")
print(f"{'='*55}\n")

result = apply_indeed(
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
