"""Integration tests for the HTML page, against the seeded DB and the JSON endpoint."""

import re
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import app

COUNT_LINE = re.compile(
    r"(\d+) of (\d+) locations outside expected range(?: \(last 4 weeks\))?(?:; (\d+) not judged)?"
)


@pytest.fixture(scope="module")
def client(conn: psycopg.Connection[Any]) -> Iterator[TestClient]:
    # Depends on `conn` so a missing database fails loudly before any request.
    with TestClient(app) as test_client:
        yield test_client


def _count_line(html: str) -> tuple[int, int, int]:
    match = COUNT_LINE.search(html)
    assert match, "count line not found"
    return int(match[1]), int(match[2]), int(match[3] or 0)


def _expected_counts(body: dict[str, Any]) -> tuple[int, int, int]:
    verdicts = [row["window"]["verdict"] for row in body["locations"]]
    n = sum(v in ("high", "low") for v in verdicts)
    k = sum(v in ("not_enough_history", "too_little_volume") for v in verdicts)
    return n, len(verdicts), k


def test_page_renders_state_from_url_and_matches_json(client: TestClient) -> None:
    page = client.get("/", params={"account_id": 6, "week": "2026-07-20"})
    assert page.status_code == 200
    assert '<option value="6" selected>' in page.text
    assert '<option value="2026-07-20" selected>' in page.text

    # The count line is derived from the same rows the JSON returns.
    body = client.get("/api/accounts/6/weekly-report", params={"week": "2026-07-20"}).json()
    assert _count_line(page.text) == _expected_counts(body)

    # A flagged row appears before an unflagged one. In week 2026-05-18, Site G is flagged
    # while Site A (alphabetically first) is not, so only flagged-first sorting puts G on top.
    flagged_html = client.get("/", params={"account_id": 6, "week": "2026-05-18"}).text
    rows = re.findall(r'<tr data-location="([^"]*)" data-verdict="([a-z_]+)"', flagged_html)
    assert rows[0] == ("Site G", "high")
    assert "high" not in [v for _, v in rows[1:]] and "low" not in [v for _, v in rows[1:]]
    assert rows.index(("Site A", "within_expected_range")) > 0
    flagged_body = client.get("/api/accounts/6/weekly-report", params={"week": "2026-05-18"}).json()
    assert _count_line(flagged_html) == _expected_counts(flagged_body)
    assert [name for name, _ in rows] == [r["location"] for r in flagged_body["locations"]]

    # A week before 04-20 shows locations that cannot be judged yet.
    early = client.get("/", params={"account_id": 6, "week": "2026-03-30"})
    assert _count_line(early.text)[2] > 0
    early_body = client.get("/api/accounts/6/weekly-report", params={"week": "2026-03-30"}).json()
    assert _count_line(early.text) == _expected_counts(early_body)

    # A non-Monday gives a message and the matching status code, not a 500.
    bad = client.get("/", params={"account_id": 6, "week": "2026-07-21"})
    assert bad.status_code == 422
    assert "Monday" in bad.text

    # An account without events renders an explicit empty state.
    empty = client.get("/", params={"account_id": 20})
    assert empty.status_code == 200
    assert "No activity recorded" in empty.text


@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({"account_id": 999_999}, 404),
        ({"account_id": "abc"}, 422),
        ({"account_id": 6, "week": "2026-01-26"}, 422),
        ({"account_id": 6, "week": "2026-07-27"}, 422),
        ({"account_id": 6, "week": "not-a-date"}, 422),
        ({"account_id": 6, "week": "20260720"}, 422),  # basic ISO form, not YYYY-MM-DD
        ({"account_id": 6, "week": "2026-W30-1"}, 422),  # ISO week date, not YYYY-MM-DD
    ],
)
def test_page_errors_render_a_message_with_the_matching_status(
    client: TestClient, params: dict[str, Any], status: int
) -> None:
    response = client.get("/", params=params)
    assert response.status_code == status
    assert 'role="alert"' in response.text


def test_week_selector_is_bounded_by_the_data(client: TestClient) -> None:
    html = client.get("/", params={"account_id": 6}).text
    weeks = re.findall(r'<option value="(\d{4}-\d{2}-\d{2})"', html)
    assert weeks[0] == "2026-07-20"  # newest first, also the default selection
    assert weeks[-1] == "2026-02-02"
    assert len(weeks) == 25
    assert '<option value="2026-07-20" selected>' in html


def _count_line_text(html: str) -> str:
    match = re.search(r'<p id="count-line"><strong>(.*?)</strong></p>', html, re.S)
    assert match, "count line not found"
    return match[1]


def test_flagged_account_total_leads_the_count_line(client: TestClient) -> None:
    # Account 6, week 2026-07-13: total 50 against 52..95 (low) while no location window is
    # flagged. The headline must not read as "all is well".
    body = client.get("/api/accounts/6/weekly-report", params={"week": "2026-07-13"}).json()
    assert body["total"]["verdict"] == "low"
    html = client.get("/", params={"account_id": 6, "week": "2026-07-13"}).text
    line = _count_line_text(html)
    assert line.startswith("Account total below expected range this week.")
    assert "0 of 15 locations outside expected range (last 4 weeks)" in line
    assert _count_line(html) == _expected_counts(body)

    # Total within range, and a single-location account: the line is unchanged.
    within = client.get("/", params={"account_id": 6, "week": "2026-07-20"}).text
    assert "Account total" not in _count_line_text(within)
    single = client.get("/", params={"account_id": 16}).text
    assert "Account total" not in _count_line_text(single)


def test_location_table_keeps_the_unjudged_week_apart_from_the_4_week_columns(
    client: TestClient,
) -> None:
    # The single-week count must not sit next to the 4-week range (account 6 Site A: 9 beside
    # 12 to 38 reads as "below range", but the range applies to the 4-week count, 22).
    html = client.get("/", params={"account_id": 6, "week": "2026-07-20"}).text
    # The legend above the table says which side is judged.
    legend = re.search(
        r'<p class="note" id="locations-legend">(.*?)</p>\s*<table id="locations">', html, re.S
    )
    assert legend
    assert legend[1].startswith("Left: the last 4 weeks, judged against this location's typical")
    assert "not judged; single weeks are too small to judge per location." in legend[1]
    table = re.search(r'<table id="locations">(.*?)</table>', html, re.S)
    assert table
    headers = [
        re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<th[^>]*>.*?</th>", table[1])
    ]
    assert headers == [
        "Location",
        "Last 4 weeks",
        "Typical (4 weeks)",
        "Range (4 weeks)",
        "Verdict (4 weeks)",
        "This week (not judged)",
        "Typical week",
    ]
    row = re.search(r'<tr data-location="Site A"[^>]*>(.*?)</tr>', table[1], re.S)
    assert row
    cells = [
        re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>.*?</td>", row[1], re.S)
    ]
    assert cells[1] == "22"
    assert cells[3] == "12 to 38"
    # This week 9 beside its typical week, 6 (the 8-week median; expected 24 = 4 x 6).
    assert cells[-2] == "9"
    assert cells[-1] == "6.0"
