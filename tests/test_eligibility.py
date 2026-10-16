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
from src.profile import UserProfile
from src.eligibility import check_eligibility, EligibilityResult


def _make_profile(**overrides) -> UserProfile:
    defaults = dict(
        name="Mudit Kumar", email="m@m.com", phone="+91 999",
        linkedin="", github="", portfolio="",
        college="AKTU", degree="B.Tech", cgpa="7.49",
        graduation_year=2024, years_of_experience=2,
        current_ctc="0", expected_ctc="8 LPA",
        notice_period="Immediate", location_preference="Remote",
        work_authorization="Authorized to work in India",
        skills=["Python", "Node.js", "Firebase"],
        resume_pdf_path="templates/resume.pdf",
        summary="Backend dev.",
    )
    defaults.update(overrides)
    return UserProfile(**defaults)


def _make_job(**overrides) -> JobPosting:
    defaults = dict(
        company="Acme", role="SWE Intern", salary="", location="",
        jd_summary="Python backend development role",
        apply_type=ApplyType.EMAIL, apply_target="hr@acme.com",
        batch="", raw_message="", is_relevant=True,
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


def test_batch_mismatch_returns_ineligible():
    profile = _make_profile(graduation_year=2024)
    job = _make_job(batch="2026 passout only")
    result = check_eligibility(job, profile)
    assert result.eligible is False
    assert "batch" in result.reason.lower()


def test_batch_match_passes():
    profile = _make_profile(graduation_year=2024)
    job = _make_job(batch="2023/2024/2025")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 80, "reason": "Good match"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is True


def test_experience_mismatch_returns_ineligible():
    profile = _make_profile(years_of_experience=1)
    job = _make_job(jd_summary="Requires 3+ years of backend experience with Python")
    result = check_eligibility(job, profile)
    assert result.eligible is False
    assert "experience" in result.reason.lower()


def test_experience_match_passes():
    profile = _make_profile(years_of_experience=2)
    job = _make_job(jd_summary="1+ years of Python backend experience required")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 75, "reason": "Good skill match"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is True


def test_skills_mismatch_returns_ineligible():
    profile = _make_profile(skills=["Python", "Firebase"])
    job = _make_job(jd_summary="Java, Spring Boot, Kubernetes, Kafka, Scala required")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 10, "reason": "No Java experience"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is False
    assert "skills" in result.reason.lower()


def test_skills_check_skipped_if_gemini_fails():
    profile = _make_profile(graduation_year=2024, years_of_experience=2)
    job = _make_job(jd_summary="Python backend role for 2024 graduates")
    with patch("src.eligibility.model") as mock_model:
        mock_model.generate_content.side_effect = Exception("API error")
        result = check_eligibility(job, profile)
    # Defaults to eligible when skills check fails
    assert result.eligible is True


def test_no_batch_in_job_skips_batch_rule():
    profile = _make_profile(graduation_year=2024)
    job = _make_job(batch="")
    with patch("src.eligibility.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = '{"overlap_percent": 80, "reason": "Good match"}'
        mock_model.generate_content.return_value = mock_response
        result = check_eligibility(job, profile)
    assert result.eligible is True
