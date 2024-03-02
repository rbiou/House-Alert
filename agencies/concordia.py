import json
from time import sleep
from traceback import print_exc
from random import randint, random
from requests import get
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
from pandas import pandas as pd
from utils.utils import log
from utils.notify import send_notification
from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion

from datetime import datetime, timezone, timedelta

from pprint import pprint

PROVIDER='CONCORDIA'
URL='https://agenceconcordia.com/nos-appartements-a-la-location/'
def notify_concordia_results():
    try:
        log('Start scrap agency...', PROVIDER)
	    #Read datas from Concordia
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml') # lxml is faster but a dependency, "html.parser" is quite fast and installed by default
        allHouse = soup.find_all('div', { 'class': 'col-md-6 listing_wrapper' })
        log('{0} house(s) found'.format(len(allHouse)), PROVIDER)
        #Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        #For each alert requested, check event and deals
        for house in allHouse:
            city = house.find('div', { 'class': 'property_location_image' }).find_all('a')[-1].text
            if (city == 'Paris'):
                id = house.get('data-listid').strip()
                log('Check if {0} deal already notified'.format(id), PROVIDER)
                db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s', {'id': id, 'provider': PROVIDER})
                count = db_cursor.fetchone()[0]
                if count == 0:
                    price = house.find('div', {'class': 'listing_unit_price_wrapper'}).text.strip()
                    size = house.find('span', {'class': 'infosize'}).find('span').text.strip()
                    address = house.find('h4').text.strip()
                    url = house.get('data-modal-link')
                    images = [house.find('img').get('src').strip()]
                    item = "{provider} - {address} - {size} - {price}".format(provider=PROVIDER, address=address, size=size, price=price)
                    log("New house : {item} => {url}".format(item=item, url=url), domain=PROVIDER)
                    content = NOTIFICATION_CONTENT.format(
                        provider = PROVIDER,
                        price = price,
                        address = address,
                        size = size,
                        url = url
                    )
                    # Send notification
                    send_notification(content, images)
                    # Add alert to DB
                    db_cursor.execute('INSERT INTO public.alert (unique_id, provider) VALUES (%(id)s, %(provider)s)', {'id': id, 'provider': PROVIDER})
                    db.commit()
                else:
                   log('Alreay notified', PROVIDER)
        log('Close db...', PROVIDER)
        db_cursor.close()
        db.close()
    except Exception:
        log('Exception catched', PROVIDER)
        print_exc()