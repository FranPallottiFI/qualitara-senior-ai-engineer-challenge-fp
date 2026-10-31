"""Integration tests for the weekly-series SQL against the real seeded database (no mocks)."""

from datetime import date
from typing import Any

import psycopg

from app.db.queries import SeriesRow, account_weeks, weekly_series


def _count(rows: list[SeriesRow], week_start: date, location: str | None) -> int:
    matches = [r.count for r in rows if r.week_start == week_start and r.location == location]
    assert len(matches) == 1, f"expected one row for {week_start} / {location!r}, got {matches}"
    return matches[0]


def test_hand_verified_total_dedupes_and_buckets_in_local_time(
    conn: psycopg.Connection[Any],
) -> None:
    rows = weekly_series(conn, 1, date(2026, 7, 6))
    # Hand-verified (PLAN §9). Week 2026-07-06 of account 1 (America/Chicago) contains a duplicate
    # pair (ids 11266/11267) and event 11094, which is in this week by UTC but in the previous
    # week locally. Without dedup: 43; UTC weeks: 43; both: 44.
    # SELECT count(*) FROM (
    #   SELECT DISTINCT location, event_type, occurred_at, duration_seconds, outcome
    #   FROM activity_events
    #   WHERE account_id = 1
    #     AND occurred_at >= ('2026-07-06'::timestamp AT TIME ZONE 'America/Chicago') AT TIME ZONE 'UTC'  # noqa: E501
    #     AND occurred_at <  ('2026-07-13'::timestamp AT TIME ZONE 'America/Chicago') AT TIME ZONE 'UTC'  # noqa: E501
    # ) x;  -- 42
    assert _count(rows, date(2026, 7, 6), None) == 42


def test_week_bounds_are_derived_from_the_data(conn: psycopg.Connection[Any]) -> None:
    account_ids = [r[0] for r in conn.execute("SELECT id FROM accounts ORDER BY id").fetchall()]
    assert len(account_ids) == 20
    for account_id in account_ids:
        weeks = account_weeks(conn, account_id)
        assert weeks is not None
        assert weeks.first_complete_week == date(2026, 2, 2), account_id
        assert weeks.latest_complete_week == date(2026, 7, 20), account_id


def test_unknown_account_has_no_metadata(conn: psycopg.Connection[Any]) -> None:
    assert account_weeks(conn, 999_999) is None


def test_empty_week_counts_as_zero(conn: psycopg.Connection[Any]) -> None:
    rows = weekly_series(conn, 6, date(2026, 6, 29))
    assert _count(rows, date(2026, 6, 29), "Site G") == 0


def test_series_has_twelve_weeks_ending_with_the_selected_week(
    conn: psycopg.Connection[Any],
) -> None:
    rows = weekly_series(conn, 6, date(2026, 7, 20))
    total_weeks = [r.week_start for r in rows if r.location is None]
    assert len(total_weeks) == 12
    assert total_weeks[0] == date(2026, 5, 4)
    assert total_weeks[-1] == date(2026, 7, 20)


def test_weeks_before_the_first_complete_week_are_absent(conn: psycopg.Connection[Any]) -> None:
    # 2026-03-23 is the 8th complete week: only 02-02..03-23 exist, nothing earlier, no padding.
    rows = weekly_series(conn, 6, date(2026, 3, 23))
    total_weeks = [r.week_start for r in rows if r.location is None]
    assert total_weeks[0] == date(2026, 2, 2)
    assert len(total_weeks) == 8


def test_total_equals_sum_of_locations(conn: psycopg.Connection[Any]) -> None:
    rows = weekly_series(conn, 6, date(2026, 7, 20))
    for week_start in {r.week_start for r in rows}:
        located = sum(r.count for r in rows if r.week_start == week_start and r.location)
        assert _count(rows, week_start, None) == located


def test_account_without_events_returns_no_rows(conn: psycopg.Connection[Any]) -> None:
    assert account_weeks(conn, 20) is not None
    assert weekly_series(conn, 20, date(2026, 7, 20)) == []
