"""Application-owned durable Skill state; model context is never the store."""

from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


class SkillStateError(ValueError):
    pass


def _scope_dir(root: Path, project: str | None) -> Path:
    if project is None:
        return Path(os.getenv("AIOS_DATA_DIR", str(Path.home() / ".local" / "share" / "ai-os" / "state"))).expanduser().resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", project):
        raise SkillStateError("Invalid project name")
    project_dir = root / "projects" / project
    if not project_dir.is_dir() or project_dir.is_symlink():
        raise SkillStateError(f"Unknown or unsafe project: {project}")
    return project_dir / "state"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".aios-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            os.fchmod(output.fileno(), 0o600)
            json.dump(value, output, indent=2, ensure_ascii=False, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillStateError(f"Cannot read Skill state: {path}") from exc
    if not isinstance(value, dict):
        raise SkillStateError(f"Invalid Skill state: {path}")
    return value


def save_context(root: Path, *, project: str | None, facts: Mapping[str, Any], confirmed: bool, source: str = "user") -> Path:
    if not confirmed:
        raise SkillStateError("Only confirmed context may be saved")
    if not isinstance(facts, Mapping) or not facts or any(not isinstance(k, str) or not k.strip() for k in facts):
        raise SkillStateError("Context facts must be a nonempty object")
    def has_secret_field(value: Any) -> bool:
        return isinstance(value, Mapping) and any(
            re.search(r"(?:api[_-]?key|password|secret|credential|access[_-]?token)", str(key), re.IGNORECASE)
            or has_secret_field(item)
            for key, item in value.items()
        )
    if has_secret_field(facts):
        raise SkillStateError("Credentials and secret fields cannot be saved as context")
    path = _scope_dir(root, project) / "context.json"
    existing = _read_json(path, {"facts": {}, "history": []})
    if not isinstance(existing.get("facts"), dict) or not isinstance(existing.get("history"), list):
        raise SkillStateError("Invalid existing context record")
    previous = dict(existing["facts"])
    changed = {key: value for key, value in facts.items() if previous.get(key) != value}
    if not changed:
        return path
    previous.update(changed)
    history = [*existing["history"], {"at": datetime.now(timezone.utc).isoformat(), "source": source, "fields": sorted(changed)}]
    _atomic_json(path, {"facts": previous, "history": history})
    return path


class SkillInterviewStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _path(self, project: str | None, session_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", session_id):
            raise SkillStateError("Invalid interview session ID")
        return _scope_dir(self.root, project) / "interviews" / f"{session_id}.json"

    def start(self, project: str | None, topic: str) -> dict[str, Any]:
        if not topic.strip():
            raise SkillStateError("Interview topic is required")
        session_id = uuid.uuid4().hex
        record = {"id": session_id, "project": project, "topic": topic.strip(), "status": "active", "answers": [], "started_at": datetime.now(timezone.utc).isoformat()}
        _atomic_json(self._path(project, session_id), record)
        return record

    def get(self, project: str | None, session_id: str) -> dict[str, Any]:
        path = self._path(project, session_id)
        record = _read_json(path, {})
        if record.get("id") != session_id or record.get("project") != project or not isinstance(record.get("answers"), list):
            raise SkillStateError(f"Interview session not found: {session_id}")
        return record

    def append(self, project: str | None, session_id: str, question: str, answer: str, status: str = "unclassified") -> dict[str, Any]:
        if status not in {"unclassified", "confirmed", "hypothesis", "idea"} or not question.strip() or not answer.strip():
            raise SkillStateError("Interview answer, question, or evidence status is invalid")
        record = self.get(project, session_id)
        if record.get("status") != "active":
            raise SkillStateError("Interview is not active")
        record["answers"].append({"question": question.strip(), "answer": answer.strip(), "evidence_status": status, "at": datetime.now(timezone.utc).isoformat()})
        _atomic_json(self._path(project, session_id), record)
        return record

    def set_status(self, project: str | None, session_id: str, status: str) -> dict[str, Any]:
        if status not in {"active", "paused", "complete"}:
            raise SkillStateError("Invalid interview status")
        record = self.get(project, session_id)
        record["status"] = status
        _atomic_json(self._path(project, session_id), record)
        return record
