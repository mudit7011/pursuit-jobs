import logging

import pytest

import src.orchestrator as orch
from src.models import ApplyType, JobPosting


def _job(t=ApplyType.WELLFOUND_APPLY):
    return JobPosting(company="Acme", role="SWE", location="", jd_summary="", apply_type=t, apply_target="https://x")


def test_failure_reason_from_applicator_log_is_surfaced(monkeypatch):
    def fake_apply(**kw):
        logging.getLogger("src.applicators.wellfound_apply").warning("Submit disabled. Blocker: visa required")
        return False
    monkeypatch.setitem(orch._PORTAL_APPLICATORS, ApplyType.WELLFOUND_APPLY, ("Wellfound Apply", fake_apply))
    with pytest.raises(Exception, match="visa required"):
        orch._submit(_job(), "r.pdf")


def test_instahyre_routes_to_its_applicator(monkeypatch):
    calls = []
    monkeypatch.setitem(orch._PORTAL_APPLICATORS, ApplyType.INSTAHYRE_APPLY,
                        ("Instahyre Apply", lambda **kw: calls.append(kw) or True))
    orch._submit(_job(ApplyType.INSTAHYRE_APPLY), "r.pdf")
    assert calls and calls[0]["company"] == "Acme"


def test_crawler_maps_instahyre_source():
    from src.job_crawler import _to_job_posting
    from src.scrapers.base import ScrapedJob
    jp = _to_job_posting(ScrapedJob(title="Backend Developer", company="X", location="", apply_url="u", source="instahyre"))
    assert jp.apply_type == ApplyType.INSTAHYRE_APPLY
