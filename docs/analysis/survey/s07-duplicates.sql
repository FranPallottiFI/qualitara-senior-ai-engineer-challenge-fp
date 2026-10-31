-- s07 · Exact duplicates (identical on every column except id); consecutive ids suggest double inserts.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s07-duplicates.sql)"
SELECT count(*) AS dup_groups, sum(n) AS rows_in_groups, sum(n - 1) AS extra_rows
FROM (SELECT count(*) n FROM activity_events
      GROUP BY account_id, location, event_type, occurred_at, duration_seconds, outcome HAVING count(*) > 1) g;
SELECT e.* FROM activity_events e
JOIN (SELECT account_id, location, event_type, occurred_at FROM activity_events GROUP BY 1,2,3,4 HAVING count(*) > 1 LIMIT 4) d
  USING (account_id, location, event_type, occurred_at)
ORDER BY occurred_at, id;
SELECT account_id, sum(n - 1) AS extra_rows
FROM (SELECT account_id, count(*) n FROM activity_events
      GROUP BY account_id, location, event_type, occurred_at, duration_seconds, outcome HAVING count(*) > 1) g
GROUP BY 1 ORDER BY 2 DESC;
