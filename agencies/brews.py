"""
brews.py

Scraper for Brews real estate agency.
"""

import re
import urllib.parse
from traceback import print_exc

import psycopg2.extensions
from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db import is_notified, mark_notified
from utils.http import fetch
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Brews'
URL = (
    'https://www.brews.fr/recherche?a=2&b%5B%5D=appt&b%5B%5D=house'
    '&c=Paris%2C+&radius=0&d=0&x=illimit%C3%A9&do_search=Rechercher'
)
PREFIX_URL = 'https://www.brews.fr'


async def notify_brews_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        # FRAGILE: relies on class 'res_div1' for listing cards
        soup = fetch(URL)
        all_houses = soup.find_all('div', {'class': 'res_div1'})

        # FRAGILE: filters out sold listings via bandeau with data-rel='loue'
        all_houses = [
            h for h in all_houses
            if not h.find('div', attrs={'class': 'bandeau_small bandeau_text', 'data-rel': 'loue'})
        ]
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: link is in <a class="prod_details btn small">
            link_tag = house.find('a', {'class': 'prod_details btn small'})
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('/')[-1].rsplit('_')[-1].rsplit('.')[0]
            url = PREFIX_URL + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: detail page uses itemprop='price', <td text='Surface'>, <td text='Ville'>
            house_details = fetch(url)

            price_tag = house_details.find('td', {'itemprop': 'price'})
            surface_tag = house_details.find('td', text='Surface')
            ville_tag = house_details.find('td', text='Ville')
            slideshow = house_details.find(class_='prod_slideshow_container')

            if not all([price_tag, surface_tag, ville_tag, slideshow]):
                log(f'Missing detail fields on {url} — skipping', PROVIDER)
                continue

            price = price_tag['content'].strip() + '€'
            size = re.findall(r'\d+', surface_tag.find_next_sibling('td').text.strip())[0] + 'm2'
            address = ville_tag.find_next_sibling('td').text.strip()

            # FRAGILE: image URLs use '_s.<ext>' (small); replaced with '_l.<ext>' (large)
            images_div = slideshow.find_all('img')
            images = [re.sub(r"_s\.([^.]+)$", r"_l.\1", img.get('src').strip()) for img in images_div]

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
