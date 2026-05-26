"""
One-time session setup — run this manually whenever sessions expire.
Opens a real browser for each platform, you login normally (Google, email, whatever),
then press Enter and the session is saved. Scrapers reuse these sessions.
"""

import os, time
from playwright.sync_api import sync_playwright

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

PLATFORMS = [
    {
        "name": "LinkedIn",
        "file": "linkedin.json",
        "url":  "https://www.linkedin.com/login",
        "check": "**/feed/**",
    },
    {
        "name": "Indeed",
        "file": "indeed.json",
        "url":  "https://secure.indeed.com/auth",
        "check": "**/myjobs**",
    },
    {
        "name": "Naukri",
        "file": "naukri.json",
        "url":  "https://www.naukri.com/nlogin/login",
        "check": "**/mnjuser/**",
    },
    {
        "name": "Instahyre",
        "file": "instahyre.json",
        "url":  "https://www.instahyre.com/login/",
        "check": "**/home**",
    },
    {
        "name": "Wellfound",
        "file": "wellfound.json",
        "url":  "https://wellfound.com/login",
        "check": "**/jobs**",
    },
    {
        "name": "Internshala",
        "file": "internshala.json",
        "url":  "https://internshala.com/login/user",
        "check": "**/student/dashboard**",
    },
]


def setup_platform(playwright, platform: dict):
    name = platform["name"]
    path = os.path.join(SESSIONS_DIR, platform["file"])

    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"{'='*50}")

    # Load existing session if available
    existing = path if os.path.exists(path) else None

    browser = playwright.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx = browser.new_context(
        storage_state=existing,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
    )
    page = ctx.new_page()
    page.goto(platform["url"], timeout=30000)

    print(f"  Browser opened for {name}.")
    print(f"  Login manually (Google, email — whatever you use).")
    print(f"  Once you're on the home/dashboard page, come back here.")
    input(f"  Press ENTER to save {name} session... ")

    ctx.storage_state(path=path)
    browser.close()
    print(f"  Session saved → sessions/{platform['file']}")


def main():
    print("\nJob Autopilot — Session Setup")
    print("This will open a browser for each platform.")
    print("Login normally, then press Enter to save the session.\n")

    platforms_to_setup = []
    for p in PLATFORMS:
        path = os.path.join(SESSIONS_DIR, p["file"])
        if os.path.exists(path):
            age_hours = (time.time() - os.path.getmtime(path)) / 3600
            ans = input(f"  {p['name']} session exists ({age_hours:.0f}h old). Refresh? [y/N]: ").strip().lower()
            if ans == "y":
                platforms_to_setup.append(p)
        else:
            print(f"  {p['name']} — no session found, will setup.")
            platforms_to_setup.append(p)

    if not platforms_to_setup:
        print("\nAll sessions are already set up. Run with force refresh if needed.")
        return

    with sync_playwright() as p:
        for platform in platforms_to_setup:
            try:
                setup_platform(p, platform)
            except Exception as e:
                print(f"  ERROR setting up {platform['name']}: {e}")

    print("\nDone! All sessions saved. Run the bot now:")
    print("  venv/bin/python -m src.main")


if __name__ == "__main__":
    main()
