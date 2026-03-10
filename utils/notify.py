"""
notify.py

Telegram notification logic.
Sends a media group (up to 3 images) or a plain text message to the configured chat.
"""

import os
import time

from dotenv import load_dotenv
from telegram import Bot, InputMediaPhoto
from telegram.error import RetryAfter, TimedOut

from utils.utils import log

# Load .env if present (no-op in production where env vars are injected directly)
load_dotenv()

TELEGRAM_KEY = os.getenv("TELEGRAM_KEY")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_KEY or not CHAT_ID:
    raise ValueError("TELEGRAM_KEY or CHAT_ID not set. Please check your .env or environment variables.")

log("Connecting to the Telegram API", "Telegram")
bot = Bot(TELEGRAM_KEY)


async def send_notification(content: str, images: list) -> None:
    """Send a Telegram notification with optional images.

    Sends a media group if images are provided (up to 3), or a plain text
    message otherwise. Retries automatically on flood-control or timeout errors.

    :param content: Markdown-formatted message text.
    :param images:  List of image URLs or file-like objects.
    """
    log("Notifying user about a new listing", "Telegram")
    try:
        if images:
            images_to_send = []
            for index, image in enumerate(images[:3]):
                media = image if hasattr(image, "read") else image.strip()
                images_to_send.append(InputMediaPhoto(
                    media=media,
                    caption=content if index == 0 else "",
                    parse_mode="Markdown",
                ))
            await bot.send_media_group(chat_id=CHAT_ID, media=images_to_send)
        else:
            await bot.send_message(chat_id=CHAT_ID, text=content)
    except RetryAfter:
        log("Flood control triggered — waiting 30s before retrying", "Telegram")
        time.sleep(30)
        await send_notification(content, images)
    except TimedOut:
        log("Request timed out — retrying", "Telegram")
        await send_notification(content, images)
