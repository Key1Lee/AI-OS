from __future__ import annotations

import json
import re
from pathlib import Path

from app.assessment import CANONICAL_COMPETENCIES
from app.database import Database, utc_now
from app.models import (
    ASSISTANCE_RANK,
    AssistanceLevel,
    CompetencyState,
    Correctness,
    EvidenceRating,
    InterviewerDecision,
)


class EvidenceSyncError(RuntimeError):
    pass


class EvidenceSynchronizer:
    def __init__(self, project_root: Path, database: Database):
        self.project_root = project_root
        self.database = database
        self.assessment_dir = project_root / "assessment"

    def synchronize(
        self,
        session: dict,
        decision: InterviewerDecision,
        turns: list[dict],
    ) -> Path:
        if not decision.module_complete:
            raise EvidenceSyncError("Only completed modules can synchronize evidence")
        if self.database.sync_exists(session["id"], session["module"]):
            return self._artifact_path(session)

        artifact_path = self._artifact_path(session)
        marker = self._marker(session)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_content = self._artifact(session, decision, turns, marker)
        self._write_atomic(artifact_path, artifact_content)

        applied_updates = self._apply_competency_updates(session, decision, artifact_path)
        weakness_ids = self._apply_weakness_updates(session, decision, artifact_path)
        self._append_history(session, decision, artifact_path, marker, applied_updates, weakness_ids)
        self.database.record_sync(session["id"], session["module"], str(artifact_path))
        return artifact_path

    def _apply_competency_updates(
        self, session: dict, decision: InterviewerDecision, artifact_path: Path
    ) -> list[tuple[str, str]]:
        independent = ASSISTANCE_RANK[AssistanceLevel(session["assistance_level"])] <= ASSISTANCE_RANK[
            AssistanceLevel.CLARIFICATION
        ]
        strong_enough = (
            decision.answer_correctness == Correctness.CORRECT
            and decision.reasoning_quality in {EvidenceRating.STRONG, EvidenceRating.EXCEPTIONAL}
            and decision.technical_depth in {
                EvidenceRating.ACCEPTABLE,
                EvidenceRating.STRONG,
                EvidenceRating.EXCEPTIONAL,
            }
        )
        applied: list[tuple[str, str]] = []
        for update in decision.record_updates.competency_updates:
            if update.competency not in CANONICAL_COMPETENCIES:
                continue
            proposed = update.proposed_state
            if proposed == CompetencyState.DEMONSTRATED and not (
                independent and update.independent and strong_enough and int(session["difficulty"]) >= 3
            ):
                proposed = CompetencyState.DEVELOPING
            if proposed == CompetencyState.UNTESTED:
                continue
            evidence = f"{session['assessment_id']} {session['module']} — {artifact_path.name}"
            level = f"Level {session['difficulty']}" if proposed == CompetencyState.DEMONSTRATED else ""
            self.database.update_competency(update.competency, proposed.value, level, evidence)
            self._update_competency_markdown(update.competency, proposed.value, level, evidence)
            applied.append((update.competency, proposed.value))
        return applied

    def _apply_weakness_updates(
        self, session: dict, decision: InterviewerDecision, artifact_path: Path
    ) -> list[str]:
        weakness_ids: list[str] = []
        for update in decision.record_updates.weakness_updates:
            if update.competency not in CANONICAL_COMPETENCIES:
                continue
            weakness_id = self.database.next_weakness_id()
            self.database.add_weakness(
                weakness_id,
                session["id"],
                update.competency,
                update.classification,
                update.evidence,
                update.remediation,
            )
            self._append_weakness_markdown(weakness_id, session, update, artifact_path)
            weakness_ids.append(weakness_id)
        return weakness_ids

    def _update_competency_markdown(
        self, competency: str, state: str, level: str, evidence: str
    ) -> None:
        path = self.assessment_dir / "competency-map.md"
        content = path.read_text(encoding="utf-8")
        prefix = f"| {competency} |"
        replacement = f"| {competency} | {state} | {level or '—'} | {self._table_text(evidence)} |"
        lines = content.splitlines()
        replaced = False
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                lines[index] = replacement
                replaced = True
                break
        if not replaced:
            raise EvidenceSyncError(f"Canonical competency row not found: {competency}")
        self._write_atomic(path, "\n".join(lines) + "\n")

    def _append_history(
        self,
        session: dict,
        decision: InterviewerDecision,
        artifact_path: Path,
        marker: str,
        competency_updates: list[tuple[str, str]],
        weakness_ids: list[str],
    ) -> None:
        path = self.assessment_dir / "history.md"
        content = path.read_text(encoding="utf-8")
        if marker in content:
            return
        assistance = session["assistance_level"]
        updates = ", ".join(f"{name}: {state}" for name, state in competency_updates) or "none"
        weaknesses = ", ".join(weakness_ids) or "none"
        addition = (
            f"\n{marker}\n"
            f"## Application module record — {session['assessment_id']} — {utc_now()}\n\n"
            f"- Session: `{session['id']}`.\n"
            f"- Module: {session['module']}.\n"
            f"- Lifecycle: MODULE_COMPLETE.\n"
            f"- Difficulty: Level {session['difficulty']}.\n"
            f"- Assistance: {assistance}; hints used: {session['hints_used']}.\n"
            f"- Competency updates: {updates}.\n"
            f"- Weakness records: {weaknesses}.\n"
            f"- Evidence artifact: [session evidence](session-evidence/{artifact_path.name}).\n"
            "- Mastery impact: none automatically awarded; mastery remains subject to the project's "
            "independent, scoped, verified-evidence rules.\n"
        )
        self._write_atomic(path, content.rstrip() + "\n" + addition)

    def _append_weakness_markdown(self, weakness_id, session, update, artifact_path: Path) -> None:
        path = self.assessment_dir / "weaknesses.md"
        content = path.read_text(encoding="utf-8")
        content = content.replace(
            "No weaknesses have been established because no assessment has been conducted.\n",
            "Evidence-backed weaknesses, when present, are recorded below.\n",
            1,
        )
        marker = f"<!-- app-weakness:{weakness_id} -->"
        if marker in content:
            return
        addition = (
            f"\n{marker}\n"
            f"## {weakness_id} — {self._heading(update.competency)}\n\n"
            f"- Status: OPEN.\n"
            f"- Source: {session['assessment_id']}, {session['module']}; "
            f"[evidence](session-evidence/{artifact_path.name}).\n"
            f"- Classification: {update.classification}.\n"
            f"- Observed evidence: {self._plain(update.evidence)}\n"
            f"- Remediation: {self._plain(update.remediation)}\n"
            "- Retest: materially different scenario required; not yet scheduled.\n"
        )
        self._write_atomic(path, content.rstrip() + "\n" + addition)

    def _artifact(self, session, decision, turns, marker: str) -> str:
        transcript = []
        for turn in turns:
            transcript.append(
                "\n".join(
                    (
                        f"### Turn {turn['turn_number']}",
                        "",
                        f"**Question**\n\n{turn['question']}",
                        "",
                        f"**Candidate submission ({turn['input_kind']})**",
                        "",
                        "```text",
                        self._fence_text(turn["candidate_input"]),
                        "```",
                        "",
                        f"**Interviewer response**\n\n{turn['interviewer_message']}",
                    )
                )
            )
        strengths = "\n".join(f"- {self._plain(item)}" for item in decision.strengths_detected) or "- None recorded."
        weaknesses = "\n".join(f"- {self._plain(item)}" for item in decision.weaknesses_detected) or "- None recorded."
        return (
            f"{marker}\n"
            f"# {session['assessment_id']} — {session['module']}\n\n"
            f"Session `{session['id']}` completed this module at Level {session['difficulty']}.\n\n"
            f"- Assistance: {session['assistance_level']}\n"
            f"- Hints used: {session['hints_used']}\n"
            f"- Correctness: {decision.answer_correctness.value}\n"
            f"- Reasoning quality: {decision.reasoning_quality.value}\n"
            f"- Technical depth: {decision.technical_depth.value}\n"
            f"- Confidence of evaluation: {decision.confidence:.2f}\n\n"
            "## Evidence observed\n\n"
            + ("\n".join(f"- {self._plain(item)}" for item in decision.evidence_observed) or "- None recorded.")
            + "\n\n## Independent strengths\n\n"
            + strengths
            + "\n\n## Weaknesses\n\n"
            + weaknesses
            + "\n\n## Transcript\n\n"
            + "\n\n".join(transcript)
            + "\n"
        )

    def _artifact_path(self, session: dict) -> Path:
        safe_session = re.sub(r"[^A-Za-z0-9_-]", "_", session["id"])
        return self.assessment_dir / "session-evidence" / f"{session['assessment_id']}-{safe_session}.md"

    @staticmethod
    def _marker(session: dict) -> str:
        safe_module = re.sub(r"[^A-Za-z0-9]+", "-", session["module"]).strip("-").lower()
        return f"<!-- app-sync:{session['id']}:{safe_module} -->"

    @staticmethod
    def _write_atomic(path: Path, content: str) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _plain(value: str) -> str:
        collapsed = " ".join(value.replace("\x00", "").split())
        return (
            collapsed.replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("[", "\\[")
            .replace("]", "\\]")
        )

    @classmethod
    def _table_text(cls, value: str) -> str:
        return cls._plain(value).replace("|", "\\|")

    @classmethod
    def _heading(cls, value: str) -> str:
        return cls._plain(value).replace("#", "")

    @staticmethod
    def _fence_text(value: str) -> str:
        return value.replace("```", "` ` `")
