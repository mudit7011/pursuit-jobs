import os
import logging
from datetime import datetime
from src.models import ApplyType, JobPosting
from src.resume_tailor import save_pdf
from src.drive_uploader import upload_pdf
from src.email_sender import send_email
from src.form_filler import fill_form
from src.notifier import notify_self, format_success, format_error
from src.config import OUTPUT_DIR, LOG_PATH

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


async def process_job(job: JobPosting) -> None:
    if not job.is_relevant:
        log.info("Skipping irrelevant message")
        return
    if job.apply_type == ApplyType.UNKNOWN or not job.apply_target:
        log.warning(f"Unknown apply method for {job.company} — {job.role}")
        return

    log.info(f"Processing: {job.role} at {job.company} ({job.apply_type.value})")

    safe_name = f"{job.company}_{job.role}".replace(" ", "_").replace("/", "-")
    pdf_path = os.path.join(OUTPUT_DIR, f"{safe_name}.pdf")

    try:
        save_pdf(job.company, job.role, job.jd_summary, pdf_path)
        log.info(f"Resume compiled: {pdf_path}")
    except Exception as e:
        log.error(f"Resume tailor failed: {e}")
        await notify_self(format_error(job.company, job.role, f"Resume tailor: {e}"))
        return

    drive_link = ""
    try:
        drive_link = upload_pdf(pdf_path, f"MuditKumar_{safe_name}.pdf")
        log.info(f"PDF uploaded to Drive: {drive_link}")
    except Exception as e:
        log.warning(f"Drive upload failed (continuing): {e}")
        drive_link = "https://linkedin.com/in/mudit-dev"

    try:
        if job.apply_type == ApplyType.EMAIL:
            send_email(job.apply_target, job.company, job.role, job.location, pdf_path)
            log.info(f"Email sent to {job.apply_target}")
        elif job.apply_type == ApplyType.FORM:
            fill_form(job.apply_target, job.company, job.role, job.jd_summary, drive_link)
            log.info(f"Form submitted: {job.apply_target}")
    except Exception as e:
        log.error(f"Apply failed: {e}")
        await notify_self(format_error(job.company, job.role, str(e)))
        return

    await notify_self(format_success(job.company, job.role, job.apply_type.value, job.apply_target))
    log.info(f"Done: {job.company} — {job.role} at {datetime.now().isoformat()}")
