import re
import urllib.parse
from traceback import print_exc
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from utils.constants import NOTIFICATION_CONTENT
from utils.db_connexion import get_connexion
from utils.notify import send_notification
from utils.utils import log, check_price_in_range

PROVIDER = 'GTF'
URL = 'https://www.gtf.fr/fr/liste-des-biens-loueur'


async def notify_gtf_results():
    try:
        log('Start scrap agency...', PROVIDER)

        # Read data from provider
        req = Request(url=URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urlopen(req).read()
        soup = BeautifulSoup(response.decode('utf-8'), 'lxml')

        # Find all properties listed
        all_house = soup.find_all('div', {'class': 'property property__search-item'})
        log(f'{len(all_house)} house(s) found', PROVIDER)

        # Get db_connexion
        db = get_connexion()
        db_cursor = db.cursor()

        # For each house found, check if it's a new alert
        for house in all_house:
            url = house.find('a', {'class': 'link__property full-link'}).get('href').strip()
            item_id = url.rsplit('-', 1)[-1]
            url = 'https://www.gtf.fr' + url

            # Extract city and check if it's Paris
            city = re.sub(r'\s+', '', house.find('div', {'class': 'property__summary'}).find('div').text.split('-')[0]).upper()
            if city != "PARIS":
                continue  # Skip if not Paris

            log(f'Check if {item_id} deal already notified', PROVIDER)

            # Check if this property was already notified in the database
            db_cursor.execute('SELECT COUNT(*) FROM public.alert WHERE unique_id = %(id)s AND provider = %(provider)s',
                              {'id': item_id, 'provider': PROVIDER})
            count = db_cursor.fetchone()[0]

            if count == 0:
                # Extract additional details about the property
                size = house.find('div', {'class': 'property-surface property-data--center'}).text.strip()
                size = re.findall(r'\d+', size)[0] + 'm2'

                # Fetch details page for price and other info
                house_details_content = urlopen(Request(url=url, headers={'User-Agent': 'Mozilla/5.0'})).read()
                house_details = BeautifulSoup(house_details_content.decode('utf-8'), 'lxml')

                price = house_details.find('span', {'class': 'price'}).text.strip()
                address = 'Paris'  # Assuming it's always in Paris
                images_div = house.find_all('img')
                images = ['https://www.gtf.fr' + img.get('src').strip() for img in images_div]

                # Create a string with the important property details
                item = f"{PROVIDER} - {address} - {size} - {price}"

                # Check if the price and size meet the criteria
                if check_price_in_range(price, size):
                    log(f"New house : {item} => {url}", domain=PROVIDER)

                    # Prepare content for notification
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

                    # Add the property to the alerts table in DB
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
