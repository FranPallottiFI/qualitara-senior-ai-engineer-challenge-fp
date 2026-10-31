import re
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import report
from app.db import queries
from app.db.queries import connect

app = FastAPI(title="DASH-247")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Strict YYYY-MM-DD only: no timestamps, no basic or week-date ISO forms (the stdlib ISO parser
# alone accepts "20260720" and "2026-W30-1"), nothing coerced silently.
WEEK_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_week(raw: str | None) -> date | None:
    """The one parsing path for `week`, shared by the JSON endpoint and the page."""
    if raw is None or raw == "":
        return None
    if WEEK_PATTERN.fullmatch(raw) is None:
        raise report.InvalidWeek(f"week {raw!r} is not a valid date (YYYY-MM-DD)")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise report.InvalidWeek(f"week {raw!r} is not a valid date (YYYY-MM-DD)") from exc


@app.get("/api/accounts/{account_id}/weekly-report", response_model=report.WeeklyReport)
def weekly_report(
    account_id: int,
    week: str | None = None,
) -> report.WeeklyReport:
    try:
        with connect() as conn:
            return report.build(conn, account_id, parse_week(week))
    except report.AccountNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except report.InvalidWeek as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
def page(request: Request, account_id: str | None = None, week: str | None = None) -> Any:
    """The same WeeklyReport as the JSON endpoint, rendered; all state comes from the URL."""
    status = 200
    error: str | None = None
    data: report.WeeklyReport | None = None
    weeks: list[date] = []
    with connect() as conn:
        accounts = queries.account_options(conn)
        selected_account: int | None = accounts[0].id if accounts else None
        if account_id not in (None, ""):
            try:
                selected_account = int(account_id or "")
            except ValueError:
                status, error = 422, f"account_id {account_id!r} is not an integer"
        if error is None and selected_account is not None:
            try:
                data = report.build(conn, selected_account, parse_week(week))
            except report.AccountNotFound as exc:
                status, error = 404, str(exc)
            except report.InvalidWeek as exc:
                status, error = 422, str(exc)
            if status != 404:
                # The week selector is bounded by the account's complete weeks (from SQL), and
                # stays usable when the requested week was invalid.
                meta = queries.account_weeks(conn, selected_account)
                if meta and meta.first_complete_week and meta.latest_complete_week:
                    weeks = queries.selectable_weeks(
                        conn, meta.first_complete_week, meta.latest_complete_week
                    )
    return templates.TemplateResponse(
        request,
        "report.html",
        {
            "accounts": accounts,
            "weeks": weeks,
            "selected_account": selected_account,
            "selected_week": data.week.start if data else None,
            "report": data,
            "error": error,
        },
        status_code=status,
    )
