"""
Job Crawler — runs all platform scrapers on schedule.
LinkedIn: once per day (to avoid bans).
Others (Naukri, Indeed, Wellfound, Internshala): every hour.
Instahyre: skipped — platform is recruiter-driven, apply manually.
"""

import asyncio
import logging
import os
import time
from typing import List

from src.scrapers.base import ScrapedJob
from src.scrapers.linkedin import scrape_linkedin
from src.scrapers.naukri import scrape_naukri
from src.scrapers.indeed import scrape_indeed
from src.scrapers.wellfound import scrape_wellfound
from src.scrapers.internshala import scrape_internshala
from src.models import JobPosting, ApplyType
from src.profile import load_profile
from src.tracker import is_duplicate

log = logging.getLogger(__name__)

LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
NAUKRI_EMAIL      = os.getenv("NAUKRI_EMAIL", "")
NAUKRI_PASSWORD   = os.getenv("NAUKRI_PASSWORD", "")

CRAWL_INTERVAL        = int(os.getenv("CRAWL_INTERVAL_SECONDS", "3600"))   # 1 hour
LINKEDIN_INTERVAL     = int(os.getenv("LINKEDIN_INTERVAL_SECONDS", "86400"))  # 24 hours

_linkedin_last_run: float = 0.0  # epoch seconds


def _to_job_posting(job: ScrapedJob) -> JobPosting:
    # Route LinkedIn Easy Apply jobs to the dedicated applicator
    if job.source == "linkedin" and job.easy_apply:
        apply_type = ApplyType.LINKEDIN_EASY_APPLY
    else:
        apply_type = ApplyType.WEB_FORM

    return JobPosting(
        is_relevant=True,
        company=job.company,
        role=job.title,
        location=job.location,
        jd_summary=job.jd_text or f"{job.title} at {job.company}",
        apply_type=apply_type,
        apply_target=job.apply_url,
        source=job.source,
    )


async def run_crawlers(process_job_fn) -> None:
    global _linkedin_last_run

    profile = load_profile()
    cfg      = profile.raw.get("job_search", {})
    keywords  = cfg.get("keywords", ["Software Engineer", "Backend Developer"])
    locations = cfg.get("locations", ["Remote", "Bangalore"])
    exp_min   = cfg.get("experience_min", 0)
    exp_max   = cfg.get("experience_max", 3)
    blacklist = cfg.get("blacklist_keywords", [])

    all_jobs: List[ScrapedJob] = []

    # ── LinkedIn (once per day) ──────────────────────────────────────────────
    now = time.time()
    linkedin_due = (now - _linkedin_last_run) >= LINKEDIN_INTERVAL

    if linkedin_due and LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
        log.info("LinkedIn scraper starting (daily run)...")
        try:
            jobs = scrape_linkedin(
                email=LINKEDIN_EMAIL, password=LINKEDIN_PASSWORD,
                keywords=keywords, locations=locations,
                experience_min=exp_min, experience_max=exp_max,
                blacklist=blacklist, max_jobs=40,
            )
            all_jobs.extend(jobs)
            _linkedin_last_run = time.time()
            log.info(f"LinkedIn: {len(jobs)} jobs found")
        except Exception as e:
            log.error(f"LinkedIn scraper failed: {e}")
    elif not linkedin_due:
        remaining = int((LINKEDIN_INTERVAL - (now - _linkedin_last_run)) / 3600)
        log.info(f"LinkedIn: skipping — next run in ~{remaining}h")
    else:
        log.info("LinkedIn credentials not set — skipping")

    # ── Naukri ───────────────────────────────────────────────────────────────
    if NAUKRI_EMAIL and NAUKRI_PASSWORD:
        log.info("Naukri scraper starting...")
        try:
            jobs = scrape_naukri(
                email=NAUKRI_EMAIL, password=NAUKRI_PASSWORD,
                keywords=keywords, experience=max(exp_min, 1),
                blacklist=blacklist, max_jobs=40,
            )
            all_jobs.extend(jobs)
            log.info(f"Naukri: {len(jobs)} jobs found")
        except Exception as e:
            log.error(f"Naukri scraper failed: {e}")
    else:
        log.info("Naukri credentials not set — skipping")

    # ── Indeed ───────────────────────────────────────────────────────────────
    log.info("Indeed scraper starting...")
    try:
        jobs = scrape_indeed(
            keywords=keywords, locations=locations,
            experience_max=exp_max, blacklist=blacklist, max_jobs=40,
        )
        all_jobs.extend(jobs)
        log.info(f"Indeed: {len(jobs)} jobs found")
    except Exception as e:
        log.error(f"Indeed scraper failed: {e}")

    # ── Wellfound ────────────────────────────────────────────────────────────
    log.info("Wellfound scraper starting...")
    try:
        jobs = scrape_wellfound(keywords=keywords, blacklist=blacklist, max_jobs=30)
        all_jobs.extend(jobs)
        log.info(f"Wellfound: {len(jobs)} jobs found")
    except Exception as e:
        log.error(f"Wellfound scraper failed: {e}")

    # ── Internshala ──────────────────────────────────────────────────────────
    log.info("Internshala scraper starting...")
    try:
        jobs = scrape_internshala(keywords=keywords, blacklist=blacklist, max_jobs=30)
        all_jobs.extend(jobs)
        log.info(f"Internshala: {len(jobs)} jobs found")
    except Exception as e:
        log.error(f"Internshala scraper failed: {e}")

    log.info(f"Crawler total: {len(all_jobs)} jobs across all platforms")

    # ── Feed into pipeline ───────────────────────────────────────────────────
    for scraped in all_jobs:
        if is_duplicate(scraped.company, scraped.title):
            log.info(f"Duplicate — skipping: {scraped.title} @ {scraped.company}")
            continue
        await process_job_fn(_to_job_posting(scraped))
        await asyncio.sleep(2)


async def crawler_loop(process_job_fn) -> None:
    """Runs every CRAWL_INTERVAL seconds. LinkedIn only fires once per day."""
    while True:
        log.info("=== Job Crawler run starting ===")
        try:
            await run_crawlers(process_job_fn)
        except Exception as e:
            log.error(f"Crawler run failed: {e}")
        log.info(f"=== Crawler done — next run in {CRAWL_INTERVAL // 60} min ===")
        await asyncio.sleep(CRAWL_INTERVAL)
