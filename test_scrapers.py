"""Test all scrapers one by one with saved sessions"""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from src.scrapers.indeed import scrape_indeed
from src.scrapers.linkedin import scrape_linkedin
from src.scrapers.naukri import scrape_naukri
from src.scrapers.wellfound import scrape_wellfound
from src.scrapers.internshala import scrape_internshala

KEYWORDS  = ["Backend Developer", "Python Developer"]
LOCATIONS = ["Remote", "Bangalore"]
BLACKLIST = ["Senior", "Lead", "Manager", "10+", "8+"]

def print_jobs(name, jobs):
    print(f"\n{'='*50}")
    print(f"  {name} — {len(jobs)} jobs found")
    print(f"{'='*50}")
    for j in jobs:
        print(f"  {j.title} @ {j.company} | {j.location}")
        print(f"  URL: {j.apply_url[:80]}")
        print()

# Test Indeed
jobs = scrape_indeed(keywords=KEYWORDS, locations=LOCATIONS, blacklist=BLACKLIST, max_jobs=3)
print_jobs("Indeed", jobs)

# Test LinkedIn
jobs = scrape_linkedin(keywords=KEYWORDS, locations=LOCATIONS, blacklist=BLACKLIST, max_jobs=3)
print_jobs("LinkedIn", jobs)

# Test Naukri
jobs = scrape_naukri(keywords=KEYWORDS, blacklist=BLACKLIST, max_jobs=3)
print_jobs("Naukri", jobs)

# Test Wellfound
jobs = scrape_wellfound(keywords=KEYWORDS, blacklist=BLACKLIST, max_jobs=3)
print_jobs("Wellfound", jobs)

# Test Internshala
jobs = scrape_internshala(keywords=KEYWORDS, blacklist=BLACKLIST, max_jobs=3)
print_jobs("Internshala", jobs)
