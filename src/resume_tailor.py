import os
import re
import subprocess
import tempfile
import shutil
import google.generativeai as genai
from src.config import GEMINI_API_KEY, BASE_TEMPLATE_PATH, OUTPUT_DIR

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def _build_tailor_prompt(base_latex: str, jd_summary: str, company: str, role: str) -> str:
    return f"""You are a resume tailoring assistant. Modify this LaTeX resume to better match the job.

STRICT RULES:
- Only modify content inside: Technical Skills section, Experience bullet points, Projects bullet points
- Do NOT change any LaTeX commands, structure, formatting, or the header
- Do NOT add or remove sections
- Keep all \\resumeItem, \\resumeSubheading, \\resumeProjectHeading commands exactly as-is
- Reorder projects to put the most relevant one first
- Return ONLY the complete valid LaTeX, no explanation, no markdown fences

JOB: {role} at {company}
JOB REQUIREMENTS: {jd_summary}

BASE LATEX:
{base_latex}"""

def _extract_latex(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:latex)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()

def save_pdf(company: str, role: str, jd_summary: str, output_path: str) -> str:
    base_latex = open(BASE_TEMPLATE_PATH).read()
    prompt = _build_tailor_prompt(base_latex, jd_summary, company, role)
    response = model.generate_content(prompt)
    tailored_latex = _extract_latex(response.text)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w") as f:
            f.write(tailored_latex)
        result = subprocess.run(
            ["tectonic", tex_path],
            capture_output=True, text=True, cwd=tmpdir
        )
        if result.returncode != 0:
            raise RuntimeError(f"tectonic failed:\n{result.stderr}")
        compiled_pdf = os.path.join(tmpdir, "resume.pdf")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy(compiled_pdf, output_path)

    return output_path
