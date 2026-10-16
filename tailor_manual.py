"""Tailor your resume for one job by hand, without the bot.

    python tailor_manual.py --company "Acme" --role "Backend Engineer" --jd jd.txt --out ~/Downloads/acme.pdf
"""
import argparse
import os

from src.resume_tailor import save_pdf

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--company", required=True)
parser.add_argument("--role", required=True)
parser.add_argument("--jd", required=True, help="text file with the job description")
parser.add_argument("--out", required=True, help="where to write the PDF")
args = parser.parse_args()

with open(args.jd) as f:
    jd = f.read()
path = save_pdf(args.company, args.role, jd, os.path.expanduser(args.out))
print(f"Saved {path}")
