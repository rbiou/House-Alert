"""
concordia.py

Scraper for Agence Concordia real estate agency.
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

PROVIDER = 'CONCORDIA'
URL = 'https://agenceconcordia.com/nos-appartements-a-la-location/'


async def notify_concordia_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        # FRAGILE: listing cards are <div class="col-md-6 listing_wrapper">
        soup = fetch(URL)
        all_houses = soup.find_all('div', {'class': 'col-md-6 listing_wrapper'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: city is the last <a> in <div class="property_location_image">
            location_div = house.find('div', {'class': 'property_location_image'})
            if location_div is None:
                log('Could not find location div — skipping', PROVIDER)
                continue
            city_links = location_div.find_all('a')
            if not city_links or city_links[-1].text != 'Paris':
                continue  # Skip non-Paris listings

            # FRAGILE: item ID and detail URL are in data attributes
            item_id = house.get('data-listid', '').strip()
            url = house.get('data-modal-link', '').strip()
            if not item_id or not url:
                log('Missing data-listid or data-modal-link — skipping', PROVIDER)
                continue

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: price in <div class="listing_unit_price_wrapper"> (dot stripped: thousands separator)
            # FRAGILE: size in <span class="infosize"> > <span>
            # FRAGILE: address in <h4>
            price_tag = house.find('div', {'class': 'listing_unit_price_wrapper'})
            size_tag = house.find('span', {'class': 'infosize'})
            address_tag = house.find('h4')

            if not all([price_tag, size_tag, address_tag]):
                log(f'Missing detail fields for {item_id} — skipping', PROVIDER)
                continue

            price = price_tag.text.strip().replace('.', '')
            size = size_tag.find('span').text.strip()
            address = address_tag.text.strip()

            # FRAGILE: images extracted from CSS background-image style of <div class="image_gallery">
            # inside <div class="gallery_wrapper">; thumbnail suffix '\-\d+x\d+' is stripped
            house_details = fetch(url)
            gallery = house_details.find('div', {'class': 'gallery_wrapper'})
            images = []
            if gallery:
                for div in gallery.find_all('div', class_='image_gallery'):
                    style = div.get('style', '')
                    if '(' in style and ')' in style:
                        img_url = style.split('(')[1].split(')')[0]
                        images.append(re.sub(r'-\d+x\d+\.', '.', img_url))

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
