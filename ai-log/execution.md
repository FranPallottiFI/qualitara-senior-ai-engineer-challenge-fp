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
