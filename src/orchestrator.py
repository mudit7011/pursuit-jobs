import asyncio
import json
import os
import logging
import threading
from dataclasses import asdict
from datetime import datetime
from src.models import ApplyType, JobPosting
from src.applicators.linkedin_easy_apply import apply_linkedin_easy_apply
from src.applicators.naukri_apply import apply_naukri
from src.applicators.internshala_apply import apply_internshala
from src.applicators.wellfound_apply import apply_wellfound
from src.applicators.indeed_apply import apply_indeed
from src.applicators.instahyre_apply import apply_instahyre
from src.resume_tailor import save_pdf, tailor_pdf
from src import resume_library
from src.drive_uploader import upload_pdf
from src.email_sender import send_email
from src.ats.engine import LoginRequiredError, MissingAnswersError, apply_form
from src.web_form_filler import fill_web_form, CaptchaDetectedError, FormSubmitError
from src.notifier import notify_self, format_success, format_error
from src.config import OUTPUT_DIR, LOG_PATH
from src.profile import load_profile
from src.eligibility import check_eligibility
from src import sessions, tracker
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

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")
WORKER_POLL_SECONDS = 5

# Applicators that return False when they could not reach the submit step.
_PORTAL_APPLICATORS = {
    ApplyType.LINKEDIN_EASY_APPLY: ("LinkedIn Easy Apply", apply_linkedin_easy_apply),
    ApplyType.NAUKRI_APPLY: ("Naukri Apply", apply_naukri),
    ApplyType.INTERNSHALA_APPLY: ("Internshala Apply", apply_internshala),
    ApplyType.WELLFOUND_APPLY: ("Wellfound Apply", apply_wellfound),
    ApplyType.INDEED_APPLY: ("Indeed Apply", apply_indeed),
    ApplyType.INSTAHYRE_APPLY: ("Instahyre Apply", apply_instahyre),
}


class _ReasonCatcher(logging.Handler):
    """Keeps the last warning/error logged by the current thread.

    Applicators return False with the real reason only in the log ("Submit
    disabled", "external apply", "session expired"...). This surfaces it.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.thread = threading.get_ident()
        self.last = ""

    def emit(self, record: logging.LogRecord) -> None:
        if record.thread == self.thread:
            self.last = record.getMessage()


async def _notify(message: str) -> None:
    """Telegram is a side channel now — never let it break the pipeline."""
    try:
        await notify_self(message)
    except Exception as e:
        log.warning(f"Telegram notify failed: {e}")


def _job_from_row(row: dict) -> JobPosting:
    data = json.loads(row["payload"]) if row.get("payload") else {}
    data.setdefault("company", row["company"])
    data.setdefault("role", row["role"])
    data.setdefault("location", row.get("location") or "")
    data.setdefault("jd_summary", row.get("jd_summary") or "")
    data.setdefault("apply_target", row["apply_target"])
    data["apply_type"] = ApplyType(data.get("apply_type") or row["apply_type"])
    return JobPosting(**{k: v for k, v in data.items() if k in JobPosting.__dataclass_fields__})


async def process_job(job: JobPosting) -> None:
    """Triage a new job: dedupe, check eligibility, tailor resume, then queue it.

    Nothing is submitted here. In approval mode the job waits in the dashboard
    queue; in auto mode (or above the auto-approve fit threshold) it is queued
    as already approved and the worker picks it up.
    """
    if not job.is_relevant:
        log.info("Skipping irrelevant message")
        return

    if job.apply_type == ApplyType.UNKNOWN or not job.apply_target:
        log.warning(f"Unknown apply method for {job.company} — {job.role}")
        return

    if is_duplicate(job.company, job.role):
        log.info(f"Already queued/applied to {job.role} at {job.company} — skipping")
        return

    settings = tracker.get_settings()
    common = dict(
        location=job.location, source=job.source, jd_summary=job.jd_summary,
        payload={**asdict(job), "apply_type": job.apply_type.value},
    )

    eligibility = await asyncio.to_thread(check_eligibility, job, _profile, int(settings["min_fit"]))
    if not eligibility.eligible:
        log.info(f"Ineligible: {job.role} at {job.company} — {eligibility.reason}")
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="skipped", skip_reason=eligibility.reason,
            fit_score=eligibility.score, **common,
        )
        if settings["notify_skips"]:
            await _notify(f"⏭ Skipped: {job.role} at {job.company}\nReason: {eligibility.reason}")
        return

    log.info(f"Preparing: {job.role} at {job.company} ({job.apply_type.value})")

    safe_name = f"{job.company}_{job.role}".replace(" ", "_").replace("/", "-")
    pdf_path = os.path.join(OUTPUT_DIR, f"{safe_name}.pdf")

    try:
        choice = await asyncio.to_thread(
            resume_library.get_resume, job.company, job.role, job.jd_summary, pdf_path, tailor_pdf,
        )
        if choice.reused_from:
            log.info(f"Resume reused from {choice.reused_from} ({choice.coverage:.0%} skill match): {pdf_path}")
        else:
            log.info(f"Resume tailored: {pdf_path}")
    except Exception as e:
        log.error(f"Resume tailor failed: {e}")
        log_application(
            company=job.company, role=job.role,
            apply_target=job.apply_target, apply_type=job.apply_type.value,
            status="failed", skip_reason=f"Resume tailor: {e}",
            fit_score=eligibility.score, fit_reason=eligibility.reason, **common,
        )
        return

    threshold = int(settings["auto_approve_min_fit"] or 0)
    auto = settings["apply_mode"] == "auto" or (
        threshold > 0 and eligibility.score is not None and eligibility.score >= threshold
    )
    app_id = log_application(
        company=job.company, role=job.role,
        apply_target=job.apply_target, apply_type=job.apply_type.value,
        status="approved" if auto else "pending_approval",
        fit_score=eligibility.score, fit_reason=eligibility.reason, pdf_path=pdf_path,
        resume_source=(
            f"{choice.reused_from} ({choice.coverage:.0%} skill match)" if choice.reused_from else None
        ),
        **common,
    )
    if not auto:
        fit = f" · {eligibility.score}% fit" if eligibility.score is not None else ""
        await _notify(
            f"🆕 Ready for review: {job.role} at {job.company}{fit}\n{DASHBOARD_URL}/queue?id={app_id}"
        )


def _submit(job: JobPosting, pdf_path: str, assist: bool = False):
    catcher = _ReasonCatcher()
    root = logging.getLogger()
    root.addHandler(catcher)
    try:
        return _submit_inner(job, pdf_path, assist)
    except (CaptchaDetectedError, FormSubmitError, MissingAnswersError, LoginRequiredError):
        raise
    except Exception as e:
        if catcher.last and catcher.last not in str(e):
            raise Exception(f"{e}: {catcher.last}") from e
        raise
    finally:
        root.removeHandler(catcher)


def _submit_inner(job: JobPosting, pdf_path: str, assist: bool = False):
    """Blocking submit. Runs in a worker thread: the applicators use sync Playwright,
    which refuses to run inside the asyncio event loop."""
    if job.apply_type == ApplyType.EMAIL:
        send_email(job.apply_target, job.company, job.role, job.location, pdf_path)
        log.info(f"Email sent to {job.apply_target}")

    elif job.apply_type == ApplyType.FORM:
        # Google Forms: filled in a logged-in browser. Text questions asking for a resume
        # link get a Drive link; upload questions get the PDF itself.
        safe_name = os.path.splitext(os.path.basename(pdf_path))[0]
        try:
            drive_link = upload_pdf(pdf_path, f"{_profile.name.replace(' ', '')}_{safe_name}.pdf")
        except Exception as e:
            log.warning(f"Drive upload failed (continuing): {e}")
            drive_link = ""
        report = apply_form(job.apply_target, job.company, job.role, job.jd_summary, pdf_path, _profile,
                            resume_link=drive_link, assist=assist)
        log.info(f"Google Form submitted: {job.apply_target}")
        return report

    elif job.apply_type in _PORTAL_APPLICATORS:
        label, apply_fn = _PORTAL_APPLICATORS[job.apply_type]
        success = apply_fn(
            apply_url=job.apply_target, company=job.company, role=job.role,
            jd_summary=job.jd_summary, pdf_path=pdf_path, profile=_profile,
        )
        if not success:
            raise Exception(f"{label} did not reach submission")
        log.info(f"{label} submitted: {job.apply_target}")

    elif job.apply_type == ApplyType.WEB_FORM:
        # Greenhouse, Lever, Ashby, Microsoft/Zoho Forms, Keka, and a generic fallback.
        report = apply_form(job.apply_target, job.company, job.role, job.jd_summary, pdf_path, _profile,
                            assist=assist)
        log.info(f"Web form submitted via {report.adapter}: {job.apply_target}")
        return report

    else:
        raise Exception(f"No applicator for {job.apply_type.value}")


async def execute_application(row: dict) -> None:
    """Submit one approved application and record the outcome."""
    app_id = row["id"]
    job = _job_from_row(row)
    if row.get("assist"):
        tracker.clear_assist(app_id)  # one-shot: a later retry runs unattended again
    pdf_path = row.get("pdf_path") or ""
    if not pdf_path or not os.path.exists(pdf_path):
        pdf_path = os.path.join(OUTPUT_DIR, os.path.basename(pdf_path or f"{job.company}_{job.role}.pdf"))
        await asyncio.to_thread(save_pdf, job.company, job.role, job.jd_summary, pdf_path)

    try:
        report = await asyncio.to_thread(_submit, job, pdf_path, bool(row.get("assist")))
    except CaptchaDetectedError as e:
        log.warning(str(e))
        tracker.set_status(app_id, "failed", "CAPTCHA detected")
        await _notify(f"🔒 CAPTCHA on {job.role} at {job.company} — apply manually:\n{job.apply_target}")
        return
    except MissingAnswersError as e:
        log.info(f"Needs answers for {job.company}: {e.questions}")
        if e.report:
            tracker.set_answers_used(app_id, e.report.filled)
        tracker.set_missing_questions(app_id, e.questions)
        tracker.set_status(app_id, "failed", str(e))
        await _notify(f"✍️ {job.company} asks {len(e.questions)} thing(s) only you know — answer once in the dashboard:\n{DASHBOARD_URL}/attention")
        return
    except LoginRequiredError as e:
        tracker.set_status(app_id, "failed", str(e))
        return
    except FormSubmitError as e:
        log.warning(str(e))
        tracker.set_status(app_id, "failed", str(e) or "Submit button not found")
        await _notify(f"⚠️ Form submit failed for {job.role} at {job.company} — apply manually:\n{job.apply_target}")
        return
    except Exception as e:
        log.error(f"Apply failed: {e}")
        tracker.set_status(app_id, "failed", str(e))
        await _notify(format_error(job.company, job.role, str(e)))
        return

    if report is not None and getattr(report, "filled", None):
        tracker.set_answers_used(app_id, report.filled)
    tracker.set_status(app_id, "applied")
    await _notify(format_success(job.company, job.role, job.apply_type.value, job.apply_target))
    log.info(f"Done: {job.company} — {job.role} at {datetime.now().isoformat()}")


async def approval_worker() -> None:
    """Submits approved applications one at a time, at a human-ish pace."""
    recovered = tracker.recover_interrupted()
    if recovered:
        log.warning(f"{recovered} application(s) were interrupted mid-apply — flagged for review")
    while True:
        tracker.set_setting("bot_heartbeat", datetime.now().isoformat(timespec="seconds"))
        row = None
        try:
            # Hold platforms that hit today's cap or whose login expired; they stay queued.
            held = set(tracker.capped_apply_types()) | {
                tracker.PLATFORM_APPLY_TYPES[p] for p in sessions.logged_out_platforms()
            }
            row = tracker.claim_next_approved(skip_types=tuple(held))
            if row:
                log.info(f"Applying (approved): {row['role']} at {row['company']}")
                await execute_application(row)
        except Exception as e:
            log.error(f"Approval worker error: {e}")
            if row:
                tracker.set_status(row["id"], "failed", f"Worker error: {e}")
        await asyncio.sleep(WORKER_POLL_SECONDS if not row else 20)
