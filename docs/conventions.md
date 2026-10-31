# Project Conventions — <TICKET-ID>

Owns **only** what no other document owns. Philosophy → `engineering-principles.md`.
Decisions, parameters and rejected alternatives → `PLAN.md` (cite sections, don't restate).

## API contract

- Invalid params → `422`/`400` with a message; never coerce silently.
- Unknown entity → `404`.
- Entity with no data → well-formed `200` with an explicit empty payload, never a `500`.
- Optional/LLM fields may be absent; absence is normal, never an error.

## Code organization

- <FILL> Aggregation SQL lives in `app/db/queries.py`, commented — queries are reviewable artifacts.
- <FILL> `app/domain/` is pure: no I/O, no DB, no clock; plain dataclasses/tuples in and out.
- Routes are thin: validate → query → domain → serialize.
- Migrations via Alembic (raw SQL in `op.execute` is fine); seed loaded verbatim by a script.

## Process

- Plan before code; scope changes go through PLAN.md first.
- One task = one commit, named for the decision: `T-07: median baseline over 8 local weeks`.
  Push the per-task commits as-is — no squash — so the history shows the process.
- AI interactions logged raw in `ai-log/`.
