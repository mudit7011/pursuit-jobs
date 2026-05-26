"""
Test Wellfound Apply on a single job URL.

Usage:
    python test_wellfound_apply.py          # dry run
    DRY_RUN=false python test_wellfound_apply.py   # actually apply
"""
import os
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.profile import load_profile
from src.applicators.wellfound_apply import apply_wellfound

TEST_URL = "https://wellfound.com/jobs/4261034-monday-com-software-engineer"
COMPANY  = "Xohani Solutions"
ROLE     = "Monday.com Software Engineer"
JD_SUMMARY = "Software Engineer role at Xohani Solutions working with Monday.com platform integrations and customizations."

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"

PDF_PATH = "output/MuditKumar_resume.pdf"
if not os.path.exists(PDF_PATH):
    import glob
    pdfs = glob.glob("output/*.pdf")
    PDF_PATH = pdfs[0] if pdfs else ""

profile = load_profile()

print(f"\n{'='*55}")
print(f"  Wellfound Apply Test")
print(f"  Job  : {ROLE} @ {COMPANY}")
print(f"  URL  : {TEST_URL}")
print(f"  Mode : {'DRY RUN (no Submit)' if DRY_RUN else '⚠️  LIVE — will actually apply!'}")
print(f"{'='*55}\n")

result = apply_wellfound(
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
