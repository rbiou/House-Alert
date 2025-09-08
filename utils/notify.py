"""
Notify.py

Holds the notification logic, using the Telegram API
"""

import os
import time

from dotenv import load_dotenv

from telegram import *
from telegram import InputMediaPhoto
from telegram.error import RetryAfter, TimedOut

from utils.utils import log


# Charger le fichier .env si présent
load_dotenv()

# Récupération des variables d'environnement
TELEGRAM_KEY = os.getenv("TELEGRAM_KEY")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_KEY or not CHAT_ID:
    raise ValueError("TELEGRAM_KEY or CHAT_ID not set. Please check your .env or environment variables.")

log("Connecting to the Telegram API", "Telegram")
bot = Bot(TELEGRAM_KEY)


async def send_notification(content, images):
    # Sends a telegram notification
    log("Notifying user about a new product", "Telegram")
    try:
        if len(images) > 0:
            # Send the 3 firsts images
            images_to_send = []
            for index, image in enumerate(images[:3]):
                media = image if hasattr(image, "read") else image.strip()
                image_obj = InputMediaPhoto(
                    media=media,
                    caption=content if index == 0 else '',
                    parse_mode='Markdown'
                )
                images_to_send.append(image_obj)
            await bot.send_media_group(chat_id=CHAT_ID, media=images_to_send)
        else:
            await bot.send_message(chat_id=CHAT_ID, text=content)
    except RetryAfter:
        print("ALERT FLOOD : wait 30s")
        time.sleep(30)
        await send_notification(content, images)
    except TimedOut:
        print("TIME OUT : try again")
        await send_notification(content, images)
