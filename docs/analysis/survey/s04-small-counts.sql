-- s04 · Location-level weekly counts are tiny, so ±50% swings are routine noise; rates swing even more.
-- Run: ./scripts/sql-ro.sh "$(cat docs/analysis/survey/s04-small-counts.sql)"
WITH w AS (SELECT e.account_id, e.location, date_trunc('week', e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)::date wk, count(*) n
           FROM activity_events e JOIN accounts a ON a.id = e.account_id
           WHERE e.occurred_at >= '2026-02-09' AND e.occurred_at < '2026-07-20' GROUP BY 1,2,3),
     m AS (SELECT account_id, location, percentile_cont(0.5) WITHIN GROUP (ORDER BY n) med FROM w GROUP BY 1,2)
SELECT width_bucket(med, 0, 20, 4) AS bucket, min(med), max(med), count(*) AS locations FROM m GROUP BY 1 ORDER BY 1;
WITH w AS (SELECT e.account_id, e.location, date_trunc('week', e.occurred_at AT TIME ZONE 'UTC' AT TIME ZONE a.timezone)::date wk, count(*) n
           FROM activity_events e JOIN accounts a ON a.id = e.account_id GROUP BY 1,2,3)
SELECT account_id, location, string_agg(n::text, ' ' ORDER BY wk) AS weekly_counts_last10
FROM w WHERE wk BETWEEN '2026-05-18' AND '2026-07-20' GROUP BY 1,2
HAVING min(n) FILTER (WHERE wk >= '2026-07-06') < 0.5*percentile_cont(0.5) WITHIN GROUP (ORDER BY n)
    OR max(n) FILTER (WHERE wk >= '2026-07-06') > 2*percentile_cont(0.5) WITHIN GROUP (ORDER BY n)
ORDER BY 1,2;
WITH c AS (SELECT account_id, date_trunc('month', occurred_at)::date m, count(*) FILTER (WHERE outcome = 'missed') missed,
                  count(*) FILTER (WHERE outcome IS NOT NULL) known
           FROM activity_events WHERE event_type = 'call_received' GROUP BY 1,2)
SELECT account_id, string_agg(round(100.0*missed/nullif(known, 0))::text, ' ' ORDER BY m) AS pct_missed_by_month_feb_jul
FROM c GROUP BY 1 HAVING max(100.0*missed/nullif(known, 0)) - min(100.0*missed/nullif(known, 0)) > 20 ORDER BY 1;
