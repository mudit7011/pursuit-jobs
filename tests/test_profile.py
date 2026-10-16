import json
import pytest
from src.profile import load_profile, UserProfile

def test_load_profile_returns_userprofile(tmp_path):
    profile_data = {
        "name": "Test User",
        "email": "test@example.com",
        "phone": "+91 9999999999",
        "linkedin": "https://linkedin.com/in/test",
        "github": "",
        "portfolio": "",
        "college": "Test University",
        "degree": "B.Tech",
        "cgpa": "8.0",
        "graduation_year": 2024,
        "years_of_experience": 2,
        "current_ctc": "0",
        "expected_ctc": "8 LPA",
        "notice_period": "Immediate",
        "location_preference": "Remote",
        "work_authorization": "Authorized to work in India",
        "skills": ["Python", "Node.js"],
        "resume_pdf_path": "templates/resume.pdf",
        "summary": "A backend developer."
    }
    profile_file = tmp_path / "profile.json"
    profile_file.write_text(json.dumps(profile_data))

    profile = load_profile(str(profile_file))

    assert isinstance(profile, UserProfile)
    assert profile.name == "Test User"
    assert profile.graduation_year == 2024
    assert profile.years_of_experience == 2
    assert "Python" in profile.skills

def test_load_profile_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_profile("/nonexistent/path/profile.json")
