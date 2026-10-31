-- 06c · Location rule (see 06a): which windows are false alarms, and in which direction.
-- Same windows as 06b (account 6 excluded). Shows whether flags are LOW or HIGH and whether one
-- noisy stretch produces flags on several consecutive Mondays (overlapping windows).
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/06c-location-4week-false-alarms.sql)"
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
pb AS (       -- Poisson 0.5% / 99.5% quantiles for baselines 0, 0.5, 1, ... 150
  SELECT lam, min(k) FILTER (WHERE cdf >= 0.005) AS plo, min(k) FILTER (WHERE cdf >= 0.995) AS phi
  FROM (
    SELECT lam, k, sum(exp(greatest(-lamf + k*ln(lamf) - lnfact, -700))) OVER (PARTITION BY lam ORDER BY k) AS cdf
    FROM (
      SELECT l/2.0 AS lam, greatest(l/2.0, 0.01)::float8 AS lamf, k,
             sum(ln(greatest(k,1)::float8)) OVER (PARTITION BY l ORDER BY k) AS lnfact
      FROM generate_series(0,300) l CROSS JOIN generate_series(0,500) k
      WHERE k <= l/2.0*3 + 40) x) y
  GROUP BY lam),
m0 AS MATERIALIZED (  -- per location and window end week: 4-week sum, its halved version, and the
                      -- weekly baseline from the 8 weeks BEFORE the window (no overlap)
  SELECT s.account_id, s.location, s.w AS window_end, win.n4, win.nh4, b.med8
  FROM s
  CROSS JOIN LATERAL (SELECT sum(n)::int AS n4, sum(ceil(n/2.0))::int AS nh4 FROM s s2
                      WHERE s2.account_id = s.account_id AND s2.location = s.location
                        AND s2.w BETWEEN s.w - 21 AND s.w) win
  CROSS JOIN LATERAL (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY n) AS med8 FROM s s2
                      WHERE s2.account_id = s.account_id AND s2.location = s.location
                        AND s2.w BETWEEN s.w - 77 AND s.w - 28) b
  WHERE s.w BETWEEN '2026-04-27' AND '2026-07-20'),
m AS (SELECT m0.*, 4*m0.med8 AS lam4, pb.plo, pb.phi FROM m0 JOIN pb ON pb.lam = (4*m0.med8)::numeric)
SELECT account_id, location, med8 AS weekly_baseline, plo || '..' || phi AS normal_range,
       string_agg(to_char(window_end, 'MM-DD') || '=' || n4 || CASE WHEN n4 < plo THEN 'L' ELSE 'H' END, ' ' ORDER BY window_end) AS flagged_windows,
       count(*) AS flags
FROM m
WHERE account_id <> 6 AND (n4 < plo OR n4 > phi)
GROUP BY account_id, location, med8, plo, phi
ORDER BY account_id, location
