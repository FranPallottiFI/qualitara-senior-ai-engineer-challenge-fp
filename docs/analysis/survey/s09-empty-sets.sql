-- s09 · Empty sets: an account with no events; location-weeks with no events (local weeks).
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s09-empty-sets.sql)"
SELECT a.id, a.name, count(e.id) AS events FROM accounts a LEFT JOIN activity_events e ON e.account_id = a.id
GROUP BY 1,2 HAVING count(e.id) = 0;
WITH w AS (SELECT e.account_id, e.location, date_trunc('week', e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)::date wk, count(*) n
           FROM activity_events e JOIN accounts a ON a.id = e.account_id GROUP BY 1,2,3),
     grid AS (SELECT l.account_id, l.location, g::date wk FROM (SELECT DISTINCT account_id, location FROM activity_events) l
              CROSS JOIN generate_series('2026-02-02'::date, '2026-07-20'::date, '7 days') g)
SELECT grid.account_id, grid.location, array_agg(grid.wk ORDER BY grid.wk) AS empty_weeks
FROM grid LEFT JOIN w USING (account_id, location, wk) WHERE w.n IS NULL GROUP BY 1,2 ORDER BY 1,2;
