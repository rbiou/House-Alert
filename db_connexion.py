import os

def get_connexion():
    if os.path.isfile("config.local.py"):
        from config.local import *
    else:
        DB_URI = os.environ['DB_URI']