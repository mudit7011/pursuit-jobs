"""The base resume every tailored resume starts from.

Uploading a new resume makes a draft first: a PDF is transcribed into the existing
LaTeX template's format (content only from the PDF), compiled, and shown to the
user. Only "use draft" replaces the base; the old one is kept in templates/history/.
Tailored resumes made from an older base are not reused afterwards.
"""
import hashlib
import io
import os
import re
import shutil
import uuid
from datetime import datetime

from src.config import BASE_TEMPLATE_PATH

TEMPLATES = os.path.dirname(os.path.abspath(BASE_TEMPLATE_PATH))
BASE_PDF = os.path.splitext(os.path.abspath(BASE_TEMPLATE_PATH))[0] + ".pdf"
DRAFTS = os.path.join(TEMPLATES, "drafts")
HISTORY = os.path.join(TEMPLATES, "history")
MAX_UPLOAD = 5 * 1024 * 1024


def base_version() -> str:
    try:
        with open(BASE_TEMPLATE_PATH, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()[:12]
    except OSError:
        return ""


def info() -> dict:
    exists = os.path.exists(BASE_TEMPLATE_PATH)
    return {
        "version": base_version(),
        "updated_at": datetime.fromtimestamp(os.path.getmtime(BASE_TEMPLATE_PATH)).isoformat(timespec="seconds") if exists else None,
        "has_pdf": os.path.exists(BASE_PDF),
    }


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)


def _transcribe_pdf(data: bytes, style_tex: str) -> str:
    """PDF → LaTeX in the current template's format. Content comes only from the PDF."""
    from src.resume_tailor import _extract_latex, model
    prompt = f"""Convert the attached resume PDF into LaTeX using EXACTLY the commands, preamble and
section layout of the template below. Rules:
- Transcribe the PDF's content faithfully: every role, date, number, link and bullet as written.
- Do NOT add, remove, improve or reword anything. Do not invent skills, metrics or dates.
- Keep the template's preamble and custom commands unchanged; only the content changes.
- Escape LaTeX special characters (& % $ # _).
- Return ONLY the complete LaTeX document, no explanation, no markdown fences.

TEMPLATE:
{style_tex}"""
    resp = model.generate_content([{"mime_type": "application/pdf", "data": data}, prompt])
    return _extract_latex(resp.text)


def _plain(latex: str) -> str:
    body = latex.split(r"\begin{document}", 1)[-1]
    body = re.sub(r"%.*", "", body)
    body = re.sub(r"-?[\d.]+\s*(in|pt|em|ex|cm|mm|bp|sp)\b", " ", body)   # LaTeX lengths, not resume facts
    body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", body)              # commands and their [options]
    return re.sub(r"[{}\\$&]", " ", body)


def unsupported_numbers(latex: str, source_text: str) -> list[str]:
    """Numbers in the transcription that never appear in the uploaded PDF."""
    src = re.sub(r"\s+", "", source_text)
    found = set(re.findall(r"\d[\d.,%+]*\d|\d", _plain(latex)))
    return sorted(n for n in found if len(n) > 1 and n.strip(".,") not in src)


def make_draft(filename: str, data: bytes) -> dict:
    from src.resume_tailor import _compile_latex
    if len(data) > MAX_UPLOAD:
        raise ValueError("That file is over 5 MB")
    ext = os.path.splitext(filename.lower())[1]
    warnings: list[str] = []
    if ext == ".tex":
        latex = data.decode("utf-8")
    elif ext == ".pdf":
        latex = _transcribe_pdf(data, open(BASE_TEMPLATE_PATH).read())
        missing = unsupported_numbers(latex, _pdf_text(data))
        if missing:
            warnings.append("These numbers aren't in your PDF — check them: " + ", ".join(missing[:12]))
    else:
        raise ValueError("Upload a PDF or a .tex file")
    try:
        pdf = _compile_latex(latex)
    except RuntimeError as e:
        raise ValueError(f"The resume didn't compile: {str(e)[-300:]}")
    draft_id = uuid.uuid4().hex[:10]
    os.makedirs(DRAFTS, exist_ok=True)
    with open(os.path.join(DRAFTS, f"{draft_id}.tex"), "w") as f:
        f.write(latex)
    with open(os.path.join(DRAFTS, f"{draft_id}.pdf"), "wb") as f:
        f.write(pdf)
    return {"id": draft_id, "warnings": warnings}


def draft_path(draft_id: str, ext: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{10}", draft_id):
        raise ValueError("Unknown draft")
    path = os.path.join(DRAFTS, f"{draft_id}.{ext}")
    if not os.path.exists(path):
        raise ValueError("Unknown draft")
    return path


def use_draft(draft_id: str) -> dict:
    tex, pdf = draft_path(draft_id, "tex"), draft_path(draft_id, "pdf")
    os.makedirs(HISTORY, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = os.path.splitext(os.path.basename(BASE_TEMPLATE_PATH))[0]
    if os.path.exists(BASE_TEMPLATE_PATH):
        shutil.copyfile(BASE_TEMPLATE_PATH, os.path.join(HISTORY, f"{name}-{stamp}.tex"))
    if os.path.exists(BASE_PDF):
        shutil.copyfile(BASE_PDF, os.path.join(HISTORY, f"{name}-{stamp}.pdf"))
    shutil.move(tex, BASE_TEMPLATE_PATH)
    shutil.move(pdf, BASE_PDF)
    return info()


def discard_draft(draft_id: str) -> None:
    for ext in ("tex", "pdf"):
        try:
            os.remove(draft_path(draft_id, ext))
        except ValueError:
            pass
