import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional
from src.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD

# Everything personal (name, contact details, the pitch itself) comes from config/profile.json,
# so the same code sends your email for you and someone else's for them.
#   "email_pitch":        the body before the sign-off; {role}, {company} and {location} are filled in
#   "email_subject_note": a short tag after your name in the subject, e.g. "Immediate Joiner"


def _profile() -> dict:
    from src.profile import load_profile
    return load_profile().raw or {}


def _build_subject(company: str, role: str, profile: Optional[dict] = None) -> str:
    p = profile if profile is not None else _profile()
    note = p.get("email_subject_note")
    who = f"{p.get('name', '')} ({note})" if note else p.get("name", "")
    return f"Application for {role} – {company} | {who}".rstrip(" |")


def _default_pitch(p: dict) -> str:
    summary = (p.get("summary") or "").strip()
    return ("I'm applying for the {role} role at {company}." + (f" {summary}" if summary else "") +
            "\n\nPlease find my resume tailored for this role attached. I'd be glad to talk about it at your convenience.")


def _build_email_body(company: str, role: str, location: str, profile: Optional[dict] = None) -> str:
    p = profile if profile is not None else _profile()
    pitch = (p.get("email_pitch") or _default_pitch(p)).format(role=role, company=company, location=location or "")
    signature = "\n".join(x for x in (p.get("name"), p.get("phone"), p.get("email"), p.get("linkedin")) if x)
    return f"Hi,\n\n{pitch}\n\nBest regards,\n{signature}"


def _attachment_name(profile: dict) -> str:
    name = re.sub(r"[^A-Za-z0-9]+", "", (profile.get("name") or "").title()) or "Candidate"
    return f"{name}_Resume.pdf"


def send_email(to_address: str, company: str, role: str, location: str, pdf_path: str) -> None:
    profile = _profile()
    # Job posts often list several HR addresses in one string ("a@x.com, b@x.com").
    # SMTP rejects that as a single recipient (553), so split it.
    recipients = [a for a in re.split(r"[,;\s/]+", to_address) if "@" in a]
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = _build_subject(company, role, profile)
    msg.attach(MIMEText(_build_email_body(company, role, location, profile), "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{_attachment_name(profile)}"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())
