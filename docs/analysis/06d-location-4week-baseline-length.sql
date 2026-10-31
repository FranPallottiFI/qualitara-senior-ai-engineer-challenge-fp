-- 06d · Location rule (see 06a) with an 8- vs 12-week baseline before the 4-week window.
-- Tests whether the excess false alarms in 06b (3.1% vs ~1% nominal) come from baseline sampling
-- error. Same windows for both (ending 2026-05-18 .. 2026-07-20, the first with 12 + 4 weeks of
-- history); account 6 excluded.  fa = actual sum outside range; det = all 4 weeks halved, flagged LOW.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/06d-location-4week-baseline-length.sql)"
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
m0 AS MATERIALIZED (
  SELECT s.account_id, s.location, s.w AS window_end, nb.nweeks, win.n4, win.nh4, b.med
  FROM s
  CROSS JOIN (VALUES (8), (12)) nb(nweeks)
  CROSS JOIN LATERAL (SELECT sum(n)::int AS n4, sum(ceil(n/2.0))::int AS nh4 FROM s s2
                      WHERE s2.account_id = s.account_id AND s2.location = s.location
                        AND s2.w BETWEEN s.w - 21 AND s.w) win
  CROSS JOIN LATERAL (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY n) AS med FROM s s2
                      WHERE s2.account_id = s.account_id AND s2.location = s.location
                        AND s2.w BETWEEN s.w - 28 - 7*nb.nweeks + 7 AND s.w - 28) b
  WHERE s.w BETWEEN '2026-05-18' AND '2026-07-20' AND s.account_id <> 6),
m AS (SELECT m0.*, pb.plo, pb.phi FROM m0 JOIN pb ON pb.lam = (4*m0.med)::numeric)
SELECT nweeks AS baseline_weeks, count(*) AS windows,
       round(100.0*avg((n4 < plo OR n4 > phi)::int), 1) AS fa_pct,
       round(100.0*avg((nh4 < plo)::int)) AS det_pct,
       round(100.0*avg((nh4 < plo)::int) FILTER (WHERE med > 5 AND med <= 10)) AS det_pct_baseline_5_10
FROM m GROUP BY nweeks ORDER BY nweeks
