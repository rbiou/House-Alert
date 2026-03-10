"""
main.py

Entry point: opens a DB connection, runs all agency scrapers, then closes the connection.
"""

import asyncio

import psycopg2.extensions

import utils.db_connexion as db_connexion
from agencies.brews import notify_brews_results
from agencies.ca import notify_ca_results
from agencies.cattalanjohnson import notify_cattalanjohnson_results
from agencies.cdc import notify_cdc_results
from agencies.concordia import notify_concordia_results
from agencies.dupleix import notify_dupleix_results
from agencies.gtf import notify_gtf_results
from agencies.inli import notify_inli_results


async def scrape_all_agencies(conn: psycopg2.extensions.connection) -> None:
    await notify_gtf_results(conn)
    await notify_cattalanjohnson_results(conn)
    await notify_concordia_results(conn)
    await notify_cdc_results(conn)
    await notify_inli_results(conn)
    await notify_ca_results(conn)
    await notify_brews_results(conn)
    await notify_dupleix_results(conn)


def main() -> None:
    conn = db_connexion.get_connexion()
    try:
        asyncio.run(scrape_all_agencies(conn))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
