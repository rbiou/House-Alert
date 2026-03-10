"""
dupleix.py

Scraper for Agence Dupleix real estate agency.
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

PROVIDER = 'Agence Dupleix'
URL = (
    'https://www.dupleix.com/index.php?action=searchresults&sortby=prix&sorttype=ASC&ref='
    '&type=Location&bien=Appartements&Villes=PARIS&prix-min=&prix-max=1500&Nbre_pieces-min='
    '&Nbre_pieces-max=&Nbre_ch-min=&Nbre_ch-max=&Surface_h-min=25&Surface_h-max='
    '&surface_t-min=&surface_t-max='
)
PREFIX_URL = 'https://www.dupleix.com/'


async def notify_dupleix_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        # FRAGILE: this site uses latin-1 encoding — do NOT change to utf-8
        # FRAGILE: listing cards are <div class="single-featured-property mb-50">
        soup = fetch(URL, encoding='latin-1')
        all_houses = soup.find_all('div', {'class': 'single-featured-property mb-50'})
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            # FRAGILE: link is in <a class="btn south-btn">
            link_tag = house.find('a', {'class': 'btn south-btn'})
            if link_tag is None:
                log('Could not find listing link — skipping', PROVIDER)
                continue

            url = link_tag.get('href').strip()
            item_id = url.rsplit('/')[-1].rsplit('_')[-1].rsplit('.')[0]
            url = PREFIX_URL + url

            # FRAGILE: size is on the listing card in <div class="space"> > <span>
            space_div = house.find('div', class_='space')
            if space_div is None:
                log(f'Could not find size for {item_id} — skipping', PROVIDER)
                continue
            size_span = space_div.find('span')
            if size_span is None:
                log(f'Could not find size span for {item_id} — skipping', PROVIDER)
                continue
            size = re.findall(r'\d+', size_span.text.strip())[0] + 'm2'

            log(f'Check if {item_id} deal already notified', PROVIDER)
            if is_notified(db_cursor, item_id, PROVIDER):
                log('Already notified', PROVIDER)
                continue

            # FRAGILE: detail page also uses latin-1
            # FRAGILE: price in <div class="list-price">; address from <h1> text after last '-'
            # FRAGILE: images from <a data-fancybox="gallery"> href attributes
            house_details = fetch(url, encoding='latin-1')

            price_div = house_details.find('div', {'class': 'list-price'})
            h1_tag = house_details.find('h1')

            if not all([price_div, h1_tag]):
                log(f'Missing detail fields on {url} — skipping', PROVIDER)
                continue

            price = re.findall(r'\d+', price_div.text.strip())[0] + '€'
            address = h1_tag.text.split('-')[-1].strip() + ' Paris'
            images = [
                PREFIX_URL + a.get('href').strip()
                for a in house_details.find_all('a', {'data-fancybox': 'gallery'})
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
