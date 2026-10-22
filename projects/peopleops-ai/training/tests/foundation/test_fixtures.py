from lab.fixtures import generate, load
from lab.contracts import EmployeeRecord


def test_reproducible_fixture_file():
    assert generate() == load() == generate()
    assert generate(43)["employees"] != generate(42)["employees"]


def test_minimum_counts_and_foreign_keys(fixture_data):
    for key, minimum in {"employees": 100, "jobs": 20, "recruiting_events": 200, "policies": 15, "tickets": 50}.items():
        assert len(fixture_data[key]) >= minimum
    employees = {e["employee_id"] for e in fixture_data["employees"]}
    jobs = {j["job_id"] for j in fixture_data["jobs"]}
    candidates = {c["candidate_id"] for c in fixture_data["candidates"]}
    assert all(e["manager_id"] is None or e["manager_id"] in employees for e in fixture_data["employees"])
    assert all(c["job_id"] in jobs for c in fixture_data["candidates"])
    assert all(e["candidate_id"] in candidates for e in fixture_data["recruiting_events"])
    assert all(t["employee_id"] in employees for t in fixture_data["tickets"])
    for record in fixture_data["employees"]:
        EmployeeRecord.model_validate(record)
    assert len(fixture_data["raw_recruiting_events"]) == 242
