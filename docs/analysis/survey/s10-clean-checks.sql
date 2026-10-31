-- s10 · Checked and found clean: timezones valid, event types, location strings, per-account coverage.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s10-clean-checks.sql)"
SELECT a.id, a.name, a.timezone, a.created_at, (a.timezone IN (SELECT name FROM pg_timezone_names)) AS tz_valid
FROM accounts a ORDER BY id;
SELECT event_type, '[' || event_type || ']' AS raw, count(*) FROM activity_events GROUP BY 1 ORDER BY 1;
SELECT count(*) FILTER (WHERE location <> btrim(location)) AS ws,
       count(*) FILTER (WHERE location ~ '[[:space:]]{2,}') AS dbl_space,
       count(*) FILTER (WHERE location = '') AS empty,
       (SELECT count(*) FROM (SELECT account_id, lower(btrim(location)) FROM activity_events GROUP BY 1, 2
                              HAVING count(DISTINCT location) > 1) x) AS case_or_ws_variants
FROM activity_events;
SELECT account_id, count(*) AS events, count(DISTINCT location) AS locations,
       min(occurred_at)::date AS first, max(occurred_at)::date AS last
FROM activity_events GROUP BY 1 ORDER BY 1;
