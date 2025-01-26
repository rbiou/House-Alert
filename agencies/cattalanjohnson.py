import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Cattalan Johnson'
URL = ('https://www.cattalanjohnson.com/fr/recherche.aspx?meuble=-1&nbChambre=&cp=75001,75002,75003,75004,75005,75006,'
       '75007,75008,75009,75010,75011,75012,75013,75014,75015,75016,75017,75018,75019,'
       '75020&pxmin=0&pxmax=1500&surfacemin=25&surfacemax=0#container')


async def notify_cattalanjohnson_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read datas from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')
        all_house = soup.find_all('div', {'class': 'row liste-biens'})
        log('{0} house(s) found'.format(len(all_house)), PROVIDER)
        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        # For each alert requested, check event and deals
        for house in all_house:
            url = house.find('div', {'class': 'crop'}).find('a').get('href').strip()
            item_id = url.rsplit('/')[-2]
            url = 'https://www.cattalanjohnson.com' + url
            log('Check if {0} deal already notified'.format(item_id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                price = house.find('p', {'class': 'prix'}).text.strip()
                price = ''.join(re.findall(r'\d+', price)) + '€'
                size = house_details.find('div', {'id': 'content_divSurface', 'class': 'col-md-3'}).text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'
                postal_code = re.search(r'map_(\d+)\.png',
                                        house.find('img', {'class': 'img-responsive'}).get('style').strip()).group(1)
                address = 'Paris ' + postal_code
                images_div = house_details.find('div', {'class': 'container-miniature no-print'}).find_all('img')
                images = [('https://www.cattalanjohnson.com' + img.get('src').strip()) for img in images_div]
                item = "{provider} - {address} - {size} - {price}".format(provider=PROVIDER, address=address, size=size,
                                                                          price=price)
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
