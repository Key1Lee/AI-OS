"""Canonical Skill discovery and Qwen-first execution boundary."""

from __future__ import annotations

import re
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .runtime import AIOSRuntime, RuntimeInput, RuntimeResult


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    task_profile: str
    instructions: str
    path: Path
    implicit_patterns: tuple[str, ...]


class SkillCatalog:
    def __init__(self, root: Path | None = None):
        self.root = (root or Path(__file__).resolve().parents[1]).resolve()
        catalog_path = self.root / "skills" / "catalog.toml"
        try:
            with catalog_path.open("rb") as stream:
                data = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise SkillError(f"Cannot read Skill catalog: {catalog_path}") from exc
        entries = data.get("skills")
        if not isinstance(entries, dict) or not entries:
            raise SkillError("Skill catalog is empty or invalid")
        self.skills: dict[str, SkillDefinition] = {}
        for name, entry in entries.items():
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or not isinstance(entry, dict):
                raise SkillError(f"Invalid Skill name: {name}")
            path = self.root / "skills" / name / "SKILL.md"
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise SkillError(f"Missing Skill instructions: {path}") from exc
            if not raw.startswith("---\n") or "\n---\n" not in raw[4:]:
                raise SkillError(f"Invalid Skill frontmatter: {path}")
            front, instructions = raw[4:].split("\n---\n", 1)
            fields: dict[str, str] = {}
            for line in front.splitlines():
                if ":" not in line:
                    raise SkillError(f"Invalid Skill frontmatter: {path}")
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip().strip('"\'')
            description = fields.get("description", "")
            if fields.get("name") != name or not description or len(description) > 180 or not instructions.strip():
                raise SkillError(f"Incomplete Skill definition: {path}")
            profile = entry.get("task_profile")
            patterns = entry.get("implicit_patterns", [])
            if not isinstance(profile, str) or not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
                raise SkillError(f"Invalid Skill routing: {name}")
            for pattern in patterns:
                try:
                    re.compile(pattern, re.IGNORECASE)
                except re.error as exc:
                    raise SkillError(f"Invalid Skill activation pattern: {name}") from exc
            self.skills[name] = SkillDefinition(name, description, profile, instructions.strip(), path, tuple(patterns))

    def resolve(self, request: str) -> SkillDefinition | None:
        if re.search(r"\b(?:do not|don't|without)\s+(?:use|run|invoke)\s+[$/][a-z0-9-]+\b", request, re.IGNORECASE):
            return None
        explicit = re.search(r"(?:^|\s)[$/]([a-z0-9]+(?:-[a-z0-9]+)*)(?=\s|$)", request.lower())
        if explicit:
            name = explicit.group(1)
            if name not in self.skills:
                raise SkillError(f"Unknown Skill command: {name}")
            return self.skills[name]
        matches = [skill for skill in self.skills.values() if any(re.search(pattern, request, re.IGNORECASE) for pattern in skill.implicit_patterns)]
        if len(matches) > 1:
            raise SkillError("Ambiguous Skill request; use one explicit $skill command")
        return matches[0] if matches else None

    def get(self, name: str) -> SkillDefinition:
        try:
            return self.skills[name.removeprefix("$").removeprefix("/")]
        except KeyError as exc:
            raise SkillError(f"Unknown Skill: {name}") from exc


@dataclass(frozen=True)
class SkillExecution:
    skill: SkillDefinition | None
    result: RuntimeResult
    session_id: str | None = None


class SkillRunner:
    def __init__(self, runtime: AIOSRuntime | None = None, catalog: SkillCatalog | None = None):
        self.runtime = runtime or AIOSRuntime()
        self.catalog = catalog or SkillCatalog(self.runtime.resolver.root)

    def run(
        self,
        request: str,
        *,
        project: str | None = None,
        skill: str | None = None,
        overrides: Mapping[str, Any] | None = None,
        authorized_tools: frozenset[str] = frozenset(),
        session_id: str | None = None,
        answer: str | None = None,
        question: str | None = None,
        answer_status: str = "unclassified",
    ) -> SkillExecution:
        definition = self.catalog.get(skill) if skill else self.catalog.resolve(request)
        instructions = definition.instructions if definition else ""
        context: tuple[str, ...] = ()
        model_prompt = request
        if definition and definition.name == "grill-me":
            from .skill_state import SkillInterviewStore

            store = SkillInterviewStore(self.catalog.root)
            if session_id is None:
                if answer is not None:
                    raise SkillError("An answer requires an existing interview session")
                topic = re.sub(r"(?:^|\s)[$/]grill-me(?=\s|$)", "", request, flags=re.IGNORECASE).strip() or "topic pending"
                session_id = store.start(project, topic)["id"]
                if topic == "topic pending":
                    model_prompt = "I want to start a discovery interview but have not provided a topic. Ask only what topic or decision I want to explore."
            if answer is not None:
                if not question:
                    raise SkillError("The question being answered is required")
                store.append(project, session_id, question, answer, answer_status)
            state = store.get(project, session_id)
            context = ("Saved interview checkpoint (recent entries): " + str(state["answers"][-6:]),)
        elif definition and definition.name == "audit":
            from .skill_audit import audit

            report = audit(self.catalog.root, project=project, live=True)
            context = ("Deterministic AI-OS audit evidence: " + json.dumps(report, ensure_ascii=False),)
        resolved = self.runtime.resolve(project=project, task=definition.task_profile if definition else None, overrides=overrides or {})
        if resolved.get("runtime", "provider") == "qwen_local":
            from .source_registry import SourceRegistry

            routes = SourceRegistry(self.catalog.root).search(request, project=project)
            if routes:
                context += ("Relevant registered source routes (metadata only; access status is explicit): " + json.dumps(routes, ensure_ascii=False),)
                instructions = (instructions + "\nUse registered routes only for their stated purpose and verified access status. Do not infer source contents from route metadata.").strip()
        result = self.runtime.run(RuntimeInput(
            prompt=model_prompt,
            project=project,
            task=definition.task_profile if definition else None,
            system_instructions=instructions,
            retrieved_context=context,
            authorized_tools=authorized_tools,
            overrides=overrides or {},
        ))
        return SkillExecution(definition, result, session_id)
