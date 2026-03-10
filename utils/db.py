"""
db.py

Shared database helpers for checking and recording notified listings.
All queries use parameterised statements to prevent SQL injection.
"""

import psycopg2.extensions


# SQL constants
_SELECT_ALERT = (
    'SELECT COUNT(*) FROM public.alert '
    'WHERE unique_id = %(id)s AND provider = %(provider)s'
)
_INSERT_ALERT = (
    'INSERT INTO public.alert (unique_id, provider, creation_date) '
    'VALUES (%(id)s, %(provider)s, CURRENT_TIMESTAMP)'
)


def is_notified(
    cursor: psycopg2.extensions.cursor,
    item_id: str,
    provider: str,
) -> bool:
    """Return True if this listing has already been notified."""
    cursor.execute(_SELECT_ALERT, {'id': item_id, 'provider': provider})
    row = cursor.fetchone()
    return bool(row and row[0] > 0)


def mark_notified(
    cursor: psycopg2.extensions.cursor,
    conn: psycopg2.extensions.connection,
    item_id: str,
    provider: str,
) -> None:
    """Insert a record marking this listing as notified and commit."""
    cursor.execute(_INSERT_ALERT, {'id': item_id, 'provider': provider})
    conn.commit()
