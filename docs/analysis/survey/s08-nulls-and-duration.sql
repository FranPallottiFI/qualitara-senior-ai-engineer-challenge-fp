-- s08 · NULL outcomes (~3%, uniform over time) and call durations that carry no meaning
-- (missed calls have a 12-minute median duration).
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s08-nulls-and-duration.sql)"
SELECT event_type, coalesce(outcome, '<NULL>') AS outcome, count(*) FROM activity_events GROUP BY 1,2 ORDER BY 1,2;
SELECT date_trunc('month', occurred_at)::date AS m, count(*) n, count(*) FILTER (WHERE outcome IS NULL) AS null_outcome,
       count(*) FILTER (WHERE event_type = 'call_received' AND duration_seconds IS NULL) AS call_null_dur
FROM activity_events GROUP BY 1 ORDER BY 1;
SELECT event_type, count(*) AS n, count(duration_seconds) AS non_null, count(*) FILTER (WHERE duration_seconds < 0) AS neg,
       count(*) FILTER (WHERE duration_seconds = 0) AS zero, min(duration_seconds),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_seconds) AS p50, max(duration_seconds)
FROM activity_events GROUP BY 1;
SELECT coalesce(outcome, '<NULL>') AS outcome, count(*), count(duration_seconds) AS non_null,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_seconds) AS p50, max(duration_seconds)
FROM activity_events WHERE event_type = 'call_received' GROUP BY 1;
