-- s03 · Account 6 (15 locations) has ~800 extra events on 2026-06-03 UTC. The shape (outcome mix,
-- business hours, all locations, no repeated timestamps) looks like real activity.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s03-spike.sql)"
SELECT occurred_at::date AS d_utc, count(*) FROM activity_events
WHERE occurred_at >= '2026-05-30' AND occurred_at < '2026-06-10' GROUP BY 1 ORDER BY 1;
SELECT account_id,
       count(*) FILTER (WHERE occurred_at >= '2026-06-01' AND occurred_at < '2026-06-08') AS spike_wk,
       round(count(*) FILTER (WHERE occurred_at >= '2026-02-02' AND occurred_at < '2026-06-01')/17.0, 1) AS avg_wk_before
FROM activity_events GROUP BY 1 ORDER BY 2 DESC LIMIT 5;
SELECT account_id, location, event_type, count(*) FROM activity_events
WHERE occurred_at >= '2026-06-01' AND occurred_at < '2026-06-08' GROUP BY 1,2,3 HAVING count(*) > 30 ORDER BY 4 DESC;
SELECT event_type, coalesce(outcome, '<NULL>') AS o, count(*), count(DISTINCT occurred_at) AS distinct_ts,
       min(occurred_at), max(occurred_at), round(avg(duration_seconds)) AS avg_dur
FROM activity_events WHERE account_id = 6 AND occurred_at::date = '2026-06-03' GROUP BY 1,2 ORDER BY 3 DESC;
SELECT extract(hour FROM occurred_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York') AS local_hr, count(*)
FROM activity_events WHERE account_id = 6 AND occurred_at::date = '2026-06-03' GROUP BY 1 ORDER BY 1;
SELECT min(id), max(id), max(id) - min(id) + 1 AS id_span, count(*)
FROM activity_events WHERE account_id = 6 AND occurred_at::date = '2026-06-03';
