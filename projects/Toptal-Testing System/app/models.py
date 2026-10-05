from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50_000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    MODULE_COMPLETE = "MODULE_COMPLETE"
    COMPLETED = "COMPLETED"


class AssessmentMode(str, Enum):
    ASSESSMENT = "ASSESSMENT"
    LEARNING = "LEARNING"


class InputKind(str, Enum):
    ANSWER = "answer"
    CLARIFICATION = "clarification"
    HINT = "hint"
    END_MODULE = "end_module"
    CONTINUE_MODULE = "continue_module"


class AssistanceLevel(str, Enum):
    NONE = "none"
    CLARIFICATION = "clarification"
    MINOR_HINT = "minor_hint"
    SUBSTANTIAL_HINT = "substantial_hint"
    ASSISTED_SOLUTION = "assisted_solution"


ASSISTANCE_RANK = {
    AssistanceLevel.NONE: 0,
    AssistanceLevel.CLARIFICATION: 1,
    AssistanceLevel.MINOR_HINT: 2,
    AssistanceLevel.SUBSTANTIAL_HINT: 3,
    AssistanceLevel.ASSISTED_SOLUTION: 4,
}


class InteractionType(str, Enum):
    FOLLOW_UP = "follow_up"
    CLARIFICATION_RESPONSE = "clarification_response"
    HINT_RESPONSE = "hint_response"
    MODULE_EVALUATION = "module_evaluation"
    ASSESSMENT_COMPLETE = "assessment_complete"


class EvidenceRating(str, Enum):
    NOT_OBSERVED = "not_observed"
    INSUFFICIENT = "insufficient"
    WEAK = "weak"
    ACCEPTABLE = "acceptable"
    STRONG = "strong"
    EXCEPTIONAL = "exceptional"


class Correctness(str, Enum):
    NOT_APPLICABLE = "not_applicable"
    INCORRECT = "incorrect"
    PARTIAL = "partial"
    CORRECT = "correct"
    UNVERIFIED = "unverified"


class DifficultyAdjustment(str, Enum):
    DECREASE = "decrease"
    MAINTAIN = "maintain"
    INCREASE = "increase"


class NextAction(str, Enum):
    CONTINUE = "continue"
    COMPLETE_MODULE = "complete_module"
    COMPLETE_ASSESSMENT = "complete_assessment"


class FeedbackVisibility(str, Enum):
    WITHHELD = "withheld"
    MODULE_SUMMARY = "module_summary"
    LEARNING = "learning"


class CompetencyState(str, Enum):
    UNTESTED = "UNTESTED"
    DEVELOPING = "DEVELOPING"
    DEMONSTRATED = "DEMONSTRATED"
    RETEST_DUE = "RETEST_DUE"
    REOPENED = "REOPENED"


class CompetencyUpdate(StrictModel):
    competency: NonBlank
    proposed_state: CompetencyState
    evidence: NonBlank
    difficulty: int = Field(ge=1, le=5)
    independent: bool


class WeaknessUpdate(StrictModel):
    competency: NonBlank
    classification: Literal[
        "Knowledge Gap",
        "Reasoning Gap",
        "Implementation Error",
        "Debugging Process Gap",
        "Architecture Gap",
        "Communication Issue",
        "Requirements Gap",
        "Avoidable Oversight",
    ]
    evidence: NonBlank
    remediation: NonBlank


class RecordUpdates(StrictModel):
    competency_updates: list[CompetencyUpdate] = Field(default_factory=list, max_length=28)
    weakness_updates: list[WeaknessUpdate] = Field(default_factory=list, max_length=20)
    next_recommended_assessment: str = Field(default="", max_length=2_000)
    mastery_recommended: bool = False


class InterviewerDecision(StrictModel):
    interviewer_message: NonBlank
    interaction_type: InteractionType
    assessment_continues: bool
    module_complete: bool
    new_constraints: list[str] = Field(default_factory=list, max_length=12)
    competencies_tested: list[str] = Field(default_factory=list, max_length=28)
    evidence_observed: list[str] = Field(default_factory=list, max_length=30)
    assistance_level: AssistanceLevel
    answer_correctness: Correctness
    reasoning_quality: EvidenceRating
    communication_quality: EvidenceRating
    technical_depth: EvidenceRating
    production_awareness: EvidenceRating
    security_awareness: EvidenceRating
    testing_quality: EvidenceRating
    confidence: float = Field(ge=0, le=1)
    weaknesses_detected: list[str] = Field(default_factory=list, max_length=20)
    strengths_detected: list[str] = Field(default_factory=list, max_length=20)
    follow_up_strategy: str = Field(max_length=2_000)
    difficulty_adjustment: DifficultyAdjustment
    next_action: NextAction
    record_updates: RecordUpdates
    feedback_visibility: FeedbackVisibility


class StartSessionRequest(StrictModel):
    target_role: str = Field(default="Senior Forward Deployed Engineer", min_length=3, max_length=200)


class SubmitRequest(StrictModel):
    request_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    kind: InputKind
    content: str = Field(default="", max_length=50_000)


class ContinueRequest(StrictModel):
    request_id: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class SessionView(StrictModel):
    id: str
    assessment_id: str
    target_role: str
    module: str
    scenario_id: str
    scenario_title: str
    scenario: str
    current_question: str
    newly_introduced_constraints: list[str]
    turn_number: int
    difficulty: int
    status: SessionStatus
    mode: AssessmentMode
    hints_used: int
    assistance_level: AssistanceLevel
    elapsed_seconds: int
    started_at: str
    updated_at: str
    last_error: str | None
    competencies_in_scope: list[str]
    module_review: dict | None = None


class ConfigurationView(StrictModel):
    api_configured: bool
    model: str
    default_reasoning_effort: str
    high_reasoning_effort: str
    request_token: str
