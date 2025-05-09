import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'Agence Dupleix'
URL = ('https://www.dupleix.com/index.php?action=searchresults&sortby=prix&sorttype=ASC&ref=&type=Location&bien'
       '=Appartements&Villes=PARIS&prix-min=&prix-max=1500&Nbre_pieces-min=&Nbre_pieces-max=&Nbre_ch-min=&Nbre_ch-max'
       '=&Surface_h-min=25&Surface_h-max=&surface_t-min=&surface_t-max=')
prefix_URL = 'https://www.dupleix.com/'


async def notify_dupleix_results():
    try:
        log('Start scrap agency...', PROVIDER)
        # Read data's from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('latin-1'), 'lxml')
        all_house = soup.find_all('div', {'class': 'single-featured-property mb-50'})
        log(f'{len(all_house)} house(s) found', PROVIDER)

        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()

        # For each alert requested, check event and deals
        for house in all_house:
            url = house.find('a', {'class': 'btn south-btn'}).get('href').strip()
            item_id = url.rsplit('/')[-1].rsplit('_')[-1].rsplit('.')[0]
            url = prefix_URL + url

            size = house.find('div', class_='space').find('span').text.strip()
            size = re.findall(r'\d+', size)[0] + 'm2'
            log(f'Check if {item_id} deal already notified', PROVIDER)

            db_cursor.execute(
                'SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                {'id': item_id, 'provider': PROVIDER}
            )
            count = db_cursor.fetchone()[0]

            if count == 0:
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('latin-1'), 'lxml')

                price = house_details.find('div', {'class': 'list-price'}).text.strip()
                price = re.findall(r'\d+', price)[0] + '€'
                address = house_details.find('h1').text.split('-')[-1].strip() + ' Paris'

                images_div = house_details.find_all('a', {'data-fancybox': 'gallery'})
                images = [(prefix_URL + img.get('href').strip()) for img in images_div]

                item = f"{PROVIDER} - {address} - {size} - {price}"

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
                    db_cursor.execute(
                        'INSERT INTO public.alert (unique_id, provider, creation_date) VALUES (%(id)s, %(provider)s, CURRENT_TIMESTAMP)',
                        {'id': item_id, 'provider': PROVIDER}
                    )
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
