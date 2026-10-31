# 00 · Advisor chat: what it was used for and who decided what

A separate Claude chat (claude.ai, Opus 5.5 / Sonnet 5.5) was my planning advisor before and during
the challenge. It never touched the repo. It's not in `raw-prompts.md`, which only records prompts
typed into Claude Code. This file is a summary written from that chat and reviewed by me. The full
transcript is available on request.

## Before the clock (morning, 2026-10-31)

- **Before the clock.** I prepared my agent harness in advance. Its structure (rules file, task loop, separate validator and reviewer, permission deny-lists) was adapted from the one that I normally use in cursor, but with some improvements that I studied beforehand, with a separate Claude chat as advisor (see ai-log/00-advisor-chat.md). I changed it deliberately: [two agents instead of three, validation scaled by risk, a read-only DB role, prompts logged by a hook]. Everything specific to this ticket (the interpretation, the analysis, PLAN.md and the code) was done after the clock started.
- **Building my harness.** The advisor drafted a Python harness kit adapted my own:
  `CLAUDE.md`, `docs/engineering-principles.md`, `docs/conventions.md`, the `validator` and
  `reviewer` subagents, the `task-loop` skill, `.claude/rules/tests.md` and `.claude/settings.json`.
  Deliberate differences from the previous version: two agents instead of three (the main
  session implements), validation scaled by risk, tests in the same task as the code they protect,
  a read-only DB role plus `scripts/sql-ro.sh` instead of a broad allow rule, and a hook that logs
  every prompt to `raw-prompts.md`.


## During the challenge

**Most structured prompts from the survey onward were drafted by the advisor using my on wording as the prompt** I sent them after
editing them and filling in my decisions. Short operational prompts and most build-phase replies
were mine. So when `raw-prompts.md` shows well-structured direction, the wording is often the
advisor's and the decisions in it are mine.

| Moment (local time) | Advisor's contribution | My decision |
|---|---|---|
| 14:47 survey prompt | Drafted a survey prompt that listed specific data traps | **I flagged it as steering the agent with knowledge from the prior submission**; we rewrote it neutral |
| 15:01–15:13 survey questions | Laid out three options each for the spike, "this week" and account 18, with a recommendation | Chose all three, with my own reasons (spike can't be flagged statistically on this volume; snapshot data; don't lose data on weak evidence) |
| 15:33 baseline methods | **Pointed out the agent had measured only false alarms, not misses** | Sent the follow-up; accepted method C |
| 15:33 dispersion | Pointed out that variance ≈ mean may only hold because the seed is synthetic | Kept it as a known limitation with a next step, not code |
| 15:56 location rule | Recommended the 4-week location window and a DB `statement_timeout` | Accepted |
| 16:03 stack | Was about to have the agent propose a stack | **I insisted on proposing the stack myself** (Python, the role's stack) and asked the agent to argue against it |
| 16:23 LLM in the product | Applied deterministic-first; recommended template now, LLM designed and deferred | **The summary-panel idea was mine**; chose the deferral. Also asked whether it would need React; advisor: no |
| 16:43 plan draft | Suggested "within expected range" instead of "normal", data-derived week bounds and the Q9 wording | Accepted; also accepted the agent's argument to drop the stub stretch goal |
| 16:56 self-audit cuts | Recommended which of the agent's cuts to accept | Accepted |
| 17:09 plan review | Recommended cutting the event-type filter now, and removing `docs/CHALLENGE.md` from history | Cut the filter; **decided to keep `docs/CHALLENGE.md` committed**, against the advisor's recommendation |
| Build | Model per task (Opus for T-03–T-06, T-09), T-07 raised to high risk, hand-verification queries, clean-machine run commands | Ran every machine command, the hand verification and the clean run myself; committed every task |

## Mistakes in the advisor's own work (caught during the challenge)

- `scripts/sql-ro.sh` allowed psql meta-commands (`\!`), a bypass of the read-only role. Claude
  Code found it while reviewing the script.
- `settings.json` set `UV_FROZEN=1` for the whole session, which also blocked my own `uv lock` in
  T-01. Claude Code diagnosed it.
- It told me to use `/agents` to check the subagents; that command no longer lists them.
- Its first survey prompt leaked knowledge of the prior submission (above).
- A prompt template left a literal `<your real reason>` placeholder, which I sent