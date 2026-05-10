import os
os.environ.setdefault("TELEGRAM_API_ID", "12345")
os.environ.setdefault("TELEGRAM_API_HASH", "fakehash")
os.environ.setdefault("TELEGRAM_SESSION_STRING", "fakesession")
os.environ.setdefault("TELEGRAM_GROUP_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_SELF_ID", "999999")
os.environ.setdefault("GEMINI_API_KEY", "fakekey")
os.environ.setdefault("GMAIL_ADDRESS", "fake@gmail.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "fakepassword")

from src.form_filler import _extract_form_id, _build_submit_url, _generate_answers

def test_extract_form_id_from_url():
    url = "https://docs.google.com/forms/d/e/1FAIpQLSexample123/viewform"
    form_id = _extract_form_id(url)
    assert form_id == "1FAIpQLSexample123"

def test_extract_form_id_from_short_url():
    # people-jobs.com style redirect - returns None, handled in fill_form
    url = "https://people-jobs.com/aspire/apply/software-engineering-intern-abc123"
    form_id = _extract_form_id(url)
    assert form_id is None

def test_build_submit_url():
    form_id = "1FAIpQLSexample123"
    url = _build_submit_url(form_id)
    assert url == "https://docs.google.com/forms/d/e/1FAIpQLSexample123/formResponse"

def test_generate_answers_returns_dict():
    from unittest.mock import patch, MagicMock
    mock_response = MagicMock()
    mock_response.text = '{"Why refer you": "Strong backend skills", "What have you built": "FootPrints app"}'
    with patch("src.form_filler.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        answers = _generate_answers(
            ["Why refer you", "What have you built"],
            "Aspire SWE Intern", "Backend, APIs, Python"
        )
    assert "Why refer you" in answers
    assert "FootPrints" in answers["What have you built"]
