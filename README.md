# DASH-247 — Weekly location activity report

A page (and a JSON endpoint behind it) that answers a customer admin's Monday question: *did
anything happen last week, overall or at one of my locations, that I should act on?*

## Run locally

```
docker compose up -d --build
```

Then open <http://localhost:8000>. The app container applies the migration, loads the seed if the
database is empty, and starts the server. Nothing else needs to be installed except Docker.

- JSON for the same data: `http://localhost:8000/api/accounts/6/weekly-report?week=2026-07-20`
  (interactive docs at `/docs`).
- Environment variables are optional and documented in `.env.example`: `DATABASE_URL` (the app's
  Postgres URL; compose sets it for the container) and `DB_PORT` (host port for Postgres,
  default 5432).
- Ports are bound to `127.0.0.1` only.

## Run tests

```
docker compose run --rm app uv run --frozen pytest -q
```

Run it after `docker compose up -d --build`, so the database is migrated and seeded: the
integration tests run against the real seeded Postgres and fail loudly if it isn't there.
Locally, with the database running: `uv run pytest -q`.

## Stack and why

Python 3.12, FastAPI, Jinja2, psycopg 3, Alembic and Postgres 16, with `uv` for dependencies.
Tests use pytest; lint and types use ruff and mypy.

- **Python** is the stack I'm strongest in and the one the role uses. 
- **Raw, parameterized SQL (psycopg), no ORM.** The aggregation SQL is the core of this slice, so
  it lives in one commented file (`app/db/queries.py`) where it can be reviewed, instead of
  being hidden behind an ORM.
- **Server-rendered page (Jinja2), no SPA.** The selected account and week live in the URL query
  string, so they survive a reload and can be shared, without any client-side state or a second
  toolchain.
- **Alembic** for the migration, because the challenge asks for the stack's standard migration
  tooling. The single revision runs `seed/schema.sql` verbatim, so the seed loads unchanged.
- **No scipy, no pool, no settings library.** Poisson ranges are about 15 lines with
  `math.lgamma`. One connection per request is enough for one trusted user. Each dependency is
  justified in `PLAN.md` §6.
- **Supply chain:** `uv.lock` is committed and installs use `uv sync --frozen`. `uv` has a
  lower-bound `required-version` and an `exclude-newer` cooling-off timestamp.

## Interpretation

**The user** is a customer admin of a service business, often with several locations. The point
is that they can answer the question without calling an account manager.

**What "normal" means here:** a count is *within the expected range* if it falls inside the range
that ordinary week-to-week noise produces around *this account's* (or this location's) own
recent typical week. Not other customers, not a target, not a forecast. The page never says
"normal": at small volumes only large changes are detectable, so "normal" would claim more than
the data supports.

**The slice.** For one account and one complete local week (default: the latest):

- the **account total**, judged on that week (multi-location accounts only);
- every **location**, judged on the **4 weeks** ending that week, with the selected week's count
  shown beside it and no verdict of its own;
- rows outside the expected range first, and one line at the top: "N of M locations outside
  expected range; K not judged".

**Assumptions** (full list with reasoning in `PLAN.md` §2; none were emailed to the recruiter, so
they are documented there with the working assumption used):

- **"This week" is not `now()`.** The seed is a static snapshot ending 2026-07-27, so the default
  is the last complete local week before the latest event in the whole dataset (2026-07-20). The
  user can pick any other complete week. In a real product the anchor would be today's date.
- **Weeks are Monday–Sunday in the account's timezone**, and only complete weeks are judged or
  selectable. Week bounds are derived from the data, never hardcoded.
- **The 2026-06-03 burst at account 6 (~800 extra events) is treated as real activity.** With
  this little data and this much variance it can't be statistically rejected, so the baseline
  must be robust to it.
- **Account 18's `UTC` timezone is treated as real**; there isn't enough evidence to flag it.
- **`occurred_at` is UTC, as the schema says.** The survey found times that look
  timezone-blind (every timezone peaks at the same UTC hour). That is logged as a data-quality
  question for product; weeks are bucketed in local time regardless.
- **Duplicates:** rows identical on every column except `id` (12 pairs) count once.
- **All three event types are summed**; outcomes and durations are not used.
- **No auth.** An account selector stands in for the logged-in admin.
- **Single-location accounts** (8, 13, 16, 19) get one location row with the 4-week verdict and
  no single-week total verdict.

## Decisions and trade-offs

**The method** (evidence in `docs/analysis/`, each query reproducible through
`./scripts/sql-ro.sh`):

- **Median baseline over the 8 weeks before the judged period, not the mean.** One extreme week
  must not distort the weeks after it. Account 6's baseline stays between 66 and 73.5 through
  and after the 880-event burst week; the mean of the eight weekly counts around it is 171.
- **Poisson 99% range (0.5%–99.5% quantiles) around the baseline, not a percentile band or a
  MAD band.** Weekly counts have variance close to their mean on this data. Measured on the
  seed: a P10–P90 band flags 23–35% of ordinary weeks by construction, and a MAD band is
  unstable on small counts (7.6% false alarms). At account level the Poisson range gives 0–2%
  false alarms and catches 59% of halved weeks at baselines 20–40 and 92% above 40.
- **Locations are judged over 4 weeks, not 1.** A single-week location verdict catches about 2%
  of halved weeks at typical location volume. Four weeks (expected = 4 × the median of the 8
  weeks before the window, no overlap) catch about 51% of sustained halvings. The price is that a
  location verdict reacts to sustained changes, not one-week dips; the page says "last 4
  weeks" next to it.
- **No range or verdict on the single-week location count.** At a baseline of about 6 the range
  is 1..13, nearly uninformative, and a range without a verdict invites the admin to judge it
  themselves. The count alone is what the dashboard shows today.
- **Verdicts are explicit about what they cannot say:** `not_enough_history` (fewer than 8
  baseline weeks), `too_little_volume` (a zero baseline, or a lower bound of 0 so a drop can't be
  detected), `high`, `low`, `within_expected_range`. A zero baseline is never `high`.
- **99%, one parameter for the window (8 weeks) at both levels,** so a Monday flag is worth
  acting on and the method is easy to explain and test.

**The structure:**

- **SQL owns "what happened"** (deduplication, local weeks, zero-fill, week bounds, totals);
  **Python owns "is it normal"** (median, Poisson range, verdicts, as pure functions with no I/O).
  Python never computes or adjusts dates.
- **The timestamp trap:** `occurred_at` is a `TIMESTAMP` without time zone holding UTC, so the
  local time is `(occurred_at AT TIME ZONE 'UTC') AT TIME ZONE tz`. A single
  `occurred_at AT TIME ZONE tz` shifts the value the wrong way. The one hand-verified number
  (account 1, week 2026-07-06 = 42) catches that mistake and the duplicate pair in the same week.
- **One typed result** (`WeeklyReport`) is built by one function and rendered by both the JSON
  endpoint and the HTML page.
- **Invalid input is rejected, never coerced:** a non-Monday, a week outside the data, or a
  malformed date gives a 422 with a message; an unknown account gives a 404; an account with no
  events gives a well-formed empty 200.

**Build-time choices made by the agent, not individually reviewed by me** [Fran to confirm]:
strict `YYYY-MM-DD` week parsing (a lax parser would accept timestamps), the page's HTML layout
and verdict wording, the account/week selector queries, and `pythonpath = ["."]` in the pytest
config.

**Trade-offs I weighed:** a server-rendered page over an SPA (less interactivity, much less to
run and review); medians and Poisson over a heavier statistical model (see the dispersion
limitation below); a smaller scope (no event-type filter, no charts) over a broader one, with
the time going to tests and verification instead.

**Tests** are aimed at the known risks in `PLAN.md` §9, each named for the belief it would
falsify: an extreme week moving the baseline, the Poisson range against the SQL reference,
verdict boundaries, undetectable drops, zero baselines, history cutoffs, empty weeks counted as
0, duplicates and UTC-vs-local bucketing (the hand-verified number), single-location and empty
accounts, rejected input, and the page matching the JSON. The integration tests use the real
seeded Postgres, with no mocks.

## Known limitations

- **Duplicates are removed silently.** Rows identical on every column except `id` count once, and
  neither the page nor the API says so; this README is the only place it is stated.
- **Location false alarms are about 3× nominal:** 3.1% of 4-week windows instead of the ~1% the
  99% range suggests (6.5% at baselines of 5 or less, where detection is also only 4%). The range
  treats the 8-week median as exact, and its sampling error is multiplied by 4. A 12-week
  baseline measured 2.4% / 46% on the same windows; I kept one parameter instead.
- **Dispersion was measured on synthetic data.** Weekly variance is about equal to the mean here;
  real activity is usually more dispersed, and then the Poisson range would over-fire. The next
  step is to measure variance/mean on production data and, if it is above 1, widen the range
  with a per-series dispersion estimate (quasi-Poisson or negative binomial).
- **At small volume, "within expected range" means "no large change."** Expected 4-week counts of
  20–30 need a drop of roughly 55% to 47% before they are flagged low. Every judged row shows its
  count, expected value and range, so smaller moves stay visible without a verdict.
- **No seasonality, holiday or weekday adjustment** (only 25 complete weeks of history).
- **Known gaps that don't occur in the seed:** permanently closed locations (their baseline decays
  to 0, which gives `too_little_volume`), and locations that first appear mid-history (they are
  zero-filled from the first complete week; the zero-baseline rule keeps that from producing
  false `high` verdicts).
- **No auth, no alerting, no forecasting** (out of scope per the ticket and the challenge).
- **Test warning:** Starlette warns that using `httpx` with its `TestClient` is deprecated and
  suggests `httpx2`. Not acted on; changing dependencies is a separate decision.

## Deferred / what I'd do with another day

- **Event-type filter** (calls vs leads vs appointments). Filtered series have zero or
  near-zero baselines (7 of 69 location appointment series have an 8-week median of 0, and 60 of
  69 are at 1 or less), and the method was never validated on them. I'd validate it first.
- **Outcome rates** (missed-call %, conversion). Denominators are tiny and rates swing 4–44%
  monthly at small accounts, so they need their own method.
- **Dispersion-aware ranges,** once real variance/mean is measured (see above).
- **Surfacing the deduplication** in the page or API instead of only in this README.
- **A second clean-machine run** and more edge-case tests with the spare time.
- **An LLM summary panel: designed, not built.** A summary adds fluency, not information, on this
  data: sorting flagged rows first plus the count line already answers "at a glance". The design
  in `PLAN.md` §10 gives the model only the computed `WeeklyReport`, forbids it to compute
  numbers, decide verdicts or explain causes, rejects any output whose numbers, location names or
  direction words don't match the input row, falls back to the table on timeout, error or
  rejection, and caches one call per (account, week). An LLM becomes necessary rather than
  optional only with free text (call notes, voicemail transcripts), which this dataset doesn't
  have.

## AI usage

- **Before the clock.** The agent harness (the `CLAUDE.md` rules, the `task-loop` skill, the
  `validator` and `reviewer` subagents, and the permission settings in `.claude/`) was adapted
  from a colleague's recommendation given in a conference, which I studied beforehand to improve my own harness. That study
  happened before the first logged prompt (2026-10-31 14:23).
- **Tools and models.** Claude Code with Opus for planning, reviews and T-03–T-06; Sonnet for
  routine tasks and the validator. A separate Claude chat served as a planning advisor to weigh
  options and review the harness; every decision was mine. [Fran to confirm: exact model
  versions]
- **Division of labor.** The agent surveyed the data, ran the analysis SQL, drafted `PLAN.md`
  and implemented the tasks in `TASKS.md` one at a time. I made the decisions listed in
  `ai-log/raw-prompts.md`, ran every machine-changing command myself (`uv lock`, `docker compose`)
  and committed. A `reviewer` subagent reviewed the plan before any code; a `validator` subagent
  with fresh context judged each high-risk task, and its verdicts are in `ai-log/execution.md`.
- **The log.** `ai-log/` holds the raw prompts (written by a hook, not edited), the survey
  output, the planning notes, the per-task execution log with every verdict, and
  `ai-log/03-reflection.md`: specific moments where the AI was wrong or I overrode it.
- **Time.** The plan budgeted about 2.6 h of analysis and planning plus a 3 h build. 
