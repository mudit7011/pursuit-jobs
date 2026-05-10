import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from src.config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD


def _build_subject(company: str, role: str) -> str:
    return f"Application for {role} – {company} | Mudit Kumar (Immediate Joiner)"


def _build_email_body(company: str, role: str, location: str) -> str:
    return f"""Hi,

I'm applying for the {role} role at {company}. I'm a 2024 CS graduate with hands-on experience in backend systems, REST APIs, Python, and AI-assisted development workflows.

At Nedzo AI, I built and owned production-grade backend integrations and automation pipelines. At Kushel Digi Solutions, I optimized MongoDB queries improving performance by 40% and shipped features that reduced operational turnaround by 25%. I've also shipped two production apps — FootPrints (cross-platform with Gemini AI integrations) and a Personal Finance Tracker (full-stack with real-time analytics).

I'm immediately available and excited about this opportunity at {company} in {location}. Please find my tailored resume attached.

Happy to connect at your convenience.

Best regards,
Mudit Kumar
+91 8533888088
muditkumar7011@gmail.com
linkedin.com/in/mudit-dev"""


def send_email(to_address: str, company: str, role: str, location: str, pdf_path: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = _build_subject(company, role)
    msg.attach(MIMEText(_build_email_body(company, role, location), "plain"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", 'attachment; filename="MuditKumar_Resume.pdf"')
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())
