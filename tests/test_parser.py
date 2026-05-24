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
from src.models import JobPosting, ApplyType
from src.parser import parse_job_message, _build_prompt

def test_build_prompt_contains_message():
    msg = "Company - TestCo\nRole - SWE Intern"
    prompt = _build_prompt(msg)
    assert "TestCo" in prompt
    assert "SWE Intern" in prompt

def test_parse_email_job():
    sample_response = '''{
        "company": "Instamart",
        "role": "Data Analyst",
        "salary": "₹50,000 - ₹90,000/month",
        "location": "Gurgaon",
        "jd_summary": "Data analysis, reports, SQL, Python",
        "apply_type": "email",
        "apply_target": "kunalranjan2k14@gmail.com",
        "batch": "2023/2024/2025",
        "is_relevant": true
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("some message text")
    assert isinstance(result, JobPosting)
    assert result.company == "Instamart"
    assert result.apply_type == ApplyType.EMAIL
    assert result.apply_target == "kunalranjan2k14@gmail.com"

def test_parse_form_job():
    sample_response = '''{
        "company": "Aspire",
        "role": "Software Engineering Intern",
        "salary": "₹40,000/month",
        "location": "Gurugram",
        "jd_summary": "Backend, APIs, AI tools, Python",
        "apply_type": "form",
        "apply_target": "https://people-jobs.com/aspire/apply/software-engineering-intern",
        "batch": "2024/2025/2026",
        "is_relevant": true
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("some message text")
    assert result.apply_type == ApplyType.WEB_FORM
    assert "aspire" in result.apply_target

def test_parse_irrelevant_message():
    sample_response = '''{
        "company": "",
        "role": "",
        "salary": "",
        "location": "",
        "jd_summary": "",
        "apply_type": "unknown",
        "apply_target": "",
        "batch": "",
        "is_relevant": false
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("Good morning everyone!")
    assert result.is_relevant is False

from src.parser import _is_web_form

def test_is_web_form_greenhouse():
    assert _is_web_form("https://boards.greenhouse.io/company/jobs/123456") is True

def test_is_web_form_lever():
    assert _is_web_form("https://jobs.lever.co/company/abc123/apply") is True

def test_is_web_form_workday():
    assert _is_web_form("https://company.wd5.myworkdayjobs.com/en-US/jobs") is True

def test_is_web_form_ashby():
    assert _is_web_form("https://jobs.ashbyhq.com/company/role/apply") is True

def test_is_web_form_microsoft_forms():
    assert _is_web_form("https://forms.office.com/r/abc123") is True

def test_is_web_form_bamboohr():
    assert _is_web_form("https://company.bamboohr.com/jobs/view.php?id=123") is True

def test_is_web_form_email_is_not_web_form():
    assert _is_web_form("hr@company.com") is False

def test_is_web_form_google_form_is_not_web_form():
    assert _is_web_form("https://docs.google.com/forms/d/e/abc123/viewform") is False

def test_is_web_form_empty_string_is_not_web_form():
    assert _is_web_form("") is False

def test_parse_greenhouse_url_returns_web_form():
    sample_response = '''{
        "company": "Acme",
        "role": "Backend Engineer",
        "salary": "",
        "location": "Remote",
        "jd_summary": "Python backend role",
        "apply_type": "form",
        "apply_target": "https://boards.greenhouse.io/acme/jobs/7654321",
        "batch": "",
        "is_relevant": true
    }'''
    with patch("src.parser.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = sample_response
        mock_model.generate_content.return_value = mock_response
        result = parse_job_message("some job posting text")
    assert result.apply_type == ApplyType.WEB_FORM
    assert "greenhouse" in result.apply_target
