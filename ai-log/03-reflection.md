# 03 · Reflection: specific moments where the AI was wrong or I overrode it

Drafted by the agent, reviewed and corrected by me (Fran). Sources: `raw-prompts.md`,
`00-advisor-chat.md`, `02-planning-notes.md` and `execution.md`. Quotes of Fran are verbatim from
`raw-prompts.md`.

## Tools and models (one honest line)

Claude Code with Opus 5.5 for planning, reviews and T-03–T-06, and Sonnet 5.5 for routine tasks
(T-01, T-02, T-07, drafting this file) and the validator; a separate advisor chat on claude.ai
(same models) to weigh options, review the harness and draft many of the structured prompts, with
every decision Fran's. The advisor chat is summarized in `00-advisor-chat.md`; it is not in
`raw-prompts.md`, which only records prompts typed into Claude Code.

## Before the clock

The harness was adapted from a colleague's prior submission of this challenge, which Fran studied
beforehand with the help of the advisor chat, before the first logged prompt (2026-10-31 14:23).
`00-advisor-chat.md` lists which files came from that work (`CLAUDE.md`, the principles and
conventions documents, the two subagents, the `task-loop` skill, the test rule and the settings)
and the deliberate differences from the colleague's version.

**A consequence worth stating:** when `raw-prompts.md` shows well-structured direction from the
survey onward, the wording is often the advisor's and the decisions in it are Fran's
(`00-advisor-chat.md`, "During the challenge").

## 1. Fran's own calls

- **Removing the trap list from the first survey prompt.** The advisor's draft listed specific
  data traps; Fran flagged it as steering the agent with knowledge from the prior submission, and
  the prompt was rewritten neutral (`00-advisor-chat.md`, 14:47). The neutral version is the one
  in `raw-prompts.md` at 14:48.
- **Proposing the stack.** Fran proposed Python + FastAPI, psycopg with raw SQL, Alembic,
  server-rendered Jinja2 and uv, and asked the agent to argue against it: "Don't agree just
  because it's my proposal." (`raw-prompts.md` 16:11; `00-advisor-chat.md`, 16:03.)
- **The LLM summary-panel idea.** "the candidate I see is a summary panel giving a quick overview
  of the week" (`raw-prompts.md` 16:36). Later designed and deferred (PLAN §10).
- **Keeping `docs/CHALLENGE.md` committed,** against the advisor's recommendation to remove it
  from history: "dont worry about the challenge.md. it stays commited" (`raw-prompts.md` 17:12;
  `00-advisor-chat.md`, 17:09). This settles an earlier conflict: at 16:36 Fran had said it
  "stays local and uncommitted", and a 17:11 draft of the next prompt said it had been untracked.
  Fran confirmed at T-09 that staying committed is final.

## 2. Fran caught the AI being wrong (planning)

Several of these were first raised in the advisor chat; Fran decided them and sent them.

1. **It measured only false alarms.** *(First raised by the advisor, `00-advisor-chat.md` 15:33.)*
   The agent's first comparison of baseline methods scored them on false-alarm rate and
   recommended method C. Fran: "you only measured false alarms, not misses. A method that never
   fires also scores 0%." The follow-up (`docs/analysis/03`, `04a`, `04b`, `05`) showed a
   single-week location verdict catches about 2% of halved weeks. That produced the 4-week
   location rule.
2. **It called the verdict "normal".** *(Advisor suggestion, 16:43.)* Fran: "'Normal' overclaims
   when only large drops would show." Renamed "within expected range" everywhere.
3. **It hardcoded week bounds into the contract.** *(Advisor suggestion, 16:43.)* Fran: "Week
   bounds must be derived from the data (first/last complete weeks), never hardcoded dates." Now
   enforced by a grep in T-04's "Done when" and a test over all 20 accounts.
4. **Variance ≈ mean.** *(First raised by the advisor, `00-advisor-chat.md` 15:33.)* The analysis found weekly variance close to the mean (median ratio
   0.97, `docs/analysis/01`) and the method rests on it. Fran: "the variance~mean result may be
   because the seed is synthetic. Real volume is usually more dispersed, and then C would
   over-fire." It became a known limitation with a next step, not code.
5. **Q9 wording.** *(Advisor suggestion, 16:43.)* Fran specified that `occurred_at` is treated as
   UTC per the schema and that the timezone-blind look of the times goes to product as a
   data-quality question.

## 3. The AI argued against Fran, or Fran changed course

- **Single-week location rows (Q12).** Fran had decided single-week location counts are "shown
  with baseline and range but no verdict". The agent argued against it (a range of 1..13 at
  baseline 6 is nearly uninformative; a range without a verdict invites the admin to judge it;
  the count alone is what the dashboard shows today). Fran: "Cut 2: accepted. Single-week
  location rows show the count only."
- **LLM stub as a stretch goal.** Fran proposed it. The agent argued it contradicts the plan's own
  argument and the challenge's warning about box-checking. Fran: "Agreed: drop the stub stretch
  goal."
- **Summary module.** The agent proposed cutting the templated summary. Fran cut it partially: no
  module, but keep a one-line count rendered from the rows.
- **Event-type filter.** Fran first said "keep; it's the first cut if time runs short". After the
  reviewer's evidence of zero and near-zero baselines on filtered series (and the advisor's
  recommendation, 17:09), Fran: "Cut the event-type filter now. Move it to 'next iteration' with
  the reviewer's reason".
- **Placeholders in Fran's prompts.** At 17:11–17:12 a prompt contained the literal text "I didn't
  email the recruiter because <your real reason>" (an advisor template, per
  `00-advisor-chat.md`). The agent did not invent a reason; `PLAN.md` states only the facts. The
  same happened twice more in the T-09 decisions. Fran then gave the reason: "I didn't want to
  block on a reply inside the time budget."

## 4. The reviewer subagent caught the AI's plan errors (before any code)

Verdict `READY_WITH_FIXES`, 16 findings. The reviewer checked every decision the plan attributes
to Fran against `raw-prompts.md` and found all of them backed. Errors it caught in the agent's
plan:

- **uvicorn bound to `127.0.0.1` inside the container** (blocker): the published port would have
  been unreachable on the evaluator's first try. Fixed to `0.0.0.0` with the host side bound to
  `127.0.0.1`, and `depends_on: service_healthy`.
- **Single-location accounts got a single-week verdict** that Q12 and §4 argue against. Fran:
  "#3: single-location accounts are treated like location rows."
- **An untraceable number** ("22–27 of 69 locations") that came from a different method's
  figure, a 12-week alternative compared against a different window set, and "two points"
  where the notes list three.
- **A count line that read as reassurance** ("0 of 15 locations outside expected range" on weeks
  where every row was `not_enough_history`), which led to the "K not judged" clause.
- **No tests for the 4-week rule or the history cutoffs**, and the validator scheduled at the end
  instead of per task.

## 5. The AI caught or admitted its own mistakes

Planning (from `02-planning-notes.md`): example numbers in the JSON contract were invented and
labelled "illustrative" until the agent queried the real ones; the "mean = 171" figure was cited
to a file that doesn't contain a mean; the first `04b` query timed out and was rewritten with
materialized baselines; a temp file went to `/tmp` instead of the scratchpad; a long heredoc
failed to parse and nothing was written; the agent reported `uv` as not installed when it was
only missing from its own PATH (Fran showed `uv 0.13.6`); and the backslash filter the agent
added to `scripts/sql-ro.sh` at Fran's request blocked one of its own queries.

Build (from `execution.md`):

- **T-01:** the agent bundled `uv lock` into a larger shell command; the permission rules denied
  it, correctly. Fran's first in-session `uv lock` failed because `settings.json` sets
  `UV_FROZEN=1` for the session (an advisor mistake, per `00-advisor-chat.md`); Fran ran
  `uv lock --system-certs` in another terminal. The agent had not anticipated the TLS certificate
  failure on package downloads (`UnknownIssuer`); it worked around it with
  `uv sync --frozen --system-certs`. The README now has a one-line troubleshooting note.
- **T-04:** the agent's own test expected the 12-week series to start on 2026-04-27; the correct
  start is 2026-05-04. It fixed the test, not the query, and logged it. The first heredoc for the
  query file also failed to parse and was rewritten with the file tool.
- **T-06:** a lax date parser would have silently accepted timestamps as the `week` parameter; the
  agent added a strict `YYYY-MM-DD` pattern to the API. Fran reviewed this and the other
  build-time choices at T-09. **But** the final reviewer found the page route never applied that
  pattern: `/?week=20260720` and `/?week=2026-W30-1` were silently accepted while the API returned
  422. Opened as T-10.
- **T-07:** the first "flagged row first" test used the burst week, in which every account-6
  location is flagged, so there was nothing to order. A second candidate week would have passed
  even without any sorting, because the flagged location was alphabetically first. The final test
  uses account 6, week 2026-05-18, where Site G (flagged) would sort after Site A by name, and it
  also asserts the page's row order equals the JSON's.
- **T-08:** the agent's own count of unresolved markers in the README was off by one
  (logged 3, actually 2), caught by the final reviewer.

## 6. Where Fran redirected or tightened the work

- **T-04's test location.** `.claude/rules/tests.md` says integration tests go through the FastAPI
  app. The endpoint doesn't exist until T-06, so Fran confirmed in `TASKS.md` that T-04's tests
  call `queries.py` directly against the real DB. Recorded as a "Confirmed deviation".
- **T-07's risk tag.** *(Advisor recommendation, `00-advisor-chat.md` "Build".)* Fran raised it to
  `high`: "Reload survival is an explicit challenge requirement, so the validator should check it
  over HTTP." The validator then ran curl against the rebuilt server and compared the page with
  the JSON.
- **The hand-verified number.** Fran re-ran the §9 SQL by hand (42), plus the agent's two
  counterfactual queries from PLAN §9: without `DISTINCT` the count is 43, and with `DISTINCT` but
  UTC week bounds it is also 43. The counterfactual figures were the agent's; Fran re-ran them.
- **A misleading headline, caught by hand (T-11).** After T-10, Fran tested the page by hand and
  found that for account 6, week 2026-07-13, the account total read "Below expected range" (50
  against 52–95) while the count line said "0 of 15 locations outside expected range", so a Monday
  reader would conclude all is well. Neither the agent, the validator (T-07) nor the final reviewer
  (T-09) had flagged it: every test checked that the count line matched the rows, none that it
  matched the account total. Fran specified the fix: the line now leads with a flagged account
  total ("Account total below expected range this week. 0 of 15 locations outside expected range
  (last 4 weeks)").
- **A misleading column layout, caught by hand (T-11 extension).** In the same hand test Fran found
  that the single-week count sat next to the 4-week range, so readers compared them: account 6,
  Site A showed "This week 9" beside "Range 12 to 38" and read as below range, though the range
  applies to the 4-week count (22) and 9 is above Site A's typical week (about 6). The agent had
  placed the columns that way in T-07, despite PLAN Q12's own warning that a range shown near an
  unjudged count invites the reader to judge it. Fran specified the fix: the judged 4-week columns
  first, "Expected" renamed "Typical", and "This week (not judged)" last and visually separated.
  Fran then added a "Typical week" (the location's 8-week median) beside the single-week count,
  partly reversing Q12 / Cut 2, which the agent had argued for: the typical value gives context
  without a verdict. Recorded in `PLAN.md`, "Changes after approval".
- **Early claims verified by hand.** After the first survey Fran checked two of the agent's claims
  (12 duplicate groups; "Site A" used by 19 accounts) and reported both held.

## 7. Where the harness limited the AI

The agent never committed, never ran `docker compose up/down` or `uv lock`, and stopped with an
`AWAITING` entry each time (T-01, T-03, T-07, T-08, T-09). The `validator` ran with fresh context
on all high-risk tasks and returned PASS on T-03–T-07. Two of its own caveats on T-03 are worth
keeping: it relied on pasted logs rather than running `docker compose logs`, and it read ruff's
and mypy's success messages rather than their exit codes. Mistakes in the advisor's own harness
work (the `sql-ro.sh` meta-command bypass, the session-wide `UV_FROZEN=1`, an outdated `/agents`
instruction, the leaky first survey prompt, the placeholder template) are listed in
`00-advisor-chat.md`.

## 8. Clean-machine run and final review

- **T-08 clean-machine run (Fran, 18:22–18:23).** Fresh clone of the GitHub remote into a temporary
  folder; `docker compose -p dash247-clean up -d --build`; `HTTP/1.1 200 OK` about 26 s after
  starting; `docker compose -p dash247-clean run --rm app uv run --frozen pytest -q` gave
  `56 passed`; the §9 SQL gave `42`; `down -v` cleaned up. Two caveats:
  - every Docker layer was cached, so image pulls and `uv sync` inside the container were not
    exercised; a cold build is still untimed;
  - the clone predates T-08, so it ran the T-07 tree with the skeleton README (same run and test
    commands).
- **T-09 final review** (reviewer subagent, FINAL mode): `READY_WITH_FIXES`, with 3 blockers (T-08
  not pushed, unresolved markers, the README and this file disagreeing on the harness origin),
  4 should-fix items and 2 nits. Report and Fran's decision on each are in `execution.md`.
