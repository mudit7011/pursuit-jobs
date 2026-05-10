"""
Quick end-to-end test — bypasses Telegram, directly runs the pipeline
with a fake job message to verify everything works.
"""
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from src.parser import parse_job_message
from src.orchestrator import process_job

FAKE_JOB = """
6) Company - Instamart
Role - Data Analyst
Batch - 2023/2024/2025
Salary - ₹50,000 - ₹90,000/month
Location - Gurgaon

Job Details:
• Hiring for a full stack Data Analyst role (~1 year of experience preferred).
• Opportunity to work on data-driven decision making and business insights.
• Work closely with teams to analyse data, build reports, and support product/business growth.
• Immediate joiners are preferred.

How to Apply:
Send your details to kunalranjan2k14@gmail.com
"""

async def main():
    print("Step 1: Parsing job message with Gemini...")
    job = parse_job_message(FAKE_JOB)
    print(f"  Company: {job.company}")
    print(f"  Role: {job.role}")
    print(f"  Apply type: {job.apply_type}")
    print(f"  Apply target: {job.apply_target}")
    print(f"  Relevant: {job.is_relevant}")

    print("\nStep 2: Running full pipeline (tailor resume + send email + notify)...")
    await process_job(job)
    print("\nDone! Check your email and Telegram for notifications.")

asyncio.run(main())
