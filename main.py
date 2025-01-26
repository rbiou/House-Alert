"""
Main.py

The main script
"""
import asyncio

from agencies.brews import notify_brews_results
from agencies.ca import notify_ca_results
from agencies.cattalanjohnson import notify_cattalanjohnson_results
from agencies.cdc import notify_cdc_results
from agencies.concordia import notify_concordia_results
from agencies.dupleix import notify_dupleix_results
from agencies.gtf import notify_gtf_results
from agencies.inli import notify_inli_results

async def get_houses_and_notify():
    await notify_gtf_results()
    await notify_cattalanjohnson_results()
    await notify_concordia_results()
    await notify_cdc_results()
    await notify_inli_results()
    await notify_ca_results()
    await notify_brews_results()
    await notify_dupleix_results()

asyncio.run(get_houses_and_notify())
