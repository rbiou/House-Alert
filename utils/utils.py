from time import time
import re

TARGET_HOUSES = [
    {"price": 800, "sizeMin": 25},
    {"price": 1100, "sizeMin": 30},
    {"price": 1200, "sizeMin": 35},
    {"price": 1300, "sizeMin": 40},
    {"price": 1500, "sizeMin": 50}]

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

    result = False
    for house in TARGET_HOUSES:
        if float(house["sizeMin"]) <= float(size):
            if float(price) <= float(house["price"]):
                result = True
                break
    return result  # Return False if the size does not fit into any range.
