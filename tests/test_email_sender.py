import os
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "fakehash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", "fakesession")
os.environ.setdefault("TELEGRAM_GROUP_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_SELF_ID", "999999")
os.environ.setdefault("GEMINI_API_KEY", "fakekey")
os.environ.setdefault("GMAIL_ADDRESS", "fake@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "fakepassword")

from src.email_sender import _build_email_body, _build_subject

def test_subject_contains_company_and_role():
    subject = _build_subject("Instamart", "Data Analyst")
    assert "Instamart" in subject
    assert "Data Analyst" in subject

def test_email_body_contains_key_info():
    body = _build_email_body("Instamart", "Data Analyst", "Gurgaon")
    assert "Instamart" in body
    assert "Data Analyst" in body
    assert "Mudit Kumar" in body
    assert "8533888088" in body
    assert "muditkumar7011@gmail.com" in body
