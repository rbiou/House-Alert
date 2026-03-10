"""
gtf.py

Scraper for GTF real estate agency.
"""

import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

import psycopg2.extensions
from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'GTF'
URL = 'https://www.gtf.fr/fr/liste-des-biens-loueur'


async def notify_gtf_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        all_houses = soup.find_all('div', {'class': 'property property__search-item'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        for house in all_houses:
            url = house.find('a', {'class': 'link__property full-link'}).get('href').strip()
            item_id = url.rsplit('-', 1)[-1]
            url = 'https://www.gtf.fr' + url

            city = re.sub(r'\s+', '', house.find('div', {'class': 'property__summary'}).find('div').text.split('-')[0]).upper()
            if city != 'PARIS':
                continue

            log(f'Check if {item_id} deal already notified', PROVIDER)
            db_cursor = conn.cursor()
            db_cursor.execute(
                'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                {'id': item_id, 'provider': PROVIDER},
            )
            result = db_cursor.fetchone()
            count = result[0] if result else 0
            db_cursor.close()

            if count == 0:
                size = house.find('div', {'class': 'property-surface property-data--center'}).text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'

                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')

                price = house_details.find('span', {'class': 'price'}).text.strip()
                address = 'Paris'
                images = ['https://www.gtf.fr' + img.get('src').strip() for img in house.find_all('img')]

                if check_price_in_range(price, size):
                    log(f"New listing: {PROVIDER} - {address} - {size} - {price} => {url}", domain=PROVIDER)
                    content = NOTIFICATION_CONTENT.format(
                        provider=PROVIDER,
                        price=price,
                        address=address,
                        addressLink=urllib.parse.quote(address, safe='/'),
                        size=size,
                        url=url,
                    )
                    await send_notification(content, images)
                    insert_cursor = conn.cursor()
                    insert_cursor.execute(
                        'INSERT INTO public.alert (unique_id, provider, creation_date) VALUES (%(id)s, %(provider)s, CURRENT_TIMESTAMP)',
                        {'id': item_id, 'provider': PROVIDER},
                    )
                    insert_cursor.close()
                    conn.commit()
                else:
                    log(f"Not in price/size range. Size: {size}; Price: {price}")
            else:
                log('Already notified', PROVIDER)

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
