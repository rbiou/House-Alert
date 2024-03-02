"""
Main.py

The main script
"""
from agencies.concordia import notify_concordia_results
from agencies.cdc import notify_cdc_results

def get_houses_and_notify():
    notify_concordia_results()
    notify_cdc_results()

get_houses_and_notify()