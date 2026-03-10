"""
inli.py

Scraper for In'li real estate agency.
"""

from io import BytesIO
import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

import psycopg2.extensions
import requests
from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Inli'
URL = (
    'https://www.inli.fr/locations/offres/paris-departement_d:75/'
    '?price_min=0&price_max=1500&area_min=25&area_max=200'
    '&room_min=0&room_max=5&bedroom_min=0&bedroom_max=5&lat=&lng=&zoom=&radius='
)


async def notify_inli_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        featured_parent = soup.find('div', {'class': 'featured-items white-background'})
        all_houses = featured_parent.find_all('div', {'class': 'featured-item'}) if featured_parent else []
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            url = house.find('a').get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            url = 'https://www.inli.fr' + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            db_cursor.execute(
                'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                {'id': item_id, 'provider': PROVIDER},
            )
            count = db_cursor.fetchone()[0]

            if count == 0:
                price = (
                    (house.find('div', {'class': 'featured-price'}) or {})
                    .find('span', {'class': 'demi-condensed'})
                    .get_text(strip=True) or '0 €'
                )
                size = (
                    re.search(
                        r'(\d+(?:[.,]\d+)?)\s*m²',
                        (house.find('div', {'class': 'featured-details'}) or {})
                        .find('span').get_text(strip=True) or '0',
                    ).group(1).replace(',', '.')
                ) + ' m²'

                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                address = 'Paris'

                images_div = house_details.find('div', {'class': 'advert-page-images'})
                images = [
                    BytesIO(r.content)
                    for img_tag in (images_div or []).find_all('img')[:3]
                    for r in [requests.get(img_tag.get('src').strip())]
                    if r.ok
                ]

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
