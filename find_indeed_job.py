"""
Find an Indeed job URL with apply button — uses clean viewjob URL (no vjs param).
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

import time, re
from playwright.sync_api import sync_playwright

SESSION = "sessions/indeed.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        storage_state=SESSION,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.new_page()
    page.goto("https://in.indeed.com/jobs?q=software+engineer&l=Remote&jt=fulltime&fromage=1", timeout=30000)
    time.sleep(3)

    # Extract job keys (jk) from card hrefs
    jks = page.eval_on_selector_all(
        ".job_seen_beacon, .tapItem",
        """els => els.slice(0, 15).map(el => {
            const linkEl = el.querySelector('h2.jobTitle a, a.jcs-JobTitle');
            if (!linkEl) return null;
            const m = linkEl.href.match(/jk=([a-z0-9]+)/);
            const titleEl = el.querySelector('h2.jobTitle span[title], h2.jobTitle a span, h2.jobTitle span');
            const coEl = el.querySelector('[data-testid="company-name"], .companyName');
            return {
                jk: m ? m[1] : null,
                title: titleEl ? titleEl.innerText.trim() : '',
                company: coEl ? coEl.innerText.trim() : ''
            };
        }).filter(x => x && x.jk)"""
    )

    print(f"\nFound {len(jks)} jobs. Checking clean URLs for apply button...\n")

    for item in jks[:8]:
        clean_url = f"https://in.indeed.com/viewjob?jk={item['jk']}"
        try:
            page.goto(clean_url, timeout=15000)
            time.sleep(2)

            btns = page.evaluate("""() =>
                [...document.querySelectorAll('button, a')]
                .map(e => e.innerText.trim().slice(0, 60))
                .filter(t => t.length > 1 && t.length < 50 &&
                    (t.toLowerCase().includes('apply') || t.toLowerCase().includes('apply')))
            """)

            all_btns = page.evaluate("""() =>
                [...document.querySelectorAll('button')]
                .map(e => e.innerText.trim().slice(0, 60))
                .filter(t => t.length > 1)
            """)

            print(f"Job: {item['title']} @ {item['company']}")
            print(f"  URL: {clean_url}")
            print(f"  Apply buttons: {btns}")
            print(f"  All buttons:   {all_btns[:10]}")
            print()
        except Exception as e:
            print(f"  Error: {e}")

    browser.close()
