import os
import psycopg2

from local import get_DB_URI
from utils import log

def get_connexion():
    log("Start getting db connexion...")
    if os.path.isfile("local.py"):
        DB_URI = get_DB_URI()
    else:
        DB_URI = os.environ['DB_URI']
    if DB_URI:
        return psycopg2.connect(DB_URI)
    else:
        log("No DB connexion available")