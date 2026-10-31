"""The one typed result (WeeklyReport) and the one function that builds it (PLAN §7, §8).

SQL supplies every date and count; this module only slices the returned rows and applies the
domain rules. Weeks before the first complete week are absent from the series, so counting
rows gives the available baseline weeks without any date arithmetic.
"""

from datetime import date
from typing import Any

import psycopg
from pydantic import BaseModel

from app.db import queries
from app.domain.baseline import BASELINE_WEEKS, Verdict, median, poisson_range, verdict

# Locations are judged over the 4 weeks ending with the selected week (PLAN §4).
LOCATION_WINDOW_WEEKS = 4
FLAGGED: frozenset[Verdict] = frozenset({"high", "low"})


class AccountNotFound(Exception):
    pass


class InvalidWeek(Exception):
    pass


class Account(BaseModel):
    id: int
    name: str
    timezone: str


class Week(BaseModel):
    start: date
    end: date


class Range(BaseModel):
    low: int
    high: int


class Total(BaseModel):
    count: int
    baseline: float | None
    range: Range | None
    verdict: Verdict
    weeks_of_history: int


class Window(BaseModel):
    start: date
    end: date
    count: int
    expected: float | None
    range: Range | None
    verdict: Verdict
    weeks_of_history: int


class LocationRow(BaseModel):
    location: str
    week_count: int
    window: Window


class WeeklyReport(BaseModel):
    account: Account
    week: Week
    first_complete_week: date
    latest_complete_week: date
    total: Total | None
    locations: list[LocationRow]


def _judge(
    count: int, baseline_weeks: list[int], multiplier: int
) -> tuple[float | None, Range | None, Verdict, int]:
    """(lambda, range, verdict, weeks_of_history) for one judged period.

    `baseline_weeks` holds the weekly counts immediately before the judged period, oldest first.
    lambda (the expected count) = multiplier x median of the last BASELINE_WEEKS of them. It and
    the range are None when there is not enough history.
    """
    history = baseline_weeks[-BASELINE_WEEKS:]
    weeks_of_history = len(history)
    if weeks_of_history < BASELINE_WEEKS:
        return None, None, verdict(count, 0, weeks_of_history), weeks_of_history
    lam = multiplier * median(history)
    lo, hi = poisson_range(lam)
    return lam, Range(low=lo, high=hi), verdict(count, lam, weeks_of_history), weeks_of_history


def _validate_week(
    meta: queries.AccountWeeks, requested: date | None
) -> tuple[date, date, date, date]:
    """(first_complete_week, latest_complete_week, week_start, week_end), or InvalidWeek."""
    first, latest = meta.first_complete_week, meta.latest_complete_week
    if first is None or latest is None or meta.week_start is None or meta.week_end is None:
        raise RuntimeError("the dataset has no events, so no week can be selected")
    if requested is not None:
        if requested.weekday() != 0:
            raise InvalidWeek(f"week must be a Monday; {requested.isoformat()} is not")
        if requested < first:
            raise InvalidWeek(
                f"week {requested.isoformat()} is before the first complete week "
                f"({first.isoformat()})"
            )
        if requested > latest:
            raise InvalidWeek(
                f"week {requested.isoformat()} is after the latest complete week "
                f"({latest.isoformat()})"
            )
    return first, latest, meta.week_start, meta.week_end


def build(conn: psycopg.Connection[Any], account_id: int, week: date | None) -> WeeklyReport:
    """The weekly report for one account and one complete local week (default: the latest).

    Raises AccountNotFound for an unknown account and InvalidWeek for a week that is not a
    Monday or is outside the account's complete weeks.
    """
    meta = queries.account_weeks(conn, account_id, week)
    if meta is None:
        raise AccountNotFound(f"account {account_id} not found")
    first, latest, week_start, week_end = _validate_week(meta, week)

    rows = queries.weekly_series(conn, account_id, week_start)
    # Series per location and for the total, oldest week first (the SQL orders by week).
    series: dict[str | None, list[queries.SeriesRow]] = {}
    for row in rows:
        series.setdefault(row.location, []).append(row)
    location_names = sorted(name for name in series if name is not None)

    total: Total | None = None
    if len(location_names) > 1:  # account total for multi-location accounts only (Q6)
        counts = [r.count for r in series[None]]
        baseline, rng, v, history = _judge(counts[-1], counts[:-1], 1)
        total = Total(
            count=counts[-1], baseline=baseline, range=rng, verdict=v, weeks_of_history=history
        )

    locations: list[LocationRow] = []
    for name in location_names:
        weeks = series[name]
        window = weeks[-LOCATION_WINDOW_WEEKS:]
        before = [r.count for r in weeks[: len(weeks) - len(window)]]
        window_count = sum(r.count for r in window)
        expected, rng, v, history = _judge(window_count, before, LOCATION_WINDOW_WEEKS)
        locations.append(
            LocationRow(
                location=name,
                week_count=weeks[-1].count,
                window=Window(
                    start=window[0].week_start,
                    end=week_end,
                    count=window_count,
                    expected=expected,
                    range=rng,
                    verdict=v,
                    weeks_of_history=history,
                ),
            )
        )
    # Rows outside the expected range first, then by name (sort is stable).
    locations.sort(key=lambda row: row.window.verdict not in FLAGGED)

    return WeeklyReport(
        account=Account(id=meta.id, name=meta.name, timezone=meta.timezone),
        week=Week(start=week_start, end=week_end),
        first_complete_week=first,
        latest_complete_week=latest,
        total=total,
        locations=locations,
    )
