-- s05 · Location names repeat across accounts: a location is identified by (account_id, location).
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s05-location-collisions.sql)"
SELECT location, count(DISTINCT account_id) AS accounts_using_name, count(*) AS events
FROM activity_events GROUP BY 1 ORDER BY 2 DESC LIMIT 3;
