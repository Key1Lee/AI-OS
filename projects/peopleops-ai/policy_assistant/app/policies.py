from dataclasses import dataclass
import hashlib
import json
import re

import yaml

from app.contracts import PolicyMetadata
from app.security import suspicious_instruction


@dataclass
class ParsedPolicy:
    metadata: PolicyMetadata
    source: str
    content_hash: str
    chunks: list[dict]


def chunk_sections(body: str, max_chars: int = 1200) -> list[dict]:
    """Split Markdown at headings, then split long sections at word boundaries. Each chunk retains its heading path and exact source text."""
    sections, path, lines = [], [], []
    for line in body.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            if any(s.strip() for s in lines):
                sections.append((" / ".join(path) or "Overview", "\n".join(lines).strip()))
            level, title = len(match[1]), match[2].strip()
            path = path[:level - 1] + [title]
            lines = []
        else:
            lines.append(line)
    if any(s.strip() for s in lines):
        sections.append((" / ".join(path) or "Overview", "\n".join(lines).strip()))
    chunks = []
    for section, text in sections:
        while text:
            end = len(text) if len(text) <= max_chars else text.rfind(" ", 0, max_chars + 1)
            if end <= 0:
                raise ValueError("Policy contains an overlong unbroken word")
            chunks.append({"section": section, "body": text[:end].strip(), "ordinal": len(chunks)})
            text = text[end:].strip()
    if not chunks or len(chunks) > 150:
        raise ValueError("A policy must contain 1–150 text chunks")
    return chunks


def parse_policy(document) -> ParsedPolicy:
    """Validate a Markdown policy and its YAML metadata before writing anything. A canonical hash makes equivalent deliveries idempotent."""
    markdown = document.markdown.replace("\r\n", "\n").strip()
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", markdown, re.S)
    if not match:
        raise ValueError("Policy requires YAML front matter between --- lines")
    metadata = PolicyMetadata.model_validate(yaml.safe_load(match[1]))
    body = match[2].strip()
    if suspicious_instruction(body) or suspicious_instruction(metadata.title) or "```" in body:
        raise ValueError("Policy contains executable content or instruction-like text; review it before publication")
    canonical = json.dumps(metadata.model_dump(mode="json"), sort_keys=True) + "\n" + body
    return ParsedPolicy(metadata, document.filename, hashlib.sha256(canonical.encode()).hexdigest(), chunk_sections(body))
