"""
notify.py

Telegram notification logic.
Sends a media group (up to 3 images) or a plain text message to the configured chat.
"""

import asyncio
import os

from dotenv import load_dotenv
from telegram import Bot, InputMediaPhoto
from telegram.error import NetworkError, RetryAfter, TimedOut

from utils.utils import log

# Load .env if present (no-op in production where env vars are injected directly)
load_dotenv()

TELEGRAM_KEY = os.getenv("TELEGRAM_KEY")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_KEY or not CHAT_ID:
    raise ValueError("TELEGRAM_KEY or CHAT_ID not set. Please check your .env or environment variables.")

log("Connecting to the Telegram API", "Telegram")
bot = Bot(TELEGRAM_KEY)

_MAX_RETRIES = 3


async def send_notification(content: str, images: list, _retries: int = 0) -> None:
    """Send a Telegram notification with optional images.

    Sends a media group if images are provided (up to 3), or a plain text
    message otherwise. Retries automatically on flood-control or timeout errors,
    up to _MAX_RETRIES times.

    :param content:  Markdown-formatted message text.
    :param images:   List of image URLs or file-like objects.
    :param _retries: Internal retry counter — do not pass manually.
    """
    log("Notifying user about a new listing", "Telegram")
    try:
        if images:
            images_to_send = [
                InputMediaPhoto(
                    media=image if hasattr(image, "read") else image.strip(),
                    caption=content if index == 0 else "",
                    parse_mode="Markdown",
                )
                for index, image in enumerate(images[:3])
            ]
            await bot.send_media_group(chat_id=CHAT_ID, media=images_to_send)
        else:
            await bot.send_message(chat_id=CHAT_ID, text=content)

    except RetryAfter as e:
        if _retries >= _MAX_RETRIES:
            log(f"Flood control: max retries ({_MAX_RETRIES}) reached, giving up", "Telegram")
            return
        wait = getattr(e, 'retry_after', 30)
        log(f"Flood control triggered — waiting {wait}s before retrying (attempt {_retries + 1}/{_MAX_RETRIES})", "Telegram")
        await asyncio.sleep(wait)
        await send_notification(content, images, _retries + 1)

    except (TimedOut, NetworkError) as e:
        if _retries >= _MAX_RETRIES:
            log(f"Network error: max retries ({_MAX_RETRIES}) reached, giving up. Error: {e}", "Telegram")
            return
        log(f"Network error — retrying (attempt {_retries + 1}/{_MAX_RETRIES}): {e}", "Telegram")
        await asyncio.sleep(2 ** _retries)  # exponential back-off: 1s, 2s, 4s
        await send_notification(content, images, _retries + 1)
