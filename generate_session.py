"""
Run this ONCE locally to get your Telegram session string.
Copy the output into .env as TELEGRAM_SESSION_STRING=...

Usage:
  1. Fill TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first
  2. Run: python3 generate_session.py
  3. Enter your phone number and OTP when prompted
  4. Copy the session string to .env
"""
import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n=== COPY THIS TO .env as TELEGRAM_SESSION_STRING ===")
    print(client.session.save())
    print("====================================================\n")
    me = client.get_me()
    print(f"Your Telegram User ID (TELEGRAM_SELF_ID): {me.id}")
