from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.assessment import next_module
from app.config import Settings
from app.database import Database, utc_now
from app.evidence import EvidenceSynchronizer
from app.models import (
    ASSISTANCE_RANK,
    AssessmentMode,
    AssistanceLevel,
    Correctness,
    DifficultyAdjustment,
    FeedbackVisibility,
    InputKind,
    InteractionType,
    NextAction,
    RecordUpdates,
    SessionStatus,
    SessionView,
    SubmitRequest,
)
from app.openai_service import InterviewerProvider, InterviewerUnavailable
from app.scenarios import BASELINE_SCENARIO, select_initial_scenario


class InvalidTransition(ValueError):
    pass


class ConfigurationError(RuntimeError):
    pass


class AssessmentEngine:
    def __init__(
        self,
        settings: Settings,
        database: Database,
        provider: InterviewerProvider,
        *,
        require_api_key: bool = True,
    ):
        self.settings = settings
        self.database = database
        self.provider = provider
        self.require_api_key = require_api_key
        self.evidence = EvidenceSynchronizer(settings.project_root, database)

    def start_session(self, target_role: str) -> SessionView:
        if self.require_api_key and not self.settings.api_configured:
            raise ConfigurationError(
                "OPENAI_API_KEY is not set. Export it in your shell environment and restart the launcher."
            )
        scenario = select_initial_scenario()
        now = utc_now()
        session_id = f"s_{uuid4().hex}"
        values = {
            "id": session_id,
            "assessment_id": self.database.next_assessment_id(),
            "target_role": target_role,
            "module": scenario.module,
            "scenario_id": scenario.id,
            "scenario_title": scenario.title,
            "scenario": scenario.public_context,
            "current_question": scenario.initial_question,
            "competencies": list(scenario.competencies),
            "difficulty": 3,
            "started_at": now,
        }
        return self.to_view(self.database.create_session(values))

    def submit(self, session_id: str, request: SubmitRequest) -> SessionView:
        session = self.database.get_session(session_id)
        if session["status"] != SessionStatus.ACTIVE.value:
            raise InvalidTransition("Answers can only be submitted to an active session")
        if request.kind == InputKind.CONTINUE_MODULE:
            raise InvalidTransition("continue_module is controlled by the application")
        if request.kind != InputKind.END_MODULE and not request.content.strip():
            raise ValueError("A response is required")

        submission, created = self.database.create_or_get_submission(
            request.request_id, session_id, request.kind.value, request.content
        )
        if not created and submission["status"] == "COMPLETED":
            return self.to_view(self.database.get_session(session_id))
        if not created and submission["status"] == "PROCESSING":
            raise InvalidTransition("This submission is already being processed")
        self.database.mark_submission_processing(request.request_id)

        force_completion = request.kind == InputKind.END_MODULE
        try:
            result = self.provider.evaluate(
                session=session,
                input_kind=request.kind,
                content=request.content,
                recent_turns=self.database.recent_turns(session_id),
                private_scenario_brief=BASELINE_SCENARIO.private_brief,
                force_module_completion=force_completion,
                next_module=next_module(session["module"]),
            )
            decision = self._enforce_decision(session, request.kind, result.decision, force_completion)
            session_updates = self._session_updates(session, request.kind, decision, result.response_id)
            self.database.complete_turn(
                session_id=session_id,
                request_id=request.request_id,
                input_kind=request.kind.value,
                candidate_input=request.content,
                previous_question=session["current_question"],
                interviewer_message=decision.interviewer_message,
                decision_json=decision.model_dump_json(),
                response_id=result.response_id,
                model=result.model,
                reasoning_effort=result.reasoning_effort,
                usage_json=json.dumps(result.usage),
                duration_ms=result.duration_ms,
                session_updates=session_updates,
            )
        except InterviewerUnavailable as exc:
            self.database.mark_submission_failed(request.request_id, session_id, str(exc))
            raise
        updated = self.database.get_session(session_id)
        if updated["status"] == SessionStatus.MODULE_COMPLETE.value:
            try:
                self.evidence.synchronize(
                    updated, decision, self.database.recent_turns(session_id, limit=100)
                )
            except Exception as exc:
                self.database.set_last_error(
                    session_id, f"The module completed, but evidence synchronization needs retry: {exc}"
                )
        return self.to_view(self.database.get_session(session_id))

    def pause(self, session_id: str) -> SessionView:
        session = self.database.get_session(session_id)
        if session["status"] != SessionStatus.ACTIVE.value:
            raise InvalidTransition("Only an active session can be paused")
        return self.to_view(self.database.set_status(session_id, SessionStatus.PAUSED))

    def resume(self, session_id: str) -> SessionView:
        session = self.database.get_session(session_id)
        if session["status"] != SessionStatus.PAUSED.value:
            raise InvalidTransition("Only a paused session can be resumed")
        return self.to_view(self.database.set_status(session_id, SessionStatus.ACTIVE))

    def continue_to_next_module(self, session_id: str, request_id: str) -> SessionView:
        session = self.database.get_session(session_id)
        if session["status"] != SessionStatus.MODULE_COMPLETE.value:
            raise InvalidTransition("The current module must be complete before continuing")
        if not self.database.sync_exists(session_id, session["module"]):
            raise InvalidTransition("Module evidence must synchronize successfully before continuing")
        following = next_module(session["module"])
        if following is None:
            return self.to_view(self.database.set_status(session_id, SessionStatus.COMPLETED))
        submission, created = self.database.create_or_get_submission(
            request_id, session_id, InputKind.CONTINUE_MODULE.value, following
        )
        if not created and submission["status"] == "COMPLETED":
            return self.to_view(self.database.get_session(session_id))
        if not created and submission["status"] == "PROCESSING":
            raise InvalidTransition("This transition is already being processed")
        self.database.mark_submission_processing(request_id)
        staged = dict(session)
        staged["module"] = following
        staged["current_question"] = "Begin the next module with one significant decision point."
        staged["module_review_json"] = None
        try:
            result = self.provider.evaluate(
                session=staged,
                input_kind=InputKind.CONTINUE_MODULE,
                content="Begin the next module without revealing future questions or solutions.",
                recent_turns=self.database.recent_turns(session_id),
                private_scenario_brief=BASELINE_SCENARIO.private_brief,
                force_module_completion=False,
                next_module=next_module(following),
            )
            decision = self._enforce_decision(staged, InputKind.CONTINUE_MODULE, result.decision, False)
            decision.module_complete = False
            decision.feedback_visibility = FeedbackVisibility.WITHHELD
            decision.record_updates = RecordUpdates()
            updates = self._session_updates(staged, InputKind.CONTINUE_MODULE, decision, result.response_id)
            updates.update(
                {
                    "module": following,
                    "status": SessionStatus.ACTIVE.value,
                    "mode": AssessmentMode.ASSESSMENT.value,
                    "module_review_json": None,
                    "active_since": utc_now(),
                }
            )
            self.database.complete_turn(
                session_id=session_id,
                request_id=request_id,
                input_kind=InputKind.CONTINUE_MODULE.value,
                candidate_input="",
                previous_question=f"Transition to {following}",
                interviewer_message=decision.interviewer_message,
                decision_json=decision.model_dump_json(),
                response_id=result.response_id,
                model=result.model,
                reasoning_effort=result.reasoning_effort,
                usage_json=json.dumps(result.usage),
                duration_ms=result.duration_ms,
                session_updates=updates,
            )
        except InterviewerUnavailable as exc:
            self.database.mark_submission_failed(request_id, session_id, str(exc))
            raise
        return self.to_view(self.database.get_session(session_id))

    def retry_evidence_sync(self, session_id: str) -> SessionView:
        session = self.database.get_session(session_id)
        if session["status"] != SessionStatus.MODULE_COMPLETE.value:
            raise InvalidTransition("Only completed module evidence can be synchronized")
        turns = self.database.recent_turns(session_id, limit=100)
        if not turns:
            raise InvalidTransition("No completed turn is available to synchronize")
        from app.models import InterviewerDecision

        decision = InterviewerDecision.model_validate_json(turns[-1]["decision_json"])
        self.evidence.synchronize(session, decision, turns)
        self.database.set_last_error(session_id, None)
        return self.to_view(self.database.get_session(session_id))

    def to_view(self, session: dict) -> SessionView:
        return SessionView(
            id=session["id"],
            assessment_id=session["assessment_id"],
            target_role=session["target_role"],
            module=session["module"],
            scenario_id=session["scenario_id"],
            scenario_title=session["scenario_title"],
            scenario=session["scenario"],
            current_question=session["current_question"],
            newly_introduced_constraints=json.loads(session["constraints_json"]),
            turn_number=session["turn_number"],
            difficulty=session["difficulty"],
            status=SessionStatus(session["status"]),
            mode=AssessmentMode(session["mode"]),
            hints_used=session["hints_used"],
            assistance_level=AssistanceLevel(session["assistance_level"]),
            elapsed_seconds=self._elapsed(session),
            started_at=session["started_at"],
            updated_at=session["updated_at"],
            last_error=session["last_error"],
            competencies_in_scope=json.loads(session["competencies_json"]),
            module_review=(
                json.loads(session["module_review_json"])
                if session["module_review_json"]
                else None
            ),
        )

    @staticmethod
    def _elapsed(session: dict) -> int:
        elapsed = int(session["accumulated_seconds"])
        if session["status"] == SessionStatus.ACTIVE.value and session["active_since"]:
            elapsed += max(
                0,
                int((datetime.now(UTC) - datetime.fromisoformat(session["active_since"])).total_seconds()),
            )
        return elapsed

    @staticmethod
    def _enforce_decision(session, input_kind, decision, force_completion):
        if input_kind == InputKind.HINT and ASSISTANCE_RANK[decision.assistance_level] < ASSISTANCE_RANK[
            AssistanceLevel.MINOR_HINT
        ]:
            decision.assistance_level = AssistanceLevel.MINOR_HINT
            decision.interaction_type = InteractionType.HINT_RESPONSE
        elif input_kind == InputKind.CLARIFICATION and decision.assistance_level == AssistanceLevel.NONE:
            decision.assistance_level = AssistanceLevel.CLARIFICATION
            decision.interaction_type = InteractionType.CLARIFICATION_RESPONSE
        if force_completion or decision.module_complete:
            decision.module_complete = True
            decision.interaction_type = InteractionType.MODULE_EVALUATION
            decision.feedback_visibility = FeedbackVisibility.MODULE_SUMMARY
            decision.next_action = NextAction.COMPLETE_MODULE
        elif not decision.module_complete:
            decision.feedback_visibility = FeedbackVisibility.WITHHELD
            decision.strengths_detected = []
            decision.weaknesses_detected = []
            decision.record_updates = RecordUpdates()
        if (
            int(session.get("failure_streak", 0)) >= 2
            and decision.answer_correctness in {Correctness.INCORRECT, Correctness.PARTIAL}
            and not decision.module_complete
        ):
            decision.difficulty_adjustment = DifficultyAdjustment.DECREASE
            decision.follow_up_strategy = (
                "Prerequisite diagnosis after repeated failure. " + decision.follow_up_strategy
            )
        return decision

    @staticmethod
    def _session_updates(session, input_kind, decision, response_id):
        current_assistance = AssistanceLevel(session["assistance_level"])
        assistance = max(
            (current_assistance, decision.assistance_level), key=lambda level: ASSISTANCE_RANK[level]
        )
        hints = int(session["hints_used"])
        if input_kind == InputKind.HINT:
            hints += 1
        difficulty = int(session["difficulty"])
        if decision.difficulty_adjustment.value == "increase":
            difficulty = min(5, difficulty + 1)
        elif decision.difficulty_adjustment.value == "decrease":
            difficulty = max(1, difficulty - 1)
        constraints = json.loads(session["constraints_json"])
        for item in decision.new_constraints:
            if item not in constraints:
                constraints.append(item)
        updates = {
            "current_question": decision.interviewer_message,
            "constraints_json": json.dumps(constraints),
            "turn_number": int(session["turn_number"]) + 1,
            "difficulty": difficulty,
            "assistance_level": assistance.value,
            "hints_used": hints,
            "previous_response_id": response_id,
            "last_error": None,
            "failure_streak": (
                int(session.get("failure_streak", 0)) + 1
                if decision.answer_correctness in {Correctness.INCORRECT, Correctness.PARTIAL}
                else 0
            ),
        }
        if decision.module_complete:
            accumulated = int(session["accumulated_seconds"])
            if session.get("active_since"):
                accumulated += max(
                    0,
                    int(
                        (
                            datetime.now(UTC)
                            - datetime.fromisoformat(session["active_since"])
                        ).total_seconds()
                    ),
                )
            review = {
                "competencies_tested": decision.competencies_tested,
                "evidence_observed": decision.evidence_observed,
                "strengths": decision.strengths_detected,
                "weaknesses": decision.weaknesses_detected,
                "assistance_level": assistance.value,
                "independent": ASSISTANCE_RANK[assistance] <= ASSISTANCE_RANK[AssistanceLevel.CLARIFICATION],
                "answer_correctness": decision.answer_correctness.value,
                "reasoning_quality": decision.reasoning_quality.value,
                "communication_quality": decision.communication_quality.value,
                "technical_depth": decision.technical_depth.value,
                "production_awareness": decision.production_awareness.value,
                "security_awareness": decision.security_awareness.value,
                "testing_quality": decision.testing_quality.value,
                "next_recommended_assessment": decision.record_updates.next_recommended_assessment,
            }
            updates.update(
                {
                    "status": SessionStatus.MODULE_COMPLETE.value,
                    "mode": AssessmentMode.LEARNING.value,
                    "module_review_json": json.dumps(review),
                    "next_recommended_assessment": decision.record_updates.next_recommended_assessment,
                    "active_since": None,
                    "accumulated_seconds": accumulated,
                }
            )
        return updates
