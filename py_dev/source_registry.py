"""Small source routes with explicit authority and verification state."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .skill_state import SkillStateError, _atomic_json, _read_json, _scope_dir


class SourceRegistryError(SkillStateError):
    pass


class SourceRegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def path(self, project: str | None) -> Path:
        return _scope_dir(self.root, project) / "sources.json"

    def list(self, project: str | None) -> list[dict[str, Any]]:
        data = _read_json(self.path(project), {"sources": []})
        sources = data.get("sources")
        if not isinstance(sources, list) or any(not isinstance(item, dict) for item in sources):
            raise SourceRegistryError("Invalid source registry")
        return sources

    def register(
        self,
        target: str,
        purpose: str,
        *,
        project: str | None = None,
        source_id: str | None = None,
        authority: str = "original",
        freshness_days: int | None = None,
        related_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        if not target.strip() or not purpose.strip() or not authority.strip():
            raise SourceRegistryError("Target, purpose, and authority are required")
        if freshness_days is not None and (not isinstance(freshness_days, int) or freshness_days < 0):
            raise SourceRegistryError("Freshness days must be nonnegative")
        parsed = urlsplit(target)
        if parsed.scheme in {"http", "https"}:
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise SourceRegistryError("Source URLs cannot contain credentials, query strings, or fragments")
            normalized = target
            mechanism, verified = "url", False
        elif parsed.scheme:
            raise SourceRegistryError("Unsupported source URL scheme")
        else:
            path = Path(target).expanduser()
            if not path.is_absolute():
                path = (_scope_dir(self.root, project).parent / path)
            path = path.resolve()
            if not path.exists():
                raise SourceRegistryError(f"Local source does not resolve: {path}")
            normalized = str(path)
            mechanism, verified = "local_path", True
        if source_id is None:
            source_id = re.sub(r"[^a-z0-9]+", "-", Path(parsed.path if parsed.scheme else normalized).stem.lower()).strip("-")[:48] or "source"
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id):
            raise SourceRegistryError("Invalid route ID")
        sources = self.list(project)
        known_ids = {current.get("id") for current in sources}
        if any(item not in known_ids or item == source_id for item in related_ids):
            raise SourceRegistryError("Related route IDs must already exist and cannot refer to the new route")
        for current in sources:
            if current.get("id") == source_id and current.get("target") != normalized:
                raise SourceRegistryError("Route ID already points to a different source")
            if current.get("target") == normalized:
                if current.get("purpose") == purpose:
                    return current
                raise SourceRegistryError("Source already linked with a different purpose; update it explicitly")
        record = {
            "id": source_id, "target": normalized, "purpose": purpose,
            "authority": authority, "mechanism": mechanism,
            "verified": verified, "verified_at": date.today().isoformat() if verified else None,
            "freshness_days": freshness_days,
            "related_ids": list(dict.fromkeys(related_ids)),
        }
        _atomic_json(self.path(project), {"sources": [*sources, record]})
        return record

    def validate(self, project: str | None) -> list[dict[str, str]]:
        issues = []
        sources = self.list(project)
        known_ids = {source.get("id") for source in sources}
        for source in sources:
            target = source.get("target")
            if source.get("mechanism") == "local_path" and (not isinstance(target, str) or not Path(target).exists()):
                issues.append({"id": str(source.get("id", "unknown")), "issue": "stale_local_target"})
            if any(item not in known_ids for item in source.get("related_ids", [])):
                issues.append({"id": str(source.get("id", "unknown")), "issue": "stale_relationship"})
            freshness = source.get("freshness_days")
            verified_at = source.get("verified_at")
            if isinstance(freshness, int) and isinstance(verified_at, str):
                try:
                    elapsed = (date.today() - date.fromisoformat(verified_at)).days
                except ValueError:
                    elapsed = freshness + 1
                if elapsed > freshness:
                    issues.append({"id": str(source.get("id", "unknown")), "issue": "stale_verification"})
        return issues

    def search(self, query: str, *, project: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        """Return route metadata only; never read target bodies."""
        stop = {"about", "from", "have", "into", "link", "route", "source", "where", "which", "this", "that", "with"}
        terms = {word for word in re.findall(r"[a-z0-9]+", query.lower()) if len(word) > 3 and word not in stop}
        if not terms or limit <= 0:
            return []
        candidates = [(project, item) for item in self.list(project)] if project else []
        if project:
            candidates.extend((None, item) for item in self.list(None))
        else:
            candidates = [(None, item) for item in self.list(None)]
        ranked = []
        seen_targets = set()
        for scope, source in candidates:
            target = source.get("target", "")
            if target in seen_targets or source.get("mechanism") == "local_path" and not Path(target).exists():
                continue
            haystack = " ".join((str(source.get("id", "")), str(source.get("purpose", "")), Path(target).name)).lower()
            matched = sum(term in haystack for term in terms)
            if matched:
                ranked.append((matched, scope is not None, {**source, "scope": scope or "global"}))
                seen_targets.add(target)
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]["id"]))
        return [item[2] for item in ranked[:limit]]
