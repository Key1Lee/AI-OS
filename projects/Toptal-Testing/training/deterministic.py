from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from .models import Evaluation, Outcome, Question


@dataclass(frozen=True)
class DeterministicCheck:
    name: str
    passed: bool
    authoritative: bool
    detail: str


@dataclass(frozen=True)
class DeterministicReport:
    version: str
    checks: tuple[DeterministicCheck, ...]

    @property
    def blocking_failures(self) -> tuple[DeterministicCheck, ...]:
        return tuple(check for check in self.checks if check.authoritative and not check.passed)

    def as_dict(self) -> dict:
        return {
            "version": self.version,
            "checks": [asdict(check) for check in self.checks],
            "blocking_failures": [check.name for check in self.blocking_failures],
        }


def run_deterministic_checks(question: Question, answer: str) -> DeterministicReport:
    """Run objective checks available for the current prose-answer contract.

    The current question bank does not execute candidate SQL or Python. Artifact
    questions can extend this report with sandboxed execution results later; LLMs
    must never override an authoritative failure added here.
    """
    checks = (
        DeterministicCheck(
            name="answer_present",
            passed=bool(answer.strip()),
            authoritative=True,
            detail="Candidate response must contain non-whitespace content.",
        ),
        DeterministicCheck(
            name="rubric_contract_valid",
            passed=bool(question.criteria)
            and len({criterion.id for criterion in question.criteria})
            == len(question.criteria),
            authoritative=False,
            detail="Question rubric must contain at least one uniquely identified criterion.",
        ),
    )
    return DeterministicReport(version="deterministic-v1", checks=checks)


def enforce_authoritative_results(
    evaluation: Evaluation, report: DeterministicReport
) -> Evaluation:
    failures = report.blocking_failures
    if not failures:
        return replace(evaluation, deterministic_results=report.as_dict())
    details = "; ".join(check.detail for check in failures)
    feedback = f"Authoritative deterministic failure: {details} {evaluation.feedback}".strip()
    return replace(
        evaluation,
        outcome=Outcome.FAIL,
        score=min(evaluation.score, 0.39),
        feedback=feedback,
        critical_errors=tuple(evaluation.critical_errors)
        + tuple(check.name for check in failures),
        deterministic_results=report.as_dict(),
    )
