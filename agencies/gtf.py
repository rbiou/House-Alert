import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log

PROVIDER = 'GTF'
URL = ('https://www.gtf.fr/fr/liste-des-biens-loueur?field_ad_type[eq][]=renting&field_price[eq]['
       ']=price_129&limit=10&offset=0&offset_additional=0&currentIndex=2&currentMode=list')


def notify_gtf_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read data's from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'),
                             'lxml')
        all_house = soup.find_all('div', {'class': 'property property__search-item'})
        log('{0} house(s) found'.format(len(all_house)), PROVIDER)
        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        # For each alert requested, check event and deals
        for house in all_house:
            url = house.find('a', {'class': 'link__property full-link'}).get('href').strip()
            item_id = url.rsplit('-', 1)[-1]
            url = 'https://www.gtf.fr' + url
            log('Check if {0} deal already notified'.format(item_id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                size = house.find('div', {'class': 'property-surface property-data--center'}).text.strip()
                size = re.findall('\d+', size)[0] + 'm2'
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                price = house_details.find('span', {'class': 'price'}).text.strip()
                address = 'Paris'
                images_div = house.find_all('img')
                images = ['https://www.gtf.fr' + img.get('src').strip() for img in images_div]
                item = "{provider} - {address} - {size} - {price}".format(provider=PROVIDER, address=address, size=size,
                                                                          price=price)
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
                send_notification(content, images)
                # Add alert to DB
                db_cursor.execute('INSERT INTO public.alert (unique_id, provider) VALUES (%(id)s, %(provider)s)',
                                  {'id': item_id, 'provider': PROVIDER})
                db.commit()
            else:
                log('Alreay notified', PROVIDER)
        log('Close db...', PROVIDER)
        db_cursor.close()
        db.close()
    except Exception:
        log('Exception catched', PROVIDER)
        print_exc()
