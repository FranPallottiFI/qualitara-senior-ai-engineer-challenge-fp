-- 02 · Methods A / B / C week by week on three series: account 6 total (around the 2026-06-01
-- spike), account 6 Site G (low volume, zero weeks 04-13 and 06-29), account 16 (single location).
--   A = median of prior 8 weeks ± 3 × 1.4826 × MAD (Hampel)    B = P10..P90 of prior 12 weeks
--   C = Poisson 0.5%..99.5% range around the median of prior 8 weeks
--   verdict: LOW / HIGH / '.' (normal) / n/a (not enough history)
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/02-method-series.sql)"
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
m0 AS MATERIALIZED (  -- baselines from prior weeks only; materialized so they are computed once per row
  SELECT t.account_id, t.location, t.w, t.n, ceil(t.n/2.0)::int AS nh, a.med8, b.mad8, c.p10, c.p90
  FROM t
  CROSS JOIN LATERAL (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY n) AS med8 FROM t t2
                      WHERE t2.account_id = t.account_id AND t2.location = t.location AND t2.w BETWEEN t.w - 56 AND t.w - 7) a
  CROSS JOIN LATERAL (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY abs(t2.n - a.med8)) AS mad8 FROM t t2
                      WHERE t2.account_id = t.account_id AND t2.location = t.location AND t2.w BETWEEN t.w - 56 AND t.w - 7) b
  CROSS JOIN LATERAL (SELECT percentile_cont(0.1) WITHIN GROUP (ORDER BY n) AS p10, percentile_cont(0.9) WITHIN GROUP (ORDER BY n) AS p90 FROM t t2
                      WHERE t2.account_id = t.account_id AND t2.location = t.location AND t2.w BETWEEN t.w - 84 AND t.w - 7) c
  ),
m AS (SELECT m0.*, pb.plo, pb.phi FROM m0 JOIN pb ON pb.lam = m0.med8::numeric)
SELECT account_id, location, w, n, med8, mad8,
       round((med8 - 3*1.4826*mad8)::numeric, 1) || '..' || round((med8 + 3*1.4826*mad8)::numeric, 1) AS a_band,
       CASE WHEN n < med8 - 3*1.4826*mad8 THEN 'LOW' WHEN n > med8 + 3*1.4826*mad8 THEN 'HIGH' ELSE '.' END AS a,
       round(p10::numeric, 1) || '..' || round(p90::numeric, 1) AS b_band,
       CASE WHEN w < '2026-04-27' THEN 'n/a' WHEN n < p10 THEN 'LOW' WHEN n > p90 THEN 'HIGH' ELSE '.' END AS b,
       plo || '..' || phi AS c_band,
       CASE WHEN n < plo THEN 'LOW' WHEN n > phi THEN 'HIGH' ELSE '.' END AS c
FROM m
WHERE (account_id = 6  AND location = '(all)'  AND w BETWEEN '2026-05-11' AND '2026-07-20')
   OR (account_id = 6  AND location = 'Site G' AND w BETWEEN '2026-04-06' AND '2026-07-20')
   OR (account_id = 16 AND location = 'Site A' AND w BETWEEN '2026-05-04' AND '2026-07-20')
ORDER BY account_id, location, w
