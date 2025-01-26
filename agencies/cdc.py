import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'CDC Habitat'
URL = ('https://www.cdc-habitat.fr/Recherche/show/cdTypage=Location&order=nb_loyer_total&pagerGo=&newSearch=true&lbLieu'
       '=Paris%3B&nbLoyerMin=&nbLoyerMax=&nbSurfaceMin=&nbSurfaceMax=&')


async def notify_cdc_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read data's from Concordia
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'),
                             'lxml')
        all_house = soup.find_all('article', {'class': 'residenceCard'})
        log('{0} house(s) found'.format(len(all_house)), PROVIDER)
        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        # For each alert requested, check event and deals
        for house in all_house:
            url = house.find('a').get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            log('Check if {0} deal already notified'.format(item_id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                price = house.find('div', {'class': 'price'}).text.strip()
                size = house.find('h3', {'class': 'h4'}).text.rsplit('–', 1)[-1].strip()
                address = house.find('div', {'class': 'location small'}).text.strip()
                images_div = house.find_all('img')
                images = [img.get('src').strip() for img in images_div]
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
                    db_cursor.execute('INSERT INTO public.alert (unique_id, provider) VALUES (%(id)s, %(provider)s)',
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
