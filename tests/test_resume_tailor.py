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
from src.resume_tailor import _build_tailor_prompt, _extract_latex, save_pdf

SAMPLE_JD = "Backend engineering, REST APIs, Python, AWS, AI tools"
SAMPLE_LATEX = r"\begin{document}\n\section{Skills}\nPython\n\end{document}"

def test_build_tailor_prompt_contains_jd():
    prompt = _build_tailor_prompt(SAMPLE_LATEX, SAMPLE_JD, "Aspire", "SWE Intern")
    assert "REST APIs" in prompt
    assert "Aspire" in prompt
    assert "SWE Intern" in prompt

def test_extract_latex_strips_fences():
    raw = "```latex\n\\documentclass{article}\n```"
    result = _extract_latex(raw)
    assert result == "\\documentclass{article}"

def test_extract_latex_no_fences():
    raw = "\\documentclass{article}"
    result = _extract_latex(raw)
    assert result == "\\documentclass{article}"

def test_save_pdf_creates_file(tmp_path):
    latex = open("templates/resume.example.tex").read()
    output_path = str(tmp_path / "test_resume.pdf")
    with patch("src.resume_tailor.model") as mock_model:
        mock_response = MagicMock()
        mock_response.text = latex  # return unmodified latex
        mock_model.generate_content.return_value = mock_response
        result = save_pdf("Test Company", "SWE", "Python backend job", output_path)
    assert os.path.exists(result)
    assert result.endswith(".pdf")
