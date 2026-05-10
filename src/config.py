import os
from dotenv import load_dotenv

load_dotenv()

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val

TELEGRAM_API_ID = int(_require("TELEGRAM_API_ID"))
TELEGRAM_API_HASH = _require("TELEGRAM_API_HASH")
TELEGRAM_SESSION_STRING = _require("TELEGRAM_SESSION_STRING")
TELEGRAM_GROUP_ID = int(_require("TELEGRAM_GROUP_ID"))
TELEGRAM_SELF_ID = int(_require("TELEGRAM_SELF_ID"))

GEMINI_API_KEY = _require("GEMINI_API_KEY")

GMAIL_ADDRESS = _require("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = _require("GMAIL_APP_PASSWORD")

GOOGLE_SERVICE_ACCOUNT_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_B64", "")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

BASE_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "templates", "MuditCV.tex")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "logs", "applications.log")
