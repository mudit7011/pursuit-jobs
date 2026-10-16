import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_STRING, TELEGRAM_GROUP_ID
from src.parser import parse_job_message
from src.orchestrator import process_job

log = logging.getLogger(__name__)


async def start_monitor():
    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        TELEGRAM_API_ID,
        TELEGRAM_API_HASH
    )

    @client.on(events.NewMessage(chats=TELEGRAM_GROUP_ID))
    async def handler(event):
        message_text = event.message.text
        if not message_text or len(message_text) < 50:
            return
        log.info(f"New message received ({len(message_text)} chars)")
        try:
            job = await asyncio.to_thread(parse_job_message, message_text)
            await process_job(job)
        except Exception as e:
            log.error(f"Pipeline error: {e}")

    await client.start()
    log.info("Pursuit running — monitoring Telegram group...")
    await client.run_until_disconnected()
