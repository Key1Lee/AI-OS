"""Central AI-OS configuration inheritance with per-run overrides."""

from __future__ import annotations

import re
import tomllib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_PROJECT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_PROVIDERS = {"qwen_local", "openai", "claude"}
_TIERS = ("small", "standard", "large", "very_large")
_REASONING = ("none", "low", "medium", "high", "xhigh")


class RuntimeConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedConfig:
    values: Mapping[str, Any]
    sources: Mapping[str, str]
    layers: tuple[str, ...]

    def get(self, *path: str) -> Any:
        value: Any = self.values
        for part in path:
            value = value[part]
        return value

    def source(self, *path: str) -> str:
        return self.sources[".".join(path)]


def _merge(base: dict[str, Any], incoming: Mapping[str, Any], source: str, provenance: dict[str, str], prefix: str = "") -> None:
    for key, value in incoming.items():
        if not isinstance(key, str):
            raise RuntimeConfigError("Configuration keys must be strings")
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value, source, provenance, path)
        else:
            base[key] = deepcopy(value)
            if isinstance(value, dict):
                _mark_leaves(value, source, provenance, path)
            else:
                provenance[path] = source


def _mark_leaves(value: Mapping[str, Any], source: str, provenance: dict[str, str], prefix: str) -> None:
    for key, item in value.items():
        path = f"{prefix}.{key}"
        if isinstance(item, dict):
            _mark_leaves(item, source, provenance, path)
        else:
            provenance[path] = source


def _load(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeConfigError(f"Cannot read configuration: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeConfigError(f"Configuration must be a table: {path}")
    return value


def _task_overlay(task: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(task))
    for key in ("provider", "model"):
        if key in result:
            result.setdefault("runtime", {})[key] = result.pop(key)
    if "reasoning" in result and isinstance(result["reasoning"], str):
        result["reasoning"] = {"default": result["reasoning"]}
    if "context" in result and isinstance(result["context"], str):
        result["context"] = {"tier": result["context"]}
    return result


def _run_overlay(run: Mapping[str, Any]) -> dict[str, Any]:
    keys = {"provider", "model", "reasoning", "context", "max_output", "tools", "verification", "model_path", "endpoint", "gpu_layers"}
    if set(run) - keys:
        raise RuntimeConfigError("Unknown per-run override")
    result: dict[str, Any] = {}
    mapping = {
        "provider": ("runtime", "provider"), "model": ("runtime", "model"),
        "reasoning": ("reasoning", "default"), "context": ("context", "tier"),
        "max_output": ("generation", "max_output_tokens"),
        "tools": ("tools", "requested"), "verification": ("verification", "enabled"),
        "model_path": ("runtime", "model_path"), "endpoint": ("runtime", "endpoint"),
        "gpu_layers": ("runtime", "gpu_layers"),
    }
    for key, value in run.items():
        section, field = mapping[key]
        result.setdefault(section, {})[field] = value
    return result


class RuntimeConfigResolver:
    def __init__(self, root: Path | None = None):
        self.root = (root or Path(__file__).resolve().parents[1]).resolve()
        self.global_defaults = _load(self.root / "config" / "defaults.toml")

    def _project(self, project: str | None) -> dict[str, Any]:
        if project is None:
            return {}
        if not _PROJECT_NAME.fullmatch(project):
            raise RuntimeConfigError("Invalid project name")
        project_dir = self.root / "projects" / project
        if not project_dir.is_dir():
            raise RuntimeConfigError(f"Unknown project: {project}")
        path = project_dir / "aios.toml"
        if not path.exists():
            return {}
        data = _load(path)
        if data.get("inherits", ["global"]) != ["global"]:
            raise RuntimeConfigError("Project must inherit global defaults")
        if data.get("project", {}).get("name", project) != project:
            raise RuntimeConfigError("Project configuration name does not match directory")
        return data

    def resolve(self, *, project: str | None = None, task: str | None = None, run: Mapping[str, Any] | None = None) -> ResolvedConfig:
        project_data = self._project(project)
        run_data = _run_overlay(run or {})
        global_tasks = self.global_defaults.get("task_profiles", {})
        project_tasks = project_data.get("task_profiles", {})
        task_data: dict[str, Any] = {}
        if task:
            if task not in global_tasks and task not in project_tasks:
                raise RuntimeConfigError(f"Unknown task profile: {task}")
            _merge(task_data, _task_overlay(global_tasks.get(task, {})), "global task", {})
            _merge(task_data, _task_overlay(project_tasks.get(task, {})), "project task", {})
        provider = run_data.get("runtime", {}).get("provider", task_data.get("runtime", {}).get("provider", project_data.get("runtime", {}).get("provider", self.global_defaults.get("runtime", {}).get("provider"))))
        if provider not in _PROVIDERS:
            raise RuntimeConfigError("Unknown provider")
        provider_data = _load(self.root / "config" / "providers" / f"{provider}.toml")
        if provider_data.get("provider", {}).get("name") != provider:
            raise RuntimeConfigError("Provider profile name mismatch")
        values: dict[str, Any] = {}
        sources: dict[str, str] = {}
        layers = []
        for label, layer in (
            ("global", self.global_defaults),
            (f"provider:{provider}", provider_data),
            (f"project:{project or 'none'}", {key: value for key, value in project_data.items() if key not in {"task_profiles", "inherits"}}),
            (f"task:{task or 'none'}", task_data),
            ("run", run_data),
        ):
            _merge(values, layer, label, sources)
            layers.append(label)
        self._validate(values)
        return ResolvedConfig(values, sources, tuple(layers))

    @staticmethod
    def _validate(value: Mapping[str, Any]) -> None:
        if value["runtime"]["provider"] not in _PROVIDERS:
            raise RuntimeConfigError("Invalid provider")
        if value["reasoning"]["default"] not in _REASONING:
            raise RuntimeConfigError("Invalid reasoning profile")
        if value["context"].get("tier") not in (*_TIERS, None):
            raise RuntimeConfigError("Invalid context tier")
        tiers = value["context"]["tiers"]
        if tuple(tiers) != _TIERS or any(not isinstance(tiers[name], int) or tiers[name] <= 0 for name in _TIERS):
            raise RuntimeConfigError("Invalid context tiers")
        if list(tiers.values()) != sorted(tiers.values()):
            raise RuntimeConfigError("Context tiers must increase")
        for key in ("default_tokens", "maximum_tokens", "safety_margin_tokens"):
            if not isinstance(value["context"][key], int) or value["context"][key] < 0:
                raise RuntimeConfigError("Invalid context policy")
        if value["context"]["maximum_tokens"] < value["context"]["default_tokens"]:
            raise RuntimeConfigError("Context maximum below default")
        if not isinstance(value["generation"]["max_output_tokens"], int) or value["generation"]["max_output_tokens"] <= 0:
            raise RuntimeConfigError("Invalid output limit")
        for name in _REASONING:
            profile = value["reasoning"]["profiles"][name]
            if set(profile) != {"thinking", "budget_tokens"}:
                raise RuntimeConfigError("Reasoning profiles may only configure thinking and budget")
            if not isinstance(profile["thinking"], bool) or not isinstance(profile["budget_tokens"], int) or profile["budget_tokens"] < 0:
                raise RuntimeConfigError("Invalid reasoning mapping")
        if not isinstance(value["verification"]["enabled"], bool) or not isinstance(value["external_escalation"]["enabled"], bool):
            raise RuntimeConfigError("Invalid policy boolean")
        if not isinstance(value["tools"]["requested"], list) or any(not isinstance(name, str) for name in value["tools"]["requested"]):
            raise RuntimeConfigError("Invalid tool request")
        if value["tools"]["least_privilege"] is not True:
            raise RuntimeConfigError("Least-privilege tool policy cannot be disabled")
