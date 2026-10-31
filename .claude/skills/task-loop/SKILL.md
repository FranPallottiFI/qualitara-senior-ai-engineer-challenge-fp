---
name: task-loop
description: Runs the next task from TASKS.md through implement → verify → (validator for risk:high) → retry ≤3 → done/escalate, updating state markers and appending every verdict to ai-log/execution.md. Use when the user says to run the loop, do the next task, resume, or names a task ID like T-05.
---

# Task loop

You are implementer and orchestrator. The `validator` subagent is the judge for risky work. The
human decides scope, runs machine-changing commands, and commits. If a situation isn't covered
below, stop and ask — don't invent a rule.

## Invariants

- **TASKS.md is the only state store.** Marker in the heading: `[ ]` pending · `[~]` in progress
  · `[x]` done · `[!]` needs human decision · `[-]` dropped.
- **One task at a time.** Never start one while another is `[~]`.
- **Never commit.** After done, suggest a message `T-nn: <decision implemented>` and stop.
- **Never edit** `PLAN.md`, `docs/`, `.claude/`, `seed/`, `ai-log/raw-prompts.md`.
- **`ai-log/execution.md` is append-only** and every verdict goes there: PASS and FAIL,
  unsanitized.
- **Validation effort scales with risk.** `risk:high` (aggregation SQL, domain math, API
  contract, migrations, anything a hand-verified number depends on) → validator subagent,
  always. `risk:low` (scaffold, config, docs, wiring) → you verify each "Done when" yourself with
  commands and log the evidence. When unsure, treat as high.

## Steps (one invocation = one task)

1. **Select.** Resume a `[~]` task if there is one. Else, the user's named task, or the first
   `[ ]` whose `deps:` are all `[x]`. A dep that's `[-]` doesn't count as satisfied: stop and
   report.
2. **Start.** Mark `[~]`. Append to `ai-log/execution.md`:
   `### T-nn · start · risk:<x>`.
3. **Implement.**
   - Read the task, the PLAN sections it cites, and `.claude/rules/tests.md` if tests are
     involved. Read only the code you need.
   - Smallest change that satisfies "Done when". Tests for the risk ship in this task.
   - Run targeted tests, `ruff check`, `ruff format --check`, `mypy` on what you touched.
   - Need a human-run command → **Human commands** below.
   - Found necessary work the task doesn't cover → finish the task as scoped, then report
     `DISCOVERED_WORK` with a drafted new task (scope, deps, Done when, risk). Append it to
     TASKS.md only after the human says yes.
   - The task can only be done by contradicting PLAN → stop with `BLOCKED_PLAN_CONFLICT`
     (what the task needs, what the plan says, the decision needed). Mark `[!]`.
4. **Scope check.** `git diff --stat`. Revert nothing yourself, but if you touched a file outside
   the task's scope, say so and justify it or undo it before validation.
5. **Verify.**
   - `risk:low` → run each "Done when" check, paste command + output to the log.
   - `risk:high` → dispatch **validator** with ONLY: the task text verbatim (incl. Done when),
     the list of changed files from `git diff --name-only`, and the cited PLAN sections. Never
     include your reasoning or a summary of why you think it works.
6. **Transition.**
   - **PASS** → log the verdict verbatim → mark `[x]` → report to the human: relay every
     `PENDING HUMAN:` line **verbatim** at the top, then the suggested commit message → stop.
   - **FAIL** → log it verbatim → set/increment `> attempts: n` under the heading → fix the root
     cause (not just the latest symptom) → back to step 4. At 3 failed attempts → mark `[!]`,
     write a short diagnosis: *task defect* (criteria wrong) / *plan defect* / *hard bug* → stop.
     Never lower a "Done when" to get past a failure.
   - **BLOCKED** → log; doesn't consume an attempt. Report and stop.

## Human commands

Machine-changing commands (`docker compose up/down`, `uv add/remove/lock/sync`, migrations
downgrade) are denied to you. Don't work around a denial. Instead:

1. Log `### T-nn · human-command · AWAITING` with the command.
2. Add `> awaiting: <command>` under the task heading; attempts unchanged.
3. Tell the human: the command in a copy-paste block, why, and what output to paste back. Stop.

Next invocation: treat the pasted output as fact, remove `> awaiting:`, continue at the same
attempt.

## Log entry format (`ai-log/execution.md`)

```
### T-nn · attempt <n> · <self-check|validator|human-command|discovered-work> · <PASS|FAIL|BLOCKED|AWAITING>
<verbatim verdict / evidence / command + output>
```

Create the file with `# Execution log (task-loop)` if missing.

## Line order under a task heading

```
### [~] T-04 · risk:high · Weekly aggregation query
deps: [T-02, T-03]
> attempts: 1
> awaiting: docker compose up -d
```
