# Engineering Principles

Normative for this project and for any agent working on it. Every architectural decision is
checked against these before it enters the plan.


## 1. Minimal and correct

- A feature enters scope only if a requirement (or a data reality) demands it.
- "Minimal" means the minimum that is **correct** against the real data, not the minimum that
  runs. A simple version that's wrong on the seed is broken, not simple.
- Leave clean seams; don't build empty floors.

## 2. Dependencies are liabilities

- Each dependency is justified against a concrete requirement. If the standard library, SQL or
  the framework already does it in reasonable lines, no library.
- Boring, transparent tools. The next engineer reads the repo without learning a framework first.
- The dependency list is part of the design and is reviewed like code.

## 3. Security and supply chain by default

- Fewest dependencies is the first control. Then:
  - **uv** as the only package manager; `uv.lock` committed (with hashes); installs are
    `uv sync --frozen` everywhere except deliberate dependency changes, which a human runs.
  - Python version pinned (`.python-version`, `requires-python`); uv version pinned
    (`[tool.uv] required-version`).
  - Cooling-off window against freshly hijacked releases: `[tool.uv] exclude-newer`
    (verify the supported format for your uv version at setup — don't configure a no-op).
- Trust boundaries are explicit: HTTP params, DB rows and model output are validated where they
  enter. SQL is always parameterized.
- No secrets in the repo. `.env.example` documents the shape.

## 4. Patterns earn their place

- A pattern enters only when the problem it solves is present. No repository layers, DI
  containers, service layers or single-implementation interfaces "for the future".
- Patterns that usually earn it:
  - **Functional core, imperative shell** — business logic as pure functions over plain data;
    I/O at the edges. Earned whenever logic needs isolated tests.
  - **Single source of truth** — every piece of state/computation has one owner.
  - **Swappable provider** — a minimal `Protocol` in front of a nondeterministic external service
    (e.g. an LLM), only when a second implementation (stub vs real) actually exists.
  - **Fail-safe fallback** — nondeterministic output is additive, validated, and backed by a
    deterministic path. The core product never depends on it.
  - **Guard clauses over nesting.**
- Name patterns when used; record when one is deliberately absent.

## 5. Deterministic first

- Specifiable as exact rules over structured input → code. Enumerable cases → static content or
  a template.
- An LLM enters only where input/output is open natural language or the criterion can't be
  written as rules — and then only if its output is verifiable or low-stakes, a deterministic
  fallback exists, and the value over the best template pays for the cost and latency.

## 6. Honest data and failure handling

- Handle the edges explicitly (nulls, duplicates, outliers, empty sets, timezones) and show them
  in the UI/API instead of hiding them.
- Handle errors where something meaningful can be done; surface them otherwise. No bare
  `except:`, no silent fallbacks.

## 7. Verification over volume

- Few tests, aimed at what could actually be wrong. No coverage farming.
- At least one number verified **by hand** against the source data, not by the code under test.
- If something can't be verified, say "unverified".

## 8. Agents are directed, not trusted

- Agent output is a proposal until verified by evidence.
- The one who implements doesn't grade it: risky work is judged by an independent validator.
- Rules that matter are enforced by tooling (permissions, hooks), not only written in prose.
- The AI log records what happened, including failures and my own mistakes.
