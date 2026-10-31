# PLAN — DASH-247: "Is this normal for us?"

Status: **APPROVED 2026-10-31. Frozen.** Scope changes go through this file first. Changes after
approval are listed at the end, dated and with a reason. The engineer approved it after a
PLAN-mode adversarial review (findings and decisions in `ai-log/02-planning-notes.md`).

Sources: the challenge prompt received by email, `docs/TICKET.md`, `docs/PRODUCT_BACKGROUND.md`,
the seed (`seed/`), and the read-only analysis in [`docs/analysis/`](docs/analysis/README.md).
Every number below is reproducible from a file there.

---

## 1. Interpretation

**User.** The customer admin of a service business, often with several locations. Not the
account manager: the point is that the customer can answer the question without calling one.

**The Monday decision.** "Did anything happen last week, overall or at one of my locations,
that I should act on?" The resulting actions are concrete: call a site manager, check the phones or
the lead form, adjust staffing, or find out what drove a surge.

**What "normal" means here.** A count is *within the expected range* if it falls inside the
range that ordinary week-to-week noise produces around *this account's* (or this location's)
own recent typical week. Not other customers, not a target, not a forecast. The product never
says "normal". At small volumes only large changes are detectable, so "normal" would claim more
than the data supports.

**The slice.** For one account and one complete local week (default: the latest), counting all
events:
- the account total, judged on that week (multi-location accounts only, Q6);
- every location, judged on the 4 weeks ending that week. The selected week's count is shown
  next to it, with no baseline, range or verdict (§4, Q12);
- rows outside the expected range sorted first, and one count line at the top: "N of M locations
  outside expected range; K not judged", rendered from the rows.

All state lives in the URL. The build is deliberately small; spare time goes to verification.

## 2. Questions and assumptions

No questions were emailed to the recruiter. The challenge prompt explicitly allows documenting
each question with its working assumption in `PLAN.md` instead; this plan does that, with the
engineer deciding each one during planning.

| # | Question | Decision / working assumption |
|---|---|---|
| Q1 | Is the 2026-06-03 burst at account 6 (~800 extra events, `survey/s03`) real or bad data? | **Decided:** treat it as real. With this little data and this much variance it cannot be statistically rejected. The baseline must be robust enough that one extreme week does not distort the weeks after it. |
| Q2 | What is "this week"? The seed is a static snapshot ending 2026-07-27 (`survey/s01`). | **Decided:** never use `now()`. The default is the last complete local week before the week of the latest event *in the whole dataset* (2026-07-20..26 for every account on this seed). The user can pick another complete week. A per-account anchor was rejected because it hides silence: account 8's last event is Friday 07-24, which would push its default back a week. In a real product the anchor would be today's date. |
| Q3 | Account 18 has timezone `UTC`: real or an unset default? | **Decided:** treat it as real; there's not enough evidence to flag it. |
| Q4 | Weeks? | **Decided:** Monday–Sunday, in the account's IANA timezone. |
| Q5 | Duplicates (12 exact pairs, `survey/s07`)? | **Decided:** rows identical on every column except `id` count once. Stated in the README (not hidden). |
| Q6 | Single-location accounts (8, 13, 16, 19)? | **Decided:** treated like location rows. One row with the selected week's count and the 4-week verdict; no single-week total verdict. Their total is a location-sized series, so a single-week verdict would catch ~2% of halvings (`04b`, 5–10 bucket). The account-level detection figures come from multi-location accounts only. |
| Q7 | Per event type? | **Decided: cut from this slice; next iteration.** Filtered series have zero or near-zero baselines (a reviewer measured 7 of 69 location appointment series with an 8-week median of 0, and 60 of 69 at 1 or less). Their behaviour under the method was never validated. |
| Q8 | Permanently closed locations (after 8 empty weeks the baseline becomes 0)? | **Out of scope:** does not occur in the seed. Documented as a known gap. A zero baseline gives `too_little_volume`, never `high` (§4). |
| Q9 | Is `occurred_at` really UTC? | **Assumption:** `occurred_at` is treated as UTC, per the schema. The survey found times that look timezone-blind (every timezone peaks at the same UTC hour, `survey/s06`). That is logged as a **data-quality question for product**. Weeks are bucketed in local time regardless (only 8 events change week). No hour-of-day features. |
| Q10 | Which events are counted? | **Assumption:** all three event types, summed. Outcomes and durations are not used (`survey/s08`). |
| Q11 | Which account is "mine"? No auth (out of scope per the challenge prompt). | **Assumption:** an account selector in the form stands in for the logged-in admin's identity. |
| Q12 | Should single-week location rows show a baseline and range? | **Decided:** count only. The earlier decision was to show the baseline and range without a verdict. It was reversed after the agent argued three points. At typical location volume the range is nearly uninformative (baseline ≈ 6 gives 1..13, `03`). A range shown without a verdict invites the user to judge it, which is the overclaim the "within expected range" wording avoids. And the count alone is what the dashboard shows today. |

## 3. Data reality (what would make a naive aggregation wrong)

Details and SQL live in [`docs/analysis/survey/`](docs/analysis/survey/). Ranked by impact:

| # | Finding | Evidence | Handling |
|---|---|---|---|
| 1 | Data ends 96 days before today; `now()` windows are empty | `s01` | Anchor on the latest event (Q2) |
| 2 | Partial first and last weeks; weekends are ~5% of volume each | `s02` | Only complete local weeks are judged or selectable |
| 3 | One-day burst at the largest customer; a mean baseline would read the next 8 weeks as −55% | `s03`, `02` | Median baseline (§4) |
| 4 | Location counts are 4–11 a week; ±50% swings are noise | `s04`, `03`, `04b` | Locations judged over 4 weeks; single-week count shown without a verdict (§4) |
| 5 | Location names collide across accounts ("Site A" in 19) | `s05` | A location is always identified by (account_id, location) |
| 6 | Local vs UTC bucketing; times look timezone-blind | `s06` | Bucket in the account's timezone, in SQL only (§7 names the conversion trap) |
| 7 | 12 exact duplicate pairs | `s07` | `SELECT DISTINCT` on all columns except `id`; stated in the README |
| 8 | ~3% NULL outcomes; durations meaningless | `s08` | Counts only; no rates, no durations |
| 9 | Account 20 has no events; 4 empty location-weeks | `s09` | Explicit empty response; empty weeks count as 0 |
| 10 | History is only 25 complete weeks | `s01` | 8-week baseline; no seasonality, no year-over-year |

Checked clean: timezones, event-type values, location strings (`s10`).

## 4. Baseline method

### Definitions

- **Week bounds are derived from the data, never hardcoded.** In each account's timezone:
  - the *first complete week* is the week after the week containing the dataset's earliest
    event;
  - the *latest complete week* is the week before the week containing the dataset's latest
    event (Q2).

  On this seed both resolve to 2026-02-02 and 2026-07-20 for every account. Those dates appear
  in this plan and in tests only as expected values, never in code.
- **Series:** deduplicated weekly counts of all events for each (account, location) that has at
  least one event in the dataset, plus the account total for multi-location accounts.
  - Every series starts at the first complete week. Weeks with no events count as **0**.
  - A location that first appears mid-history is therefore zero-filled from the first complete
    week. No location in the seed does this (0 of 69 start after 2026-02-02, per the PLAN
    review). The zero-baseline rule below keeps it from producing false `high` verdicts.
    Documented as a known gap.
- **Baseline:** the median of the **8** complete weeks immediately before the judged period.
  The same parameter is used at both levels.
- **Expected range:** Poisson 0.5%–99.5% quantiles (99%, two-sided) around the expected count λ.
- **Account total** (multi-location accounts):
  - judged period = the selected week;
  - λ = baseline;
  - baseline weeks = the 8 weeks before the selected week.
- **Location** (and single-location accounts, Q6):
  - judged period = the 4 weeks ending with the selected week;
  - λ = 4 × baseline, where the baseline is taken from the 8 weeks *before* that window
    (no overlap);
  - the row also shows the selected week's count only: no baseline, range or verdict (Q12).
- **`weeks_of_history`** = baseline weeks available, capped at 8: complete weeks from the first
  complete week up to the start of the judged period (the selected week for totals, the window
  start for locations).
- **Verdicts, in precedence order:**

  | # | Verdict | When |
  |---|---|---|
  | 1 | `not_enough_history` | `weeks_of_history` < 8 |
  | 2 | `too_little_volume` | λ = 0 (never `high`; a zero baseline says nothing about volume) |
  | 3 | `high` | count > upper bound (still reported when the lower bound is 0, because rises remain detectable) |
  | 4 | `low` | count < lower bound |
  | 5 | `too_little_volume` | the lower bound is 0, so a drop can't be detected |
  | 6 | `within_expected_range` | otherwise; the UI says "within expected range" |

- **Earliest judgeable week:** first complete week + 8 for account totals, + 11 for locations (on
  this seed, 2026-03-30 and 2026-04-20). Earlier selectable weeks show counts with
  `not_enough_history`.

### Why this is correct on this data

- **Median, not mean:** the account 6 baseline stays between 66 and 73.5 through and after the
  burst week (880 events). The mean of the 8 weekly counts in `02` from 05-25 to 07-13, which
  include that week, is 171.
- **A Poisson range fits:** weekly counts have variance ≈ mean (median ratio 0.97, `01`), so the
  noise width is predictable from volume.
- **99%, not a percentile band or a MAD band:**
  - The P10–P90 band (B) flags 23–35% of ordinary weeks by construction (`04b`).
  - The MAD band (A) is unstable on small counts: 7.6% false alarms, and it collapses at MAD = 0
    (`04b`).
  - The Poisson range (C) at account level: 0–2% false alarms; catches 59% of halved weeks at
    baselines 20–40 and 92% above 40 (`04b`).
- **The window length barely matters** (6/8/12 weeks, `05`); 8 is one parameter to explain and
  test.
- **4-week location windows:** a single-week location verdict catches 2% of halved weeks
  (`04b`). Four weeks catch 51% of sustained halvings at typical location volume (`06b`).

### Known limitations (stated in the README and the UI)

1. **Location false alarms are ~3× nominal:** 3.1% of windows vs ~1% (`06b`).
   - By bucket: weekly baseline 5–10 is 2.4% false alarms / 51% detection; ≤ 5 is 6.5% / 4%
     (`06b`).
   - Cause: the range treats the 8-week median as exact, and its sampling error is multiplied by 4.
   - Flags are marginal and scattered (`06c`).
   - Alternative measured on the same 540 windows (`06d`): 8-week baseline 3.1% / 49%, 12-week
     2.4% / 46%. Not adopted, to keep one parameter.
2. **Dispersion is measured on synthetic data.** Real activity is usually more dispersed, and then
   C over-fires. Next step: measure variance/mean on production data; if it is above 1, widen the
   range with a per-series dispersion estimate (quasi-Poisson or negative binomial).
3. **At small volume, "within expected range" means "no large change."** Expected 4-week counts of
   20–30 need a drop of about −55% to −47% to be flagged low (`03`). Every judged row shows its
   count, expected value and range, so smaller moves are visible without a verdict.
4. **A location verdict reflects 4 weeks** and reacts to sustained changes, not one-week dips.
   The UI says so next to the verdict.
5. No seasonality, holiday or weekday adjustment (25 weeks of history). Closed locations (Q8)
   and locations that first appear mid-history (§4 Series) are known gaps.

## 5. Scope

**In**
- One JSON endpoint and one HTML page rendering the same typed result.
- Account and week selection in the URL query string (survives reload, shareable).
- Account verdict (multi-location), location verdicts (4 weeks), the selected week's count per
  location.
- Flagged rows sorted first and a one-line count ("N of M locations outside expected range; K not
  judged"), rendered in the template from the rows. No summary module.
- Explicit empty and edge states: no activity, not enough history, too little volume.
- Alembic migration; seed loader; `docker compose up` runs everything.
- Tests (§9); README; AI log.

**Out, with reasons**
- **Auth:** out of scope per the challenge prompt; the account selector stands in (Q11).
- **Alerting / notifications, forecasting / ML:** out of scope per the ticket.
- **Durations and hour-of-day views:** unreliable in this seed (`survey/s06`, `s08`).
- **Charts and history views:** visual polish is out of scope; a table with count, expected value,
  range and verdict answers the question.
- **Closed locations, mid-history locations:** known gaps (Q8, §4).
- **Summary text, deterministic or LLM-generated:** sorting plus the count line answers "at a
  glance"; the LLM version is designed, not built (§10).

**Next iteration (in the README's "what I'd do with another day")**
- **Event-type filter** (Q7): first validate the method on filtered series, because their baselines
  are zero or near zero.
- **Outcome rates** (missed-call %, conversion): denominators are tiny and rates swing 4–44%
  monthly at small accounts (`survey/s04`). They need their own method.

## 6. Stack and dependencies

The challenge prompt says to use your strongest stack. That's Python for this engineer, and also
what the role uses. Every dependency below is justified against a requirement (principles §2).
Versions are pinned in `uv.lock` (with hashes) at setup.

| Dependency | Kind | Why it is needed | Rejected alternative |
|---|---|---|---|
| Python 3.12 | runtime | stable, widely available; pinned in `.python-version` and `requires-python` | — |
| `fastapi` | runtime | typed query parameters give HTTP-boundary validation and automatic 422s (principles §3, conventions' API contract); JSON serialization of the typed result | Flask: hand-written validation |
| `uvicorn` | runtime | ASGI server to serve FastAPI (plain, not `[standard]`: fewer dependencies) | — |
| `jinja2` | runtime | server-rendered page; FastAPI's templating requires it | SPA: second toolchain and lockfile, client state, more 15-minute-run risk |
| `psycopg[binary]` | runtime | Postgres driver for raw, parameterized SQL; the binary build avoids compiling libpq | ORM: hides the aggregation SQL, which is the product |
| `alembic` | runtime | the challenge prompt asks for migrations with the stack's standard tooling; conventions freeze it. Brings **SQLAlchemy core** as a dependency; the migration itself is raw SQL in `op.execute` | hand-rolled migration runner: not "standard tooling" |
| `pytest` | dev | tests | — |
| `httpx` | dev | required by FastAPI's `TestClient` for integration tests | — |
| `ruff`, `mypy` | dev | lint, format, types (CLAUDE.md commands) | — |

**Not added:**
- **No scipy:** Poisson quantiles are ~15 lines with `math.lgamma`. λ = 0 is handled explicitly,
  without calling `log(0)`.
- **No connection pool:** single trusted user, one connection per request.
- **No pydantic-settings or python-dotenv:** `os.environ` with defaults matching compose.
- **No indexes beyond the primary keys:** 12.6k rows.

**Supply chain** (principles §3):
- `uv.lock` committed; `uv sync --frozen`.
- `[tool.uv] required-version` as a **lower bound** (`>=`), because an exact pin breaks
  reviewers' uv installs.
- `exclude-newer` cooling-off window, with the format verified at setup.
- Docker images pinned by tag.

**Infrastructure.** `docker-compose.yml` with two services:
- **`db`** (existing): `postgres:16` with the read-only role and the existing healthcheck.
- **`app`** (new):
  - `python:3.12-slim`, with uv copied from its pinned official image;
  - `uv sync --frozen` including the dev group, with `tests/` in the image, so reviewers can run
    tests without a local uv;
  - `depends_on: db: condition: service_healthy`;
  - on start: `alembic upgrade head`, then the seed loader (loads only if `accounts` is empty,
    otherwise prints that it skipped), then `uvicorn --host 0.0.0.0 --port 8000`;
  - published as `"127.0.0.1:8000:8000"`, so it's reachable from the host only;
  - DB host port configurable (`${DB_PORT:-5432}`); `.env.example` documents the variables.

**15-minute run:** `docker compose up`, then open `http://localhost:8000`.
**Tests:** `docker compose run --rm app uv run --frozen pytest -q`, or locally with
`uv run pytest -q`.

## 7. Architecture and the SQL/Python split

**Single source of truth:**
- **SQL owns "what happened":** deduplication, local Monday–Sunday weeks, zero-fill, week bounds,
  account totals, and how many baseline weeks are available.
- **Python owns "is it normal":** median, Poisson range, verdicts, as pure functions.
- **Python never computes or adjusts dates.**

**Timestamp trap.** `occurred_at` is a `TIMESTAMP` without time zone, holding UTC.
- The local time is `(occurred_at AT TIME ZONE 'UTC') AT TIME ZONE tz`.
- A single `occurred_at AT TIME ZONE tz` reads the value as local time and shifts it the wrong way.
- The hand-verified number (§9) catches this: with the wrong form, event 11094 lands in week
  07-06 and the count becomes 43.

```
app/
  main.py          routes only: validate → report.build() → JSON or template
  report.py        WeeklyReport pydantic models (the one typed result) and
                   build(conn, account_id, week) -> WeeklyReport (the one function)
  db/queries.py    connect() from DATABASE_URL; commented, parameterized SQL
                   (account + week bounds; weekly series)
  domain/baseline.py  median, poisson_range(lam) -> (lo, hi), verdict(...)   pure
  templates/report.html  GET form, count line, table (flagged rows first); renders WeeklyReport
  seed.py          load seed/seed.sql verbatim if accounts is empty
migrations/        Alembic; one revision = seed/schema.sql DDL verbatim
tests/domain/      pure tests (no DB)
tests/integration/ against the real seeded Postgres
```

**Queries.** Two per request, both parameterized:
1. Account metadata, plus the first and latest complete local weeks, computed from the global
   `min(occurred_at)` and `max(occurred_at)` converted to the account's timezone.
2. For the 12 weeks ending with the selected week:
   - weekly counts per location and for the account total (`GROUPING SETS`), from the same
     deduplicated, zero-filled set;
   - weeks before the first complete week come back as absent, so Python counts available
     baseline weeks without date arithmetic.

**Migration.** Schema exactly as `seed/schema.sql`, so the seed loads unchanged.
- No unique constraint on the natural key, because the seed contains duplicates; deduplication
  happens in queries.
- No CHECK constraints: messiness is handled in queries, not by rejecting data.

## 8. Endpoint contract

`GET /api/accounts/{account_id}/weekly-report?week=YYYY-MM-DD`

| Param | Rule | Error |
|---|---|---|
| `account_id` | integer; must exist | `404` unknown account |
| `week` | optional; a Monday between the account's first and latest complete weeks, both derived from the data (§4); default = latest | `422` not a Monday, before the first complete week, after the latest, or malformed. Never silently coerced. |

Response `200`, judged case. The numbers are the real seed values for account 6, week
2026-07-20: the total from `docs/analysis/02`; Site A from the same CTEs as `06a`.
```json
{
  "account": {"id": 6, "name": "Metro Collision Centers", "timezone": "America/New_York"},
  "week": {"start": "2026-07-20", "end": "2026-07-26"},
  "first_complete_week": "2026-02-02",
  "latest_complete_week": "2026-07-20",
  "total": {
    "count": 87, "baseline": 72.5, "range": {"low": 52, "high": 95},
    "verdict": "within_expected_range", "weeks_of_history": 8
  },
  "locations": [
    {
      "location": "Site A",
      "week_count": 9,
      "window": {
        "start": "2026-06-29", "end": "2026-07-26", "count": 22,
        "expected": 24.0, "range": {"low": 12, "high": 38},
        "verdict": "within_expected_range", "weeks_of_history": 8
      }
    }
  ]
}
```

Not-enough-history case (same account, week 2026-03-23: the total has 7 baseline weeks; the
location windows have fewer). `baseline`, `expected` and `range` are `null` whenever the verdict
is `not_enough_history`:
```json
{
  "total": {"count": 71, "baseline": null, "range": null, "verdict": "not_enough_history", "weeks_of_history": 7},
  "locations": [
    {"location": "Site A", "week_count": 6,
     "window": {"start": "2026-03-02", "end": "2026-03-29", "count": 19, "expected": null, "range": null,
                "verdict": "not_enough_history", "weeks_of_history": 4}}
  ]
}
```
The counts are real seed values (same CTEs as `06a`).

- `first_complete_week` and `latest_complete_week` bound the page's week selector.
- `total` is `null` for single-location accounts (Q6); their one location row carries the verdict.
- `locations` is sorted with rows outside the expected range (`high`, `low`) first, then by name.
- **No-activity account** (account 20): `200` with `total: null` and `locations: []`. The page
  renders "No activity recorded for this account" from that state.
- **Count line:** M = all location rows; N = rows that are `high` or `low`; K = rows that are
  `not_enough_history` or `too_little_volume`. Rendered as "N of M locations outside expected
  range; K not judged" (the "K not judged" part is omitted when K = 0).
- **Page:** `GET /?account_id=&week=` renders the same `WeeklyReport` (account defaults to the
  first id).
  - Invalid params render the error message on the page with the matching status code, never a
    500.
  - Verdict labels are plain language, and a location verdict reads "last 4 weeks".

## 9. Tests (aimed at the known risks, not coverage)

Each test is written in the same task as the code it protects, and is named for the belief it
would falsify.

**Domain (pure, no DB)**

| Risk | Test |
|---|---|
| One extreme week distorts the baseline | `test_single_extreme_week_does_not_move_the_baseline` |
| Poisson range is wrong | `test_poisson_range_matches_reference_table`: λ = 4, 8, 15, 30, 70 against `docs/analysis/03` |
| Verdict boundaries off by one | `test_verdict_boundaries` at λ = 30 (range 17..45, lower bound > 0): 16 → low, 17 → within, 45 → within, 46 → high |
| "Within expected range" claimed when a drop is undetectable | `test_low_impossible_at_small_baseline_gives_too_little_volume` (and a rise still gives `high`) |
| A zero baseline crashes or reads every event as `high` | `test_zero_baseline_gives_too_little_volume_never_high` |
| Verdict without history | `test_fewer_than_8_baseline_weeks_gives_not_enough_history` |

**Integration (real seeded Postgres; fails loudly if the DB is missing)**

| Risk | Test |
|---|---|
| Duplicates counted, or weeks bucketed in UTC | the hand-verified number below (account 1, week 2026-07-06 = 42) |
| Default week drifts to `now()`; bounds hardcoded | `test_week_bounds_are_derived_from_the_data` (first 2026-02-02, latest/default 2026-07-20) |
| Burst distorts later weeks; Python and SQL disagree | `test_account_verdicts_and_baselines_match_sql_analysis`: account 6, weeks 05-11..07-20, verdicts and baselines against the C column and `med8` of `docs/analysis/02` (06-01 high; baseline stays 66–73.5). This is a cross-check against the agent's own SQL analysis, not independent verification; the hand-verified number is the independent check. |
| The 4-week location rule is wrong | `test_location_window_matches_sql_analysis`: account 6 Site A, week 2026-07-20: count 22, expected 24, range 12..38 (`06a` CTEs) |
| History cutoffs off by one | `test_history_cutoffs`: account 6 total `not_enough_history` at 03-23, judged at 03-30; Site A `not_enough_history` at 04-13, judged at 04-20 |
| Empty week dropped instead of counted as 0 | `test_empty_week_counts_as_zero` (account 6 Site G, `week_count` = 0 at 06-29) |
| Single-location account gets a single-week verdict | `test_single_location_account_has_no_total_verdict` (account 16: `total` null, one location row with a 4-week verdict) |
| Account with no data crashes | `test_account_without_events_returns_explicit_empty_200` (account 20) |
| Bad input coerced or 500 | `test_invalid_params_are_rejected` (parametrized: non-Monday, before the first week, after the latest week, malformed → 422; unknown account → 404) |
| UI state lost on reload | `test_page_renders_state_from_url_and_matches_json` (also checks the count line, including "K not judged", and flagged-first order) |

**The one hand-verified number:** account 1 (America/Chicago), week 2026-07-06, all events =
**42**. This week contains a duplicate pair (ids 11266/11267) and an event (id 11094, Sun
07-05 22:35 local) that falls in this week by UTC but in the previous week locally. Skipping
deduplication gives 43, UTC weeks give 43, both give 44. Computed by converting the week
boundaries rather than the rows (independent of the app's query):

```sql
SELECT count(*) FROM (
  SELECT DISTINCT location, event_type, occurred_at, duration_seconds, outcome
  FROM activity_events
  WHERE account_id = 1
    AND occurred_at >= ('2026-07-06'::timestamp AT TIME ZONE 'America/Chicago') AT TIME ZONE 'UTC'
    AND occurred_at <  ('2026-07-13'::timestamp AT TIME ZONE 'America/Chicago') AT TIME ZONE 'UTC'
) x;  -- 42
```

The engineer re-runs this by hand before the test is accepted.

## 10. Where would an LLM fit?

**Candidate:** a summary panel giving a quick overview of the week.

**Principles §5 applied honestly.** A summary's input would be fully structured (counts, ranges,
verdicts), and its cases are enumerable:
- account verdict × number of unusual locations × direction × not-judged count;
- on this seed most rows are `within_expected_range` (`04b`, `06b`), so most weeks come down to
  "nothing unusual";
- "at a glance" is already answered without prose: flagged rows sorted first, plus the count line
  "N of M locations outside expected range; K not judged" (§5). An LLM summary would add
  fluency, not information, on this data. It would also add nondeterminism, cost and latency to
  the Monday glance.

**Decision:** no summary text in this slice. The sorted table plus the count line is the
deterministic answer, and it's what an LLM version would fall back to. **Design, don't build,**
the LLM version:

- **Input:** only the computed `WeeklyReport` (counts, expected values, ranges, verdicts, names).
  Never raw events.
- **May not:** compute or estimate numbers, decide or soften verdicts, or explain causes (the
  data cannot support causes).
- **Output contract:** short JSON list of `{row, text}` sentences.
- **Verification (reject on any failure and show only the deterministic view):**
  - every number in the text appears in the input row it refers to;
  - every location name exists in the input;
  - the direction words match that row's verdict (no "drop" on a `high` row, no alarm words on
    `within_expected_range`).

  Matching numbers alone isn't enough, because a correct number can be attached to the wrong
  location.
- **Failure fallback:** on timeout (~2 s), error or rejected output, the panel is omitted and the
  sorted table plus the count line stand alone. The page never depends on the model.
- **Cost / latency:** one call per (account, week). Complete weeks never change, so the result is
  cached indefinitely under that key; at most one call per key ever. A small, fast model is
  sufficient.
- **Prompt:** committed as a reviewable artifact if the design is ever built.

**Where an LLM becomes necessary, not optional:** free text such as call notes, voicemail
transcripts or lead-form messages. Classifying *why* volume moved, or what customers are
asking for, is open language that rules can't capture. This dataset has no free text.

**Not built, including as a stretch goal.** A stub boundary would contradict the argument
above. Spare time goes to verification instead (§11).

## 11. Time budget

About 2.6 h had gone into analysis and planning when this plan was approved (first logged prompt
14:23, plan review ~17:00). The build is budgeted at **3:00**, to stay close to the challenge's
4–6 h cap. If it overruns, cut README polish first, never tests. Tests ship inside each task;
there are no optional features. Risky tasks go through the validator as they finish, not at the
end.

| # | Work | Time |
|---|---|---|
| 1 | Project setup: `pyproject.toml`, tool config, app skeleton (`NEEDS_HUMAN_COMMAND`: `uv lock`) | 0:10 |
| 2 | README skeleton: run instructions, test command, section headings to fill | 0:10 |
| 3 | Migration, seed loader, Dockerfile, compose `app` service (`NEEDS_HUMAN_COMMAND`: `docker compose down -v`, then `up`) | 0:20 |
| 4 | `db/queries.py` (week bounds + weekly series) with integration tests: hand number, week bounds, zero-fill | 0:35 |
| 5 | `domain/baseline.py` with domain tests | 0:25 |
| 6 | `report.build` + JSON endpoint with contract, cross-check, location-rule, cutoff, single-location and empty-account tests | 0:25 |
| 7 | Page (form, week selector from the data bounds, count line, flagged-first table, plain-language verdicts, "last 4 weeks" label) + page test | 0:20 |
| 8 | Clean-machine run: fresh `git clone` into a temporary folder, then `docker compose -p dash247-clean up` (separate project name, so a separate DB volume), following only the README; hand-verify the number; README completed (stack and why, interpretation, decisions, trade-offs, limitations incl. duplicates, deferred, what I'd do with another day) + AI-log reflection with one line on which tools/models were used and for what | 0:25 |
| 9 | Final adversarial review (reviewer subagent, FINAL mode) and fixes | 0:10 |
| — | Spare time, if any: a second clean-machine run; more edge-case tests | — |

**Setup steps only a human can run:** `uv lock`; `docker compose down -v` / `up`. uv 0.13.6 is
installed (it's on the engineer's shell PATH, not on the agent's Bash tool PATH, so the agent asks
the engineer to run uv commands or to expose uv to that shell).

## Changes after approval

None.
