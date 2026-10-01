"""Bounded, evidence-labelled AI-OS Skill and runtime audit checks."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .context_policy import ContextLimitError, choose_context
from .local_runtime import LocalRuntimeError, _read_gguf_metadata, discover_gguf, inspect_local
from .runtime_config import RuntimeConfigError, RuntimeConfigResolver
from .skills import SkillCatalog, SkillError
from .source_registry import SourceRegistry, SourceRegistryError


@dataclass(frozen=True)
class AuditFinding:
    id: str
    classification: str
    message: str
    evidence: str


def _files(folder: Path) -> dict[str, bytes]:
    allowed = {"SKILL.md", "references", "scripts", "assets", "agents"}
    if not folder.is_dir():
        return {}
    return {str(path.relative_to(folder)): path.read_bytes() for path in folder.rglob("*") if path.is_file() and path.relative_to(folder).parts[0] in allowed}


def _hardcoded_model_paths(root: Path, project: str | None) -> list[str]:
    projects = [root / "projects" / project] if project else [item for item in (root / "projects").iterdir() if item.is_dir()]
    matches = []
    pattern = re.compile(r"(?:/Users/[^\s'\"]+|/home/[^\s'\"]+|[A-Za-z]:\\[^\s'\"]+)\.gguf", re.IGNORECASE)
    skip = {".venv", "venv", "node_modules", "__pycache__", ".git", "state", "data"}
    for directory in projects:
        for current, folders, files in os.walk(directory):
            folders[:] = [folder for folder in folders if folder not in skip]
            for name in files:
                path = Path(current) / name
                if path.suffix not in {".py", ".js", ".mjs", ".sh", ".command"} or path.stat().st_size > 2_000_000:
                    continue
                try:
                    if pattern.search(path.read_text(encoding="utf-8")):
                        matches.append(str(path.relative_to(root)))
                except (OSError, UnicodeDecodeError):
                    continue
    return matches


def audit(root: Path, *, project: str | None = None, live: bool = False) -> dict:
    root = root.resolve()
    findings: list[AuditFinding] = []
    passed: list[str] = []

    def add(identifier: str, classification: str, message: str, evidence: str) -> None:
        findings.append(AuditFinding(identifier, classification, message, evidence))

    try:
        catalog = SkillCatalog(root)
        passed.append("AUD-001 canonical Skill catalog loads")
        for name in catalog.skills:
            canonical = _files(root / "skills" / name)
            for mirror in (root / ".agents" / "skills", root / ".claude" / "skills"):
                if _files(mirror / name) != canonical:
                    add("AUD-002", "confirmed defect", "Skill mirror differs from canonical instructions", str(mirror / name))
        if not any(item.id == "AUD-002" for item in findings):
            passed.append("AUD-002 Codex and Claude mirrors match")
    except SkillError as exc:
        catalog = None
        add("AUD-001", "confirmed defect", "Canonical Skill catalog cannot load", str(exc))

    try:
        resolver = RuntimeConfigResolver(root)
    except RuntimeConfigError as exc:
        add("AUD-003", "confirmed defect", "Global configuration cannot load", str(exc))
        return {"scope": project or "global", "live": live, "passed": passed, "findings": [asdict(item) for item in findings], "coverage_limit": "Global configuration failed to load; remaining checks were skipped"}
    try:
        config = resolver.resolve(project=project)
        if config.get("runtime", "provider") == "qwen_local" and config.source("runtime", "provider") in {"global", f"project:{project}"}:
            passed.append("AUD-003 configuration inheritance resolves")
        else:
            passed.append("AUD-003 configuration inheritance resolves with explicit provider")
    except RuntimeConfigError as exc:
        add("AUD-003", "confirmed defect", "Configuration inheritance fails", str(exc))
        config = None

    if config is not None:
        try:
            none = resolver.resolve(project=project, run={"reasoning": "none"})
            xhigh = resolver.resolve(project=project, run={"reasoning": "xhigh"})
            if none.get("tools", "least_privilege") != xhigh.get("tools", "least_privilege") or none.get("tools", "requested") != xhigh.get("tools", "requested"):
                add("AUD-004", "confirmed defect", "Reasoning changes tool permissions", "resolved none/xhigh tool policies differ")
            else:
                passed.append("AUD-004 reasoning and tool policy remain separate")
        except RuntimeConfigError as exc:
            add("AUD-004", "confirmed defect", "Reasoning permission invariant could not resolve", str(exc))
        if config.get("runtime", "provider") == "qwen_local":
            try:
                gguf_path = discover_gguf(config)
                gguf = _read_gguf_metadata(gguf_path)
                if gguf.get("general.architecture") != "qwen3":
                    raise LocalRuntimeError("GGUF architecture is not Qwen3")
                passed.append("AUD-005 Qwen GGUF identity and header read")
            except LocalRuntimeError as exc:
                add("AUD-005", "confirmed defect", "Configured Qwen model is missing or invalid", str(exc))
            if live:
                try:
                    report = inspect_local(config, probe_budget=False)
                    passed.append("AUD-006 live Qwen endpoint and model identity verified")
                    if catalog:
                        for skill in catalog.skills.values():
                            skill_config = resolver.resolve(project=project, task=skill.task_profile)
                            try:
                                choose_context(skill_config, report, prompt_text="audit", reasoning_budget=0, output_tokens=128)
                            except ContextLimitError:
                                add("AUD-007", "intentional configuration difference", f"Skill {skill.name} requests a tier above the active runtime", skill.task_profile)
                except LocalRuntimeError as exc:
                    category = "confirmed defect" if "differs" in str(exc) or "not a Qwen3" in str(exc) else "verification gap"
                    add("AUD-006", category, "Local Qwen health or identity could not be verified", str(exc))
            else:
                add("AUD-006", "verification gap", "Live Qwen endpoint was not probed", "run audit with --live")
        else:
            add("AUD-005", "intentional configuration difference", "Selected provider is not local Qwen", str(config.get("runtime", "provider")))

        trace_path = Path(os.getenv("AIOS_TRACE_FILE", str(Path.home() / ".config" / "py-dev" / "run-traces.jsonl"))).expanduser()
        if not config.get("external_escalation", "enabled") and trace_path.is_file():
            for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), 1):
                try:
                    trace = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if trace.get("escalation_decision", "").startswith("verification_failed_to_") and trace.get("external_escalation_enabled") is False:
                    add("AUD-008", "confirmed defect", "Trace records external escalation while run policy disabled it", f"{trace_path}:{line_number}")
                    break
        if not any(item.id == "AUD-008" for item in findings):
            passed.append("AUD-008 no conflicting escalation trace found")

    try:
        issues = SourceRegistry(root).validate(project)
        for issue in issues:
            add("AUD-009", "confirmed defect", f"Stale source route: {issue['issue']}", issue["id"])
        if not issues:
            passed.append("AUD-009 registered local routes resolve and freshness is current")
    except SourceRegistryError as exc:
        add("AUD-009", "confirmed defect", "Source registry cannot be validated", str(exc))

    paths = _hardcoded_model_paths(root, project)
    for path in paths:
        add("AUD-010", "confirmed defect", "Project code hardcodes a GGUF path", path)
    if not paths:
        passed.append("AUD-010 no hardcoded GGUF path found in sampled project code")

    return {
        "scope": project or "global", "live": live, "passed": passed,
        "findings": [asdict(item) for item in findings],
        "coverage_limit": "Bounded static and local checks only; project workflow execution, cloud/Codex/Claude invocation, and all permission paths were not exhaustively verified",
    }
