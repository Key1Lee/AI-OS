from __future__ import annotations

import logging
import json
from datetime import datetime
from typing import Callable
from uuid import uuid4

from sqlalchemy import case, select

from trainer.adaptive.selection import recommend
from trainer.execution.sql import ExecutionUnavailable, SqlRunner
from trainer.exercises.bank import Bank
from trainer.mastery.policy import parse, stamp, utc_now
from trainer.repositories.models import AttemptRow, ExerciseVersionRow, InteractionRow, MasteryRow, MistakeRow, SessionRow, SubmissionRow, TestRunRow
from trainer.repositories.store import Store
from trainer.schemas.models import DraftRequest, Exercise, StartRequest, SubmitRequest
from trainer.services.progress import add_event, record_progress

log = logging.getLogger(__name__)


class Conflict(ValueError):
    pass


class TrainingService:
    def __init__(self, store: Store, bank: Bank, runner: SqlRunner, clock: Callable[[], datetime] = utc_now):
        self.store, self.bank, self.runner, self.clock = store, bank, runner, clock

    def _attempt(self, session, key: str) -> AttemptRow:
        row = session.get(AttemptRow, key)
        if row is None:
            raise KeyError(key)
        return row

    def _exercise(self, session, attempt: AttemptRow) -> Exercise:
        return Exercise.model_validate(session.get(ExerciseVersionRow, attempt.exercise_version_id).definition)

    def _active(self, row: AttemptRow):
        if row.status != "active":
            raise Conflict("This attempt is paused, grading or completed. Resume it or create a revision.")

    def _current(self, session):
        priority = case((AttemptRow.status == "grading", 0), (AttemptRow.status == "active", 1), else_=2)
        return session.scalar(select(AttemptRow).where(AttemptRow.status.in_(["active","paused","grading"])).order_by(priority,AttemptRow.started_at.desc()))

    def _view(self, session, row: AttemptRow) -> dict:
        exercise = self._exercise(session, row)
        interactions = list(session.scalars(select(InteractionRow).where(InteractionRow.attempt_id == row.id).order_by(InteractionRow.created_at)))
        pending = None if row.status == "completed" else session.scalar(select(SubmissionRow).where(SubmissionRow.attempt_id == row.id, SubmissionRow.status != "completed").order_by(SubmissionRow.created_at.desc()))
        return dict(id=row.id, session_id=row.session_id, parent_attempt_id=row.parent_attempt_id,
                    mode=row.mode, status=row.status, started_at=row.started_at, completed_at=row.completed_at,
                    code=row.code, explanation=row.explanation, external_assistance=row.external_assistance,
                    hint_count=row.hint_count, solution_seen=row.solution_seen, draft_revision=row.draft_revision,
                    timed=row.timed, exercise=exercise.public(), result=row.result, selection=row.selection,
                    pending_request_id=pending.id if pending else None,
                    pending_submission=dict(request_id=pending.id,code=pending.code,explanation=pending.explanation,external_assistance=pending.external_assistance) if pending else None,
                    interactions=[dict(kind=i.kind, at=i.created_at, **i.payload) for i in interactions])

    def attempt(self, key: str) -> dict:
        with self.store.transaction() as session:
            return self._view(session, self._attempt(session, key))

    def _context(self, session):
        states = {r.competency_id: r.state for r in session.scalars(select(MasteryRow))}
        history = []
        for row in session.scalars(select(AttemptRow).where(AttemptRow.status == "completed").order_by(AttemptRow.completed_at)):
            e = self._exercise(session, row)
            history.append(dict(id=row.id,exercise_id=e.id,title=e.title,version=e.version,family=e.family,
                                difficulty=e.difficulty,competencies=e.competencies,result=row.result,
                                mode=row.mode,at=row.completed_at,hints=row.hint_count,solution_seen=row.solution_seen))
        return states, history

    def recommendation(self) -> dict | None:
        with self.store.transaction() as session:
            states, history = self._context(session)
            return recommend(self.bank, states, history, self.clock())

    def start(self, request: StartRequest, *, parent_id: str | None = None) -> dict:
        now = self.clock()
        with self.store.transaction(write=True) as session:
            active = self._current(session)
            if not request.exercise_id and not request.competency and not request.difficulty and not parent_id and active and request.mode == "adaptive":
                if active.status == "paused":
                    active.status = "active"
                    session.get(SessionRow, active.session_id).status = "active"
                return self._view(session, active)
            if active and active.status == "grading":
                raise Conflict("A saved submission is being graded. Finish or retry that submission before starting another exercise.")
            if request.exercise_id and request.exercise_id not in self.bank.exercises:
                raise KeyError(request.exercise_id)
            if active and active.status == "active":
                active.status = "paused"
                session.get(SessionRow, active.session_id).status = "paused"
            states, history = self._context(session)
            selection = recommend(self.bank,states,history,now,competency=request.competency,difficulty=request.difficulty,practice=request.mode != "adaptive")
            if request.exercise_id:
                exercise = self.bank.exercises[request.exercise_id]
                selection = dict(exercise_id=exercise.id,title=exercise.title,difficulty=exercise.difficulty,reasons=["Selected for practice."],factors={})
            elif selection:
                exercise = self.bank.exercises[selection["exercise_id"]]
            else:
                raise Conflict("No exercise meets these filters or prerequisites. Choose another difficulty or competency.")
            parent = self._attempt(session, parent_id) if parent_id else None
            if parent and parent.status != "completed":
                raise Conflict("Only a completed attempt can be revised.")
            # A revision keeps the exact frozen version, not the newest bank file.
            if parent:
                exercise = self._exercise(session, parent)
            new_session = SessionRow(id=uuid4().hex,mode=request.mode,created_at=stamp(now),status="active")
            session.add(new_session)
            session.flush()
            row = AttemptRow(id=uuid4().hex,session_id=new_session.id,exercise_version_id=f"{exercise.id}:v{exercise.version}",parent_attempt_id=parent_id,
                             mode=request.mode,status="active",started_at=stamp(now),code=parent.code if parent else exercise.starter_code,
                             explanation=parent.explanation if parent else "",external_assistance=parent.external_assistance if parent else False,
                             hint_count=parent.hint_count if parent else 0,solution_seen=parent.solution_seen if parent else False,
                             draft_revision=0,timed=request.timed,selection=selection or {})
            session.add(row)
            session.flush()
            add_event(session,row.id,"attempt_started",{"exercise_id": exercise.id,"version": exercise.version,"mode":request.mode},now)
            return self._view(session,row)

    def revise(self, key: str) -> dict:
        old = self.attempt(key)
        return self.start(StartRequest(mode=old["mode"],exercise_id=old["exercise"]["id"],timed=old["timed"]),parent_id=key)

    def save(self, key: str, draft: DraftRequest) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            self._active(row)
            if row.draft_revision != draft.revision:
                raise Conflict("This draft changed in another request or tab. Reload the saved version before writing.")
            row.code, row.explanation = draft.code, draft.explanation
            row.external_assistance = row.external_assistance or draft.external_assistance
            row.draft_revision += 1
            return dict(revision=row.draft_revision,saved=True)

    def run(self, key: str, code: str) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            self._active(row)
            row.code, row.draft_revision = code, row.draft_revision + 1
            exercise = self._exercise(session,row)
        result = self.runner.execute(code,exercise.visible_case)
        with self.store.transaction(write=True) as session:
            session.add(TestRunRow(id=uuid4().hex,attempt_id=key,kind="run",code=code,created_at=stamp(self.clock()),result=result))
        return dict(run=result,attempt=self.attempt(key))

    def submit(self, key: str, payload: SubmitRequest) -> dict:
        now = self.clock()
        lease_started = stamp(now)
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            submission = session.get(SubmissionRow,payload.request_id)
            if submission:
                if submission.attempt_id != key or submission.code != payload.code or submission.explanation != payload.explanation or submission.external_assistance != payload.external_assistance:
                    raise Conflict("This request ID belongs to a different submission.")
                if submission.status == "completed":
                    return self._view(session,row)
                if submission.status == "processing":
                    if row.status != "grading":
                        raise Conflict("This saved submission is no longer the attempt's active grading request.")
                    if (now-parse(submission.created_at)).total_seconds() < self.runner.settings.suite_timeout + 20:
                        raise Conflict("This submission is still grading. Retry the saved request after the execution lease expires.")
                else:
                    self._active(row)
                submission.status, submission.created_at = "processing", lease_started
            else:
                self._active(row)
                submission = SubmissionRow(id=payload.request_id,attempt_id=key,created_at=lease_started,code=payload.code,explanation=payload.explanation,external_assistance=payload.external_assistance,status="processing")
                session.add(submission)
            row.code, row.explanation = payload.code, payload.explanation
            row.external_assistance = row.external_assistance or payload.external_assistance
            row.status = "grading"
            row.draft_revision += 1
            exercise = self._exercise(session,row)
        try:
            result = self.runner.grade(payload.code,exercise)
        except Exception:
            with self.store.transaction(write=True) as session:
                submission = session.get(SubmissionRow,payload.request_id)
                row = self._attempt(session,key)
                # A recovered lease may have completed while this older worker
                # was still returning. Only the current owner can change state.
                if submission.status == "processing" and submission.created_at == lease_started and row.status == "grading":
                    submission.status, row.status = "failed", "active"
            log.error(json.dumps({"event":"grading_failed","attempt_id":key}))
            raise
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            submission = session.get(SubmissionRow,payload.request_id)
            if submission.status == "completed":
                return self._view(session,row)
            if row.status != "grading" or submission.status != "processing" or submission.created_at != lease_started:
                raise Conflict("A newer recovery request owns grading. Reload the saved attempt to continue.")
            earlier = list(session.scalars(select(AttemptRow).join(ExerciseVersionRow,AttemptRow.exercise_version_id == ExerciseVersionRow.id).where(ExerciseVersionRow.exercise_id == exercise.id,AttemptRow.id != key)))
            exposed = any(a.status == "completed" or a.solution_seen or a.hint_count or a.external_assistance for a in earlier)
            independent = result["outcome"] == "Correct" and not (row.hint_count or row.solution_seen or row.external_assistance or exposed)
            result["independent"] = independent
            result["evidence_label"] = "Independent deterministic success" if independent else "Assisted / revised practice success" if result["outcome"] == "Correct" else "Deterministic gaps observed"
            failed = [c for c in result["categories"] if not c["passed"]]
            result["primary_issue"] = failed[0]["feedback"] if failed else "The SQL satisfies every tested result contract. Broader reasoning remains unassessed."
            if failed and all(c["reason"] in {"runtime","timeout","policy","limit"} for c in result["categories"]):
                result["primary_issue"] = "The query did not produce a usable result. Run the public fixture to inspect the execution error; other concepts remain unassessed."
            result["strongest_aspect"] = f"{result['passed']} of {result['total']} test categories satisfied." if failed else "Correct results across dirty-data and boundary fixtures."
            result["senior_review"] = exercise.senior_review
            result["mastery_updates"] = record_progress(session,row,exercise,result,independent,now)
            result["reasoning_evaluation"] = "Unavailable — SQL correctness was evaluated deterministically; explanation quality has not been scored."
            row.status, row.completed_at, row.result = "completed", stamp(now), result
            submission.status, submission.result = "completed", result
            session.get(SessionRow,row.session_id).status = "completed"
            session.get(SessionRow,row.session_id).completed_at = stamp(now)
            session.add(TestRunRow(id=uuid4().hex,attempt_id=key,kind="submit",code=payload.code,created_at=stamp(now),result=result))
            add_event(session,key,"attempt_completed",{"outcome":result["outcome"],"independent":independent},now)
        view = self.attempt(key)
        view["recommendation"] = self.recommendation()
        return view

    def hint(self, key: str) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            self._active(row)
            if row.mode == "interview":
                session.add(InteractionRow(id=uuid4().hex,attempt_id=key,kind="hint_denied",created_at=stamp(self.clock()),payload={"message":"Hints are disabled in strict SQL interview practice."}))
                return {"denied":True,"message":"Hints are disabled in strict SQL interview practice."}
            if row.hint_count >= 3:
                return {"level":3,"hint":self._exercise(session,row).hints[2]}
            row.hint_count += 1
            text = self._exercise(session,row).hints[row.hint_count-1]
            session.add(InteractionRow(id=uuid4().hex,attempt_id=key,kind="hint",created_at=stamp(self.clock()),payload={"level":row.hint_count,"message":text}))
            add_event(session,key,"hint_used",{"level":row.hint_count},self.clock())
            return {"level":row.hint_count,"hint":text}

    def solution(self, key: str) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            if row.status == "grading":
                raise Conflict("Wait for the saved submission to finish grading.")
            exercise = self._exercise(session,row)
            if row.status != "completed":
                row.solution_seen = True
                add_event(session,key,"solution_revealed",{"exercise_id":exercise.id},self.clock())
            else:
                # Keep completed evidence frozen. Exposure is recorded separately;
                # any repeated exercise is already excluded from new credit.
                session.add(InteractionRow(id=uuid4().hex,attempt_id=key,kind="solution_viewed",created_at=stamp(self.clock()),payload={"message":"Reference solution viewed after completion."}))
            return {"code":exercise.reference_solution,"explanation":exercise.solution_explanation}

    def clarify(self, key: str, question: str) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            self._active(row)
            exercise = self._exercise(session,row)
            rule = next((r for r in exercise.clarification_rules if any(k.casefold() in question.casefold() for k in r.keywords)),None)
            response = rule.response if rule else "The published contract contains the frozen requirements. Record any remaining assumption in your explanation; no extra acceptance rule will be added retroactively."
            view = dict(question=question,response=response,topic=rule.topic if rule else "Contract / assumption")
            session.add(InteractionRow(id=uuid4().hex,attempt_id=key,kind="clarification",created_at=stamp(self.clock()),payload=view))
            return view

    def pause(self, key: str) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            self._active(row)
            row.status = "paused"
            session.get(SessionRow,row.session_id).status = "paused"
        return self.attempt(key)

    def resume(self, key: str) -> dict:
        with self.store.transaction(write=True) as session:
            row = self._attempt(session,key)
            if row.status != "paused":
                raise Conflict("Only paused drafts can be resumed.")
            if session.scalar(select(AttemptRow.id).where(AttemptRow.status == "grading")):
                raise Conflict("Finish or retry the submission being graded before resuming a different draft.")
            for other in session.scalars(select(AttemptRow).where(AttemptRow.status == "active")):
                other.status = "paused"
                session.get(SessionRow,other.session_id).status = "paused"
            row.status = "active"
            session.get(SessionRow,row.session_id).status = "active"
        return self.attempt(key)

    def dashboard(self) -> dict:
        with self.store.transaction() as session:
            states, history = self._context(session)
            competencies = [dict(**c.model_dump(),**states[c.id]) for c in self.bank.competencies.values()]
            mistakes = [dict(id=m.id,competency_id=m.competency_id,category=m.category,**m.state) for m in session.scalars(select(MistakeRow))]
            active = self._current(session)
            due = [c for c in competencies if c["next_review"] and parse(c["next_review"]) <= self.clock()]
            return dict(competencies=competencies,mistakes=mistakes,reviews=due,history=list(reversed(history)),
                        recommendation=recommend(self.bank,states,history,self.clock()),
                        active_attempt=self._view(session,active) if active else None,
                        stats=dict(attempts=len(history),solved=len({h["exercise_id"] for h in history if h["result"]["outcome"]=="Correct"}),tested=sum(c["attempts"]>0 for c in competencies),total_competencies=len(competencies),open_mistakes=sum(m["status"]=="OPEN" for m in mistakes),due_reviews=len(due)))
