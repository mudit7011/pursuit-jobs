import os

import pytest

import src.tracker as tracker
from src import resume_library as lib

PY_BACKEND_JD = "We need Python, FastAPI, PostgreSQL, Docker and AWS. REST APIs, Redis a plus."


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", str(tmp_path / "apps.db"))
    return tmp_path


def _fake_tailor(calls, ok=True):
    def tailor(company, role, jd, out):
        calls.append(company)
        with open(out, "wb") as f:
            f.write(f"resume for {company}".encode())
        return ok
    return tailor


def test_role_family():
    assert lib.role_family("Backend Developer") == "backend"
    assert lib.role_family("Full Stack Engineer (MERN)") == "fullstack"
    assert lib.role_family("ML Engineer") == "ai-ml"
    assert lib.role_family("SDE 1") == "swe"


def test_extract_skills_handles_aliases():
    s = lib.extract_skills("Node.js, nodejs, Postgres, k8s, golang developer, C++ and JavaScript")
    assert {"node.js", "postgresql", "kubernetes", "go", "c++", "javascript"} <= s
    assert "java" not in s  # "JavaScript" must not count as Java


def test_similar_job_reuses_resume_under_new_name(db):
    calls = []
    first = lib.get_resume("Acme", "Backend Developer", PY_BACKEND_JD, str(db / "Acme.pdf"), _fake_tailor(calls))
    second = lib.get_resume("Beta", "Python Backend Engineer",
                            "Python, FastAPI, Postgres, Docker on AWS", str(db / "Beta.pdf"), _fake_tailor(calls))
    assert calls == ["Acme"]                      # tailored once
    assert first.reused_from is None
    assert second.reused_from == "Acme · Backend Developer"
    assert os.path.exists(db / "Beta.pdf")       # copied under the new job's name
    assert open(db / "Beta.pdf", "rb").read() == b"resume for Acme"
    assert lib.stats() == {"tailored": 1, "reused": 1}


def test_different_stack_gets_new_resume(db):
    calls = []
    lib.get_resume("Acme", "Backend Developer", PY_BACKEND_JD, str(db / "A.pdf"), _fake_tailor(calls))
    r = lib.get_resume("Gamma", "Backend Developer", "Java, Spring Boot, Kafka, MySQL, Kubernetes",
                       str(db / "G.pdf"), _fake_tailor(calls))
    assert r.reused_from is None and calls == ["Acme", "Gamma"]


def test_different_role_family_never_reused(db):
    calls = []
    lib.get_resume("Acme", "Backend Developer", PY_BACKEND_JD, str(db / "A.pdf"), _fake_tailor(calls))
    r = lib.get_resume("Delta", "Frontend Developer", PY_BACKEND_JD, str(db / "D.pdf"), _fake_tailor(calls))
    assert r.reused_from is None


def test_thin_jd_needs_same_title(db):
    calls = []
    lib.get_resume("Acme", "Backend Developer", "", str(db / "A.pdf"), _fake_tailor(calls))
    assert lib.get_resume("B", "Senior Backend Developer", "", str(db / "B.pdf"), _fake_tailor(calls)).reused_from
    assert lib.get_resume("C", "Backend API Lead Architect", "", str(db / "C.pdf"), _fake_tailor(calls)).reused_from is None


def test_fallback_base_resume_is_not_reused(db):
    calls = []
    lib.get_resume("Acme", "Backend Developer", PY_BACKEND_JD, str(db / "A.pdf"), _fake_tailor(calls, ok=False))
    r = lib.get_resume("Beta", "Backend Developer", PY_BACKEND_JD, str(db / "B.pdf"), _fake_tailor(calls))
    assert r.reused_from is None and calls == ["Acme", "Beta"]


def test_deleted_resume_file_is_skipped(db):
    calls = []
    lib.get_resume("Acme", "Backend Developer", PY_BACKEND_JD, str(db / "A.pdf"), _fake_tailor(calls))
    os.remove(db / "A.pdf")
    r = lib.get_resume("Beta", "Backend Developer", PY_BACKEND_JD, str(db / "B.pdf"), _fake_tailor(calls))
    assert r.reused_from is None
