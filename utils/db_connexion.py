import os
import psycopg2

from utils.utils import log

if os.path.isfile("local.py"):
    from local import DB_URI
else:
    DB_URI = os.environ['DB_URI']

def get_connexion():
    log("Start getting db connexion...")
    if DB_URI:
        return psycopg2.connect(DB_URI)
    else:
        log("No DB connexion available")