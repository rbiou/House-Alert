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
from utils.db import is_notified, mark_notified
from utils.http import fetch
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

        # FRAGILE: all listings are inside <div class="featured-items white-background">
        # If this wrapper is missing, the site may be down or blocking the request (e.g. 502)
        soup = fetch(URL)
        featured_parent = soup.find('div', {'class': 'featured-items white-background'})
        if featured_parent is None:
            log('Featured items wrapper not found — site may be unavailable or blocking', PROVIDER)
            return

        # FRAGILE: individual cards are <div class="featured-item">
        all_houses = featured_parent.find_all('div', {'class': 'featured-item'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: link is in the first <a> of the card
            link_tag = house.find('a')
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            url = 'https://www.inli.fr' + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: price in <div class="featured-price"> > <span class="demi-condensed">
            # FRAGILE: size extracted via regex from <div class="featured-details"> > <span> text
            price_div = house.find('div', {'class': 'featured-price'})
            details_div = house.find('div', {'class': 'featured-details'})

            price = '0 €'
            if price_div:
                price_span = price_div.find('span', {'class': 'demi-condensed'})
                if price_span:
                    price = price_span.get_text(strip=True) or '0 €'

            size = '0 m²'
            if details_div:
                size_span = details_div.find('span')
                if size_span:
                    size_match = re.search(r'(\d+(?:[.,]\d+)?)\s*m²', size_span.get_text(strip=True) or '0')
                    if size_match:
                        size = size_match.group(1).replace(',', '.') + ' m²'

            # FRAGILE: images are in <div class="advert-page-images"> on the detail page
            # Images are fetched via the `requests` library (not urllib) to get binary content for Telegram
            house_details = fetch(url)
            address = 'Paris'

            images_div = house_details.find('div', {'class': 'advert-page-images'})
            images = []
            if images_div:
                for img_tag in images_div.find_all('img')[:3]:
                    src = img_tag.get('src', '').strip()
                    if src:
                        r = requests.get(src)
                        if r.ok:
                            images.append(BytesIO(r.content))

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
                mark_notified(db_cursor, conn, item_id, PROVIDER)
            else:
                log(f"Not in price/size range. Size: {size}; Price: {price}")

        log('Closing db cursor...', PROVIDER)
        db_cursor.close()

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
