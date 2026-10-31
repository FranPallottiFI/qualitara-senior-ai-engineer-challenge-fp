"""Alembic environment: online migrations only, URL taken from DATABASE_URL."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DEFAULT_URL = "postgresql://app:app@localhost:5432/app"


def _sqlalchemy_url() -> str:
    # SQLAlchemy maps plain "postgresql://" to psycopg2; this project ships psycopg 3.
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def run_migrations_online() -> None:
    engine = create_engine(_sqlalchemy_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported.")
run_migrations_online()
