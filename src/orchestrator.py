import os
import logging
from datetime import datetime
from src.models import ApplyType, JobPosting
from src.applicators.linkedin_easy_apply import apply_linkedin_easy_apply
from src.resume_tailor import save_pdf
from src.drive_uploader import upload_pdf
from src.email_sender import send_email
from src.form_filler import fill_form
from src.web_form_filler import fill_web_form, CaptchaDetectedError, FormSubmitError
from src.notifier import notify_self, format_success, format_error
from src.config import OUTPUT_DIR, LOG_PATH
from src.profile import load_profile
from src.eligibility import check_eligibility
from src.tracker import is_duplicate, log_application

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# Load user profile once at startup
_profile = load_profile()


async def process_job(job: JobPosting) -> None:
    if not job.is_relevant:
        log.info("Skipping irrelevant message")
        return

    if job.apply_type == ApplyType.UNKNOWN or not job.apply_target:
        log.warning(f"Unknown apply method for {job.company} — {job.role}")
        return

    # Duplicate check
    if is_duplicate(job.company, job.role):
        log.info(f"Already applied to {job.role} at {job.company} — skipping")
        return

    # Eligibility check
    eligibility = check_eligibility(job, _profile)
    if not eligibility.eligible:
        log.info(f"Ineligible: {job.role} at {job.company} — {eligibility.reason}")
        log_application(
            company=job.company,
            role=job.role,
            apply_target=job.apply_target,
            apply_type=job.apply_type.value,
            status="skipped",
            skip_reason=eligibility.reason,
        )
        await notify_self(
            f"⏭ Skipped: {job.role} at {job.company}\nReason: {eligibility.reason}"
        )
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
            log.info(f"Google Form submitted: {job.apply_target}")

        elif job.apply_type == ApplyType.LINKEDIN_EASY_APPLY:
            success = apply_linkedin_easy_apply(
                apply_url=job.apply_target,
                company=job.company,
                role=job.role,
                jd_summary=job.jd_summary,
                pdf_path=pdf_path,
                profile=_profile,
            )
            if not success:
                raise Exception("LinkedIn Easy Apply did not reach submission")
            log.info(f"LinkedIn Easy Apply submitted: {job.apply_target}")

        elif job.apply_type == ApplyType.WEB_FORM:
            fill_web_form(
                url=job.apply_target,
                company=job.company,
                role=job.role,
                jd_summary=job.jd_summary,
                pdf_path=pdf_path,
                profile=_profile,
            )
            log.info(f"Web form submitted: {job.apply_target}")

    except CaptchaDetectedError as e:
        log.warning(str(e))
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason="CAPTCHA detected",
        )
        await notify_self(
            f"🔒 CAPTCHA on {job.role} at {job.company} — apply manually:\n{job.apply_target}"
        )
        return

    except FormSubmitError as e:
        log.warning(str(e))
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason="Submit button not found",
        )
        await notify_self(
            f"⚠️ Form submit failed for {job.role} at {job.company} — apply manually:\n{job.apply_target}"
        )
        return

    except Exception as e:
        log.error(f"Apply failed: {e}")
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason=str(e),
        )
        await notify_self(format_error(job.company, job.role, str(e)))
        return

    log_application(
        company=job.company, role=job.role,
        apply_target=job.apply_target, apply_type=job.apply_type.value,
        status="applied",
    )
    await notify_self(
        format_success(job.company, job.role, job.apply_type.value, job.apply_target)
    )
    log.info(f"Done: {job.company} — {job.role} at {datetime.now().isoformat()}")
