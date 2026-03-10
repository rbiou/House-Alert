"""
gtf.py

Scraper for GTF real estate agency.
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

PROVIDER = 'GTF'
URL = 'https://www.gtf.fr/fr/liste-des-biens-loueur'


async def notify_gtf_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        # FRAGILE: listing cards are <div class="property property__search-item">
        soup = fetch(URL)
        all_houses = soup.find_all('div', {'class': 'property property__search-item'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: link is in <a class="link__property full-link">
            link_tag = house.find('a', {'class': 'link__property full-link'})
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('-', 1)[-1]
            url = 'https://www.gtf.fr' + url

            # FRAGILE: city is extracted from <div class="property__summary"> > first <div>,
            # split on '-', whitespace stripped, uppercased
            summary_div = house.find('div', {'class': 'property__summary'})
            if summary_div is None:
                log(f'Could not find summary div for {item_id} — skipping', PROVIDER)
                continue
            first_div = summary_div.find('div')
            if first_div is None:
                log(f'Could not find city div for {item_id} — skipping', PROVIDER)
                continue
            city = re.sub(r'\s+', '', first_div.text.split('-')[0]).upper()
            if city != 'PARIS':
                continue  # Skip non-Paris listings

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: size in <div class="property-surface property-data--center">
            size_div = house.find('div', {'class': 'property-surface property-data--center'})
            if size_div is None:
                log(f'Could not find size for {item_id} — skipping', PROVIDER)
                continue
            size = re.findall(r'\d+', size_div.text.strip())[0] + 'm2'

            # FRAGILE: price in <span class="price"> on the detail page
            house_details = fetch(url)
            price_tag = house_details.find('span', {'class': 'price'})
            if price_tag is None:
                log(f'Could not find price on {url} — skipping', PROVIDER)
                continue

            price = price_tag.text.strip()
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
                mark_notified(db_cursor, conn, item_id, PROVIDER)
            else:
                log(f"Not in price/size range. Size: {size}; Price: {price}")

        log('Closing db cursor...', PROVIDER)
        db_cursor.close()

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
