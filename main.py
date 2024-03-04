"""
Main.py

The main script
"""
from agencies.ca import notify_ca_results
from agencies.cattalanjohnson import notify_cattalanjohnson_results
from agencies.cdc import notify_cdc_results
from agencies.concordia import notify_concordia_results
from agencies.gtf import notify_gtf_results
from agencies.inli import notify_inli_results


def get_houses_and_notify():
    notify_gtf_results()
    notify_cattalanjohnson_results()
    notify_concordia_results()
    notify_cdc_results()
    notify_inli_results()
    notify_ca_results()


get_houses_and_notify()
