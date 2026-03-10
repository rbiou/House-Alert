"""
utils.py

Shared utilities: logging helper, price/size filter criteria, and validation logic.
"""

import re
from time import time

# Rental criteria: (minimum size in m², maximum price in €)
# A listing is a match if it fits any of these brackets.
TARGET_HOUSES = [
    {"price": 900.0,  "sizeMin": 25.0},
    {"price": 1100.0, "sizeMin": 30.0},
    {"price": 1200.0, "sizeMin": 35.0},
    {"price": 1300.0, "sizeMin": 40.0},
    {"price": 1500.0, "sizeMin": 50.0},
]


def log(message: str = "Log", domain: str = "app") -> None:
    print("\033[90m{timestamp}\033[0m｜[House-Alert] [{domain}] {message}".format(
        timestamp=int(time()),
        domain=domain,
        message=message,
    ))


def check_price_in_range(price: float | str, size: float | str) -> bool:
    """
    Return True if the listing matches at least one target bracket.

    A bracket matches when:
      - the listing size >= bracket minimum size, AND
      - the listing price <= bracket maximum price.

    :param price: Listing price (numeric or raw string like "850 €").
    :param size:  Listing size  (numeric or raw string like "32 m²").
    :return: True if the listing fits any bracket; False otherwise.
    """
    price = float(re.sub(r'[^\d.]', '', price.replace(" ", "").replace(",", "."))) if isinstance(price, str) else price
    size  = float(re.sub(r'm.*$',   '', size ).replace(" ", "").replace(",", ".")) if isinstance(size,  str) else size

    for house in TARGET_HOUSES:
        if size >= house["sizeMin"] and price <= house["price"]:
            return True

    return False
