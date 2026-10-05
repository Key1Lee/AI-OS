"""Command-level regression for recall routing and durable learner response."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parent.parent


class RecallCliTests(unittest.TestCase):
    def test_recall_answer_assessment_and_end_survive_separate_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            def call(*arguments):
                result = subprocess.run([sys.executable, "-m", "lab", "--state-dir", directory, *arguments],
                                        cwd=PROJECT, text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout

            call("next")
            first = call("recall")
            self.assertIn("[grain-check]", first)
            self.assertEqual(call("recall"), first)
            call("answer", "A retained delivery row is distinct from an order; inspect the business identity and version.", "--kind", "recall")
            state = json.loads((Path(directory) / "state.json").read_text())
            self.assertEqual(state['submissions'][-1]['prompt'], 'grain-check')
            self.assertIsNone(state['pending_recall'])
            reviewed = call("review", "submission-0001", "--result", "demonstrated", "--note", "Explains row identity and version rather than counting deliveries.",
                            "--concept", "data-grain", "--tutor", "CLI test tutor")
            self.assertIn('assessed by CLI test tutor', reviewed)
            self.assertIn('data-grain: UNDERSTOOD', call('progress'))
            summary = call('end')
            self.assertIn('WHAT YOU SOLVED', summary)
            self.assertIn('[request-trace]', summary)
            self.assertNotIn('Traceback', summary)


if __name__ == '__main__':
    unittest.main()
