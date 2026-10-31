-- s06 · Local-time bucketing moves few events in this seed, and event times look timezone-blind:
-- every timezone peaks at the same UTC hour, hours 00-01 UTC are nearly empty, pile-up at 23:59.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s06-timezone.sql)"
SELECT count(*) AS n,
       count(*) FILTER (WHERE e.occurred_at::date <> (e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)::date) AS day_differs,
       count(*) FILTER (WHERE date_trunc('week', e.occurred_at) <> date_trunc('week', e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)) AS week_differs
FROM activity_events e JOIN accounts a ON a.id = e.account_id;
SELECT a.timezone, count(*) AS n,
       round(100.0*count(*) FILTER (WHERE e.occurred_at::date <> (e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)::date)/count(*), 1) AS pct_day_differs
FROM activity_events e JOIN accounts a ON a.id = e.account_id GROUP BY 1 ORDER BY 3 DESC;
SELECT a.timezone, count(*) n,
       round(100.0*count(*) FILTER (WHERE extract(hour FROM e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone) NOT BETWEEN 6 AND 21)/count(*), 1) AS pct_local_night,
       mode() WITHIN GROUP (ORDER BY extract(hour FROM e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)) AS local_mode_hr,
       mode() WITHIN GROUP (ORDER BY extract(hour FROM e.occurred_at)) AS utc_mode_hr
FROM activity_events e JOIN accounts a ON a.id = e.account_id GROUP BY 1 ORDER BY 3 DESC;
SELECT extract(hour FROM occurred_at)::int h, count(*) n, count(DISTINCT account_id) accts,
       count(*) FILTER (WHERE occurred_at::time >= '23:59:00') AS last_min
FROM activity_events WHERE extract(hour FROM occurred_at) IN (21, 22, 23, 0, 1) GROUP BY 1 ORDER BY 1;
