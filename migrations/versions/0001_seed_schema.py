"""Seed schema: accounts and activity_events, exactly as seed/schema.sql.

The DDL is read from seed/schema.sql and executed verbatim, so the seed loads unchanged.
No unique constraint on the natural key (the seed has duplicates; queries deduplicate) and no
CHECK constraints (messiness is handled in queries, not by rejecting data). See PLAN §7.

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "seed" / "schema.sql"


def upgrade() -> None:
    op.execute(SCHEMA_SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    op.execute("DROP TABLE activity_events")
    op.execute("DROP TABLE accounts")
