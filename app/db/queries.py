"""Database access: connection and the two parameterized queries behind a weekly report.

SQL owns "what happened" (PLAN §7): deduplication, local Monday-Sunday weeks, zero-fill and
week bounds. Python never computes or adjusts dates; it receives them from these queries.

Timestamp trap: `occurred_at` is TIMESTAMP WITHOUT TIME ZONE holding UTC. The local time is
`(occurred_at AT TIME ZONE 'UTC') AT TIME ZONE tz`: the first step marks the value as UTC
(giving a timestamptz), the second renders it in the account's zone. A single
`occurred_at AT TIME ZONE tz` would read the value as local time and shift it the wrong way.
"""

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Final

import psycopg
from psycopg.rows import class_row

DEFAULT_URL: Final = "postgresql://app:app@localhost:5432/app"

# Number of weeks in a series: the location window (4 weeks) plus its 8 baseline weeks before
# it. The account total needs only the selected week plus 8, which fits inside.
SERIES_WEEKS: Final = 12


def connect() -> psycopg.Connection[Any]:
    return psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_URL))


@dataclass(frozen=True)
class AccountWeeks:
    id: int
    name: str
    timezone: str
    # NULL only if activity_events is empty for the whole dataset.
    first_complete_week: date | None
    latest_complete_week: date | None


@dataclass(frozen=True)
class SeriesRow:
    week_start: date
    # NULL marks the account-total row of GROUPING SETS.
    location: str | None
    count: int


# Account metadata plus the week bounds selectable for it (PLAN §4 Definitions, Q2).
# The bounds come from the global earliest/latest event of the whole dataset (never now()),
# converted to this account's timezone:
#   first complete week  = the local week after the one containing the earliest event;
#   latest complete week = the local week before the one containing the latest event.
# date_trunc('week', ...) truncates to Monday 00:00 (ISO weeks), so weeks are Monday-Sunday.
ACCOUNT_WEEKS_SQL: Final = """
WITH params AS (
    SELECT %s::integer AS account_id
),
dataset AS (
    SELECT min(occurred_at) AS earliest_utc, max(occurred_at) AS latest_utc
    FROM activity_events
)
SELECT
    a.id,
    a.name,
    a.timezone,
    (date_trunc('week', (d.earliest_utc AT TIME ZONE 'UTC') AT TIME ZONE a.timezone)
        + interval '1 week')::date AS first_complete_week,
    (date_trunc('week', (d.latest_utc AT TIME ZONE 'UTC') AT TIME ZONE a.timezone)
        - interval '1 week')::date AS latest_complete_week
FROM accounts a
JOIN params p ON a.id = p.account_id
CROSS JOIN dataset d
"""


def account_weeks(conn: psycopg.Connection[Any], account_id: int) -> AccountWeeks | None:
    """The account and its selectable week bounds, or None if the account does not exist."""
    with conn.cursor(row_factory=class_row(AccountWeeks)) as cur:
        cur.execute(ACCOUNT_WEEKS_SQL, (account_id,))
        return cur.fetchone()


# Weekly counts for the SERIES_WEEKS local weeks ending with the selected week, per location
# and for the account total, from one deduplicated, zero-filled set (PLAN §4 Series, §7).
#   params       the account, the selected week (a Monday) and the series length, bound once.
#   weeks        the local Monday of every week in the series. It starts no earlier than the
#                first complete week, so weeks before it are absent, not zero: Python counts
#                available baseline weeks by counting rows, without date arithmetic.
#   events       duplicates collapse: rows identical on every column except id count once (Q5).
#   local_events each event's local week, via the two-step AT TIME ZONE conversion.
#   locations    every location with at least one event for the account, in the whole dataset.
#   grid         week x location, so a week with no events is present with count 0.
# GROUPING SETS returns one row per (week, location) and one per week with location NULL
# (the account total). count(le.week_start) counts only matched events, so empty cells give 0.
# An account with no events has no locations, so it returns no rows.
WEEKLY_SERIES_SQL: Final = """
WITH params AS (
    SELECT %s::integer AS account_id, %s::date AS week, %s::integer AS n_weeks
),
acct AS (
    SELECT a.id, a.timezone, p.week, p.n_weeks
    FROM accounts a
    JOIN params p ON a.id = p.account_id
),
weeks AS (
    SELECT gs::date AS week_start
    FROM acct,
    LATERAL generate_series(
        GREATEST(
            acct.week::timestamp - (acct.n_weeks - 1) * interval '1 week',
            date_trunc(
                'week',
                ((SELECT min(occurred_at) FROM activity_events) AT TIME ZONE 'UTC')
                    AT TIME ZONE acct.timezone
            ) + interval '1 week'
        ),
        acct.week::timestamp,
        interval '1 week'
    ) AS gs
),
events AS (
    SELECT DISTINCT e.location, e.event_type, e.occurred_at, e.duration_seconds, e.outcome
    FROM activity_events e
    JOIN acct ON e.account_id = acct.id
),
local_events AS (
    SELECT
        ev.location,
        date_trunc('week', (ev.occurred_at AT TIME ZONE 'UTC') AT TIME ZONE acct.timezone)::date
            AS week_start
    FROM events ev
    CROSS JOIN acct
),
locations AS (
    SELECT DISTINCT location FROM events
),
grid AS (
    SELECT w.week_start, l.location
    FROM weeks w
    CROSS JOIN locations l
)
SELECT
    g.week_start,
    CASE WHEN GROUPING(g.location) = 1 THEN NULL ELSE g.location END AS location,
    count(le.week_start)::integer AS count
FROM grid g
LEFT JOIN local_events le
    ON le.location = g.location AND le.week_start = g.week_start
GROUP BY GROUPING SETS ((g.week_start, g.location), (g.week_start))
ORDER BY g.week_start, location NULLS FIRST
"""


def weekly_series(conn: psycopg.Connection[Any], account_id: int, week: date) -> list[SeriesRow]:
    """Weekly counts per location and for the account total, for the weeks ending with `week`."""
    with conn.cursor(row_factory=class_row(SeriesRow)) as cur:
        cur.execute(WEEKLY_SERIES_SQL, (account_id, week, SERIES_WEEKS))
        return cur.fetchall()
