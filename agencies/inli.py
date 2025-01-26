import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Inli'
URL = ('https://www.inli.fr/locations/offres/paris-departement_d:75/?price_min=0&price_max=1500&area_min=25&area_max'
       '=200&room_min=0&room_max=5&bedroom_min=0&bedroom_max=5&lat=&lng=&zoom=&radius=')


async def notify_inli_results():
    try:
        log('Start scrap agency...', PROVIDER)

        # Fetch data from the provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        all_house = soup.find_all('li', {'class': 'liste-bien-item', 'data-id': True})
        log(f'{len(all_house)} house(s) found', PROVIDER)

        # Get database connection
        db = get_connexion()
        db_cursor = db.cursor()

        # For each property, check if it has been notified
        for house in all_house:
            url = house.find('a').get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            url = 'https://www.inli.fr' + url

            log(f'Check if {item_id} deal already notified', PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]

            if count == 0:
                price = house.find('p', {'class': 'liste-bien-item-price'}).text.strip()
                size = house.find('p', {'class': 'liste-bien-item-description'}).text.replace('"', '').rsplit('de ', 1)[-1].strip()
                size = re.findall(r'\d+', size)[0] + 'm2'

                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                address = house_details.find('li', {'class': 'propos__attributs__section__list__item propos__attributs__section__list__item__address'}).text.strip()

                images_div = house_details.find('div', {'class': 'thumbnail-container page-bien__thumbnails'}).find_all('img', {'class': 'thumbnail__image'})
                images = [img.get('src').strip() for img in images_div]

                item = f"{PROVIDER} - {address} - {size} - {price}"

                # Check if the price and size match the criteria
                if check_price_in_range(price, size):
                    log(f"New house: {item} => {url}", domain=PROVIDER)
                    content = NOTIFICATION_CONTENT.format(
                        provider=PROVIDER,
                        price=price,
                        address=address,
                        addressLink=urllib.parse.quote(address, safe='/', encoding=None, errors=None),
                        size=size,
                        url=url
                    )
                    # Send notification
                    await send_notification(content, images)

                    # Add alert to DB
                    db_cursor.execute('INSERT INTO public.alert (unique_id, provider, creation_date) VALUES (%(id)s, %(provider)s, CURRENT_TIMESTAMP)',
                                      {'id': item_id, 'provider': PROVIDER})
                    db.commit()
                else:
                    log(f"Not in price/size range. Size: {size}; Price: {price}")
            else:
                log('Already notified', PROVIDER)

        log('Close db...', PROVIDER)
        db_cursor.close()
        db.close()

    except Exception:
        log('Exception caught', PROVIDER)
        print_exc()
