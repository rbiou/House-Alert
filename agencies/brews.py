"""
brews.py

Scraper for Brews real estate agency.
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

PROVIDER = 'Brews'
URL = (
    'https://www.brews.fr/recherche?a=2&b%5B%5D=appt&b%5B%5D=house'
    '&c=Paris%2C+&radius=0&d=0&x=illimit%C3%A9&do_search=Rechercher'
)
PREFIX_URL = 'https://www.brews.fr'


async def notify_brews_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        all_houses = soup.find_all('div', {'class': 'res_div1'})
        all_houses = [h for h in all_houses if not h.find('div', attrs={'class': 'bandeau_small bandeau_text', 'data-rel': 'loue'})]
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            url = house.find('a', {'class': 'prod_details btn small'}).get('href').strip()
            item_id = url.rsplit('/')[-1].rsplit('_')[-1].rsplit('.')[0]
            url = PREFIX_URL + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            db_cursor.execute(
                'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                {'id': item_id, 'provider': PROVIDER},
            )
            count = db_cursor.fetchone()[0]

            if count == 0:
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')

                price = house_details.find('td', {'itemprop': 'price'})['content'].strip() + '€'
                size = house_details.find('td', text='Surface').find_next_sibling('td').text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'
                address = house_details.find('td', text='Ville').find_next_sibling('td').text.strip()
                images_div = house_details.find(class_='prod_slideshow_container').find_all('img')
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
