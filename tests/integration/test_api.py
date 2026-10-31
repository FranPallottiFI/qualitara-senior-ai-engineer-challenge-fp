"""Integration tests for the JSON endpoint, through the FastAPI app against the seeded DB."""

from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client(conn: psycopg.Connection[Any]) -> Iterator[TestClient]:
    # Depends on `conn` so a missing database fails loudly before any request.
    with TestClient(app) as test_client:
        yield test_client


def _report(client: TestClient, account_id: int, week: str | None = None) -> dict[str, Any]:
    params = {"week": week} if week is not None else {}
    response = client.get(f"/api/accounts/{account_id}/weekly-report", params=params)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _location(body: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [row for row in body["locations"] if row["location"] == name]
    assert len(matches) == 1
    return matches[0]


# Account 6 total, from ./scripts/sql-ro.sh "$(cat docs/analysis/02-method-series.sql)",
# rows location = '(all)': week, n, med8, c_band, c ('.' = within expected range).
# This cross-checks the agent's own SQL analysis; the hand-verified number is in test_queries.py.
ACCOUNT_6_TOTAL = [
    ("2026-05-11", 78, 73.5, (52, 96), "within_expected_range"),
    ("2026-05-18", 62, 73.5, (52, 96), "within_expected_range"),
    ("2026-05-25", 53, 72.0, (51, 95), "within_expected_range"),
    ("2026-06-01", 880, 66.0, (46, 88), "high"),
    ("2026-06-08", 102, 66.0, (46, 88), "high"),
    ("2026-06-15", 59, 73.0, (52, 96), "within_expected_range"),
    ("2026-06-22", 76, 73.0, (52, 96), "within_expected_range"),
    ("2026-06-29", 69, 72.0, (51, 95), "within_expected_range"),
    ("2026-07-06", 79, 72.5, (52, 95), "within_expected_range"),
    ("2026-07-13", 50, 72.5, (52, 95), "low"),
    ("2026-07-20", 87, 72.5, (52, 95), "within_expected_range"),
]


@pytest.mark.parametrize(("week", "count", "med8", "band", "verdict"), ACCOUNT_6_TOTAL)
def test_account_verdicts_and_baselines_match_sql_analysis(
    client: TestClient,
    week: str,
    count: int,
    med8: float,
    band: tuple[int, int],
    verdict: str,
) -> None:
    total = _report(client, 6, week)["total"]
    assert total["count"] == count
    assert total["baseline"] == pytest.approx(med8)
    assert (total["range"]["low"], total["range"]["high"]) == band
    assert total["verdict"] == verdict
    assert total["weeks_of_history"] == 8


def test_location_window_matches_sql_analysis(client: TestClient) -> None:
    # PLAN §8 example, from the same CTEs as docs/analysis/06a.
    site_a = _location(_report(client, 6, "2026-07-20"), "Site A")
    assert site_a["week_count"] == 9
    window = site_a["window"]
    assert (window["start"], window["end"]) == ("2026-06-29", "2026-07-26")
    assert window["count"] == 22
    assert window["expected"] == pytest.approx(24.0)
    assert window["range"] == {"low": 12, "high": 38}
    assert window["verdict"] == "within_expected_range"
    assert window["weeks_of_history"] == 8


def test_history_cutoffs(client: TestClient) -> None:
    before = _report(client, 6, "2026-03-23")["total"]
    assert before["verdict"] == "not_enough_history"
    assert before["weeks_of_history"] == 7
    assert before["baseline"] is None and before["range"] is None
    judged = _report(client, 6, "2026-03-30")["total"]
    assert judged["verdict"] != "not_enough_history"
    assert judged["weeks_of_history"] == 8
    assert judged["baseline"] is not None

    site_a_before = _location(_report(client, 6, "2026-04-13"), "Site A")["window"]
    assert site_a_before["verdict"] == "not_enough_history"
    assert site_a_before["expected"] is None and site_a_before["range"] is None
    site_a_judged = _location(_report(client, 6, "2026-04-20"), "Site A")["window"]
    assert site_a_judged["verdict"] != "not_enough_history"
    assert site_a_judged["weeks_of_history"] == 8


def test_single_location_account_has_no_total_verdict(client: TestClient) -> None:
    body = _report(client, 16)
    assert body["total"] is None
    assert len(body["locations"]) == 1
    window = body["locations"][0]["window"]
    assert window["weeks_of_history"] == 8
    assert window["verdict"] != "not_enough_history"


def test_account_without_events_returns_explicit_empty_200(client: TestClient) -> None:
    body = _report(client, 20)
    assert body["total"] is None
    assert body["locations"] == []
    assert body["week"]["start"] == body["latest_complete_week"]


def test_default_week_is_the_latest_complete_week(client: TestClient) -> None:
    body = _report(client, 6)
    assert body["week"]["start"] == body["latest_complete_week"] == "2026-07-20"
    assert body["week"]["end"] == "2026-07-26"
    assert body["first_complete_week"] == "2026-02-02"


def test_flagged_locations_sort_first(client: TestClient) -> None:
    # Week 2026-06-01 contains account 6's burst, so some location windows are flagged.
    verdicts = [row["window"]["verdict"] for row in _report(client, 6, "2026-06-01")["locations"]]
    flagged = [v in ("high", "low") for v in verdicts]
    assert any(flagged)
    assert flagged == sorted(flagged, reverse=True)


@pytest.mark.parametrize(
    ("account_id", "week", "status"),
    [
        (6, "2026-07-21", 422),  # not a Monday
        (6, "2026-01-26", 422),  # before the first complete week
        (6, "2026-07-27", 422),  # after the latest complete week
        (6, "2026-13-01", 422),  # malformed: no month 13
        (6, "20260720", 422),  # malformed: not YYYY-MM-DD
        (6, "2026-07-20T00:00:00", 422),  # malformed: a timestamp, not a date
        (6, "last-week", 422),  # malformed
        (999_999, "2026-07-20", 404),  # unknown account
        (999_999, None, 404),  # unknown account, default week
    ],
)
def test_invalid_params_are_rejected(
    client: TestClient, account_id: int, week: str | None, status: int
) -> None:
    params = {"week": week} if week is not None else {}
    response = client.get(f"/api/accounts/{account_id}/weekly-report", params=params)
    assert response.status_code == status, response.text
    assert response.json()["detail"]
