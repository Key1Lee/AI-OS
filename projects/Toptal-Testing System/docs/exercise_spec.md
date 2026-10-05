# Exercise contract

Versioned JSON files in `exercise_bank/sql` validate against Pydantic schemas.
Required: stable ID, version, title, type, domain, competency IDs, difficulty,
duration, prompt, context, tables, visible case, hidden cases, expected columns,
reference solution, explanation, three hints, prerequisites and tags.
Optional: fixed clarification rules, follow-up variants, rubric and timestamps.

Tables have typed named columns and rows. Cases have category IDs, fixtures and
explicit expected rows. Expected rows are authored independently of candidate
SQL. Visible Run returns candidate output, never expected output. Submit reports
category success and general diagnostic probes without revealing hidden rows.

Comparisons preserve duplicate multiplicity; unordered comparison is the default.
Exact order is opt-in. NULLs compare only to NULLs, numbers use documented
absolute/relative tolerances, and dates/timestamps normalize to ISO forms.
Column names/count and optional type-family contracts are checked. DATE output
cannot be substituted with formatted VARCHAR; aware timestamps compare by
their instant, and naive and aware values are distinct. Cases include empty input, dirty records and
boundary conditions relevant to the stated contract.
