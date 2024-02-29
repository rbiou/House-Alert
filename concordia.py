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

def notify_concordia_results():
    try:
	    #Read datas from Concordia
        req = Request(url="https://agenceconcordia.com/nos-appartements-a-la-location/", headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml') # lxml is faster but a dependency, "html.parser" is quite fast and installed by default
        allHouse = soup.find_all('div', { 'class': 'col-md-6 listing_wrapper' })
        #For each alert requested, check event and deals
        for house in allHouse:
            city = house.find('div', { 'class': 'property_location_image' }).find_all('a')[-1].text
            if (city == 'Paris'):
                id = house.get('data-listid').strip()
                price = house.find('div', {'class': 'listing_unit_price_wrapper'}).text.strip()
                size = house.find('span', {'class': 'infosize'}).find('span').text.strip()
                address = house.find('h4').text.strip()
                url = house.get('data-modal-link')
                images = [house.find('img').get('src').strip()]
                item = "{address} - {size} - {price}".format(address=address, size=size, price=price)
                log("New house : {item} => {url}".format(item=item, url=url), domain="Concordia")
                content = NOTIFICATION_CONTENT.format(
                    price = price,
                    address = address,
                    size = size,
                    url = url
                )
                # Send notification
                send_notification(content, images)
    except Exception:
        print_exc()