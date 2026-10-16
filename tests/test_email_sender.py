import os
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "fakehash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", "fakesession")
os.environ.setdefault("TELEGRAM_GROUP_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_SELF_ID", "999999")
os.environ.setdefault("GEMINI_API_KEY", "fakekey")
os.environ.setdefault("GMAIL_ADDRESS", "fake@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "fakepassword")

from src.email_sender import _attachment_name, _build_email_body, _build_subject

PROFILE = {"name": "Asha Rao", "phone": "+91 90000 00000", "email": "asha@example.com",
           "linkedin": "linkedin.com/in/asha", "summary": "I build backend services in Python."}


def test_subject_contains_company_role_and_name():
    subject = _build_subject("Instamart", "Data Analyst", PROFILE)
    assert "Instamart" in subject and "Data Analyst" in subject and "Asha Rao" in subject


def test_subject_note_is_optional():
    assert _build_subject("Acme", "SDE", {**PROFILE, "email_subject_note": "Immediate Joiner"}).endswith("(Immediate Joiner)")


def test_default_body_uses_profile_not_hardcoded_details():
    body = _build_email_body("Instamart", "Data Analyst", "Gurgaon", PROFILE)
    assert "Instamart" in body and "Data Analyst" in body
    assert "I build backend services in Python." in body
    assert body.rstrip().endswith("Asha Rao\n+91 90000 00000\nasha@example.com\nlinkedin.com/in/asha")


def test_custom_pitch_fills_placeholders():
    body = _build_email_body("Acme", "SDE 1", "Pune", {**PROFILE, "email_pitch": "Applying to {company} for {role} in {location}."})
    assert "Applying to Acme for SDE 1 in Pune." in body


def test_attachment_named_after_candidate():
    assert _attachment_name(PROFILE) == "AshaRao_Resume.pdf"
