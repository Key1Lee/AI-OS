"""Unit evidence for the independently implemented Python rules."""
import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("reference", Path(__file__).resolve().parents[1] / "scripts/verify.py")
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


class ReferenceTest(unittest.TestCase):
    def test_reproducible_seed_and_cohorts(self):
        root = Path(__file__).resolve().parents[1]
        seed_spec = importlib.util.spec_from_file_location("seed", root / "scripts/seed_data.py")
        seed = importlib.util.module_from_spec(seed_spec)
        seed_spec.loader.exec_module(seed)
        with tempfile.TemporaryDirectory() as directory:
            seed.ROOT = Path(directory)
            (seed.ROOT / "fixtures").mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                seed.seed()
            for file in ["qualtrics_responses.json", "eligible_headcount.json"]:
                self.assertEqual((seed.ROOT / "fixtures" / file).read_bytes(), (root / "fixtures" / file).read_bytes())
            snapshot = {"responses": json.loads((root / "fixtures/qualtrics_responses.json").read_text()), "headcount": json.loads((root / "fixtures/eligible_headcount.json").read_text())}
            expected = {"Human Resources": 250, "Marketing": 500, "Engineering & Product": 2000, "Sales": 1250, "Customer Success & Support": 1000}
            self.assertEqual(len(snapshot["headcount"]), 15)
            for year in (2024, 2025, 2026):
                actual = {c["Department"]: c["EligibleEmployees"] for c in snapshot["headcount"] if c["SurveyYear"] == year}
                self.assertEqual(actual, expected)
                self.assertEqual(sum(actual.values()), 5000)
            for cohort in snapshot["headcount"]:
                metric = ref.reference(snapshot, [cohort["SurveyYear"]], [cohort["Department"]])
                rate = metric["overall"]["validRespondents"] / cohort["EligibleEmployees"]
                self.assertTrue(.65 <= rate <= .9)
                self.assertLessEqual(metric["overall"]["validRespondents"], cohort["EligibleEmployees"])
            self.assertTrue(all(r["RecordedDate"][:10] <= "2026-10-21" for r in snapshot["responses"] if r["SurveyYear"] == 2026))

    def row(self, **changes):
        return dict(ResponseID="R1", RecordedDate="2025-01-01T00:00:00Z", SurveyYear=2025,
                    Department="Engineering & Product", Finished=1, QID1=5, QID2=5, QID3=5, **changes)

    def test_latest_invalid_wins(self):
        early = self.row()
        late = {**early, "QID3": None, "RecordedDate": "2025-01-02T00:00:00Z"}
        result = ref.reference({"responses": [late, early], "headcount": [{"SurveyYear": 2025, "Department": "Engineering & Product", "EligibleEmployees": 60}]}, [2025], ["Engineering & Product"])
        self.assertEqual(result["overall"]["validRespondents"], 0)
        self.assertIsNone(result["overall"]["score"])

    def test_equal_respondents_and_invalid_rules(self):
        rows = [self.row()]
        for i in range(3):
            rows.append({**self.row(), "ResponseID": f"S{i}", "Department": "Sales", "QID1": 1, "QID2": 1, "QID3": 1})
        for i, values in enumerate([{"Finished": 0}, {"QID1": None}, {"QID2": 6}, {"QID3": 1.5}, {"QID1": True}, {"SurveyYear": 2026, "RecordedDate": "2026-10-22T00:00:00Z"}]):
            rows.append({**self.row(), "ResponseID": f"I{i}", **values})
        snapshot = {"responses": rows, "headcount": [{"SurveyYear": 2025, "Department": d, "EligibleEmployees": 60} for d in ["Engineering & Product", "Sales"]]}
        result = ref.reference(snapshot, [2025], ["Engineering & Product", "Sales"])
        self.assertEqual(result["overall"]["score"], 25)
        self.assertEqual(result["overall"]["validRespondents"], 4)
        self.assertEqual(result["overall"]["eligibleEmployees"], 120)
        self.assertEqual(result["overall"]["responseRate"], 4 / 120 * 100)


if __name__ == "__main__":
    unittest.main()
