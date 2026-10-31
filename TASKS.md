# TASKS — DASH-247

Derived from [PLAN.md](PLAN.md) (approved 2026-10-31). A task may not contradict the plan. Work
runs through the `task-loop` skill: one task at a time; `risk:high` is judged by the `validator`
subagent; every verdict is appended to `ai-log/execution.md`; only the human commits.

Markers: `[ ]` pending · `[~]` in progress · `[x]` done · `[!]` needs human decision · `[-]` dropped.

**Prerequisites and conventions**
- **uv on the agent's PATH.** The `Done when` checks use `uv run …`. uv is on the engineer's
  shell PATH but not on the agent's Bash tool PATH. Either expose it to Git Bash, or, from T-03
  on, run the same checks as `docker compose run --rm app uv run --frozen …`.
- **Machine-changing commands are the human's** (`uv lock`, `docker compose up/down/restart`).
  The agent stops with `NEEDS_HUMAN_COMMAND`.
- **Code that runs inside the app container is baked into the image.** Checks against the running
  server need `docker compose up -d --build app` (human) after code changes.
- **Every check is a command a validator can run.** No check reads "looks right".

---

### [x] T-01 · risk:low · Project setup
deps: []

**Scope** (PLAN §6, §7):
- `pyproject.toml`: runtime deps exactly as PLAN §6, dev group (`pytest`, `httpx`, `ruff`,
  `mypy`), `requires-python`, `[tool.uv] required-version = ">=<lowest version supporting the
  options used>"`, `exclude-newer` with its format checked against the uv docs;
- `.python-version` (3.12), ruff and mypy config;
- `app/__init__.py`, and `app/main.py` holding only the FastAPI app object;
- `.env.example` (`DATABASE_URL`, `DB_PORT`).
- Human runs `uv lock`.

**Done when**
1. `uv lock --check` exits 0.
2. `uv tree --depth 1` shows exactly these top-level packages:
   - runtime: `fastapi`, `uvicorn`, `jinja2`, `psycopg` (binary extra), `alembic`;
   - dev: `pytest`, `httpx`, `ruff`, `mypy`;
   - nothing else.
3. `grep -nE "required-version|exclude-newer|requires-python" pyproject.toml` shows all three, and
   `required-version` starts with `>=`.
4. `uv run python -c "import app.main"` exits 0.
5. `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy app` all exit 0.

**Out of scope:** routes, SQL, Docker.

---

### [x] T-02 · risk:low · README skeleton
deps: [T-01]

**Scope** (PLAN §6, §11): replace the starter README with a skeleton.
- The run and test commands are final, exactly as in PLAN §6.
- These sections are headed with a `TODO` line: Stack and why · Interpretation · Decisions and
  trade-offs · Known limitations · Deferred / what I'd do with another day · AI usage.

**Done when**
1. `grep -nE "^## " README.md` lists: Run locally, Run tests, Stack and why, Interpretation,
   Decisions and trade-offs, Known limitations, Deferred / what I'd do with another day, AI usage.
2. `grep -n "docker compose up" README.md` and `grep -n "pytest" README.md` each match inside
   the run and test sections.
3. `grep -nEi "pip install|uvx|poetry" README.md` returns nothing.

**Out of scope:** filling the TODO sections (T-08).

---

### [x] T-03 · risk:high · Migration, seed loader, Dockerfile, compose `app` service
deps: [T-01]

**Scope** (PLAN §6 Infrastructure, §7 Migration):
- **Alembic:** `alembic.ini`, `migrations/` and one revision that runs the `seed/schema.sql` DDL
  verbatim via `op.execute`. No unique or CHECK constraints.
- **`app/seed.py`:** loads `seed/seed.sql` in one transaction only if `accounts` is empty;
  otherwise prints that it skipped.
- **`Dockerfile`:** `python:3.12-slim` and uv from its pinned image; `uv sync --frozen` including
  dev; copies `app/`, `migrations/`, `seed/`, `tests/`.
- **Compose `app` service:**
  - `depends_on: db: condition: service_healthy`;
  - command: `alembic upgrade head` → seed loader → `uvicorn app.main:app --host 0.0.0.0 --port 8000`;
  - ports `"127.0.0.1:8000:8000"`; DB host port `${DB_PORT:-5432}`.
- **Human commands:** `docker compose down -v`, then `docker compose up -d --build`.

**Done when**
1. `docker compose logs app` (human-provided after `up`) shows the migration applied, the seed
   loaded, and uvicorn listening on `0.0.0.0:8000`.
2. `./scripts/sql-ro.sh "SELECT (SELECT count(*) FROM accounts) AS accounts, (SELECT count(*) FROM activity_events) AS events, (SELECT count(*) FROM alembic_version) AS revisions"`
   returns `20 | 12626 | 1`. This also proves the read-only role can read the migrated tables.
3. `./scripts/sql-ro.sh "SELECT table_name, column_name, data_type, character_maximum_length, is_nullable FROM information_schema.columns WHERE table_schema = 'public' AND table_name IN ('accounts','activity_events') ORDER BY table_name, ordinal_position"`
   matches `seed/schema.sql` column by column (types, lengths, nullability).
4. After `docker compose restart app` (human), `docker compose logs app --tail 30` shows the seed
   loader skipped, and check 2 returns the same counts.
5. `curl -si http://localhost:8000/docs` starts with `HTTP/1.1 200`, which proves the app is
   reachable from the host.
6. `uv run ruff check .` and `uv run mypy app` exit 0.

**Out of scope:** any route besides FastAPI's default docs.

---

### [x] T-04 · risk:high · Weekly series SQL
deps: [T-03]

**Scope** (PLAN §4 Definitions, §7 Queries and Timestamp trap, §9 hand-verified number):
- `app/db/queries.py`:
  - `connect()` from `DATABASE_URL`;
  - a query for account metadata plus the first and latest complete local weeks, derived from the
    global `min`/`max(occurred_at)` in the account's timezone;
  - a query for the 12 weeks ending with the selected week: counts per location and for the
    account total (`GROUPING SETS`), deduplicated on all columns except `id`, local
    Monday–Sunday weeks with the `(occurred_at AT TIME ZONE 'UTC') AT TIME ZONE tz` form,
    zero-filled, and weeks before the first complete week absent;
  - all SQL commented and parameterized.
- Tests: `tests/integration/conftest.py`, which fails loudly when the DB is missing and never
  skips, and `tests/integration/test_queries.py`.
- **Confirmed deviation (engineer, 2026-10-31):** `.claude/rules/tests.md` says integration
  tests go "through the FastAPI app". The endpoint doesn't exist until T-06, so these tests call
  `queries.py` directly against the real seeded DB, with no mocking.

**Done when**
1. `uv run pytest tests/integration/test_queries.py -q` passes, including:
   - the hand-verified number: account 1, week 2026-07-06, total = 42, with the PLAN §9 SQL in a
     comment directly above the assertion;
   - `test_week_bounds_are_derived_from_the_data`: first 2026-02-02, latest 2026-07-20;
   - `test_empty_week_counts_as_zero`: account 6 Site G, week 2026-06-29 = 0, present rather than
     missing;
   - account 20 returns no series rows and raises no error.
2. `grep -rnE "20[0-9]{2}-[0-9]{2}-[0-9]{2}" app/` returns nothing: no hardcoded dates in code.
3. `grep -nE "f\"[^\"]*(SELECT|WHERE|FROM)|\.format\(|%\s*\(" app/db/queries.py` returns nothing:
   no string-built SQL.
4. `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy app` exit 0.
5. `PENDING HUMAN:` the engineer re-runs the PLAN §9 SQL by hand and pastes `42`.

**Out of scope:** median, ranges, verdicts (T-05); HTTP (T-06).

---

### [x] T-05 · risk:high · Domain: baseline, Poisson range, verdicts
deps: [T-01]

**Scope** (PLAN §4 Definitions and Verdicts, §6 "No scipy"):
- `app/domain/baseline.py`, pure functions:
  - `median`;
  - `poisson_range(lam) -> (lo, hi)`: the 0.5% / 99.5% quantiles using `math.lgamma`; λ = 0
    returns `(0, 0)` without calling `log(0)`;
  - `verdict(count, lam, weeks_of_history)`, applying the PLAN §4 precedence table exactly.
- `tests/domain/test_baseline.py` with the six domain tests in PLAN §9.

**Done when**
1. `uv run pytest tests/domain -q` passes, with these tests present by name:
   - `test_single_extreme_week_does_not_move_the_baseline`;
   - `test_poisson_range_matches_reference_table`: λ 4 → 0..10, 8 → 2..16, 15 → 6..26,
     30 → 17..45, 70 → 49..92, which reproduces `./scripts/sql-ro.sh "$(cat docs/analysis/03-min-detectable-change.sql)"`;
   - `test_verdict_boundaries` at λ = 30: 16 low, 17 within, 45 within, 46 high;
   - `test_low_impossible_at_small_baseline_gives_too_little_volume`, which also asserts a rise
     gives `high`;
   - `test_zero_baseline_gives_too_little_volume_never_high`;
   - `test_fewer_than_8_baseline_weeks_gives_not_enough_history`.
2. `grep -rnE "^(import|from) (psycopg|fastapi|datetime|app\.db)" app/domain/` returns nothing:
   the domain stays pure.
3. `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy app` exit 0.

**Out of scope:** SQL, HTTP, presentation.

---

### [x] T-06 · risk:high · `report.build` and the JSON endpoint
deps: [T-04, T-05]

**Scope** (PLAN §4, §7, §8, §9):
- `app/report.py`: the `WeeklyReport` pydantic models and `build(conn, account_id, week)`.
  - It applies the account rule (multi-location accounts only) and the location rule: 4-week
    window against 4 × the median of the 8 weeks before it.
  - It computes `weeks_of_history` from the absent weeks the SQL returns; Python does no date
    arithmetic.
  - Nullable `baseline` / `expected` / `range` when the verdict is `not_enough_history`; `total`
    null for single-location accounts; flagged-first sorting.
- Route `GET /api/accounts/{account_id}/weekly-report?week=` in `app/main.py`: 404 for an unknown
  account; 422 for a non-Monday, out-of-range or malformed week.
- `tests/integration/test_api.py` through `TestClient`.

**Done when**
1. `uv run pytest tests/integration/test_api.py -q` passes, with these tests present by name:
   - `test_account_verdicts_and_baselines_match_sql_analysis`: account 6, weeks 05-11..07-20,
     verdicts and baselines equal to the C column and `med8` of
     `./scripts/sql-ro.sh "$(cat docs/analysis/02-method-series.sql)"`;
   - `test_location_window_matches_sql_analysis`: account 6 Site A at 2026-07-20 has count 22,
     expected 24, range 12..38;
   - `test_history_cutoffs`: total `not_enough_history` at 03-23 (with `weeks_of_history` 7) and
     judged at 03-30; Site A `not_enough_history` at 04-13 and judged at 04-20;
   - `test_single_location_account_has_no_total_verdict` (account 16);
   - `test_account_without_events_returns_explicit_empty_200` (account 20: `total` null,
     `locations` empty);
   - `test_invalid_params_are_rejected`: non-Monday, before the first week, after the latest week
     and malformed give 422; an unknown account gives 404.
2. The default-week call (no `week` parameter) returns `week.start` equal to
   `latest_complete_week`. Asserted in `test_api.py`.
3. `uv run pytest -q` (whole suite), `uv run ruff check .`, `uv run ruff format --check .` and
   `uv run mypy app` exit 0.

**Out of scope:** HTML.

---

### [x] T-07 · risk:high · Page
deps: [T-06]

**Scope** (PLAN §1, §5, §8 Page and Count line):
- `GET /?account_id=&week=` renders the same `WeeklyReport` through `app/templates/report.html`:
  - a GET form with an account select and a week select bounded by `first_complete_week`..
    `latest_complete_week`;
  - the count line ("N of M locations outside expected range; K not judged");
  - the table with flagged rows first and plain-language verdicts, with the location verdict
    labelled "last 4 weeks";
  - "No activity recorded for this account" for account 20;
  - errors rendered with the matching status code. No JavaScript.
- `tests/integration/test_page.py`.

**Done when**
1. `uv run pytest tests/integration/test_page.py -q` passes, and
   `test_page_renders_state_from_url_and_matches_json` asserts:
   - `/?account_id=6&week=2026-07-20` returns 200 with account 6 and that week selected;
   - the count line's N, M and K equal the values derived from the JSON for the same parameters;
   - a flagged row appears before an unflagged one;
   - a week before 04-20 shows a non-zero "not judged" count;
   - `/?account_id=6&week=2026-07-21` returns 422 with a message, not 500;
   - account 20's page contains "No activity recorded".
2. `grep -c "<script" app/templates/report.html` returns 0.
3. `uv run pytest -q`, `uv run ruff check .` and `uv run mypy app` exit 0.
4. **Reload survival over HTTP against the running server**, checked by the validator. This is
   an explicit challenge requirement. The human first runs `docker compose up -d --build app`.
   - `curl -s "http://localhost:8000/?account_id=6&week=2026-07-20"` returns HTML in which:
     - the account control has account 6 selected and the week control has 2026-07-20 selected;
     - every location row's week count, 4-week count, expected value, range and verdict equal
       `curl -s "http://localhost:8000/api/accounts/6/weekly-report?week=2026-07-20"`, in the
       same flagged-first order.
   - Repeating the page request with a different account and week (e.g. `account_id=1&week=2026-07-06`)
     shows those values selected instead, so the state comes from the URL, not from defaults.

**Out of scope:** styling beyond legibility.

---

### [x] T-08 · risk:low · Clean-machine run, hand verification, README and AI log
deps: [T-02, T-07]

**Scope** (PLAN §11 row 8):
- **Human:** stop the main stack with `docker compose down`, keeping its volume (ports 8000/5432
  are shared). Clone the repo fresh into a temporary folder and follow only the README:
  `docker compose -p dash247-clean up -d --build`.
- Fill every README `TODO`: stack and why, interpretation, decisions and trade-offs, known
  limitations (including silent deduplication and the ~3× location false alarms), deferred / what
  I'd do with another day (event-type filter, outcome rates), AI usage.
- AI-log reflection: specific moments where the AI was wrong or overridden, plus one line on
  which tools/models were used and for what.

**Done when**
1. Human pastes the output of `curl -si http://localhost:8000/` (`HTTP/1.1 200`) from the fresh
   clone, and the elapsed time from clone to first page, which must be at most 15 minutes.
2. Human pastes `docker compose -p dash247-clean run --rm app uv run --frozen pytest -q`, all
   passed.
3. Human pastes the PLAN §9 SQL result: `42`.
4. `grep -n "TODO" README.md` returns nothing, and `grep -nEi "another day|duplicate" README.md`
   matches.
5. `ai-log/` contains a reflection naming specific moments and a tools/models line:
   `grep -rniE "tools|model" ai-log/*reflection*` matches.
6. Human runs `docker compose -p dash247-clean down -v` to clean up.

**Out of scope:** new features or fixes. Problems found become new tasks via `DISCOVERED_WORK`.

---

### [x] T-09 · risk:low · Final adversarial review
deps: [T-08]

**Scope** (PLAN §11 row 9): run the `reviewer` subagent in FINAL mode on the repo and diff. Relay
its findings to the human unedited. Fixes happen only with human approval, as new tasks if they
fall outside an existing task's scope.

**Done when**
1. The reviewer's report is appended verbatim to `ai-log/execution.md`.
2. Every finding has a recorded decision there: fixed (with task id), deferred (with README line),
   or rejected (with reason).
3. `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy app`
   exit 0 on the final tree.

---

### [x] T-10 · risk:high · Strict week parsing shared by the page and the API
deps: [T-09]

**Origin:** T-09 final review finding (SHOULD), approved by the engineer. The page route calls
`parse_week` without `WEEK_PATTERN`; Python 3.12 `date.fromisoformat` accepts `20260720` and
`2026-W30-1`, so the page silently coerces formats the API rejects with 422 (conventions: "never
coerce silently"; README: "Invalid input is rejected, never coerced").

**Scope** (PLAN §8 `week` rule):
- `app/main.py`: one strict `YYYY-MM-DD` check inside `parse_week`, used by both routes; the
  API keeps returning 422 with a message, the page renders the message with 422.
- `tests/integration/test_page.py`: page cases `20260720` and `2026-W30-1` → 422 with a message.
- `tests/integration/test_api.py:31`: annotate a local so `uv run mypy app tests` passes
  (folded-in NIT).

**Done when**
1. `uv run pytest tests/integration/test_page.py tests/integration/test_api.py -q` passes, and the
   page error test includes `20260720` and `2026-W30-1` (each 422 with `role="alert"`), while the
   API's existing malformed cases (`20260720`, `2026-07-20T00:00:00`, `2026-13-01`, `last-week`)
   still give 422.
2. `grep -c "fromisoformat" app/main.py` returns 1: there is one parsing path.
3. `uv run pytest -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`
   and `uv run mypy app tests` exit 0.
4. Against the running server after `docker compose up -d --build app` (human):
   `curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/?account_id=6&week=20260720"`
   prints `422`, and the same for `week=2026-W30-1`; `week=2026-07-20` prints `200`.

**Out of scope:** any other validation change.
