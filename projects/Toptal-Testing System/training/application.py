from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Protocol

from .config import Settings
from .content import load_questions
from .deterministic import enforce_authoritative_results, run_deterministic_checks
from .evaluation import evaluate_deterministically
from .generation import originalize
from .llm import EvaluationProvider, LLMUnavailable, select_provider
from .models import Assistance, Evaluation, Mode, Outcome, Question
from .mastery import assessment_eligibility, assessment_outcome
from .persistence import TrainingStore
from .scheduling import next_review_at
from .selection import Selector


class IO(Protocol):
    def write(self, text: str = "") -> None: ...
    def read(self, prompt: str = "") -> str: ...


class ConsoleIO:
    def write(self, text: str = "") -> None:
        print(text)

    def read(self, prompt: str = "") -> str:
        return input(prompt)


@dataclass(frozen=True)
class Response:
    answer: str | None
    assistance: Assistance
    hint_count: int
    control: str | None = None


MENU = """
[Enter] Daily Training     2 Cold Recall      3 Practice
4 Assessment              5 Mock Interview    6 Weakness Review
7 Progress                q Quit
""".strip()


MODE_CHOICES = {
    "": Mode.DAILY,
    "1": Mode.DAILY,
    "2": Mode.COLD_RECALL,
    "3": Mode.PRACTICE,
    "4": Mode.ASSESSMENT,
    "5": Mode.MOCK_INTERVIEW,
    "6": Mode.WEAKNESS_REVIEW,
}


class TrainingApplication:
    def __init__(
        self,
        settings: Settings,
        io: IO | None = None,
        provider: EvaluationProvider | None = None,
    ):
        self.settings = settings
        self.io = io or ConsoleIO()
        self.questions = load_questions()
        self.by_id = {question.id: question for question in self.questions}
        self.store = TrainingStore(settings.database_path)
        self.store.sync_questions(self.questions)
        self.selector = Selector(self.store, self.questions)
        self.provider = provider
        self.provider_fallback_reason: str | None = None
        self.provider_note = "offline fallback"
        if provider is not None:
            self.provider_note = provider.name
        else:
            selection = select_provider(settings)
            self.provider = selection.provider
            self.provider_note = selection.display_name
            self.provider_fallback_reason = selection.fallback_reason

    def run(self) -> int:
        self._starting_screen()
        active = self.store.active_session()
        if active is not None:
            choice = self.io.read(
                f"Resume interrupted {active['mode']} session #{active['id']}? [Y/n] "
            ).strip().lower()
            if choice in {"", "y", "yes"}:
                return self._run_session_safely(Mode(active["mode"]), int(active["id"]))
            self.store.set_session_status(int(active["id"]), "paused")
        self.io.write(MENU)
        choice = self.io.read("Select mode: ").strip().lower()
        if choice == "q":
            return 0
        if choice == "7":
            self._show_progress()
            return 0
        mode = MODE_CHOICES.get(choice)
        if mode is None:
            self.io.write("Unknown selection. No session started.")
            return 2
        session_id = self.store.create_session(mode)
        return self._run_session_safely(mode, session_id)

    def _run_session_safely(self, mode: Mode, session_id: int) -> int:
        try:
            return self._run_session(mode, session_id)
        except LLMUnavailable as exc:
            self.store.set_session_status(session_id, "paused")
            self.io.write(f"Evaluation unavailable; answer remains saved. {exc}")
            return 3

    def _starting_screen(self) -> None:
        rows = self.store.competency_rows()
        attempted = sum(1 for row in rows if row["attempts"] > 0)
        legacy = self.store.legacy_credit_competencies()
        weak = sum(1 for row in rows if row["state"] == "WEAK" and row["name"] not in legacy)
        mastered = sum(1 for row in rows if row["state"] == "MASTERED" and row["name"] not in legacy)
        self.io.write("=" * 68)
        self.io.write("TOPTAL TECHNICAL TRAINING SYSTEM")
        self.io.write("Adaptive local practice • one question at a time")
        self.io.write(
            f"Progress: {attempted}/{len(rows)} competencies attempted | {weak} weak | {mastered} mastered"
        )
        if legacy:
            self.io.write(f"Legacy/unverified credit: {len(legacy)} competencies. Preview an explicit profile rebuild before trusting their mastery.")
        self.io.write(f"Current goal: {self.settings.goal}")
        self.io.write(f"Evaluator: {self.provider_note}")
        if self.provider is None:
            self.io.write(
                "Offline evaluation is conservative and lexical; it cannot replace semantic senior review."
            )
            if self.provider_fallback_reason:
                self.io.write(f"Fallback reason: {self.provider_fallback_reason}")
        self.io.write("=" * 68)

    def _run_session(self, mode: Mode, session_id: int) -> int:
        self.store.resume_session(session_id)
        self._recover_pending(session_id, mode)
        existing = self.store.session_attempts(session_id)
        primary_done = sum(1 for row in existing if not row["is_followup"])
        used = {row["question_id"] for row in existing if not row["is_followup"]}
        target = 3 if mode == Mode.MOCK_INTERVIEW else self.settings.session_questions
        outcomes: list[Evaluation] = []
        while primary_done < target:
            selection = self.selector.select(mode, used)
            exposure = self.store.question_attempt_count(selection.question.id)
            question = originalize(selection.question, session_id, exposure)
            is_transfer = selection.is_transfer or (
                self.store.competency(question.competency)["attempts"] > 0
                and not self.store.competency_family_attempted(
                    question.competency, question.family
                )
            )
            self.io.write("")
            self.io.write(
                f"[{mode.value.replace('_', ' ').title()}] {question.competency} "
                f"(difficulty {question.difficulty}/5; selected for {selection.reason})"
            )
            self.io.write(question.prompt)
            response = self._read_response(session_id, question, mode)
            if response.control:
                self.store.set_session_status(session_id, "paused")
                self.io.write(f"Session #{session_id} paused. Launch again to resume.")
                return 0
            assert response.answer is not None
            evaluation = self._persist_and_evaluate(
                session_id=session_id,
                question=question,
                answer=response.answer,
                assistance=response.assistance,
                hint_count=response.hint_count,
                mode=mode,
                is_followup=False,
                is_cold_recall=selection.is_cold_recall,
                is_transfer=is_transfer,
            )
            outcomes.append(evaluation)
            if evaluation.missing:
                followup_prompt = self._followup_prompt(question, evaluation, mode)
                self.io.write("")
                self.io.write("Follow-up: " + followup_prompt)
                followup = self._read_response(session_id, question, mode, allow_hints=False)
                if followup.control:
                    self.store.set_session_status(session_id, "paused")
                    self.io.write(f"Session #{session_id} paused. Launch again to resume.")
                    return 0
                assert followup.answer is not None
                followup_question = Question(
                    id=question.id,
                    competency=question.competency,
                    family=question.family,
                    difficulty=question.difficulty,
                    prompt=followup_prompt,
                    criteria=tuple(
                        item for item in question.criteria if item.id in evaluation.missing
                    ),
                    hints=(),
                    followups={},
                    source=question.source,
                )
                followup_eval = self._persist_and_evaluate(
                    session_id=session_id,
                    question=followup_question,
                    answer=followup.answer,
                    assistance=response.assistance,
                    hint_count=response.hint_count,
                    mode=mode,
                    is_followup=True,
                    is_cold_recall=False,
                    is_transfer=False,
                )
                outcomes.append(followup_eval)
            if mode not in {Mode.ASSESSMENT, Mode.MOCK_INTERVIEW}:
                label = "Assessment result" if assessment_eligibility(evaluation).assessed else "Unassessed practice coverage"
                self.io.write(f"{label}: {evaluation.outcome.value.upper()} ({evaluation.score:.0%})")
                self.io.write(
                    f"Evaluator: {evaluation.evaluator_provider} / {evaluation.evaluator_model} "
                    f"({evaluation.evaluation_mode})"
                )
                self.io.write(evaluation.feedback)
            else:
                self.io.write("Response recorded. Detailed assessment is withheld until session end.")
            used.add(question.id)
            primary_done += 1

        summary = self._summary(session_id, outcomes)
        self.store.set_session_status(session_id, "completed", summary)
        self.io.write("")
        self.io.write("SESSION COMPLETE")
        self.io.write(
            f"Evaluated attempts: {summary['evaluated']} | assessed {summary['assessed']}: "
            f"pass {summary['pass']} | partial {summary['partial']} | fail {summary['fail']} | "
            f"unassessed/diagnostic {summary['diagnostic']}"
        )
        if mode in {Mode.ASSESSMENT, Mode.MOCK_INTERVIEW}:
            self._show_assessment_feedback(session_id)
        self._show_progress(limit=8)
        return 0

    def _read_response(
        self, session_id: int, question: Question, mode: Mode, allow_hints: bool = True
    ) -> Response:
        self.io.write("Enter your answer and reasoning. Finish with /submit. Use /pause to stop safely.")
        if allow_hints and mode in {Mode.DAILY, Mode.PRACTICE}:
            self.io.write("Use /hint on its own line for progressive assistance.")
        lines: list[str] = []
        hint_count = 0
        while True:
            line = self.io.read("> ")
            command = line.strip().lower()
            if command in {"/pause", "/quit"}:
                self.store.record_event(session_id, "session_paused", command)
                return Response(None, Assistance.NONE, hint_count, command)
            if command == "/hint":
                self.store.record_event(session_id, "hint_requested", f"question={question.id}")
                if not allow_hints or mode not in {Mode.DAILY, Mode.PRACTICE}:
                    self.io.write("Hints are disabled in this mode. Your request was recorded.")
                    self.store.record_event(session_id, "hint_denied", f"mode={mode.value}")
                    continue
                hint_index = min(hint_count, max(0, len(question.hints) - 1))
                if question.hints:
                    self.io.write("Hint: " + question.hints[hint_index])
                else:
                    self.io.write("No hint is available for this prompt.")
                hint_count += 1
                self.store.record_event(session_id, "hint_shown", f"level={hint_count}")
                continue
            if command == "/submit":
                answer = "\n".join(lines).strip()
                if not answer:
                    self.io.write("Enter an answer before submitting.")
                    continue
                assistance = (
                    Assistance.STRONG
                    if hint_count >= 2
                    else Assistance.LIGHT
                    if hint_count == 1
                    else Assistance.NONE
                )
                return Response(answer, assistance, hint_count)
            lines.append(line)

    def _evaluate(self, question: Question, answer: str, mode: Mode) -> Evaluation:
        deterministic = run_deterministic_checks(question, answer)
        if self.provider is None:
            evaluation = evaluate_deterministically(
                question,
                answer,
                deterministic,
                fallback_reason=self.provider_fallback_reason,
            )
            return enforce_authoritative_results(evaluation, deterministic)
        try:
            method = getattr(self.provider, "evaluate_with_context", None)
            evaluation = (
                method(question, answer, mode, deterministic)
                if method
                else self.provider.evaluate(question, answer, mode)
            )
            if self.provider_fallback_reason and not evaluation.fallback_reason:
                evaluation = replace(
                    evaluation, fallback_reason=self.provider_fallback_reason
                )
        except LLMUnavailable as exc:
            if self.settings.llm_mode == "required":
                raise
            self.io.write(
                "Reasoning evaluator unavailable; using conservative offline rubric for this saved answer."
            )
            evaluation = evaluate_deterministically(
                question, answer, deterministic, fallback_reason=str(exc)
            )
        return enforce_authoritative_results(evaluation, deterministic)

    def _persist_and_evaluate(
        self,
        *,
        session_id: int,
        question: Question,
        answer: str,
        assistance: Assistance,
        hint_count: int,
        mode: Mode,
        is_followup: bool,
        is_cold_recall: bool,
        is_transfer: bool,
    ) -> Evaluation:
        attempt_id = self.store.record_answer(
            session_id=session_id,
            question_id=question.id,
            prompt_snapshot=question.prompt,
            family_snapshot=question.family,
            answer=answer,
            assistance=assistance,
            hint_count=hint_count,
            is_followup=is_followup,
            is_cold_recall=is_cold_recall,
            is_transfer=is_transfer,
        )
        evaluation = self._evaluate(question, answer, mode)
        row = self.store.competency(question.competency)
        review = next_review_at(
            outcome=evaluation.outcome,
            evaluation=evaluation,
            assistance=assistance,
            mode=mode,
            is_transfer=is_transfer,
            consecutive_failures=int(row["consecutive_failures"]) + int(
                assessment_outcome(evaluation, evaluation.outcome) == Outcome.FAIL
            ),
            settings=self.settings,
        )
        self.store.record_evaluation(
            attempt_id=attempt_id,
            question=question,
            evaluation=evaluation,
            assistance=assistance,
            mode=mode,
            is_followup=is_followup,
            is_cold_recall=is_cold_recall,
            is_transfer=is_transfer,
            next_review_at=review.isoformat(),
            settings=self.settings,
        )
        return evaluation

    def _recover_pending(self, session_id: int, mode: Mode) -> None:
        pending = self.store.unanswered_evaluations(session_id)
        if pending:
            self.io.write(f"Recovering {len(pending)} saved answer(s) before continuing.")
        for row in pending:
            question = replace(
                self.by_id[row["question_id"]],
                prompt=row["prompt_snapshot"],
                family=row["family_snapshot"],
            )
            evaluation = self._evaluate(question, row["answer"], mode)
            competency = self.store.competency(question.competency)
            review = next_review_at(
                outcome=evaluation.outcome,
                evaluation=evaluation,
                assistance=Assistance(row["assistance"]),
                mode=mode,
                is_transfer=bool(row["is_transfer"]),
                consecutive_failures=int(competency["consecutive_failures"]) + int(
                    assessment_outcome(evaluation, evaluation.outcome) == Outcome.FAIL
                ),
                settings=self.settings,
            )
            self.store.record_evaluation(
                attempt_id=int(row["id"]),
                question=question,
                evaluation=evaluation,
                assistance=Assistance(row["assistance"]),
                mode=mode,
                is_followup=bool(row["is_followup"]),
                is_cold_recall=bool(row["is_cold_recall"]),
                is_transfer=bool(row["is_transfer"]),
                next_review_at=review.isoformat(),
                settings=self.settings,
            )

    @staticmethod
    def _followup_prompt(question: Question, evaluation: Evaluation, mode: Mode) -> str:
        if evaluation.follow_up_questions:
            return evaluation.follow_up_questions[0]
        if mode in {Mode.ASSESSMENT, Mode.MOCK_INTERVIEW}:
            return "Challenge your own answer: identify the highest-risk missing assumption or failure mode."
        missing = evaluation.missing[0]
        return question.followups.get(missing, "What important dimension is still missing?")

    def _summary(self, session_id: int, new_outcomes: list[Evaluation]) -> dict:
        rows = self.store.session_attempts(session_id)
        counts = {name: 0 for name in ("pass", "partial", "fail")}
        diagnostic = 0
        for row in rows:
            if row["status"] != "evaluated":
                continue
            outcome = assessment_outcome(self.store._metadata(row["evaluation_json"]), row["outcome"])
            if outcome is not None and not row["is_followup"]:
                counts[outcome.value] += 1
            else:
                diagnostic += 1
        assessed = sum(counts.values())
        return {"evaluated": assessed + diagnostic, "assessed": assessed, "diagnostic": diagnostic,
                **counts, "new_outcomes": len(new_outcomes)}

    def _show_progress(self, limit: int | None = None) -> None:
        rows = sorted(
            self.store.competency_rows(),
            key=lambda row: (
                0 if int(row["attempts"]) > 0 else 1,
                float(row["mastery"]),
                row["name"],
            ),
        )
        if limit:
            rows = rows[:limit]
        self.io.write("")
        self.io.write("PROGRESS")
        legacy = self.store.legacy_credit_competencies()
        self.io.write(f"{'Competency':38} {'State':11} {'Score':>5} {'Attempts':>8} {'Next review'}")
        for row in rows:
            next_review = (row["next_review_at"] or "-")[:10]
            state = "LEGACY" if row["name"] in legacy else row["state"]
            score = "?" if row["name"] in legacy else f"{float(row['mastery']):.0%}"
            self.io.write(
                f"{row['name'][:38]:38} {state:11} {score:>5} "
                f"{int(row['attempts']):8d} {next_review}"
            )
        weaknesses = self.store.open_weaknesses()
        if weaknesses:
            self.io.write(f"Open weakness records: {len(weaknesses)}")

    def _show_assessment_feedback(self, session_id: int) -> None:
        self.io.write("ASSESSMENT FEEDBACK")
        for index, row in enumerate(self.store.session_attempts(session_id), start=1):
            if not row["evaluation_json"]:
                continue
            payload = json.loads(row["evaluation_json"])
            kind = "follow-up" if row["is_followup"] else "primary"
            assessed = assessment_outcome(payload, row["outcome"])
            label = "assessed" if assessed is not None and not row["is_followup"] else "unassessed/diagnostic"
            self.io.write(
                f"{index}. {kind}, {label}: {str(row['outcome']).upper()} — {payload['feedback']} "
                f"[{payload.get('evaluator_provider', 'unknown')} / "
                f"{payload.get('evaluator_model', 'unknown')}]"
            )
