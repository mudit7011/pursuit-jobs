import os
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "fakehash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", "fakesession")
os.environ.setdefault("TELEGRAM_GROUP_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_SELF_ID", "999999")
os.environ.setdefault("GEMINI_API_KEY", "fakekey")
os.environ.setdefault("GMAIL_ADDRESS", "fake@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "fakepassword")

import pytest
from unittest.mock import patch, MagicMock
from src.web_form_filler import (
    _check_captcha_in_content,
    _generate_answers,
    CaptchaDetectedError,
    FormSubmitError,
)
from src.profile import UserProfile


def _make_profile() -> UserProfile:
    return UserProfile(
        name="Mudit Kumar", email="m@m.com", phone="+91 999",
        linkedin="https://linkedin.com/in/mudit-dev", github="", portfolio="",
        college="AKTU", degree="B.Tech", cgpa="7.49",
        graduation_year=2024, years_of_experience=2,
        current_ctc="0", expected_ctc="8 LPA",
        notice_period="Immediate", location_preference="Remote",
        work_authorization="Authorized to work in India",
        skills=["Python", "Node.js", "Firebase"],
        resume_pdf_path="templates/resume.pdf",
        summary="Backend dev with 2 years of experience.",
    )


def test_captcha_detection_positive():
    content = "<html><div class='g-recaptcha'>Please verify</div></html>"
    assert _check_captcha_in_content(content) is True


def test_captcha_detection_hcaptcha():
    content = "<html><script src='hcaptcha.com/api.js'></script></html>"
    assert _check_captcha_in_content(content) is True


def test_captcha_detection_negative():
    content = "<html><form><input type='text' name='email'></form></html>"
    assert _check_captcha_in_content(content) is False


def test_generate_answers_returns_dict():
    profile = _make_profile()
    fields = [
        {"id": "name_field", "label": "Full Name", "type": "text", "name": "name_field"},
        {"id": "email_field", "label": "Email Address", "type": "email", "name": "email_field"},
    ]
    mock_response = MagicMock()
    mock_response.text = '{"name_field": "Mudit Kumar", "email_field": "m@m.com"}'
    with patch("src.web_form_filler.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        answers = _generate_answers(fields, profile, "Python backend role", "Acme", "SWE")
    assert answers["name_field"] == "Mudit Kumar"
    assert answers["email_field"] == "m@m.com"


def test_generate_answers_strips_markdown_fences():
    profile = _make_profile()
    fields = [{"id": "f1", "label": "Name", "type": "text", "name": "f1"}]
    mock_response = MagicMock()
    mock_response.text = '```json\n{"f1": "Mudit Kumar"}\n```'
    with patch("src.web_form_filler.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        answers = _generate_answers(fields, profile, "role desc", "Co", "Role")
    assert answers["f1"] == "Mudit Kumar"


def test_captcha_detected_error_is_exception():
    with pytest.raises(CaptchaDetectedError):
        raise CaptchaDetectedError("CAPTCHA found")


def test_form_submit_error_is_exception():
    with pytest.raises(FormSubmitError):
        raise FormSubmitError("Submit button not found")
