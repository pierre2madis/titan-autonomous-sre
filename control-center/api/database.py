import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


@contextmanager
def database_connection():
    password_file = os.environ["TITAN_POSTGRES_PASSWORD_FILE"]

    with open(password_file, encoding="utf-8") as handle:
        password = handle.read().strip()

    with psycopg.connect(
        host=os.environ["TITAN_POSTGRES_HOST"],
        port=os.environ["TITAN_POSTGRES_PORT"],
        dbname=os.environ["TITAN_POSTGRES_DB"],
        user=os.environ["TITAN_POSTGRES_USER"],
        password=password,
        row_factory=dict_row,
        options="-c default_transaction_read_only=on -c statement_timeout=5000",
        connect_timeout=5,
    ) as conn:
        yield conn
