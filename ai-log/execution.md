# Execution log (task-loop)

### T-01 · start · risk:low

### T-01 · human-command · AWAITING
`uv lock` (creates uv.lock; denied to the agent)

### T-01 · human-command · PASS
Human ran `uv lock --system-certs` in another terminal (in-session `uv lock` failed: UV_FROZEN=1 in env). Output: "Resolved 38 packages in 1.27s".

### T-01 · attempt 1 · self-check · PASS
1. `uv lock --check` -> exit 0 (Resolved 38 packages).
2. `uv tree --depth 1` -> alembic, fastapi, jinja2, psycopg[binary], uvicorn; dev: httpx, mypy, pytest, ruff. Nothing else.
3. grep: line 5 `requires-python = ">=3.12"`, line 24 `required-version = ">=0.8.0"`, line 26 `exclude-newer = "2026-10-24T00:00:00Z"`.
4. `uv run python -c "import app.main"` -> exit 0 (after `uv sync --frozen --system-certs`; plain run failed with TLS UnknownIssuer, environment issue, not code).
5. `ruff check .` -> All checks passed (exit 0); `ruff format --check .` -> 21 files already formatted (exit 0); `mypy app` -> Success, no issues in 2 source files (exit 0).
Note: .gitignore extended (.env, .venv/, caches) — outside listed scope, needed so the venv isn't committed.

### T-02 · start · risk:low

### T-02 · attempt 1 · self-check · PASS
1. `grep -nE "^## " README.md` -> lines 3-40: Run locally, Run tests, Stack and why, Interpretation, Decisions and trade-offs, Known limitations, Deferred / what I'd do with another day, AI usage.
2. `grep -n "docker compose up"` -> line 6 (Run locally); `grep -n pytest` -> lines 15, 18 (Run tests).
3. `grep -nEi "pip install|uvx|poetry" README.md` -> no output (exit 1).
Note: run command is `docker compose up -d --build` (PLAN §6 says `docker compose up`; -d --build matches T-03/T-08 usage).

### T-03 · start · risk:high

### T-03 · attempt 1 · human-command · AWAITING
`docker compose down -v` then `docker compose up -d --build`, then `docker compose logs app` pasted back (Done-when 1). Later: `docker compose restart app` (Done-when 4).

### T-03 · attempt 1 · human-command · PASS (partial evidence)
Human pasted `docker compose logs app`:
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Seed schema: accounts and activity_events, exactly as seed/schema.sql.
seed: loaded seed.sql
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
Self-run: check 2 -> `20 | 12626 | 1`; check 3 -> 12 columns matching seed/schema.sql (types, lengths 120/60/60/80/40/40, nullability: only duration_seconds, outcome nullable); check 5 -> `HTTP/1.1 200 OK`; check 6 -> ruff All checks passed, mypy Success (3 files).

### T-03 · attempt 1 · human-command · AWAITING
`docker compose restart app`, then `docker compose logs app --tail 30` (Done-when 4).

### T-03 · attempt 1 · human-command · PASS
Human pasted `docker compose logs app --tail 30` after restart: second start shows no "Running upgrade" line and
`seed: accounts is not empty, skipped loading seed/seed.sql`, then uvicorn on 0.0.0.0:8000.
Check 2 re-run: `20 | 12626 | 1`.

### T-03 · attempt 1 · validator · PASS
T-03 verdict: PASS. All six Done-when criteria have evidence.

1. Logs: the human-pasted logs show the migration running ("Running upgrade -> 0001"), then "seed: loaded seed.sql", then "Uvicorn running on http://0.0.0.0:8000". I did not run `docker compose logs` myself; I relied on the pasted output.
2. Counts: `./scripts/sql-ro.sh` returned `20 | 12626 | 1` against the running stack, so the read-only role can read the migrated tables.
3. Schema: the information_schema output matches `seed/schema.sql` on all 12 columns. Types match, and so do the lengths (accounts: 120/60/60; activity_events: 80/40/40) and nullability. Only `duration_seconds` and `outcome` are nullable, as in the seed. `timestamp without time zone` is correct for TIMESTAMP.
4. Restart: the pasted post-restart logs show "seed: accounts is not empty, skipped loading seed/seed.sql". The counts I queried match check 2, and the stack is running after the restart.
5. /docs: `curl -si http://localhost:8000/docs` returned `HTTP/1.1 200 OK`.
6. Lint and types: `uv run ruff check .` printed "All checks passed!". `uv run mypy app` printed "Success: no issues found in 3 source files". I did not read the exit codes directly, only the success messages.

Scope and rules:
- `git status` shows only the expected files. The other modified files (TASKS.md, ai-log/*) are process logs.
- `migrations/versions/0001_seed_schema.py` runs `seed/schema.sql` verbatim via `op.execute`, with no extra unique or CHECK constraints.
- `app/seed.py` loads the seed in a single transaction, uses no string-built SQL, and does not modify `seed/`.
- The compose `app` service has `depends_on` with `service_healthy`, runs alembic then the seed loader then uvicorn, and binds `127.0.0.1:8000`. The DB port is `${DB_PORT:-5432}`.
- The Dockerfile uses `python:3.12-slim`, the pinned uv image 0.13.6, and `uv sync --frozen`. It copies `app/`, `migrations/`, `seed/` and `tests/`.
- No routes were added beyond FastAPI's default docs.

No PENDING HUMAN item. This task does not carry the hand-verified number.

### T-04 · start · risk:high

### T-04 · attempt 1 · self-check (pre-validator notes)
- First pytest run failed at import (`No module named 'app'`): added `pythonpath = ["."]` to [tool.pytest.ini_options] in pyproject.toml (outside listed scope; needed for tests to import app).
- Agent mistake: `test_series_has_twelve_weeks_ending_with_the_selected_week` initially expected first week 2026-04-27; correct is 2026-05-04 (12 weeks ending 07-20 = 05-04..07-20, consistent with PLAN §8 Site A baseline weeks). Test expectation fixed; query unchanged.
- PLAN §9 SQL kept verbatim in the comment; two lines marked `# noqa: E501`.
- Agent ran PLAN §9 SQL via sql-ro.sh -> 42. (Done-when 5 still requires the engineer.)
- pytest 8 passed; ruff check/format clean; mypy Success (5 files); grep checks 2 and 3 -> no output.

### T-04 · attempt 1 · validator · PASS
PASS for T-04.

Evidence per criterion:
1. `uv run pytest tests/integration/test_queries.py -q` gave 8 passed. The named tests are present:
   - The hand-verified total, account 1 week 2026-07-06, asserts 42. The PLAN §9 SQL sits in a comment directly above the assertion.
   - `test_week_bounds_are_derived_from_the_data` checks all 20 accounts: first week 2026-02-02, latest 2026-07-20.
   - `test_empty_week_counts_as_zero` asserts account 6, Site G, week 2026-06-29 is exactly one row with count 0.
   - `test_account_without_events_returns_no_rows` asserts account 20 returns `[]` with no error.
   - The suite also covers 12-week length, absent pre-first weeks, total equal to the sum of locations, and an unknown account.
2. The grep for hardcoded dates in `app/` returned nothing (exit 1).
3. The grep for string-built SQL in `app/db/queries.py` returned nothing (exit 1). Parameters are bound via `%s` with tuples. The SQL is commented.
4. `ruff check` passed. `ruff format --check` reported 28 files already formatted. `mypy app` reported no issues. All three exited 0.
5. Constitution and PLAN:
   - The queries use the `(occurred_at AT TIME ZONE 'UTC') AT TIME ZONE tz` form.
   - They deduplicate on all columns except `id` and use `GROUPING SETS`. Zero-fill comes from the week x location grid.
   - Weeks before the first complete week are excluded via `GREATEST`.
   - Bounds come from the dataset's min/max `occurred_at`, not `now()`.
   - Tests use the real DB with no mocks, and the conftest fixture calls `pytest.fail` on a connection error and never skips.
   - The integration tests call `queries.py` directly instead of going through the FastAPI app. That is the engineer-confirmed deviation in the task text.
6. Scope: the changed files are `app/db/__init__.py`, `app/db/queries.py`, `tests/integration/conftest.py`, `tests/integration/test_queries.py` and `pyproject.toml`. The `pyproject.toml` change adds `pythonpath = ["."]` under pytest options so tests can import `app`. It is minor and justified by the tests. `TASKS.md` and the `ai-log` files are process logs, and `.env.example` is the T-01 leftover.
7. I ran the §9 SQL independently through `sql-ro.sh`. It returned 42, matching the test.

PENDING HUMAN: hand-verify the figure 42 (account 1, week 2026-07-06) by re-running the PLAN §9 SQL by hand: SELECT count(*) FROM (SELECT DISTINCT location, event_type, occurred_at, duration_seconds, outcome FROM activity_events WHERE account_id=1 AND occurred_at >= ('2026-07-06'::timestamp AT TIME ZONE 'America/Chicago') AT TIME ZONE 'UTC' AND occurred_at < ('2026-07-13'::timestamp AT TIME ZONE 'America/Chicago') AT TIME ZONE 'UTC') x;

### T-04 · human-command · PASS (PENDING HUMAN resolved)
Engineer re-ran the PLAN §9 SQL by hand in psql -> `42`.
Engineer also ran two counterfactuals:
- same window, no DISTINCT -> `43` (dedup removes the 11266/11267 pair);
- DISTINCT but UTC week bounds ('2026-07-06'..'2026-07-13' unconverted) -> `43` (event 11094 moves in).

### T-05 · start · risk:high

### T-05 · attempt 1 · self-check (pre-validator notes)
- `uv run pytest tests/domain -q` -> 15 passed; full suite 23 passed; ruff check/format clean; mypy Success (7 files); purity grep -> no output.
- Extra: poisson_range matches all 11 rows of docs/analysis/03 output (2:0..6 4:0..10 5:0..12 6:1..13 8:2..16 10:3..19 15:6..26 20:10..32 30:17..45 50:33..69 70:49..92); lam=72.5 -> 52..95 (= PLAN §8 account 6 total range).

### T-05 · attempt 1 · validator · PASS
T-05 verdict: PASS. Every Done-when item has execution evidence.

Done when 1:
- `uv run pytest tests/domain -q` passes: 15 passed.
- All six named tests are present in `/tests/domain/test_baseline.py` (full path: C:\Users\Windows\Desktop\FDE Challenge\qualitara-senior-ai-engineer-challenge-fp\tests\domain\test_baseline.py).
- `test_poisson_range_matches_reference_table` asserts 4→0..10, 8→2..16, 15→6..26, 30→17..45, 70→49..92. I ran `./scripts/sql-ro.sh "$(cat docs/analysis/03-min-detectable-change.sql)"`. Its `normal_range` column shows the same five ranges.
- `test_verdict_boundaries` at λ=30 asserts 16 low, 17 within, 45 within, 46 high.
- `test_low_impossible_at_small_baseline_gives_too_little_volume` asserts that 0, 4 and 10 at λ=4 give `too_little_volume`, and that 11 gives `high`.
- `test_zero_baseline_gives_too_little_volume_never_high` asserts that count 500 at λ=0 gives `too_little_volume`, not `high`.
- `test_fewer_than_8_baseline_weeks_gives_not_enough_history` is parametrized over 0, 1 and 7 weeks of history.
- `test_single_extreme_week_does_not_move_the_baseline` asserts a median of 13 with an 800 outlier in the weeks.

Done when 2: the purity grep over `app/domain/` returned nothing (exit 1). `baseline.py` imports only `math`, `statistics`, `collections.abc` and `typing`.

Done when 3: `ruff check .` exits 0, `ruff format --check .` exits 0 (31 files already formatted), and `mypy app` exits 0 (no issues in 7 source files).

PLAN §4 verdict table: `verdict()` applies the rows in order, and each row matches PLAN.
1. `not_enough_history` when weeks of history are under 8.
2. `too_little_volume` when λ=0.
3. `high` when count is above the upper bound.
4. `low` when count is below the lower bound.
5. `too_little_volume` when the lower bound is 0.
6. Otherwise `within_expected_range`.

`poisson_range` uses `math.lgamma`, returns (0, 0) for λ=0 before any `log` call, and uses no scipy.

Scope: the changed files are only `/app/domain/__init__.py`, `/app/domain/baseline.py` and `/tests/domain/test_baseline.py`. The other changes in the tree are process logs and the `.env.example` leftover. I found no unscoped change.

Tests: none mock the DB, and the assertions would fail on wrong code. The domain code is pure, so `.claude/rules/tests.md` has no mocked-DB issue to flag.

No PENDING HUMAN item for this task.

### T-06 · start · risk:high

### T-06 · attempt 1 · self-check (pre-validator notes)
- Touched T-04 file `app/db/queries.py`: `account_weeks(conn, account_id, week=None)` now also returns `week_start` (requested week or latest complete week) and `week_end` (its Sunday), computed in SQL, so Python never computes week/window end dates. Still two queries per request; T-04 tests still pass (8).
- Malformed week is rejected strictly: `Query(pattern=^\d{4}-\d{2}-\d{2}$)` + `date.fromisoformat`, so "20260720" and timestamps give 422 instead of being coerced (pydantic lax date parsing would accept unix timestamps).
- `uv run pytest tests/integration/test_api.py -q` -> 26 passed first run; full suite 49 passed; ruff check/format clean; mypy Success (8 files).
- Extra: PLAN §8 examples reproduced exactly: account 6 default week total {count 87, baseline 72.5, range 52..95, within, 8}; week 2026-03-23 total {71, null, null, not_enough_history, 7}, Site A {week_count 6, window 03-02..03-29, count 19, not_enough_history, 4}.
- Warning seen: StarletteDeprecationWarning "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead." Not acted on (dependency change = human decision).

### T-06 · attempt 1 · validator · PASS
T-06 verdict: PASS

Criterion 1: met.
- `uv run pytest tests/integration/test_api.py -q` gives 26 passed.
- All six named tests are present: `test_account_verdicts_and_baselines_match_sql_analysis` (parametrized over 11 weeks), `test_location_window_matches_sql_analysis`, `test_history_cutoffs`, `test_single_location_account_has_no_total_verdict`, `test_account_without_events_returns_explicit_empty_200` and `test_invalid_params_are_rejected` (9 cases).
- I compared the pinned account 6 totals with the real output of `docs/analysis/02-method-series.sql`. Counts, `med8`, the C-column ranges (e.g. 52..96, 46..88) and verdicts all match. The C column shows high at 06-01 and 06-08, low at 07-13, and within range elsewhere.
- `test_location_window_matches_sql_analysis` asserts Site A at 2026-07-20 has count 22, expected 24 and range 12..38.
- `test_history_cutoffs` asserts `weeks_of_history` 7 and `not_enough_history` at 03-23, judged at 03-30; Site A `not_enough_history` at 04-13, judged at 04-20.
- The tests run through `TestClient` against the real seeded DB with no mocks, and the assertions are specific rather than "is not None".

Criterion 2: met. `test_default_week_is_the_latest_complete_week` asserts that with no `week` parameter, `week.start == latest_complete_week == "2026-07-20"`.

Criterion 3: met.
- `uv run pytest -q`: 49 passed.
- `ruff check .`: all checks passed.
- `ruff format --check .`: 33 files already formatted.
- `mypy app`: no issues in 8 source files.

Scope and rules:
- Changed files are `app/report.py`, `app/main.py`, `app/db/queries.py` and `tests/integration/test_api.py`, all in scope. The `queries.py` change only adds `week_start` and `week_end` to the account SQL, and the SQL stays parameterized.
- `week_end` and the default week are computed in SQL.
- `report.py` only slices the returned rows and counts them to get `weeks_of_history`. The one date check in Python is the `weekday() != 0` Monday validation, which I take to be input validation, not date arithmetic.
- There is no HTML. The 404 and 422 mapping is in `app/main.py`.

PENDING HUMAN: none for this task. The hand-verified figure belongs to `tests/integration/test_queries.py`, not to T-06.

### T-07 · start · risk:high

### T-07 · attempt 1 · self-check (pre-validator notes)
- Added to T-04 file `app/db/queries.py`: `account_options()` (account selector) and `selectable_weeks(first, latest)` (SQL generate_series, so Python does no date arithmetic for the week selector). Not in T-07's listed scope but required by "week select bounded by first..latest complete week".
- Agent mistake 1: test asserted a mix of flagged/unflagged rows in burst week 2026-06-01; there ALL account-6 location windows contain the burst, so all are flagged. Replaced with week 2026-05-18 (Site G high, Site A within).
- Agent mistake 2 (caught before running): first choice of "flagged first" week would have passed even without sorting if the flagged location were alphabetically first. Searched all accounts/weeks via the JSON endpoint; chose account 6 / 2026-05-18, where Site G (flagged) sorts before Site A only because of flagged-first ordering. Test also asserts page row order == JSON order.
- `uv run pytest tests/integration/test_page.py -q` -> 7 passed; full suite 56 passed; ruff check/format clean; mypy Success (8 files); `grep -c "<script" app/templates/report.html` -> 0.
- Done-when 4 (live server) needs the engineer: `docker compose up -d --build app`.

### T-07 · attempt 1 · human-command · AWAITING
`docker compose up -d --build app` (image bakes in app/ and templates; running container predates T-06/T-07).

### T-07 · attempt 1 · human-command · PASS
Engineer ran `docker compose up -d --build app`; reported "app is up".

### T-07 · attempt 1 · self-check · live server vs JSON (Done-when 4, agent evidence)
curl http://localhost:8000/?account_id=A&week=W and curl .../api/accounts/A/weekly-report?week=W, compared cell by cell (week count, 4-week count, expected, range, verdict label, row order, total row, selected account/week options):
- account 6 / 2026-07-20: 15 rows + total match, selected = 6 / 2026-07-20, count line "0 of 15 locations outside expected range".
- account 6 / 2026-05-18: 15 rows match, first row Site G (high) = JSON first row.
- account 1 / 2026-07-06: 6 rows + total match, selected = 1 / 2026-07-06 (state comes from the URL, not defaults).
Script: scratchpad cmp.py (not part of the repo). Validator to re-check independently.

### T-07 · attempt 1 · validator · PASS
T-07 verdict: PASS. I checked every "Done when" item by execution against the running server.

1. PASS. `uv run pytest -q` ran the full suite, which includes `tests/integration/test_page.py`: 56 passed. Reading `test_page_renders_state_from_url_and_matches_json` confirms it asserts each required point:
   - account 6 and week 2026-07-20 selected, with a 200;
   - count line N, M and K equal to the values derived from the JSON;
   - a flagged row first (Site G, week 2026-05-18);
   - a non-zero "not judged" count for 2026-03-30;
   - 422 with "Monday" in the body for 2026-07-21;
   - "No activity recorded" for account 20.
   The test uses the real seeded DB and nothing is mocked. The extra tests cover error statuses and the week selector bounds.
2. PASS. `grep -c "<script" app/templates/report.html` returns 0.
3. PASS. `uv run pytest -q` gives 56 passed, `uv run ruff check .` passes, and `uv run mypy app` reports no issues.
4. PASS. I ran curl against http://localhost:8000 and compared each page with its JSON endpoint.
   - **account 6, week 2026-07-20:** HTTP 200 and both controls selected (`<option value="6" selected>`, `<option value="2026-07-20" selected>`). All 15 rows match the JSON on week count, 4-week count, expected value, range and verdict, in the same order. The count line reads "0 of 15 locations outside expected range".
   - **account 6, week 2026-05-18:** Site G (verdict high) is the first row. The page and JSON orders are identical for all 15 rows, and the values match. The count line reads "1 of 15".
   - **account 1, week 2026-07-06:** account 1 and 2026-07-06 are selected instead, so the state comes from the URL. All 6 rows match the JSON.
   - **errors and empty state:** `/?account_id=6&week=2026-07-21` returns 422. `/?account_id=20` contains "No activity recorded for this account."
   - **labels:** verdicts read in plain language with "(last 4 weeks)", and the column headers carry "last 4 weeks".

I found no scope or constitution problems. The changes are limited to `app/main.py`, `app/db/queries.py`, `app/templates/report.html` and `tests/integration/test_page.py`. The SQL is parameterized, week dates come from SQL `generate_series`, and the page reuses `report.build`.

Not covered: I had no real browser, so the HTTP checks above are the only reload-survival evidence. The form is a plain GET with no JavaScript, so nothing else owns the control state. There is no `PENDING HUMAN` line for this task.

### T-08 · start · risk:low

### T-08 · attempt 1 · self-check (partial: agent-verifiable items only)
- README: all six TODO sections drafted from PLAN.md (stack, interpretation, decisions/trade-offs, known limitations incl. silent deduplication and the ~3x location false alarms, deferred/another day incl. event-type filter and outcome rates, AI usage incl. "Before the clock" and the tools/models line as specified by the engineer). Three `[Fran to confirm]` marks remain in README.md.
- AI-log reflection drafted at ai-log/03-reflection.md from raw-prompts.md, 02-planning-notes.md and this file; 9 `[Fran to confirm]` marks (model versions, advisor-chat transcript, harness provenance detail, CHALLENGE.md final decision, recruiter-email reason, TLS note, strict week parsing, why the T-03 log call was rejected).
- Done-when 4: `grep -n "TODO" README.md` -> no output; `grep -nEi "another day|duplicate" README.md` -> matches; `grep -nEi "pip install|uvx|poetry" README.md` -> no output.
- Done-when 5: `grep -rniE "tools|model" ai-log/*reflection*` -> matches (ai-log/03-reflection.md).
- Not done, human-only: Done-when 1 (fresh clone `docker compose -p dash247-clean up -d --build`, curl 200, elapsed time <= 15 min), 2 (`docker compose -p dash247-clean run --rm app uv run --frozen pytest -q`), 3 (PLAN §9 SQL = 42 on the fresh clone), 6 (`docker compose -p dash247-clean down -v`). Note for the engineer: the README test command assumes the DB is already migrated and seeded (run after `up`).
- Nothing committed.

### T-08 · attempt 1 · human-command · AWAITING
Clean-machine run per TASKS.md T-08 scope; engineer also reviews/resolves the `[Fran to confirm]` items in README.md and ai-log/03-reflection.md.

### T-08 · attempt 1 · human-command · AWAITING (engineer reports a manual build; evidence not yet pasted)
Engineer: "i did build it manually and everything seems fine". No output pasted yet, so Done-when 1-3 and 6 are unverified. Still needed: curl -si http://localhost:8000/ status line from the fresh clone, clone-to-first-page elapsed time (<= 15 min), pytest -q result from `docker compose -p dash247-clean run --rm app uv run --frozen pytest -q`, the PLAN §9 SQL result (42), and confirmation that `down -v` was run.

### T-08 · attempt 1 · human-command · PASS
Engineer pasted the fresh-clone run (git clone of the GitHub remote into $env:TEMP\dash247-clean; `docker compose stop` on the main stack first):
1. `docker compose -p dash247-clean up -d --build` -> app Built, db Healthy (3.3s), app Started (3.4s). `curl.exe -si http://localhost:8000/ | Select-Object -First 1` -> `HTTP/1.1 200 OK`. Timestamps: 18:22:44 before `up`, 18:23:10 after the curl, i.e. about 26 s. All 10 Dockerfile layers were CACHED, so this is a warm-cache figure, not a cold first build (image pulls and `uv sync` were not exercised).
2. `docker compose -p dash247-clean run --rm app uv run --frozen pytest -q` -> `56 passed, 1 warning in 2.49s` (the Starlette httpx deprecation warning). 56 matches the tree after T-07, so the clone contained T-07; the README/reflection drafts were not yet pushed, so the clone's README was the skeleton (run/test commands identical).
3. PLAN §9 SQL via `docker compose -p dash247-clean exec -T db psql ...` -> `42`.
4. `docker compose -p dash247-clean down -v` -> app, db, volume dash247-clean_pgdata and network removed.
After cleanup, `docker compose start` in the main directory printed `service "db" has no container to start`: the main stack has no containers and needs `docker compose up -d` (not `start`). Not checked by the agent.
Observation: the psql command line appears echoed inside the pytest output; read as the engineer's next command typed ahead. [Fran to confirm]

### T-08 · attempt 1 · self-check · PASS
Done-when 1 (200 from fresh clone, elapsed <= 15 min: ~26 s warm cache), 2 (56 passed), 3 (42), 4 (no TODO; "another day|duplicate" match), 5 (reflection has "tools"/"model"), 6 (down -v ran) all satisfied.
PENDING HUMAN: resolve the `[Fran to confirm]` marks in README.md (3) and ai-log/03-reflection.md (9) before submission; they are drafts under Fran's name.
