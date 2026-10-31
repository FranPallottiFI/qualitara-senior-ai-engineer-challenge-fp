-- s02 · Partial first/last weeks look like crashes; weekday volume is very uneven, so a partial
-- week cannot be scaled up linearly.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s02-partial-weeks-and-weekday.sql)"
SELECT date_trunc('week', occurred_at)::date AS wk_utc, count(*) FROM activity_events GROUP BY 1 ORDER BY 1;
SELECT to_char(e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone, 'ID Dy') AS local_dow, count(*),
       round(100.0*count(*)/sum(count(*)) OVER (), 1) AS pct
FROM activity_events e JOIN accounts a ON a.id = e.account_id
WHERE NOT (e.account_id = 6 AND e.occurred_at::date = '2026-06-03')
GROUP BY 1 ORDER BY 1;
