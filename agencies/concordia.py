import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'CONCORDIA'
URL = 'https://agenceconcordia.com/nos-appartements-a-la-location/'


async def notify_concordia_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read datas from Concordia
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')
        all_house = soup.find_all('div', {'class': 'col-md-6 listing_wrapper'})
        log('{0} house(s) found'.format(len(all_house)), PROVIDER)
        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        # For each alert requested, check event and deals
        for house in all_house:
            city = house.find('div', {'class': 'property_location_image'}).find_all('a')[-1].text
            if city == 'Paris':
                item_id = house.get('data-listid').strip()
                log('Check if {0} deal already notified'.format(item_id), PROVIDER)
                db_cursor.execute(
                    'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                    {'id': item_id, 'provider': PROVIDER})
                count = db_cursor.fetchone()[0]
                if count == 0:
                    price = house.find('div', {'class': 'listing_unit_price_wrapper'}).text.strip().replace('.', '')
                    size = house.find('span', {'class': 'infosize'}).find('span').text.strip()
                    address = house.find('h4').text.strip()
                    url = house.get('data-modal-link')
                    house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                    house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                    images_div = house_details.find('div', {'class': 'gallery_wrapper'}).find_all('div', class_='image_gallery')
                    images = []
                    for div in images_div:
                        style = div.get('style')
                        img_url = style.split('(')[1].split(')')[0]
                        img_url = re.sub(r'-\d+x\d+\.', '.', img_url)
                        images.append(img_url)
                    item = "{provider} - {address} - {size} - {price}".format(provider=PROVIDER, address=address,
                                                                              size=size, price=price)
                    if (check_price_in_range(price, size)):
                        log("New house : {item} => {url}".format(item=item, url=url), domain=PROVIDER)
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
                        log("Not in price/size range. Size: {size}; Price: {price}".format(price=price, size=size))
                else:
                    log('Alreay notified', PROVIDER)
        log('Close db...', PROVIDER)
        db_cursor.close()
        db.close()
    except Exception:
        log('Exception catched', PROVIDER)
        print_exc()
