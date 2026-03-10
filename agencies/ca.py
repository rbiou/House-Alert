"""
ca.py

Scraper for Crédit Agricole Immobilier real estate agency.
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

PROVIDER = 'Crédit Agricole Immobilier'
URL = (
    'https://www.ca-immobilier.fr/louer/recherche?minarea=25&maxprice=1500&sortby='
    '&codes=75000%3Aparis%3A75056&sections=location&types=appartment'
    '&zones=&distance=0&displayMode=mosaic'
)


async def notify_ca_results(conn: psycopg2.extensions.connection) -> None:
    try:
        log('Start scraping agency...', PROVIDER)

        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        all_houses = soup.find_all('article', {'class': 'sub_card-entities'})
        all_houses = [d for d in all_houses if d.find('div', {'class': 'sub_card-entities--infos'})]
        log(f'{len(all_houses)} house(s) found', PROVIDER)

        db_cursor = conn.cursor()

        for house in all_houses:
            url = house.find('a', {'data-tc-category': 'Bouton biens'}).get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            url = 'https://www.ca-immobilier.fr' + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            db_cursor.execute(
                'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                {'id': item_id, 'provider': PROVIDER},
            )
            count = db_cursor.fetchone()[0]

            if count == 0:
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')

                price = int(re.sub(r'\D', '', house_details.find('strong', {'class': 'mention-charge-comprise'}).get_text(strip=True) or '0'))
                price = f"{price}€"
                size = house_details.find('h4', {'class': 'picto_surface'}).find('span').text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'
                address = (
                    house_details.find('h3', {'class': 'prog_title'}).text.strip()
                    + ', '
                    + house_details.find('h3', {'class': 'prog_city'}).text.strip()
                )
                images_div = house_details.find('div', {'class': 'block_apercu-bien__bg block_apercu-bien__bg--partial'})
                images_div = images_div.find_all('img') if images_div else []
                images = [('https://www.ca-immobilier.fr' + img.get('src').strip()) for img in images_div]

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
