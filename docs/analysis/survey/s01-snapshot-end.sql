-- s01 · The seed is a static snapshot: by the wall clock, "the last 7 days" is empty.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s01-snapshot-end.sql)"
SELECT now()::date AS today, max(occurred_at)::date AS data_end, now()::date - max(occurred_at)::date AS days_stale,
       (SELECT count(*) FROM activity_events WHERE occurred_at >= now() - interval '7 days') AS events_last_7d_by_clock
FROM activity_events;
SELECT to_char(min(occurred_at), 'Dy YYYY-MM-DD HH24:MI') AS first_utc, to_char(max(occurred_at), 'Dy YYYY-MM-DD HH24:MI') AS last_utc,
       count(*) AS events, count(DISTINCT id) AS distinct_ids
FROM activity_events;
