"""
Main.py

The main script
"""
import json
from time import sleep
from traceback import print_exc
from random import randint, random
from requests import get
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from pandas import pandas as pd
import config
from utils import log
from notify import send_notification
from constants import NOTIFICATION_CONTENT
from datetime import datetime, timezone, timedelta
from pprint import pprint
from concordia import notify_concordia_results

def get_houses_and_notify():
    notify_concordia_results()

get_houses_and_notify()