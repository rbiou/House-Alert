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

PROVIDER='CDC Habitat'
URL='https://www.cdc-habitat.fr/Recherche/show/cdTypage=Location&order=nb_loyer_total&pagerGo=&newSearch=true&lbLieu=Paris%3B&nbLoyerMin=&nbLoyerMax=&nbSurfaceMin=&nbSurfaceMax=&'
def notify_cdc_results():
    try:
        log('Start scrap agency...', PROVIDER)
	    #Read datas from Concordia
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml') # lxml is faster but a dependency, "html.parser" is quite fast and installed by default
        allHouse = soup.find_all('article', { 'class': 'residenceCard' })
        log('{0} house(s) found'.format(len(allHouse)), PROVIDER)
        #Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        #For each alert requested, check event and deals
        for house in allHouse:
            url = house.find('a').get('href').strip()
            id = url.rsplit('/', 1)[-1]
            log('Check if {0} deal already notified'.format(id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s', {'id': id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                price = house.find('div', {'class': 'price'}).text.strip()
                size = house.find('h3', {'class': 'h4'}).text.rsplit('–', 1)[-1].strip()
                address = house.find('div', {'class': 'location small'}).text.strip()
                imagesDiv = house.find_all('img')
                images = [img.get('src').strip() for img in imagesDiv]
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