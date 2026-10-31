-- 01 · Dispersion check: are weekly counts per location Poisson-like (variance ≈ mean)?
-- Spike week (account 6, week of 2026-06-01) excluded. Ratio ≈ 1 → Poisson; > 1 → overdispersed.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/01-dispersion.sql)"
WITH ev AS (  -- dedup: identical on every column except id counts once
  SELECT DISTINCT e.account_id, e.location, e.event_type, e.occurred_at, e.duration_seconds, e.outcome, a.timezone
  FROM activity_events e JOIN accounts a ON a.id = e.account_id),
wk AS (       -- Monday-Sunday weeks in the account's local timezone
  SELECT account_id, location, date_trunc('week', occurred_at AT TIME ZONE 'UTC' AT TIME ZONE timezone)::date AS w, count(*) AS n
  FROM ev GROUP BY 1,2,3),
grid AS (     -- complete local weeks in the snapshot (data: 2026-02-01 .. 2026-07-27)
  SELECT l.account_id, l.location, g::date AS w
  FROM (SELECT DISTINCT account_id, location FROM wk) l
  CROSS JOIN generate_series('2026-02-02'::date, '2026-07-20'::date, '7 days') g),
s AS (        -- zero-filled: a week with no events counts as 0
  SELECT grid.account_id, grid.location, grid.w, coalesce(wk.n, 0) AS n
  FROM grid LEFT JOIN wk USING (account_id, location, w)),
t AS MATERIALIZED (  -- location series + account totals (multi-location accounts only)
  SELECT account_id, location, w, n FROM s
  UNION ALL
  SELECT account_id, '(all)', w, sum(n)::int FROM s GROUP BY account_id, w HAVING count(*) > 1)
, d AS (SELECT account_id, location, avg(n) AS m, var_samp(n) AS v
        FROM s WHERE NOT (account_id = 6 AND w = '2026-06-01') GROUP BY 1, 2)
SELECT count(*) AS locations, round(min(v/m), 2) AS min_ratio,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY v/m)::numeric, 2) AS median_ratio,
       round(max(v/m), 2) AS max_ratio, count(*) FILTER (WHERE v/m > 1.5) AS locs_over_1_5
FROM d
