from __future__ import annotations

import json
from pathlib import Path

from .models import Criterion, Question


CONTENT_PATH = Path(__file__).with_name("content") / "questions.json"


def load_questions(path: Path = CONTENT_PATH) -> tuple[Question, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    questions: list[Question] = []
    seen: set[str] = set()
    for item in raw:
        if item["id"] in seen:
            raise ValueError(f"Duplicate question id: {item['id']}")
        seen.add(item["id"])
        criteria = tuple(
            Criterion(
                id=c["id"],
                description=c["description"],
                any_of=tuple(term.lower() for term in c["any_of"]),
                weight=float(c.get("weight", 1.0)),
            )
            for c in item["criteria"]
        )
        if not criteria:
            raise ValueError(f"Question {item['id']} has no rubric criteria")
        if len({criterion.id for criterion in criteria}) != len(criteria):
            raise ValueError(f"Question {item['id']} has duplicate rubric criterion ids")
        questions.append(
            Question(
                id=item["id"],
                competency=item["competency"],
                family=item["family"],
                difficulty=int(item["difficulty"]),
                prompt=item["prompt"],
                criteria=criteria,
                hints=tuple(item.get("hints", [])),
                followups=dict(item.get("followups", {})),
                source=item.get("source", "curated"),
            )
        )
    return tuple(questions)


def competency_names(questions: tuple[Question, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(q.competency for q in questions))
