import os

import pytest

from src import resume_base as rb
from src import resume_library as lib
import src.tracker as tracker

TEX = r"""\documentclass{article}\begin{document}Mudit Kumar \\ Backend Developer, 2024--2025, CGPA 7.49\end{document}"""


@pytest.fixture
def base(tmp_path, monkeypatch):
    tex = tmp_path / "CV.tex"
    tex.write_text("old resume")
    (tmp_path / "CV.pdf").write_bytes(b"old pdf")
    monkeypatch.setattr(rb, "BASE_TEMPLATE_PATH", str(tex))
    monkeypatch.setattr(rb, "BASE_PDF", str(tmp_path / "CV.pdf"))
    monkeypatch.setattr(rb, "DRAFTS", str(tmp_path / "drafts"))
    monkeypatch.setattr(rb, "HISTORY", str(tmp_path / "history"))
    monkeypatch.setattr(tracker, "DB_PATH", str(tmp_path / "apps.db"))
    import src.resume_tailor as rt
    monkeypatch.setattr(rt, "_compile_latex", lambda latex: b"%PDF compiled")
    return tmp_path


def test_flags_numbers_not_in_the_pdf():
    latex = r"\begin{document}Improved latency by 40\% in 2024, CGPA 7.49\end{document}"
    assert rb.unsupported_numbers(latex, "Improved latency in 2024. CGPA 7.49") == ["40"]


def test_tex_upload_makes_draft_then_replaces_base_with_backup(base):
    d = rb.make_draft("new.tex", TEX.encode())
    assert d["warnings"] == []
    assert open(rb.BASE_TEMPLATE_PATH).read() == "old resume"   # nothing changes until "use"
    rb.use_draft(d["id"])
    assert open(rb.BASE_TEMPLATE_PATH).read() == TEX
    history = os.listdir(rb.HISTORY)
    assert any(h.endswith(".tex") for h in history) and any(h.endswith(".pdf") for h in history)


def test_rejects_other_file_types_and_bad_ids(base):
    with pytest.raises(ValueError):
        rb.make_draft("resume.docx", b"x")
    with pytest.raises(ValueError):
        rb.use_draft("../../etc")


def test_new_base_makes_old_tailored_resumes_stale(base, monkeypatch):
    version = {"v": "aaa"}
    monkeypatch.setattr(lib, "_base_version", lambda: version["v"])
    def tailor(c, r, jd, out):
        open(out, "wb").write(b"x")
        return True
    jd = "Python FastAPI PostgreSQL Docker AWS"
    lib.get_resume("A", "Backend Developer", jd, str(base / "a.pdf"), tailor)
    assert lib.find_reusable("Backend Developer", jd) is not None
    version["v"] = "bbb"   # user uploaded a new resume
    assert lib.find_reusable("Backend Developer", jd) is None


def test_latex_lengths_are_not_flagged():
    latex = r"\begin{document}\vspace{-0.15in}\setlength{\tabcolsep}{2pt}CGPA 7.49\end{document}"
    assert rb.unsupported_numbers(latex, "CGPA 7.49") == []
