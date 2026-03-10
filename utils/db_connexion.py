"""
db_connexion.py

Provides a PostgreSQL connection using the DB_URI environment variable.
"""

import os

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv

from utils.utils import log

# Load .env if present (no-op in production where env vars are injected directly)
load_dotenv()

DB_URI = os.getenv("DB_URI")

if not DB_URI:
    raise ValueError("DB_URI not set. Please check your .env or environment variables.")


def get_connexion() -> psycopg2.extensions.connection:
    log("Opening database connection...")
    return psycopg2.connect(DB_URI)
