from training.config import Settings
from training.content import load_questions
from training.models import Mode
from training.persistence import TrainingStore
from training.selection import Selector


def test_new_learner_gets_untested_question_and_exclusion_changes_selection(tmp_path):
    questions = load_questions()
    store = TrainingStore(Settings(database_path=tmp_path / "training.db").database_path)
    store.sync_questions(questions)
    selector = Selector(store, questions)
    first = selector.select(Mode.DAILY)
    second = selector.select(Mode.DAILY, {first.question.id})
    assert first.reason == "untested competency"
    assert second.question.id != first.question.id


def test_all_required_competencies_have_content():
    expected = {
        "Python semantics", "Python design", "SQL correctness", "Data modeling",
        "Distributed systems", "API and integration design", "Reliability",
        "Incident reasoning", "Testing strategy", "Debugging",
        "Delivery and operational readiness", "Communication under ambiguity",
        "Decision quality", "Learning and correction",
    }
    assert {question.competency for question in load_questions()} == expected
