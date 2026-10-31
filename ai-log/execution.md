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
