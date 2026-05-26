"""
Instahyre job scraper using Playwright.
Instahyre shows jobs at /candidate/opportunities/ — fill the search form,
click Show Results, then extract job cards.
"""

import os
import time
import random
import logging
from typing import List
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from src.scrapers.base import ScrapedJob, is_blacklisted

log = logging.getLogger(__name__)
_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/instahyre.json")


def _human_delay(min_s: float = 0.8, max_s: float = 2.0):
    time.sleep(random.uniform(min_s, max_s))


def _search_and_extract(page: Page, keyword: str, blacklist: List[str]) -> List[ScrapedJob]:
    jobs = []

    # Navigate to opportunities page
    page.goto("https://www.instahyre.com/candidate/opportunities/", timeout=30000)
    _human_delay(2.0, 3.0)

    # Instahyre uses a custom React component for skills input.
    # Strategy: click the visible container, then type via keyboard.
    SKILLS_CONTAINER_SELS = [
        "input[placeholder*='skill' i]",
        "input[placeholder*='title' i]",
        "input[placeholder*='e.g Java' i]",
        "#skills",
        "input[name='skills']",
        # React-select: the dummy input inside
        ".css-1hwfws3 input, .css-b8ldur-Input input",
        # Generic: first input inside the search form area
    ]

    filled = False
    for sel in SKILLS_CONTAINER_SELS:
        try:
            el = page.query_selector(sel)
            if el:
                # Use JS to focus + set value so React state picks it up
                page.evaluate(
                    """(el, val) => {
                        el.focus();
                        const nativeInput = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value');
                        nativeInput.set.call(el, val);
                        el.dispatchEvent(new Event('input', {bubbles: true}));
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                    }""",
                    el, keyword
                )
                _human_delay(0.4, 0.8)
                filled = True
                log.info(f"Instahyre: filled skills with JS via '{sel}'")
                break
        except Exception as e:
            log.debug(f"Instahyre: selector '{sel}' failed — {e}")
            continue

    if not filled:
        # Last resort: click anywhere visible, tab to first input, type
        try:
            page.keyboard.press("Tab")
            _human_delay(0.3, 0.5)
            page.keyboard.type(keyword, delay=80)
            filled = True
        except Exception:
            pass

    if not filled:
        log.warning(f"Instahyre: could not fill skills field for '{keyword}'")
        return jobs

    _human_delay(0.5, 1.0)

    # Click Show Results button
    show_btn = None
    for sel in ["button:has-text('Show results')", "button:has-text('Show Results')",
                "button:has-text('Search')", "input[value*='Show']",
                "button[type='submit']"]:
        try:
            el = page.query_selector(sel)
            if el:
                show_btn = el
                break
        except Exception:
            continue

    if show_btn:
        try:
            show_btn.click(force=True)
        except Exception:
            page.evaluate("el => el.click()", show_btn)
        _human_delay(2.5, 4.0)
    else:
        page.keyboard.press("Enter")
        _human_delay(2.5, 4.0)

    # Wait for job cards — Instahyre uses .employer-block as the card wrapper
    try:
        page.wait_for_selector(".employer-block, .employer-row", timeout=8000)
    except PWTimeout:
        log.warning("Instahyre: no .employer-block cards appeared after search")
        return jobs

    cards = page.query_selector_all(".employer-block")
    if not cards:
        cards = page.query_selector_all(".employer-row")
    log.info(f"Instahyre: {len(cards)} employer cards found")

    for card in cards:
        try:
            title_el    = card.query_selector(".employer-job-name, .job-title, [class*='job-name']")
            company_el  = card.query_selector(".company-name, [class*='company-name']")
            location_el = card.query_selector(".employer-locations, [class*='location']")

            if not title_el:
                continue

            raw_title = title_el.inner_text().strip().split("\n")[0]
            company_raw = company_el.inner_text().strip().split("\n")[0] if company_el else ""
            location = location_el.inner_text().strip() if location_el else ""

            # .employer-job-name often has "Company - Job Title" format
            # If company_raw is a prefix, strip it from title
            if company_raw and raw_title.startswith(company_raw + " - "):
                title = raw_title[len(company_raw) + 3:].strip()
                company = company_raw
            elif " - " in raw_title:
                # Split on first " - ": assume left=company, right=job title
                parts = raw_title.split(" - ", 1)
                company = parts[0].strip()
                title = parts[1].strip()
            else:
                title = raw_title
                company = company_raw or "Unknown"

            if not title or len(title) < 2:
                continue
            if is_blacklisted(title, blacklist):
                log.info(f"Instahyre: blacklisted — {title}")
                continue

            # Get job URL — try anchor in card, else the "View »" button
            href = ""
            link_el = card.query_selector("a[href]")
            if link_el:
                href = link_el.get_attribute("href") or ""
            if not href:
                # Build a candidate URL from the card's ng-scope data if possible
                href = page.url  # fallback
            if href and not href.startswith("http"):
                href = "https://www.instahyre.com" + href

            # "View »" opens an inline MODAL on the same page (not a new tab)
            jd_text = ""
            try:
                view_btn = card.query_selector("#interested-btn, .button-interested")
                if view_btn:
                    view_btn.click()
                    _human_delay(1.2, 2.0)
                    # Wait for modal to appear
                    try:
                        page.wait_for_selector(
                            ".modal.in, .modal[style*='display: block'], "
                            ".modal-dialog, [class*='opportunity-modal']",
                            timeout=6000)
                    except PWTimeout:
                        pass

                    modal = page.query_selector(
                        ".modal.in, .modal[style*='display: block'], .modal-dialog")
                    if modal:
                        # Update title/company from modal (more accurate)
                        modal_title = modal.query_selector("h2, h3, .modal-title, [class*='job-title']")
                        modal_company = modal.query_selector(".company-name, h4 a, [class*='company']")
                        if modal_title:
                            t = modal_title.inner_text().strip().split("\n")[0]
                            if t and len(t) > 2:
                                title = t
                        if modal_company:
                            c = modal_company.inner_text().strip().split("\n")[0]
                            if c and len(c) > 1:
                                company = c

                        jd_el = modal.query_selector(
                            ".job-description, [class*='description'], .jd-text, p")
                        if jd_el:
                            jd_text = jd_el.inner_text().strip()[:3000]

                        # Close modal
                        close_btn = page.query_selector(
                            ".modal .close, .modal button.close, [data-dismiss='modal']")
                        if close_btn:
                            close_btn.click()
                        else:
                            page.keyboard.press("Escape")
                        _human_delay(0.5, 1.0)
            except Exception as e:
                log.warning(f"Instahyre: modal JD error — {e}")

            jobs.append(ScrapedJob(
                title=title, company=company, location=location,
                apply_url=href, jd_text=jd_text,
                source="instahyre", easy_apply=True,
            ))
            log.info(f"Instahyre: {title} @ {company}")
            _human_delay(0.5, 1.0)

        except Exception as e:
            log.warning(f"Instahyre: card parse error — {e}")
            continue

    return jobs


def scrape_instahyre(
    keywords: List[str],
    blacklist: List[str] = [],
    max_jobs: int = 30,
) -> List[ScrapedJob]:
    all_jobs: List[ScrapedJob] = []
    seen_urls: set = set()

    session_file = os.path.abspath(_SESSION_FILE)
    session = session_file if os.path.exists(session_file) else None
    if not session:
        log.error("Instahyre session not found. Run: python setup_sessions.py")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            storage_state=session,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        log.info("Instahyre: loaded saved session")

        for keyword in keywords:
            if len(all_jobs) >= max_jobs:
                break
            log.info(f"Instahyre: searching '{keyword}'")
            try:
                for job in _search_and_extract(page, keyword, blacklist):
                    if job.apply_url not in seen_urls and len(all_jobs) < max_jobs:
                        seen_urls.add(job.apply_url)
                        all_jobs.append(job)
            except Exception as e:
                log.warning(f"Instahyre: search failed for '{keyword}' — {e}")
            _human_delay(2.0, 3.5)

        browser.close()

    log.info(f"Instahyre total scraped: {len(all_jobs)} jobs")
    return all_jobs
