# 03 · Reflection: specific moments where the AI was wrong or I overrode it

**DRAFT written by the agent (Claude Code, Sonnet 5.5) from `raw-prompts.md`,
`02-planning-notes.md` and `execution.md`. Fran reviews it before submission.** Quotes of Fran are
verbatim from `raw-prompts.md`. Anything I could not source to a prompt, a log entry or a commit
is marked **[Fran to confirm]**. I have not attributed reasoning to Fran beyond what the
prompts say.

## Tools and models (one honest line)

Claude Code with Opus for planning, reviews and T-03–T-06; Sonnet for routine tasks (T-01, T-02,
T-07, this draft) and the validator; a separate Claude chat used as a planning advisor to weigh
options and review the harness, with every decision Fran's. The chat is not in `raw-prompts.md`,
which only records prompts submitted in Claude Code. [Fran to confirm: exact model versions, and
whether the advisor chat transcript should be added to `ai-log/`]

## Before the clock

The harness (`CLAUDE.md`, the `task-loop` skill, the `validator` and `reviewer` subagents, the
permission settings and `docs/engineering-principles.md` / `docs/conventions.md`) was adapted from
a colleague's prior submission of this challenge, which Fran studied beforehand, before the first
logged prompt (2026-10-31 14:23). [Fran to confirm: which parts were adapted, which were written
fresh, and whether the principles and conventions documents are part of that]

## 1. Fran caught the AI being wrong (planning)

1. **It measured only false alarms.** The agent's first comparison of baseline methods scored them
   on false-alarm rate and recommended method C. Fran: "you only measured false alarms, not
   misses. A method that never fires also scores 0%." The follow-up (`docs/analysis/03`, `04a`,
   `04b`, `05`) showed a single-week location verdict catches about 2% of halved weeks. That
   produced the 4-week location rule.
2. **It called the verdict "normal".** Fran: "'Normal' overclaims when only large drops would
   show." Renamed "within expected range" everywhere.
3. **It hardcoded week bounds into the contract.** Fran: "Week bounds must be derived from the
   data (first/last complete weeks), never hardcoded dates." This is now enforced by a grep in
   T-04's "Done when" and a test over all 20 accounts.
4. **Variance ≈ mean.** The analysis found weekly variance close to the mean (median ratio 0.97,
   `docs/analysis/01`) and the method rests on it. Fran: "the
   variance~mean result may be because the seed is synthetic. Real volume is usually more
   dispersed, and then C would over-fire." It became a known limitation with a next step, not
   code.
5. **Q9 wording.** Fran specified that `occurred_at` is treated as UTC per the schema and that the
   timezone-blind look of the times goes to product as a data-quality question.

## 2. The AI argued against Fran, or Fran changed course

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
  reviewer's evidence of zero and near-zero baselines on filtered series, Fran: "Cut the
  event-type filter now. Move it to 'next iteration' with the reviewer's reason".
- **`docs/CHALLENGE.md`.** Fran's messages conflict. At 16:36: "docs/CHALLENGE.md stays local and
  uncommitted." The reviewer found it already committed and pushed (`7e30e69`). The 17:11
  version of the next prompt says "I've untracked docs/CHALLENGE.md and removed it from history";
  the 17:12 version says "dont worry about the challenge.md. it stays commited". The file is
  tracked today, which matches the last message. [Fran to confirm that "stays committed" is the
  final decision]
- **A placeholder in Fran's prompt.** The prompt contained the literal text "I didn't email the
  recruiter because <your real reason>". The agent did not invent a reason; `PLAN.md` states only
  the facts. The README does the same. [Fran to confirm: the real reason, if it should be stated]

## 3. The reviewer subagent caught the AI's plan errors (before any code)

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

## 4. The AI caught or admitted its own mistakes

Planning (from `02-planning-notes.md`): example numbers in the JSON contract were invented and
labelled "illustrative" until the agent queried the real ones; the "mean = 171" figure was cited
to a file that doesn't contain a mean; the first `04b` query timed out and was rewritten with
materialized baselines; a temp file went to `/tmp` instead of the scratchpad; a long heredoc
failed to parse and nothing was written; the agent reported `uv` as not installed when it was
only missing from its own PATH (Fran showed `uv 0.13.6`); and the backslash filter the agent
added to `scripts/sql-ro.sh` at Fran's request blocked one of its own queries.

Build (from `execution.md`):

- **T-01:** the agent bundled `uv lock` into a larger shell command; the permission rules denied
  it, correctly. It then split the file writes from the human command. Fran's first in-session
  `uv lock` failed because the session sets `UV_FROZEN=1`; Fran ran `uv lock --system-certs` in
  another terminal instead. The agent had also not anticipated the TLS certificate failure on
  package downloads, which showed up as `UnknownIssuer` on the first `uv run`; it worked around it
  with `uv sync --frozen --system-certs`. [Fran to confirm whether the certificate problem should
  be mentioned in the README for reviewers]
- **T-04:** the agent's own test expected the 12-week series to start on 2026-04-27; the correct
  start is 2026-05-04. It fixed the test, not the query, and logged it. The first heredoc for the
  query file also failed to parse and was rewritten with the file tool.
- **T-06:** a lax date parser would have silently accepted timestamps as the `week` parameter; the
  agent added a strict `YYYY-MM-DD` pattern. This is an agent decision. [Fran to confirm]
- **T-07:** the first "flagged row first" test used the burst week, in which every account-6
  location is flagged, so there was nothing to order. A second candidate week would have passed
  even without any sorting, because the flagged location was alphabetically first. The final test
  uses account 6, week 2026-05-18, where Site G (flagged) would sort after Site A by name, and it
  also asserts the page's row order equals the JSON's.

## 5. Where Fran redirected or tightened the work

- **T-04's test location.** `.claude/rules/tests.md` says integration tests go through the FastAPI
  app. The endpoint doesn't exist until T-06, so Fran confirmed in `TASKS.md` that T-04's tests
  call `queries.py` directly against the real DB. Recorded as a "Confirmed deviation".
- **T-07's risk tag.** Fran raised it to `high`: "Reload survival is an explicit challenge
  requirement, so the validator should check it over HTTP." The validator then ran curl against
  the rebuilt server and compared the page with the JSON.
- **T-03's log check.** The agent tried to read `docker compose ps` and `docker compose logs` in
  one call; Fran rejected the call and pasted the logs by hand. [Fran to confirm why]
- **The hand-verified number.** Fran re-ran the §9 SQL by hand (42) and added two counterfactuals
  of their own: without `DISTINCT` the count is 43, and with `DISTINCT` but UTC week bounds it is
  also 43.
- **Early claims verified by hand.** After the first survey Fran checked two of the agent's claims
  (12 duplicate groups; "Site A" used by 19 accounts) and reported both held.

## 6. Where the harness limited the AI

The agent never committed, never ran `docker compose up/down` or `uv lock`, and stopped with an
`AWAITING` entry each time (T-01, T-03, T-07). The `validator` ran with fresh context on all
high-risk tasks and returned PASS on T-03–T-07. Two of its own caveats on T-03 are worth keeping:
it relied on pasted logs rather than running `docker compose logs`, and it read ruff's and
mypy's success messages rather than their exit codes.

## 7. Not yet done

- **[Fran to confirm]** every item marked above.
- The clean-machine run, the §9 hand-verification on the fresh clone and the timing are Fran's
  (T-08 steps 1–3, 6); nothing here claims they have happened.
