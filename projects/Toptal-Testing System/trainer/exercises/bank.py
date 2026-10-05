from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import yaml

from trainer.schemas.models import Competency, Exercise

log = logging.getLogger(__name__)


def content_hash(exercise: Exercise) -> str:
    raw = json.dumps(exercise.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class Bank:
    def __init__(self, root: Path):
        curriculum = yaml.safe_load((root / "curriculum/competencies.yaml").read_text())
        self.competencies = {c.id: c for c in map(Competency.model_validate, curriculum["competencies"])}
        if len(self.competencies) != len(curriculum["competencies"]):
            raise ValueError("Duplicate competency ID")
        self._validate_graph()
        self.exercises: dict[str, Exercise] = {}
        for path in sorted((root / "exercise_bank/sql").glob("*.json")):
            try:
                exercise = Exercise.model_validate_json(path.read_text())
                if not set(exercise.competencies + exercise.prerequisites).issubset(self.competencies):
                    raise ValueError("Unknown competency reference")
                if exercise.id in self.exercises:
                    raise ValueError("Duplicate exercise ID")
                self.exercises[exercise.id] = exercise
            except Exception:
                log.error(json.dumps({"event": "malformed_exercise", "file": path.name}))
                raise
        if not self.exercises:
            raise ValueError("Exercise bank is empty")
        self.weights = yaml.safe_load((root / "curriculum/selection.yaml").read_text())

    def _validate_graph(self):
        visited: set[str] = set()
        active: set[str] = set()

        def visit(key: str):
            if key in active:
                raise ValueError("Competency prerequisite cycle")
            if key in visited:
                return
            active.add(key)
            competency = self.competencies[key]
            for other in competency.related + competency.prerequisites:
                if other not in self.competencies:
                    raise ValueError("Unknown competency relationship")
            for prerequisite in competency.prerequisites:
                visit(prerequisite)
            active.remove(key)
            visited.add(key)

        for key in self.competencies:
            visit(key)
