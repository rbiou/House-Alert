from time import time
import re

TARGET_HOUSES = [
    {"price": 900.0, "sizeMin": 25.0},
    {"price": 1100.0, "sizeMin": 30.0},
    {"price": 1200.0, "sizeMin": 35.0},
    {"price": 1300.0, "sizeMin": 40.0},
    {"price": 1500.0, "sizeMin": 50.0}]

def log(message: str = "Log", domain: str = "app"):
    print("\033[90m{timestamp}\033[0m｜[House-Alert] [{domain}] {message}".format(
        timestamp=int(time()),
        domain=domain,
        message=message
    ))

def check_price_in_range(price, size):
    """
    Check if the input price is less than or equal to the max price
    for the size range that the input size falls into.

    :param price: The price to check.
    :param size: The size to check.
    :param target_houses: A list of dictionaries defining price ranges and size intervals.
    :return: True if the price is under or equals the max price in the range; otherwise False.
    """

    price = float(re.sub(r'[^\d.]', '', price.replace(" ", "").replace(",", "."))) if isinstance(price, str) else price
    size = float(re.sub(r'm.*$', '', size).replace(" ", "").replace(",", ".")) if isinstance(size, str) else size

    # Iterate over the target houses and check the conditions
    for house in TARGET_HOUSES:
        if size >= house["sizeMin"] and price <= house["price"]:
            return True  # Return True if a matching house is found

    return False  # Return False if no house meets the criteria
