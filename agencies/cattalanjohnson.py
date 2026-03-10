"""
cattalanjohnson.py

Scraper for Cattalan Johnson real estate agency.
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

PROVIDER = 'Cattalan Johnson'
URL = (
    'https://www.cattalanjohnson.com/fr/recherche.aspx?meuble=-1&nbChambre='
    '&cp=75001,75002,75003,75004,75005,75006,'
    '75007,75008,75009,75010,75011,75012,75013,75014,75015,75016,75017,75018,75019,'
    '75020&pxmin=0&pxmax=1500&surfacemin=25&surfacemax=0#container'
)


async def notify_cattalanjohnson_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        # FRAGILE: listing cards are <div class="row liste-biens">
        soup = fetch(URL)
        all_houses = soup.find_all('div', {'class': 'row liste-biens'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: link is inside <div class="crop"> > <a>
            crop_div = house.find('div', {'class': 'crop'})
            if crop_div is None:
                log('Could not find crop div — skipping', PROVIDER)
                continue
            link_tag = crop_div.find('a')
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('/')[-2]
            url = 'https://www.cattalanjohnson.com' + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # Price is on the listing card itself (no detail page needed)
            # FRAGILE: price in <p class="prix">
            price_tag = house.find('p', {'class': 'prix'})
            if price_tag is None:
                log(f'Could not find price on {url} — skipping', PROVIDER)
                continue
            price = ''.join(re.findall(r'\d+', price_tag.text.strip())) + '€'

            # FRAGILE: surface in <div id="content_divSurface" class="col-md-3">
            # FRAGILE: postal code extracted from style attribute of <img class="img-responsive">
            house_details = fetch(url)

            surface_div = house_details.find('div', {'id': 'content_divSurface', 'class': 'col-md-3'})
            img_tag = house.find('img', {'class': 'img-responsive'})

            if surface_div is None or img_tag is None:
                log(f'Missing detail fields on {url} — skipping', PROVIDER)
                continue

            size = re.findall(r'\d+', surface_div.text.strip())[0] + 'm2'
            postal_code_match = re.search(r'map_(\d+)\.png', img_tag.get('style', '').strip())
            if postal_code_match is None:
                log(f'Could not extract postal code on {url} — skipping', PROVIDER)
                continue
            address = 'Paris ' + postal_code_match.group(1)

            # FRAGILE: images in <div class="container-miniature no-print"> > <img>
            miniature_div = house_details.find('div', {'class': 'container-miniature no-print'})
            images = [
                'https://www.cattalanjohnson.com' + img.get('src').strip()
                for img in (miniature_div.find_all('img') if miniature_div else [])
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
                mark_notified(db_cursor, conn, item_id, PROVIDER)
            else:
                log(f"Not in price/size range. Size: {size}; Price: {price}")

        log('Closing db cursor...', PROVIDER)
        db_cursor.close()

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
