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

PROVIDER='Crédit Agricole Immobilier'
URL='https://www.ca-immobilier.fr/louer/recherche?minarea=25&minprice=500&maxprice=900&sortby=&codes=75000%3Aparis%3A75056&sections=location&types=appartment&zones=&distance=0&displayMode=mosaic'
def notify_ca_results():
    try:
        log('Start scrap agency...', PROVIDER)
	    #Read datas from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml') # lxml is faster but a dependency, "html.parser" is quite fast and installed by default
        allHouse = soup.find_all('article', {'class': 'sub_card-entities'})
        allHouse = [d for d in allHouse if d.find('div', {'class': 'sub_card-entities--infos'})]
        log('{0} house(s) found'.format(len(allHouse)), PROVIDER)
        #Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        #For each alert requested, check event and deals
        for house in allHouse:
            url = house.find('a', {'data-tc-category': 'Bouton biens'}).get('href').strip()
            id = url.rsplit('/', 1)[-1]
            url = 'https://www.ca-immobilier.fr' + url
            log('Check if {0} deal already notified'.format(id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s', {'id': id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                price = house.find('div', {'class': 'infos-price'}).find('strong').text.strip()
                houseDetailsContent = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                houseDetails = BeautifulSoup(houseDetailsContent.decode('utf-8'), 'lxml')
                size = houseDetails.find('h4', {'class': 'picto_surface'}).find('span').text.strip()
                size = re.findall('\d+', size)[0] + 'm2'
                address = houseDetails.find('h3', {'class': 'prog_title'}).text.strip() + ', ' + houseDetails.find('h3', {'class': 'prog_city'}).text.strip()
                imagesDiv = houseDetails.find('div', {'class': 'block_apercu-bien__bg block_apercu-bien__bg--partial'}).find_all('img')
                images = [('https://www.ca-immobilier.fr' + img.get('src').strip()) for img in imagesDiv]
                item = "{provider} - {address} - {size} - {price}".format(provider=PROVIDER, address=address, size=size, price=price)
                log("New house : {item} => {url}".format(item=item, url=url), domain=PROVIDER)
                content = NOTIFICATION_CONTENT.format(
                    provider = PROVIDER,
                    price = price,
                    address = address,
                    addressLink = address.replace(' ', '+'),
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