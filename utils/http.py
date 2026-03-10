"""
http.py

Shared HTTP fetch helper.
Wraps urllib's Request/urlopen into a single call that returns a parsed BeautifulSoup.
"""

from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

# Sent with every outgoing request to avoid being blocked as a bot.
_USER_AGENT = 'Mozilla/5.0'


def fetch(url: str, encoding: str = 'utf-8') -> BeautifulSoup:
    """Fetch *url* and return a parsed BeautifulSoup document.

    :param url:      Full URL to GET.
    :param encoding: Response charset. Defaults to 'utf-8'.
                     Pass 'latin-1' for agencies that require it (e.g. Dupleix).
    :return: Parsed BeautifulSoup using the 'lxml' parser.
    """
    req = Request(url=url, headers={'User-Agent': _USER_AGENT})
    content = urlopen(req).read()
    return BeautifulSoup(content.decode(encoding), 'lxml')
