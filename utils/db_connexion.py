import os

from dotenv import load_dotenv
import psycopg2

from utils.utils import log


# Charger le fichier .env si présent
load_dotenv()

# Récupération de DB_URI depuis le .env ou la variable d'environnement
DB_URI = os.getenv("DB_URI")

if not DB_URI:
    raise ValueError("DB_URI not set. Please check your .env or environment variables.")

def get_connexion():
    log(DB_URI)
    log("Start getting db connexion...")
    if DB_URI:
        return psycopg2.connect(DB_URI)
    else:
        log("No DB connexion available")
