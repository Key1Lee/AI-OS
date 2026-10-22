-- Run from the project root: sqlite3 -header -column data/peopleops.db < sql/practice.sql
-- SELECT chooses fields. WHERE chooses rows. COUNT(*) counts those rows.
SELECT employee_id, full_name, department, status FROM employees
WHERE employee_id IN ('EMP-001','EMP-002','EMP-015');

-- GROUP BY forms one group per department. HAVING filters the grouped results.
SELECT department, COUNT(*) AS headcount FROM employees
WHERE status IN ('active','leave')
GROUP BY department HAVING COUNT(*) >= 3 ORDER BY department;

-- JOIN connects requests to employees through their keys.
SELECT r.request_id, e.full_name, r.team, r.status
FROM hr_requests r JOIN employees e ON r.employee_id=e.employee_id
WHERE r.status!='resolved' ORDER BY r.request_id;

-- A CTE gives a temporary result a readable name. COALESCE substitutes for NULL.
WITH completion AS (
    SELECT employee_id, COUNT(*) AS assigned,
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed
    FROM onboarding_tasks GROUP BY employee_id
)
SELECT e.employee_id, e.full_name, COALESCE(c.assigned,0) AS assigned,
       COALESCE(c.completed,0) AS completed
FROM employees e LEFT JOIN completion c ON e.employee_id=c.employee_id
WHERE e.employee_id IN ('EMP-001','EMP-011','EMP-020');

-- ROW_NUMBER assigns an ordered position within each employee's requests.
WITH ranked AS (
    SELECT request_id, employee_id, status,
           ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY created_at DESC,request_id) AS position
    FROM hr_requests
)
SELECT request_id,employee_id,status FROM ranked WHERE position=1 ORDER BY employee_id;

-- UPSERT is demonstrated safely in a temporary table; it does not change employees.
CREATE TEMP TABLE practice_status(employee_id TEXT PRIMARY KEY,status TEXT NOT NULL);
INSERT INTO practice_status VALUES('EMP-001','open');
INSERT INTO practice_status VALUES('EMP-001','resolved')
ON CONFLICT(employee_id) DO UPDATE SET status=excluded.status;
SELECT * FROM practice_status;
