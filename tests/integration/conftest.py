from collections.abc import Iterator
from typing import Any

import psycopg
import pytest

from app.db.queries import connect


@pytest.fixture(scope="session")
def conn() -> Iterator[psycopg.Connection[Any]]:
    """The real seeded Postgres. Fails loudly when it is missing; never skips."""
    try:
        connection = connect()
    except psycopg.OperationalError as exc:
        pytest.fail(
            f"Cannot connect to the database ({exc}). "
            "Start it with `docker compose up -d --build` and retry.",
            pytrace=False,
        )
    with connection:
        yield connection
