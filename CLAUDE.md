# CLAUDE.md

Project: **DASH-247 — weekly location activity report — <one-line feature>** (take-home challenge, see
[docs/CHALLENGE.md](docs/CHALLENGE.md)).

## Read first, in this order

1. [docs/engineering-principles.md](docs/engineering-principles.md) — normative. Check every
   proposal against it **before** presenting it.
2. [docs/conventions.md](docs/conventions.md) — decisions already frozen for this repo. Don't
   re-litigate them; if one looks wrong, say so and wait. Never deviate silently.
3. [PLAN.md](PLAN.md) — the plan. Scope changes go through this file first. Frozen once approved.
4. [TASKS.md](TASKS.md) — the plan as atomic, verifiable tasks. Work is picked up here, never
   from a free-form request.

## How work flows (spec-driven)

Principles → PLAN → TASKS → code. One-way: a task may not contradict the plan; the plan may not
contradict the principles. One task at a time; stop when its **Done when** is demonstrated.
Missing work → propose a new task, don't widen the current one. Plan wrong → say so, fix PLAN.md
first (with my approval), then code.

Execution runs through the `task-loop` skill: the main session implements, the `validator`
subagent judges high-risk tasks with fresh context, every verdict goes to `ai-log/execution.md`.
The `reviewer` subagent runs adversarial reviews of the plan (before code) and of the final diff.

## Boundaries (enforced in `.claude/settings.json`, not just requested)

- **Agents edit files; only the human commits.** After a PASS, suggest a commit message and stop.
- **Agents never change the machine.** `docker compose up/down`, `uv add/remove/lock/sync`
  (anything but `uv sync --frozen`) are mine. Need one → stop with `NEEDS_HUMAN_COMMAND`.
- **DB inspection is read-only** via `./scripts/sql-ro.sh "<SQL>"` (read-only role).
- `ai-log/raw-prompts.md` is written by a hook. Nobody edits it.

## Hard rules

- **Minimal and correct.** No feature, dependency or abstraction without a requirement demanding
  it. When in doubt, propose the smaller version.
- **Never edit `seed/`** or regenerate data. Messiness is handled in queries/code.
- **SQL is always parameterized** (`%s` / named params via psycopg). String-built SQL is a defect.
- **uv only.** Never `pip`, `uv pip`, `uvx`, `poetry`.
- <FILL: single-source-of-truth rule specific to this domain, e.g. "date bucketing happens in SQL
  only, in the account's timezone; Python never recomputes dates">
- **Log honestly.** Your mistakes and my corrections go in the AI log as they happened. Never
  attribute to me a decision or reasoning I didn't state — ask instead of inferring.

## Verify, don't assume

- Any number you report must come with the SQL that verifies it against the seed.
- Tests target the known risks listed in PLAN §Tests, written in the same task as the code they
  protect — not coverage.
- Commands: `uv run pytest -q` · `uv run ruff check .` · `uv run ruff format --check .` ·
  `uv run mypy <pkg>`
