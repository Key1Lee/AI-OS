-- E03: implement one query at a time. Each named block is independently tested.
-- Parameters: :as_of = 2026-10-01, :period_start = 2026-09-01.
-- name: headcount
-- Return department, headcount; one row per department, department order.
SELECT NULL::text AS department, 0::bigint AS headcount WHERE false;

-- name: turnover
-- Return departures, opening_headcount, closing_headcount, turnover_rate.
SELECT 0::bigint AS departures, 0::bigint AS opening_headcount,
       0::bigint AS closing_headcount, NULL::numeric AS turnover_rate WHERE false;

-- name: funnel
-- Return stage, candidates; count unique candidates reaching each stage.
SELECT NULL::text AS stage, 0::bigint AS candidates WHERE false;

-- name: onboarding
-- Return department, assigned, completed, completion_rate; include empty groups.
SELECT NULL::text AS department, 0::bigint AS assigned,
       0::bigint AS completed, NULL::numeric AS completion_rate WHERE false;
