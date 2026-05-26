"""Debug — find apply button by text"""
import os, time
from dotenv import load_dotenv
load_dotenv()
from playwright.sync_api import sync_playwright

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()

    page.goto("https://www.linkedin.com/login")
    page.fill("#username", EMAIL)
    time.sleep(1)
    page.fill("#password", PASSWORD)
    time.sleep(0.5)
    page.click('[type="submit"]')
    page.wait_for_url("**/feed/**", timeout=20000)
    print("Logged in")

    page.goto("https://www.linkedin.com/jobs/search/?keywords=Backend+Developer&location=Remote&f_E=2%2C3&f_TPR=r86400")
    time.sleep(3)

    links = page.eval_on_selector_all(
        "a.job-card-list__title--link, a.job-card-container__link",
        "els => els.map(e => e.href)"
    )
    print(f"Found {len(links)} links: {links[0] if links else 'none'}")

    if links:
        page.goto(links[0], timeout=20000)
        time.sleep(4)

        # Try text-based selectors
        apply_text = page.query_selector("button:has-text('Easy Apply'), button:has-text('Apply now'), button:has-text('Apply')")
        print(f"\nApply button by text: {apply_text}")

        # Check page title
        title = page.title()
        print(f"Page title: {title}")

        # Check if we got redirected (not logged in?)
        print(f"Current URL: {page.url}")

        # Print full page text snippet
        body_text = page.inner_text("body")[:500]
        print(f"\nPage text snippet:\n{body_text}")

    input("Press Enter to close...")
    browser.close()
