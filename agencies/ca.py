"""
ca.py

Scraper for Crédit Agricole Immobilier real estate agency.
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

PROVIDER = 'Crédit Agricole Immobilier'
URL = (
    'https://www.ca-immobilier.fr/louer/recherche?minarea=25&maxprice=1500&sortby='
    '&codes=75000%3Aparis%3A75056&sections=location&types=appartment'
    '&zones=&distance=0&displayMode=mosaic'
)


async def notify_ca_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        # FRAGILE: listing cards are <article class="sub_card-entities">
        soup = fetch(URL)
        all_houses = soup.find_all('article', {'class': 'sub_card-entities'})
        # Keep only cards that have the info block (filters out skeleton/placeholder cards)
        all_houses = [d for d in all_houses if d.find('div', {'class': 'sub_card-entities--infos'})]
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: href is on <a data-tc-category="Bouton biens">
            link_tag = house.find('a', {'data-tc-category': 'Bouton biens'})
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            url = 'https://www.ca-immobilier.fr' + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: price in <strong class="mention-charge-comprise">, surface in <h4 class="picto_surface">
            # FRAGILE: address split across <h3 class="prog_title"> and <h3 class="prog_city">
            house_details = fetch(url)

            price_tag = house_details.find('strong', {'class': 'mention-charge-comprise'})
            size_tag = house_details.find('h4', {'class': 'picto_surface'})
            title_tag = house_details.find('h3', {'class': 'prog_title'})
            city_tag = house_details.find('h3', {'class': 'prog_city'})

            if not all([price_tag, size_tag, title_tag, city_tag]):
                log(f'Missing detail fields on {url} — skipping', PROVIDER)
                continue

            price = int(re.sub(r'\D', '', price_tag.get_text(strip=True) or '0'))
            price = f"{price}€"
            size = re.findall(r'\d+', size_tag.find('span').text.strip())[0] + 'm2'
            address = title_tag.text.strip() + ', ' + city_tag.text.strip()

            # FRAGILE: images in <div class="block_apercu-bien__bg block_apercu-bien__bg--partial">
            images_div = house_details.find('div', {'class': 'block_apercu-bien__bg block_apercu-bien__bg--partial'})
            images = [
                'https://www.ca-immobilier.fr' + img.get('src').strip()
                for img in (images_div.find_all('img') if images_div else [])
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
