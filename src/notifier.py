from telethon import TelegramClient
from telethon.sessions import StringSession
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING, TELEGRAM_SELF_ID


async def notify_self(message: str) -> None:
    async with TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    ) as client:
        await client.send_message(TELEGRAM_SELF_ID, message)


def format_success(company: str, role: str, apply_type: str, target: str) -> str:
    return (
        f"✅ Applied!\n"
        f"🏢 {company} — {role}\n"
        f"📨 Via: {apply_type} → {target}\n"
    )


def format_error(company: str, role: str, error: str) -> str:
    return (
        f"❌ Apply failed!\n"
        f"🏢 {company} — {role}\n"
        f"⚠️ Error: {error}\n"
    )
