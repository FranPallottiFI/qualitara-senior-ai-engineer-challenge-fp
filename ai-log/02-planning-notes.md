# 02 · Planning notes: corrections, overrides and agent mistakes

Written by the agent (Claude Code, Opus 5.5) during planning, 2026-10-31. Raw prompts are in
`raw-prompts.md`. This file records the moments where a decision changed, who changed it, and why.
Quotes of the engineer are verbatim from the prompts.

## Agent argued against an engineer decision, and the engineer reversed it

**Single-week location rows (PLAN Q12).**
- **Earlier decision (engineer):** "Single-week location counts are shown with baseline and
  range but no verdict."
- **Agent's argument (plan audit):**
  - at typical location volume the range is nearly uninformative: a baseline of ≈ 6 gives 1..13
    (`docs/analysis/03`);
  - a range shown without a verdict invites the admin to judge it themselves, which is the
    overclaim the "within expected range" wording was introduced to avoid;
  - the count alone is what the dashboard shows today.
- **Outcome:** engineer accepted: "Cut 2: accepted. Single-week location rows show the count only."

## Engineer corrected the agent

1. **Only false alarms were measured.** The agent's first comparison of baseline methods scored
   them on false-alarm rate only, and recommended C. Engineer: "you only measured false alarms,
   not misses. A method that never fires also scores 0%."
   - The follow-up analysis (`03`, `04a`, `04b`, `05`) showed single-week location verdicts catch
     about 2% of halved weeks.
   - That led to the 4-week location rule (`06a`–`06d`).
2. **"Normal" as a verdict label.** The agent used `normal`. Engineer: "'Normal' overclaims when
   only large drops would show." Renamed to "within expected range" throughout.
3. **Hardcoded week bounds.** The agent wrote the seed's first and latest complete weeks into
   the contract as dates. Engineer: "Week bounds must be derived from the data (first/last complete
   weeks), never hardcoded dates."
4. **Q9 wording.** Engineer specified that `occurred_at` is treated as UTC per the schema, and that
   the timezone-blind look of the times is logged as a data-quality question for product.
5. **Variance ≈ mean.** Engineer: "the variance~mean result may be because the seed is synthetic.
   Real volume is usually more dispersed, and then C would over-fire." Recorded as a known
   limitation with a next step, not built.

## Agent pushed back on an engineer proposal, and the engineer agreed

- **LLM stub as first stretch goal.** Engineer proposed building the LLM boundary with a stub
  provider if time remained.
  - **Agent's argument:** the challenge prompt asks for surplus time to go to verification, and
    warns against box-checking LLM calls; building a stub after arguing a template suffices
    contradicts the plan's own argument.
  - **Outcome:** engineer: "Agreed: drop the stub stretch goal."
- **Summary module.** The agent proposed cutting the templated summary once the LLM version was
  deferred, since half its justification was "LLM fallback". Engineer cut it partially: no
  module, but keep a one-line count ("N of M locations outside expected range") rendered from
  the rows.

## Agent additions nobody asked for, later proposed for cutting

The agent added these to the draft PLAN, then flagged and removed them in the audit:
- a generic `notes` response field;
- `db/conn.py` and `models.py` as separate one-purpose modules;
- a duplicate `baseline` field next to `expected`;
- a "what evaluators score" paragraph.

## PLAN-mode review (reviewer subagent) and decisions

- **Verdict:** `READY_WITH_FIXES`. 16 findings, the top two marked blocker. The reviewer checked
  every decision the plan attributes to the engineer against `raw-prompts.md` and found them all
  backed.
- **Agent errors it caught:**
  - uvicorn bound to `127.0.0.1` inside the container (the app would be unreachable from the host);
  - single-location accounts still getting the single-week verdict that Q12/§4 argue against;
  - "22–27 of 69 locations" with no source (it came from `05`'s 95% flags-per-Monday, not from
    method B);
  - the 12-week alternative compared against a different window set;
  - Q12 saying "two points" where the notes list three.
- **Engineer decisions:**
  - "Cut the event-type filter now. Move it to 'next iteration' with the reviewer's reason";
  - "Accept all other findings as you proposed. #3: single-location accounts are treated like
    location rows";
  - "dont worry about the challenge.md. it stays commited". This reverses the earlier decision
    that it stays local; the reviewer had found it already committed and pushed in `7e30e69`;
  - "#8: start the README skeleton early, not last."
- **#16 (why questions weren't emailed to the recruiter):** the engineer's message contained the
  literal placeholder "<your real reason>". The agent did not invent a reason. `PLAN.md` states
  only the facts: none were emailed, and the challenge prompt allows documenting questions with
  working assumptions instead.
- **Series-start clause:** the agent chose to drop it, since with the filter cut it never fires
  on the seed. A zero-baseline rule (`too_little_volume`, never `high`) covers locations that
  appear mid-history, and that case is listed as a known gap.

## Agent mistakes

- **Unverified example numbers.** The first draft's JSON contract example had invented numbers
  for account 6 Site A labeled "illustrative". The agent noticed before reporting, queried the
  real values and replaced them (week count 9; 4-week count 22 against an expected 24, range
  12..38).
- **Wrong citation.** The plan first cited the "mean = 171" figure to `docs/analysis/02`, which
  doesn't contain a mean. Corrected to say it's the mean of the eight weekly counts shown in
  `02`.
- **Slow query.** The first version of `04b` timed out (> 2 min): the planner re-ran the
  per-row windows once per lookup-table row. The agent stopped it and materialized the baselines;
  it now runs in ~2 s. The stopped client may have left the read-only query running on the
  server until it finished.
- **Wrong temp location.** The agent wrote a temp file to `/tmp` instead of the session
  scratchpad, then deleted it.
- **Shell script failed to parse.** A long heredoc script for the survey files failed to parse
  and nothing was written; the agent rewrote the files with the file tool and re-ran all of them.
- **uv "not installed".** The agent reported uv as not installed; it was only missing from the
  agent's Bash tool PATH. The engineer showed `uv 0.13.6`.
- **Agent's own filter blocked a query.** The backslash filter the agent added to
  `scripts/sql-ro.sh` (at the engineer's request) blocked one of the agent's own survey queries
  (`\s` in a regex). Rewritten with `[[:space:]]`.
