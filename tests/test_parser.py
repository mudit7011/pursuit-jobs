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
    assert result.apply_type == ApplyType.FORM
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
