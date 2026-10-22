# Data quality and participation methodology

Deduplicate by ResponseID across the complete export before applying filters.
Keep the latest RecordedDate; if timestamps tie, the later source record wins.
Require Finished = 1 and all three scores to be integers from 1 to 5.
Exclude missing, incomplete, invalid, unknown-department, and out-of-period records.
The timestamp must match SurveyYear. 2024 and 2025 cover full calendar years; 2026 is YTD through October 21, 2026, inclusive, in UTC.
Response rate = valid deduplicated respondents / eligible employee headcount × 100.
The fictional eligible population totals 5,000 each year: Human Resources 250; Marketing 500; Engineering & Product 2,000; Sales 1,250; Customer Success & Support 1,000. This is an illustrative allocation, not actual Samsara staffing. Participation rates and score distributions vary by department and year; incomplete, missing, invalid and duplicate submissions are deliberately included. Pooled eligibility counts employee-year opportunities; it does not imply distinct people across years.
The independent Python reference checks the same source checksum, counts, scores, department results, rates, year-over-year changes and pooled results.
2026 YTD is not a complete calendar-year comparison; no significance or causal inference is implied.
