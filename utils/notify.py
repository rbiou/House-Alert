"""
Notify.py

Holds the notification logic, using the Telegram API
"""

import os
import time
from telegram import *
from telegram import InputMediaPhoto
from telegram.ext import *
from telegram.error import RetryAfter, TimedOut
from utils.utils import log
if os.path.isfile("local.py"):
    from local import TELEGRAM_KEY, CHAT_ID
else:
    TELEGRAM_KEY = os.environ['TELEGRAM_KEY']
    CHAT_ID = os.environ['CHAT_ID']
from pprint import pprint

log("Connecting to the Telegram API", "Telegram")
bot = Bot(TELEGRAM_KEY)

def send_notification(content, images):
    '''Sends a telegram notification'''
    log("Notifying user about a new product", "Telegram")
    try:
        # Send the 3 firsts images
        images_to_send = []
        for image in images[:3]:
            image_obj = InputMediaPhoto(media = image, caption = content if image == images[0] else '')
            images_to_send.append(image_obj)
        bot.send_media_group(chat_id = CHAT_ID, media = images_to_send)
    except RetryAfter:
        print("ALERT FLOOD : wait 30s")
        time.sleep(30)
        send_notification(content, images)
    except TimedOut:
        print("TIME OUT : try again")
        send_notification(content, images)