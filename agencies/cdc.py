"""
cdc.py

Scraper for CDC Habitat real estate agency.
"""

import re
import urllib.parse
from traceback import print_exc

import psycopg2.extensions

from utils.constants import NOTIFICATION_CONTENT
from utils.db import is_notified, mark_notified
from utils.http import fetch
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

        # FRAGILE: listing cards are <article class="residenceCard">
        soup = fetch(URL)
        all_houses = soup.find_all('article', {'class': 'residenceCard'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: link is the first <a> in the card
            link_tag = house.find('a')
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('/', 1)[-1]

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: price in <div class="price">
            # FRAGILE: size extracted via regex '(\d+)\s*m²' from <h3 class="h4"> text
            # FRAGILE: address in <div class="location small">
            price_tag = house.find('div', {'class': 'price'})
            h3_tag = house.find('h3', {'class': 'h4'})
            address_tag = house.find('div', {'class': 'location small'})

            if not all([price_tag, h3_tag, address_tag]):
                log(f'Missing detail fields on {url} — skipping', PROVIDER)
                continue

            price = price_tag.text.strip()
            raw_h3 = h3_tag.get_text(strip=True)
            size_match = re.search(r'(\d+)\s*m²', raw_h3)
            size = int(size_match.group(1)) if size_match else 0
            address = address_tag.text.strip()
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
                mark_notified(db_cursor, conn, item_id, PROVIDER)
            else:
                log(f"Not in price/size range. Size: {size}; Price: {price}")

        log('Closing db cursor...', PROVIDER)
        db_cursor.close()

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
