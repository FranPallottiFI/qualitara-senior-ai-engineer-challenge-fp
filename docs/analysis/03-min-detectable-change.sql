-- 03 · Minimum detectable change for method C (Poisson 99% two-sided range around the baseline)
-- For a baseline (expected weekly count) lam, C flags LOW if n < plo and HIGH if n > phi, where
-- plo / phi are the 0.5% / 99.5% Poisson quantiles. The smallest flagged drop is plo-1 events,
-- the smallest flagged rise is phi+1. plo = 0 means a LOW verdict is impossible at that volume.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/03-min-detectable-change.sql)"
WITH pb AS (
  SELECT lam, min(k) FILTER (WHERE cdf >= 0.005) AS plo, min(k) FILTER (WHERE cdf >= 0.995) AS phi
  FROM (
    SELECT lam, k, sum(exp(greatest(-lamf + k*ln(lamf) - lnfact, -700))) OVER (PARTITION BY lam ORDER BY k) AS cdf
    FROM (
      SELECT l/2.0 AS lam, greatest(l/2.0, 0.01)::float8 AS lamf, k,
             sum(ln(greatest(k,1)::float8)) OVER (PARTITION BY l ORDER BY k) AS lnfact
      FROM generate_series(0,300) l CROSS JOIN generate_series(0,500) k
      WHERE k <= l/2.0*3 + 40) x) y
  GROUP BY lam)
SELECT lam::float8 AS baseline,
       plo || '..' || phi AS normal_range,
       CASE WHEN plo = 0 THEN 'impossible' ELSE (plo-1)::text END AS low_if_at_most,
       CASE WHEN plo = 0 THEN '-' ELSE round(100.0*(plo-1-lam)/lam)::text || '%' END AS min_drop,
       phi+1 AS high_if_at_least,
       '+' || round(100.0*(phi+1-lam)/lam) || '%' AS min_rise
FROM pb
WHERE lam IN (2, 4, 5, 6, 8, 10, 15, 20, 30, 50, 70)
ORDER BY lam
