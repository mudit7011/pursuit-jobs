"""Saved browser logins (sessions/<platform>.json) and whether they still work."""
import json
import os
from datetime import datetime

SESSIONS_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "sessions"))
# Cookie that proves you're logged in, per platform. None = no reliable marker known.
_AUTH_COOKIE = {
    "linkedin": "li_at", "naukri": "nauk_rt", "instahyre": "sessionid", "wellfound": "_wellfound",
    "indeed": None, "internshala": None,
}


def session_status(platform: str) -> dict:
    path = os.path.join(SESSIONS_DIR, f"{platform}.json")
    if not os.path.exists(path):
        return {"status": "missing", "saved_at": None, "expires_at": None}
    saved_at = datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
    name = _AUTH_COOKIE.get(platform)
    if not name:
        return {"status": "unknown", "saved_at": saved_at, "expires_at": None}
    try:
        with open(path) as f:
            cookies = json.load(f).get("cookies", [])
    except (OSError, ValueError):
        return {"status": "missing", "saved_at": saved_at, "expires_at": None}
    exp = max((c.get("expires", -1) for c in cookies if c.get("name") == name), default=None)
    if exp is None:
        return {"status": "expired", "saved_at": saved_at, "expires_at": None}
    if exp <= 0:  # browser-session cookie: valid until the browser closes, so unknown here
        return {"status": "unknown", "saved_at": saved_at, "expires_at": None}
    expires = datetime.fromtimestamp(exp)
    return {
        "status": "connected" if expires > datetime.now() else "expired",
        "saved_at": saved_at,
        "expires_at": expires.isoformat(timespec="seconds"),
    }



def logged_out_platforms() -> set:
    """Platforms whose saved login is known to be expired or missing."""
    return {p for p in _AUTH_COOKIE if session_status(p)["status"] in ("expired", "missing")}
