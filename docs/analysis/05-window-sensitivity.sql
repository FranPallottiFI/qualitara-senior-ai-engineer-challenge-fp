-- 05 · Sensitivity of method C to window length (6 / 8 / 12 prior weeks) and range (99% / 95%).
-- Same judged weeks and definitions as 04b (2026-04-27 .. 2026-07-20, account 6 excluded):
--   fa  = actual week flagged LOW or HIGH      det = halved week (ceil(n/2)) flagged LOW
-- Baseline = median of the prior N complete weeks; range = Poisson quantiles around it.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/05-window-sensitivity.sql)"
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
  SELECT account_id, '(all)', w, sum(n)::int FROM s GROUP BY account_id, w HAVING count(*) > 1),
pb AS (       -- Poisson quantiles for baselines 0, 0.5, ... 150: 99% (0.5/99.5) and 95% (2.5/97.5)
  SELECT lam,
         min(k) FILTER (WHERE cdf >= 0.005) AS lo99, min(k) FILTER (WHERE cdf >= 0.995) AS hi99,
         min(k) FILTER (WHERE cdf >= 0.025) AS lo95, min(k) FILTER (WHERE cdf >= 0.975) AS hi95
  FROM (
    SELECT lam, k, sum(exp(greatest(-lamf + k*ln(lamf) - lnfact, -700))) OVER (PARTITION BY lam ORDER BY k) AS cdf
    FROM (
      SELECT l/2.0 AS lam, greatest(l/2.0, 0.01)::float8 AS lamf, k,
             sum(ln(greatest(k,1)::float8)) OVER (PARTITION BY l ORDER BY k) AS lnfact
      FROM generate_series(0,300) l CROSS JOIN generate_series(0,500) k
      WHERE k <= l/2.0*3 + 40) x) y
  GROUP BY lam),
m0 AS MATERIALIZED (
  SELECT t.account_id, t.location, t.w, t.n, ceil(t.n/2.0)::int AS nh, nw.nweeks, b.med
  FROM t
  CROSS JOIN (VALUES (6), (8), (12)) nw(nweeks)
  CROSS JOIN LATERAL (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY n) AS med FROM t t2
                      WHERE t2.account_id = t.account_id AND t2.location = t.location
                        AND t2.w BETWEEN t.w - 7*nw.nweeks AND t.w - 7) b
  WHERE t.w BETWEEN '2026-04-27' AND '2026-07-20' AND t.account_id <> 6),
r AS (
  SELECT m0.*, rng.pct, rng.lo, rng.hi, (m0.location = '(all)') AS is_acct
  FROM m0 JOIN pb ON pb.lam = m0.med::numeric
  CROSS JOIN LATERAL (VALUES (99, pb.lo99, pb.hi99), (95, pb.lo95, pb.hi95)) rng(pct, lo, hi))
SELECT nweeks, pct || '%' AS range,
       round(100.0*avg((n  < lo OR n > hi)::int) FILTER (WHERE NOT is_acct)) AS loc_fa_pct,
       round(100.0*avg((nh < lo)::int)           FILTER (WHERE NOT is_acct)) AS loc_det_pct,
       round(100.0*avg((n  < lo OR n > hi)::int) FILTER (WHERE is_acct))     AS acct_fa_pct,
       round(100.0*avg((nh < lo)::int)           FILTER (WHERE is_acct))     AS acct_det_pct,
       round(sum(((n < lo OR n > hi) AND NOT is_acct)::int) / 13.0, 1)       AS loc_flags_per_monday
FROM r GROUP BY nweeks, pct ORDER BY pct DESC, nweeks
