import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Crédit Agricole Immobilier'
URL = ('https://www.ca-immobilier.fr/louer/recherche?minarea=25&maxprice=1500&sortby=&codes=75000%3Aparis'
       '%3A75056&sections=location&types=appartment&zones=&distance=0&displayMode=mosaic')


async def notify_ca_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read data's from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'),
                             'lxml')
        all_house = soup.find_all('article', {'class': 'sub_card-entities'})
        all_house = [d for d in all_house if d.find('div', {'class': 'sub_card-entities--infos'})]
        log('{0} house(s) found'.format(len(all_house)), PROVIDER)
        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        # For each alert requested, check event and deals
        for house in all_house:
            url = house.find('a', {'data-tc-category': 'Bouton biens'}).get('href').strip()
            item_id = url.rsplit('/', 1)[-1]
            url = 'https://www.ca-immobilier.fr' + url
            log('Check if {0} deal already notified'.format(item_id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                price = house.find('div', {'class': 'infos-price'}).find('strong').text.strip()
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                size = house_details.find('h4', {'class': 'picto_surface'}).find('span').text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'
                address = house_details.find('h3', {'class': 'prog_title'}).text.strip() + ', ' + house_details.find('h3', {'class': 'prog_city'}).text.strip()
                images_div = house_details.find('div', {'class': 'block_apercu-bien__bg block_apercu-bien__bg--partial'})
                images_div = images_div.find_all('img') if images_div else []
                images = [('https://www.ca-immobilier.fr' + img.get('src').strip()) for img in images_div]
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
