---
paths: ["tests/**/*.py"]
---

# Test rule

Tests exist to falsify the known risks listed in PLAN §Tests — <FILL: e.g. outlier robustness
of the baseline, duplicate collapse, timezone bucketing, zero-fill, empty entity> — plus one
hand-verified number. Nothing else. No coverage farming (principles §7).

## Patterns

- **Tests ship with the code they protect.** The task that writes a query writes the test that
  could catch it being wrong. Not a later "tests" task.
- **Domain tests are pure.** `tests/domain/` imports `app.domain` and feeds it plain lists — no
  DB, no I/O, no dates computed in the test. If a domain test needs a mock, the domain module
  has an impurity bug.
- **Integration tests hit the real seeded Postgres** through the FastAPI app
  (`fastapi.testclient.TestClient` / `httpx`). Never mock the DB — the seed's messiness *is* the
  test material.
- **Fail loudly if the DB isn't there.** A session fixture checks connectivity and raises with a
  clear message ("run docker compose up -d && make db"). Never `pytest.skip` on a missing DB.
- **Names state the belief they would falsify:**
  `test_single_day_burst_does_not_move_the_baseline`, not `test_median`.
- **The hand-verified number:** exactly one assertion pinned to a figure computed by hand in
  SQL. The SQL goes in a comment right above the assertion.
- Use `pytest.mark.parametrize` for edge-case tables instead of copy-pasted tests.

## Quality bar

```python
# ✅ Strong — pins the behavior the median decision exists for
assert baseline([12, 14, 11, 13, 800, 12, 14, 13]).median == pytest.approx(13)

# ❌ Weak — only proves it runs
assert baseline(weeks) is not None
```

If deleting an assertion wouldn't change which bugs the test catches, it's too weak.

## Running

uv only — never `pip`, `uvx`, `python -m pytest` outside uv.

- While implementing: `uv run pytest tests/<file>.py -q`
- Before handing to the validator: `uv run pytest -q`
