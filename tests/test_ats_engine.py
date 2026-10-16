"""Engine tests against local HTML forms. Real browser, mocked Gemini."""
import os
import pathlib

import pytest

import src.tracker as tracker
from src.ats import answers, engine
from src.ats.engine import MissingAnswersError, apply_form
from src.profile import load_profile
from src.web_form_filler import FormSubmitError

FIX = pathlib.Path(__file__).parent / "fixtures" / "forms"
RESUME = str(pathlib.Path(__file__).parent / "fixtures" / "resume.pdf")


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("JAC_HEADLESS", "1")
    monkeypatch.setattr(tracker, "DB_PATH", str(tmp_path / "apps.db"))


def _gemini_returns(monkeypatch, mapping_by_label):
    def fake(fields, profile, jd, company, role):
        return {f["jid"]: mapping_by_label.get(f["label"]) for f in fields}
    monkeypatch.setattr(answers, "_gemini", fake)


def test_best_option():
    assert answers.best_option("yes", ["Yes", "No"]) == "Yes"
    assert answers.best_option("Bengaluru, India", ["Mumbai", "Bengaluru"]) == "Bengaluru"
    assert answers.best_option("Maybe", ["Yes", "No"]) is None


def test_fills_form_skips_honeypots_and_submits(monkeypatch):
    _gemini_returns(monkeypatch, {"Are you willing to relocate?": "Yes",
                                  "Why do you want to work here?": "I build backend systems.",
                                  "Company name": "Nedzo AI"})
    r = apply_form(f"file://{FIX/'basic.html'}", "Acme", "Backend Engineer", "", RESUME, load_profile())
    labels = {l: v for l, v, _ in r.filled}
    assert labels["First Name"] == load_profile().name.split()[0]
    assert labels["Company name"] == "Nedzo AI"
    assert not any("website" in l.lower() or "company_hp" in l for l in labels)


def test_hiring_company_never_used_as_candidate_fact(monkeypatch):
    _gemini_returns(monkeypatch, {"Are you willing to relocate?": "Yes", "Company name": "Acme"})
    with pytest.raises(MissingAnswersError) as e:
        apply_form(f"file://{FIX/'basic.html'}", "Acme", "Backend Engineer", "", RESUME, load_profile())
    assert e.value.questions == ["Company name"]


def test_unknown_required_fact_stops_before_submit(monkeypatch):
    _gemini_returns(monkeypatch, {})  # Gemini doesn't know 10th marks
    with pytest.raises(MissingAnswersError) as e:
        apply_form(f"file://{FIX/'needs_user.html'}", "Acme", "SWE", "", RESUME, load_profile())
    assert e.value.questions == ["How much did you score in your 10th Class?"]


def test_answer_bank_fills_it_next_time(monkeypatch):
    from src.ats import answer_bank
    _gemini_returns(monkeypatch, {})
    answer_bank.save("How much did you score in your 10th class?", "82%")
    r = apply_form(f"file://{FIX/'needs_user.html'}", "Acme", "SWE", "", RESUME, load_profile())
    assert ("How much did you score in your 10th Class?", "82%", "bank") in r.filled


def test_dry_run_never_submits(monkeypatch, tmp_path):
    _gemini_returns(monkeypatch, {"Are you willing to relocate?": "Yes", "Company name": "Nedzo AI"})
    r = apply_form(f"file://{FIX/'basic.html'}", "Acme", "Backend Engineer", "", RESUME, load_profile(), dry_run=True)
    assert r.pages == 1  # reached submit step and returned without clicking


def test_no_confirmation_is_a_failure(monkeypatch, tmp_path):
    html = (FIX / "basic.html").read_text().replace("window.__ok = true", "window.__ok = false")
    page = tmp_path / "noconfirm.html"
    page.write_text(html)
    _gemini_returns(monkeypatch, {"Are you willing to relocate?": "Yes", "Company name": "Nedzo AI"})
    monkeypatch.setattr(engine, "_wait_success", lambda *a, **k: False)
    with pytest.raises(FormSubmitError, match="no confirmation"):
        apply_form(f"file://{page}", "Acme", "Backend Engineer", "", RESUME, load_profile())


def test_adapter_routing():
    assert engine.adapter_for("https://jobs.lever.co/cred/abc").form_url("https://jobs.lever.co/cred/abc") == "https://jobs.lever.co/cred/abc/apply"
    assert engine.adapter_for("https://jobs.ashbyhq.com/x/y").name == "ashby"
    assert engine.adapter_for("https://job-boards.greenhouse.io/x/jobs/1").name == "greenhouse"
    assert engine.adapter_for("https://forms.office.com/pages/responsepage.aspx?id=1").name == "microsoft_forms"
    assert engine.adapter_for("https://forms.gle/abc").name == "google_forms"
    assert engine.adapter_for("https://forms.zohopublic.in/x/form/Apply").name == "zoho_forms"
    assert engine.adapter_for("https://ekacare.keka.com/careers/applyjob/1").name == "keka"
    assert engine.adapter_for("https://example.com/careers/apply").name == "generic"


def test_text_captcha_is_never_answered(monkeypatch):
    from src.web_form_filler import CaptchaDetectedError
    asked = []
    monkeypatch.setattr(answers, "_gemini", lambda fields, *a: asked.extend(f["label"] for f in fields) or {})
    with pytest.raises(CaptchaDetectedError):
        apply_form(f"file://{FIX/'captcha.html'}", "Acme", "SWE", "", RESUME, load_profile())
    assert "Captcha" not in asked


def test_never_fills_own_details_into_reference_fields(monkeypatch):
    _gemini_returns(monkeypatch, {})
    r = apply_form(f"file://{FIX/'references.html'}", "Acme", "SWE", "", RESUME, load_profile(), dry_run=True)
    filled = {l: v for l, v, _ in r.filled}
    name = load_profile().name.split()
    assert filled == {"Full name First": name[0], "Full name Last": name[-1]}


def test_zoho_style_split_name_and_required_suffix(monkeypatch):
    _gemini_returns(monkeypatch, {})
    with pytest.raises(MissingAnswersError) as e:
        apply_form(f"file://{FIX/'zoho_like.html'}", "Acme", "SWE", "", RESUME, load_profile())
    assert e.value.questions == ["Date of birth"]
    filled = {l: v for l, v, _ in e.value.report.filled}
    name = load_profile().name.split()
    assert filled == {"Full name First": name[0], "Full name Last": name[-1]}


def test_reference_answers_never_become_own_name(monkeypatch, tmp_path):
    from src.ats import answer_bank
    html = (FIX / "references.html").read_text().replace('<input id="r1">', '<input id="r1" required>')
    page = tmp_path / "ref_required.html"
    page.write_text(html)
    _gemini_returns(monkeypatch, {})
    with pytest.raises(MissingAnswersError) as e:
        apply_form(f"file://{page}", "Acme", "SWE", "", RESUME, load_profile())
    assert e.value.questions == ["Reference 1 › Name"]
    answer_bank.save("Reference 1 › Name", "Priya Sharma")
    # A later form's own name question must still get the candidate's name.
    assert answer_bank.lookup("Name") is None


def test_role_question_uses_job_and_checkbox_stays_ticked(monkeypatch, tmp_path):
    monkeypatch.setattr(answers, "_gemini", lambda fields, *a: {f["jid"]: ["I confirm"] for f in fields if f["kind"] == "checkbox"})
    r = apply_form(f"file://{FIX/'gform_like.html'}", "Acme", "Backend Engineer", "", RESUME, load_profile(), dry_run=True)
    filled = {l: v for l, v, _ in r.filled}
    assert filled["Role Applying For"] == "Backend Engineer"
    # The box is required: reaching the submit step (no MissingAnswersError) means it ended up ticked.
    assert any(l.startswith("I confirm") for l in filled)


def test_logistics_stay_with_user_but_behavioral_questions_are_written(monkeypatch):
    asked = []
    monkeypatch.setattr(answers, "_gemini", lambda fields, *a: asked.extend(f["label"] for f in fields) or {})
    fields = [{"jid": "j1", "kind": "textarea", "label": "A production bug or downtime you caused and how you acted on it"},
              {"jid": "j2", "kind": "textarea", "label": "What's a technical decision you made that you'd reverse today?"},
              {"jid": "j3", "kind": "radio", "label": "Are You Comfertable For Walkin Drive on next Saturday", "options": ["Yes", "No"]},
              {"jid": "j4", "kind": "textarea", "label": "Why do you want to join us?"}]
    answers.decide(fields, load_profile(), "", "Acme", "SWE")
    assert "Are You Comfertable For Walkin Drive on next Saturday" not in asked
    assert len(asked) == 3


def test_answers_sent_are_recorded(monkeypatch):
    a = tracker.log_application("Acme", "SWE", "u", "web_form", "approved")
    tracker.set_answers_used(a, [("Full name", "Mudit Kumar", "rules"), ("Skills", ["Python"], "gemini")])
    from fastapi.testclient import TestClient
    from src.api.server import app
    row = TestClient(app).get(f"/api/applications/{a}").json()
    assert row["answers_used"] == [["Full name", "Mudit Kumar", "rules"], ["Skills", ["Python"], "gemini"]]


def test_assist_mode_hands_over_and_never_clicks_submit(monkeypatch):
    handed = []
    monkeypatch.setattr(engine, "_hand_over", lambda page, ad, report, role, company: handed.append(page.url) or report)
    _gemini_returns(monkeypatch, {"Are you willing to relocate?": "Yes", "Company name": "Nedzo AI"})
    # Captcha form: no exception, handed over to the user.
    apply_form(f"file://{FIX/'captcha.html'}", "Acme", "SWE", "", RESUME, load_profile(), assist=True)
    # Fully answerable form: still handed over; the page was not submitted by the bot.
    r = apply_form(f"file://{FIX/'basic.html'}", "Acme", "Backend Engineer", "", RESUME, load_profile(), assist=True)
    assert len(handed) == 2 and r.filled


def test_google_required_marker_on_text_question(monkeypatch):
    _gemini_returns(monkeypatch, {})
    with pytest.raises(MissingAnswersError) as e:
        apply_form(f"file://{FIX/'gform_required.html'}", "Acme", "SWE", "", RESUME, load_profile())
    assert e.value.questions == ["Your Postal Address"]
