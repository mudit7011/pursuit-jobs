"""
Run this ONCE locally to find your Telegram group ID.
Copy the ID of the SDE Jobs group into .env as TELEGRAM_GROUP_ID=...

Usage:
  1. Make sure .env has all Telegram credentials including TELEGRAM_SESSION_STRING
  2. Run: python3 get_group_id.py
"""
import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session = os.environ["TELEGRAM_SESSION_STRING"]

with TelegramClient(StringSession(session), api_id, api_hash) as client:
    print("\nYour groups and channels:\n")
    for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            print(f"ID: {dialog.id:<20} Name: {dialog.name}")
