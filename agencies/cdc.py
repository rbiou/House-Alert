"""
cdc.py

Scraper for CDC Habitat real estate agency.
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

PROVIDER = 'CDC Habitat'
URL = (
    'https://www.cdc-habitat.fr/Recherche/show/cdTypage=Location&order=nb_loyer_total'
    '&pagerGo=&newSearch=true&lbLieu=Paris%3B&nbLoyerMin=&nbLoyerMax=&nbSurfaceMin=&nbSurfaceMax=&'
)


async def notify_cdc_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        all_houses = soup.find_all('article', {'class': 'residenceCard'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            url = house.find('a').get('href').strip()
            item_id = url.rsplit('/', 1)[-1]

            log(f'Check if {item_id} deal already notified', PROVIDER)
            db_cursor.execute(
                'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                {'id': item_id, 'provider': PROVIDER},
            )
            count = db_cursor.fetchone()[0]

            if count == 0:
                price = house.find('div', {'class': 'price'}).text.strip()
                raw_h3 = house.find('h3', {'class': 'h4'}).get_text(strip=True)
                size_match = re.search(r'(\d+)\s*m²', raw_h3)
                size = int(size_match.group(1)) if size_match else 0
                address = house.find('div', {'class': 'location small'}).text.strip()
                images = [img.get('src').strip() for img in house.find_all('img')]

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
                    db_cursor.execute(
                        'INSERT INTO public.alert (unique_id, provider, creation_date) VALUES (%(id)s, %(provider)s, CURRENT_TIMESTAMP)',
                        {'id': item_id, 'provider': PROVIDER},
                    )
                    conn.commit()
                else:
                    log(f"Not in price/size range. Size: {size}; Price: {price}")
            else:
                log('Already notified', PROVIDER)

        log('Closing db cursor...', PROVIDER)
        db_cursor.close()

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
