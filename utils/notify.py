"""
Notify.py

Holds the notification logic, using the Telegram API
"""

import os
import time

from telegram import *
from telegram import InputMediaPhoto
from telegram.error import RetryAfter, TimedOut

from utils.utils import log

if os.path.isfile("local.py"):
    from local import TELEGRAM_KEY, CHAT_ID
else:
    TELEGRAM_KEY = os.environ['TELEGRAM_KEY']
    CHAT_ID = os.environ['CHAT_ID']

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
                image_obj = InputMediaPhoto(media=image, caption=content if index == 0 else '', parse_mode='Markdown')
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
