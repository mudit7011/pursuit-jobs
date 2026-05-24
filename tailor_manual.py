import re, json, tempfile, os, subprocess, shutil
import google.generativeai as genai
from src.config import GEMINI_API_KEY, BASE_TEMPLATE_PATH
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

base_latex = open(BASE_TEMPLATE_PATH).read()
jd = "Design and implement high-performance C++ services for trading and market data. Develop features in OMS, RMS, Smart Order Routing, and Algo platforms. Optimize systems for latency, throughput, and memory usage. Debug production issues. Required: C++ (C++14/17), multithreading, STL, Linux, backend or real-time systems. Good to have: financial markets, network programming, Python scripting."

prompt = f"""You are a resume tailoring assistant. Modify this LaTeX resume to better match the job.

STRICT RULES:
- Only modify content inside: Technical Skills section, Experience bullet points, Projects bullet points
- Do NOT change any LaTeX commands, structure, formatting, or the header
- Do NOT add or remove sections
- Keep all \\resumeItem, \\resumeSubheading, \\resumeProjectHeading commands exactly as-is
- NEVER use & outside of tabular/table environments
- Return ONLY the complete valid LaTeX, no explanation, no markdown fences

JOB: Software Engineer (C++) at FYERS
JOB REQUIREMENTS: {jd}

BASE LATEX:
{base_latex}"""

response = model.generate_content(prompt)
raw = response.text.strip()
raw = re.sub(r"^```(?:latex)?\s*", "", raw)
raw = re.sub(r"\s*```$", "", raw)

with tempfile.TemporaryDirectory() as tmpdir:
    tex_path = os.path.join(tmpdir, "resume.tex")
    with open(tex_path, "w") as f:
        f.write(raw)
    result = subprocess.run(["/opt/homebrew/bin/tectonic", tex_path], capture_output=True, text=True, cwd=tmpdir)
    if result.returncode != 0:
        print("LaTeX error, using base template")
        with open(tex_path, "w") as f:
            f.write(base_latex)
        result = subprocess.run(["/opt/homebrew/bin/tectonic", tex_path], capture_output=True, text=True, cwd=tmpdir)
    shutil.copy(os.path.join(tmpdir, "resume.pdf"), "/Users/muditchaudhary/Downloads/FYERS_SWE_CPP.pdf")

print("Done: /Users/muditchaudhary/Downloads/FYERS_SWE_CPP.pdf")
