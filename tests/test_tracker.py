import os
import pytest
import tempfile

# Patch DB_PATH before importing tracker
import src.tracker as tracker_module


def test_is_duplicate_returns_false_for_new_job(tmp_path):
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    assert tracker_module.is_duplicate("Acme Corp", "SWE Intern") is False


def test_log_and_detect_duplicate(tmp_path):
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    tracker_module.log_application(
        company="Acme Corp",
        role="SWE Intern",
        apply_target="hr@acme.com",
        apply_type="email",
        status="applied",
        skip_reason="",
    )
    assert tracker_module.is_duplicate("Acme Corp", "SWE Intern") is True


def test_skipped_job_not_counted_as_duplicate(tmp_path):
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    tracker_module.log_application(
        company="Beta Inc",
        role="PM",
        apply_target="",
        apply_type="",
        status="skipped",
        skip_reason="Batch mismatch",
    )
    # Skipped jobs should NOT block future re-evaluation
    assert tracker_module.is_duplicate("Beta Inc", "PM") is False


def test_log_application_stores_all_fields(tmp_path):
    import sqlite3
    tracker_module.DB_PATH = str(tmp_path / "test_applications.db")
    tracker_module.log_application(
        company="Gamma Ltd",
        role="Backend Dev",
        apply_target="https://greenhouse.io/gamma/backend",
        apply_type="web_form",
        status="applied",
        skip_reason="",
    )
    conn = sqlite3.connect(tracker_module.DB_PATH)
    row = conn.execute(
        "SELECT company, role, apply_type, status FROM applications WHERE company='Gamma Ltd'"
    ).fetchone()
    conn.close()
    assert row == ("Gamma Ltd", "Backend Dev", "web_form", "applied")
