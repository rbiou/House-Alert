import json
import time
import re
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

PROVIDER='Inli'
URL='https://www.inli.fr/locations/offres/paris-departement_d:75/?price_min=0&price_max=900&area_min=20&area_max=200&room_min=0&room_max=5&bedroom_min=0&bedroom_max=5&lat=&lng=&zoom=&radius='
def notify_inli_results():
    try:
        log('Start scrap agency...', PROVIDER)
	    #Read datas from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml') # lxml is faster but a dependency, "html.parser" is quite fast and installed by default
        allHouse = soup.find_all('li', { 'class': 'liste-bien-item' })
        log('{0} house(s) found'.format(len(allHouse)), PROVIDER)
        #Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        #For each alert requested, check event and deals
        for house in allHouse:
            url = house.find('a').get('href').strip()
            id = url.rsplit('/', 1)[-1]
            url = 'https://www.inli.fr' + url
            log('Check if {0} deal already notified'.format(id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s', {'id': id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                price = house.find('p', {'class': 'liste-bien-item-price'}).text.strip()
                size = house.find('p', {'class': 'liste-bien-item-description'}).text.replace('"', '').rsplit('de ', 1)[-1].strip()
                size = re.findall('\d+', size)[0] + 'm2'
                houseDetailsContent = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                houseDetails = BeautifulSoup(houseDetailsContent.decode('utf-8'), 'lxml')
                address = houseDetails.find('li', {'class': 'propos__attributs__section__list__item propos__attributs__section__list__item__address'}).text.strip()
                imagesDiv = houseDetails.find_all('img', {'class': 'thumbnail__image'})
                images = [img.get('src').strip() for img in imagesDiv]
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