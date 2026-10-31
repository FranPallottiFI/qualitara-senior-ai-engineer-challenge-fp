from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from app import report
from app.db.queries import connect

app = FastAPI(title="DASH-247")

# Strict YYYY-MM-DD only: no timestamps, no basic ISO format, nothing coerced silently.
WEEK_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def parse_week(raw: str | None) -> date | None:
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise report.InvalidWeek(f"week {raw!r} is not a valid date (YYYY-MM-DD)") from exc


@app.get("/api/accounts/{account_id}/weekly-report", response_model=report.WeeklyReport)
def weekly_report(
    account_id: int,
    week: Annotated[str | None, Query(pattern=WEEK_PATTERN)] = None,
) -> report.WeeklyReport:
    try:
        with connect() as conn:
            return report.build(conn, account_id, parse_week(week))
    except report.AccountNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except report.InvalidWeek as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
