"""
Instahyre apply.

Instahyre applications are profile-based: your Instahyre profile and resume go
to the employer when you click "Apply" in a job's detail modal. There's no form.

Jobs have no stable per-job URL, so the scraper stores the search-results page
it found the job on. This opens that page, finds the card by company + title,
opens its modal (.application-modal-wrap) and clicks Apply
(ng-click="submitChoice(opp, true)"). It never touches "Not interested"
(submitChoice(opp, false)) and skips jobs that only apply on the company site.
"""

import os
import time
import random
import logging

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

from src.profile import UserProfile

log = logging.getLogger(__name__)

_SESSION_FILE = os.path.join(os.path.dirname(__file__), "../../sessions/instahyre.json")
_OPPORTUNITIES = "https://www.instahyre.com/candidate/opportunities/?matching=true"
_MODAL = ".application-modal-wrap"
_APPLY = "[ng-click='submitChoice(opp, true)']"


def _delay(a: float = 0.8, b: float = 1.8) -> None:
    time.sleep(random.uniform(a, b))


def _find_card(page: Page, company: str, role: str):
    want_company, want_role = company.lower().strip(), role.lower().strip()
    for card in page.query_selector_all(".employer-block"):
        try:
            head = card.inner_text().split("\n")[0].lower()  # "Company - Job Title"
        except Exception:
            continue
        if want_company in head and want_role in head:
            return card
    return None


def _visible(page: Page, sel: str):
    el = page.query_selector(sel)
    return el if el and el.is_visible() else None


def apply_instahyre(
    apply_url: str,
    company: str,
    role: str,
    jd_summary: str,
    pdf_path: str,
    profile: UserProfile,
    dry_run: bool = False,
) -> bool:
    session_file = os.path.abspath(_SESSION_FILE)
    if not os.path.exists(session_file):
        log.error("Instahyre session not found — run setup_sessions.py instahyre")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        ctx = browser.new_context(
            storage_state=session_file,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        log.info(f"Instahyre Apply: '{role}' @ {company}")
        try:
            urls = [apply_url] if "instahyre.com/candidate/opportunities" in apply_url else []
            urls.append(_OPPORTUNITIES)
            card = None
            for url in urls:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                if "/login" in page.url:
                    log.warning("Instahyre session expired — run setup_sessions.py instahyre")
                    return False
                try:
                    page.wait_for_selector(".employer-block", timeout=15000)
                except PWTimeout:
                    continue
                _delay(1.0, 2.0)
                card = _find_card(page, company, role)
                if card:
                    break
            if not card:
                log.warning(f"Instahyre: '{role}' @ {company} is no longer in your opportunities list")
                return False

            view = card.query_selector(".btn-interested") or card.query_selector("#employer-profile-opportunity")
            view.click()
            try:
                page.wait_for_selector(_MODAL, state="visible", timeout=10000)
            except PWTimeout:
                log.warning("Instahyre: job details didn't open")
                return False
            _delay(1.0, 1.8)

            modal_text = page.query_selector(_MODAL).inner_text()
            if role.lower() not in modal_text.lower():
                log.warning("Instahyre: opened the wrong job's details — stopping to be safe")
                return False

            apply_btn = _visible(page, f"{_MODAL} {_APPLY}")
            if not apply_btn:
                if _visible(page, f"{_MODAL} button:has-text('Apply on company site')"):
                    log.warning("Instahyre: this job only takes applications on the company site")
                else:
                    log.warning("Instahyre: Apply button not found (already applied or job closed)")
                return False

            if dry_run:
                log.info(f"DRY RUN — would click Apply on Instahyre: '{role}' @ {company}")
                return True

            apply_btn.click()
            _delay(2.5, 3.5)
            # After applying, Instahyre either closes the modal or moves it on to the
            # next opportunity. Either way this job's Apply button is gone.
            still_here = _visible(page, f"{_MODAL} {_APPLY}")
            if still_here and role.lower() in page.query_selector(_MODAL).inner_text().lower():
                log.warning("Instahyre: clicked Apply but the job is still showing — check it by hand")
                return False
            if _visible(page, f"{_MODAL} textarea, {_MODAL} input[type='text']"):
                log.warning("Instahyre: employer asked screening questions — finish by hand")
                return False
            log.info(f"✅ Applied (Instahyre): '{role}' @ {company}")
            return True
        except Exception as e:
            log.error(f"Instahyre Apply error: {e}")
            return False
        finally:
            browser.close()
