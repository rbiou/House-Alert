import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Brews'
URL = ('https://www.brews.fr/recherche?a=2&b%5B%5D=appt&b%5B%5D=house&c=Paris%2C+&radius=0&d=0&x=illimit%C3%A9&do_search=Rechercher')
prefix_URL = 'https://www.brews.fr'

async def notify_brews_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read data's from provider

        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'),
                             'lxml')
        all_house = soup.find_all('div', {'class': 'res_div1'})
        all_house = [house for house in all_house if not house.find('div', attrs={'class': 'bandeau_small bandeau_text', 'data-rel': 'loue'})]
        log('{0} house(s) found'.format(len(all_house)), PROVIDER)
        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()
        # For each alert requested, check event and deals
        for house in all_house:
            url = house.find('a', {'class': 'prod_details btn small'}).get('href').strip()
            item_id = url.rsplit('/')[-1].rsplit('_')[-1].rsplit('.')[0]
            url = prefix_URL + url
            log('Check if {0} deal already notified'.format(item_id), PROVIDER)
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]
            if count == 0:
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')
                price = house_details.find('td', {'itemprop': 'price'})['content'].strip() + '€'
                size = house_details.find('td', text='Surface').find_next_sibling('td').text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'
                address = house_details.find('td', text='Ville').find_next_sibling('td').text.strip()
                images_div = house_details.find(class_='prod_slideshow_container').find_all('img')
                images = [(re.sub(r"_s\.([^.]+)$", "_l.\\1", img.get('src').strip())) for img in images_div]
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
